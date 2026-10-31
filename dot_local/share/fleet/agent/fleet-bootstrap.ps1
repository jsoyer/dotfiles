<#
.SYNOPSIS
    One-time setup of a Windows workstation for the fleet-updates agent. Run in an
    elevated PowerShell (Administrator). PowerShell 5.1.

.DESCRIPTION
    Nothing here runs by itself: Jerome reviews and launches it on each PC.

      1. OpenSSH Server capability + sshd service (automatic start)
      2. Firewall: port 22 reachable from the tailnet only (100.64.0.0/10); the
         default OpenSSH rule is disabled
      3. Agent installed in C:\ProgramData\fleet-agent (ACL: Administrators + SYSTEM
         only), staged then verified then moved into place
      4. administrators_authorized_keys: one line per master with a FORCED COMMAND
         and `restrict`; ACL Administrators + SYSTEM only; other lines are kept
      5. Event Log source fleet-agent (refusals and job results are logged there)
      6. Scheduled tasks: fleet-agent-update (detached update, interactive user's
         context, 120 min limit) and, with -EnablePull, fleet-agent-pull (SYSTEM,
         starts the update task; never restarts)
      7. winget check (reported, not fixed)

    Public keys are passed in (read them from 1Password with the op CLI:
    op://Private/Fleet/public-key-<master>); this script never reads a secret.
    Tailscale SSH must stay OFF on this PC: it bypasses the forced command.

.PARAMETER MasterKey
    Hashtable master name -> ssh-ed25519 public key line, e.g.
    @{ diabolo = 'ssh-ed25519 AAAA...'; penelope = 'ssh-ed25519 AAAA...' }

.PARAMETER TaskUser
    Account of the interactive session in which winget and Scoop run
    (default: the account running this script).

.PARAMETER EnablePull
    Opt this PC in to pull mode (marker file + scheduled task).

.PARAMETER AgentSource
    Path of fleet-agent.ps1 to install (default: next to this script).

.PARAMETER ProgramDataRoot
    Override of %ProgramData% (tests only).
#>
param(
    [Parameter(Mandatory = $true)]
    [hashtable]$MasterKey,
    [string]$TaskUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name,
    [switch]$EnablePull,
    [string]$AgentSource = (Join-Path $PSScriptRoot 'fleet-agent.ps1'),
    [string]$ProgramDataRoot = $env:ProgramData
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

$agentRoot = Join-Path $ProgramDataRoot 'fleet-agent'
$agentDest = Join-Path $agentRoot 'fleet-agent.ps1'
$stateDir = Join-Path $agentRoot 'state'
$keysFile = Join-Path (Join-Path $ProgramDataRoot 'ssh') 'administrators_authorized_keys'
$forcedCommand = 'powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File ' + $agentDest
$keyPattern = '^ssh-ed25519 AAAA[A-Za-z0-9+/=]{20,} ?[A-Za-z0-9._@-]{0,64}$'
$namePattern = '^[a-z0-9][a-z0-9-]{0,30}$'

function Write-Step {
    param([string]$Message)
    [Console]::Out.WriteLine('fleet-bootstrap: ' + $Message)
}

function Test-Administrator {
    $principal = New-Object System.Security.Principal.WindowsPrincipal([System.Security.Principal.WindowsIdentity]::GetCurrent())
    return $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Replaces inherited permissions by Administrators + SYSTEM (full control) only.
function Protect-AclAdminOnly {
    param([string]$Path)
    $acl = Get-Acl -LiteralPath $Path
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($rule in @($acl.Access)) { [void]$acl.RemoveAccessRule($rule) }
    $inherit = [System.Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit'
    $isDir = (Get-Item -LiteralPath $Path).PSIsContainer
    foreach ($sid in @('S-1-5-32-544', 'S-1-5-18')) {
        $account = (New-Object System.Security.Principal.SecurityIdentifier($sid)).Translate([System.Security.Principal.NTAccount])
        if ($isDir) {
            $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($account, 'FullControl', $inherit, 'None', 'Allow')
        }
        else {
            $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($account, 'FullControl', 'Allow')
        }
        $acl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $Path -AclObject $acl
}

# Fails if anything other than Administrators / SYSTEM can touch the path.
function Assert-AclAdminOnly {
    param([string]$Path)
    $allowed = @('S-1-5-32-544', 'S-1-5-18')
    foreach ($rule in (Get-Acl -LiteralPath $Path).Access) {
        $sid = $rule.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value
        if ($allowed -notcontains $sid) { throw ('unexpected ACL entry on {0}: {1}' -f $Path, $rule.IdentityReference) }
    }
}

function Install-AgentFile {
    if (-not (Test-Path -LiteralPath $AgentSource)) { throw ('agent source not found: ' + $AgentSource) }
    foreach ($dir in @($agentRoot, $stateDir)) {
        if (-not (Test-Path -LiteralPath $dir)) { [void](New-Item -ItemType Directory -Path $dir -Force) }
        Protect-AclAdminOnly -Path $dir
    }
    # Stage, verify, then move into place: a half-written agent is never the forced command.
    $staged = $agentDest + '.new'
    Copy-Item -LiteralPath $AgentSource -Destination $staged -Force
    Protect-AclAdminOnly -Path $staged
    $want = (Get-FileHash -LiteralPath $AgentSource -Algorithm SHA256).Hash
    $got = (Get-FileHash -LiteralPath $staged -Algorithm SHA256).Hash
    if ($want -ne $got) { throw 'staged agent hash mismatch' }
    Move-Item -LiteralPath $staged -Destination $agentDest -Force
    Assert-AclAdminOnly -Path $agentDest
    Write-Step ('agent installed: ' + $agentDest)
}

function Install-OpenSshServer {
    $cap = Get-WindowsCapability -Online -Name 'OpenSSH.Server*' | Select-Object -First 1
    if ($null -ne $cap -and $cap.State -ne 'Installed') {
        [void](Add-WindowsCapability -Online -Name $cap.Name)
    }
    Set-Service -Name sshd -StartupType Automatic
    if ((Get-Service -Name sshd).Status -ne 'Running') { Start-Service -Name sshd }
    Write-Step 'OpenSSH Server installed, sshd automatic and running'
}

function Initialize-SshFirewall {
    $rule = 'fleet-sshd-tailnet'
    if (Get-NetFirewallRule -Name $rule -ErrorAction SilentlyContinue) { Remove-NetFirewallRule -Name $rule }
    [void](New-NetFirewallRule -Name $rule -DisplayName 'fleet agent SSH (tailnet only)' -Direction Inbound `
            -Protocol TCP -LocalPort 22 -Action Allow -RemoteAddress '100.64.0.0/10' -Profile Any)
    # The stock rule allows port 22 from anywhere: disable it so only the tailnet rule applies.
    $stock = Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue
    if ($null -ne $stock) { Disable-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' }
    Write-Step 'firewall: port 22 limited to 100.64.0.0/10'
}

function Write-AuthorizedKey {
    $lines = @()
    foreach ($name in ($MasterKey.Keys | Sort-Object)) {
        $key = ([string]$MasterKey[$name]).Trim()
        if ([string]$name -notmatch $namePattern) { throw ('invalid master name: ' + $name) }
        if ($key -notmatch $keyPattern) { throw ('invalid public key for ' + $name) }
        $keyOnly = ($key -split ' ')[0..1] -join ' '
        $lines += ('restrict,command="{0}" {1} fleet-master-{2}' -f $forcedCommand, $keyOnly, $name)
    }
    $kept = @()
    if (Test-Path -LiteralPath $keysFile) {
        $kept = @(Get-Content -LiteralPath $keysFile | Where-Object { $_ -notmatch ' fleet-master-[a-z0-9-]+$' })
    }
    $sshDir = Split-Path -Parent $keysFile
    if (-not (Test-Path -LiteralPath $sshDir)) { [void](New-Item -ItemType Directory -Path $sshDir -Force) }
    $staged = $keysFile + '.new'
    [System.IO.File]::WriteAllLines($staged, [string[]]($kept + $lines), (New-Object System.Text.UTF8Encoding($false)))
    Protect-AclAdminOnly -Path $staged
    Assert-AclAdminOnly -Path $staged
    Move-Item -LiteralPath $staged -Destination $keysFile -Force
    Assert-AclAdminOnly -Path $keysFile
    $cfg = Join-Path $sshDir 'sshd_config'
    if ((Test-Path -LiteralPath $cfg) -and -not (Select-String -LiteralPath $cfg -Pattern 'administrators_authorized_keys' -Quiet)) {
        [Console]::Error.WriteLine('fleet-bootstrap: WARNING sshd_config does not reference administrators_authorized_keys; check the Match Group administrators block')
    }
    Write-Step ('authorized keys written with forced command for: ' + (($MasterKey.Keys | Sort-Object) -join ', '))
}

function Register-AgentEventSource {
    if (-not [System.Diagnostics.EventLog]::SourceExists('fleet-agent')) {
        New-EventLog -LogName Application -Source 'fleet-agent'
    }
    Write-Step 'event log source fleet-agent ready'
}

function Register-AgentTask {
    $psExe = 'powershell.exe'
    $baseArgs = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File ' + $agentDest

    # Detached update: the interactive user's context (winget and Scoop fail under SSH / SYSTEM).
    $updateAction = New-ScheduledTaskAction -Execute $psExe -Argument ($baseArgs + ' -RunJob')
    $updatePrincipal = New-ScheduledTaskPrincipal -UserId $TaskUser -LogonType Interactive -RunLevel Highest
    $updateSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 120) -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName 'fleet-agent-update' -Action $updateAction -Principal $updatePrincipal `
        -Settings $updateSettings -Force | Out-Null
    Write-Step ('scheduled task fleet-agent-update registered for ' + $TaskUser)

    if ($EnablePull) {
        [System.IO.File]::WriteAllText((Join-Path $agentRoot 'pull-enabled'), '')
        $pullAction = New-ScheduledTaskAction -Execute $psExe -Argument ($baseArgs + ' -RunPull')
        $pullTriggers = @(
            (New-ScheduledTaskTrigger -Daily -At '12:00'),
            (New-ScheduledTaskTrigger -AtLogOn)
        )
        $pullPrincipal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
        $pullSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable `
            -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
        Register-ScheduledTask -TaskName 'fleet-agent-pull' -Action $pullAction -Trigger $pullTriggers `
            -Principal $pullPrincipal -Settings $pullSettings -Force | Out-Null
        Write-Step 'pull mode enabled: scheduled task fleet-agent-pull (never restarts)'
    }
}

function Test-WingetAvailable {
    $pkg = Get-AppxPackage -AllUsers -Name 'Microsoft.DesktopAppInstaller' -ErrorAction SilentlyContinue
    if ($null -eq $pkg) {
        [Console]::Error.WriteLine('fleet-bootstrap: WARNING winget (App Installer) not found; the winget step will be skipped')
        return
    }
    Write-Step ('winget (App Installer) present: ' + $pkg[0].Version)
}

function Test-TailscaleSshOff {
    $ts = Get-Command -Name 'tailscale.exe' -ErrorAction SilentlyContinue
    if ($null -eq $ts) { return }
    $prefs = (& $ts.Source debug prefs 2>$null) -join ' '
    if ($prefs -match '"RunSSH":\s*true') {
        [Console]::Error.WriteLine('fleet-bootstrap: WARNING Tailscale SSH is ON; turn it off (tailscale set --ssh=false), it bypasses the forced command')
    }
}

if (-not (Test-Administrator)) { throw 'run this script in an elevated PowerShell (Administrator)' }
Install-AgentFile
Install-OpenSshServer
Initialize-SshFirewall
Write-AuthorizedKey
Register-AgentEventSource
Register-AgentTask
Test-WingetAvailable
Test-TailscaleSshOff
Write-Step 'done'
