<#
.SYNOPSIS
    fleet-agent (Windows) - agent of the fleet-updates system. PowerShell 5.1.

.DESCRIPTION
    Installed by fleet-bootstrap.ps1 as C:\ProgramData\fleet-agent\fleet-agent.ps1
    (writable by Administrators and SYSTEM only) and referenced ONLY by the forced
    command of administrators_authorized_keys:

        restrict,command="C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File \"C:\ProgramData\fleet-agent\fleet-agent.ps1\"" ssh-ed25519 AAAA... fleet-master-<master>

    sshd puts what the master asked for in SSH_ORIGINAL_COMMAND. It is UNTRUSTED:
    exactly one of five verbs, alone, is accepted. Anything else (unknown verb,
    extra argument, empty = interactive shell attempt) exits 1, writes the refusal
    to the Event Log (source fleet-agent) and runs nothing.

        check          read-only: pending updates, health, reboot state
        update         start a DETACHED update (scheduled task in the interactive
                       user's context); returns status "started" + job id at once
        reboot-status  is a restart required
        reboot         restart only if required
        report         final (or current) state of the last update job, from disk

    Output: exactly one JSON line, schema v1 (same shape and status vocabulary as
    the Unix agent). Exit codes: 0 success, 1 refused, 2 update failed, 3 busy.

    Two LOCAL-ONLY entries exist, selected by script switches that the forced
    command never passes (the client cannot add arguments to a forced command) and
    that are refused when SSH_CONNECTION or SSH_ORIGINAL_COMMAND is set:
        -RunJob    the detached update, started by the scheduled task fleet-agent-update
        -RunPull   pull mode (catch-up update, never a restart), started by the
                   scheduled task fleet-agent-pull

    winget and Scoop misbehave under SSH or SYSTEM, so the whole update runs in
    the scheduled task, in the interactive user's context.
#>
param(
    [switch]$RunJob,
    [switch]$RunPull
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

# ------------------------------------------------------------------ constants

$script:Verbs = @('check', 'update', 'reboot-status', 'reboot', 'report')
$script:TestMode = ($env:FLEET_AGENT_TEST -eq '1')
$script:AgentRoot = Join-Path $env:ProgramData 'fleet-agent'
# Test overrides are honoured ONLY with FLEET_AGENT_TEST=1 AND a path under $env:TEMP;
# anything else is ignored (and reported on stderr).
function Get-TestOverridePath {
    param([string]$Name, [string]$Default)
    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrEmpty($value)) { return $Default }
    if (-not $script:TestMode) {
        [Console]::Error.WriteLine('fleet-agent: ignoring ' + $Name + ' (not in test mode)')
        return $Default
    }
    $tempRoot = [System.IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
    $full = [System.IO.Path]::GetFullPath($value)
    if (-not $full.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        [Console]::Error.WriteLine('fleet-agent: ignoring ' + $Name + ' (not under TEMP)')
        return $Default
    }
    return $full
}
$script:StateDir = Get-TestOverridePath -Name 'FLEET_AGENT_STATE_DIR' -Default (Join-Path $script:AgentRoot 'state')
$script:ConfDir = Get-TestOverridePath -Name 'FLEET_AGENT_CONF_DIR' -Default $script:AgentRoot
$script:AgentLogMaxBytes = 1048576
$script:JobsDir = Join-Path $script:StateDir 'jobs'
$script:LockFile = Join-Path $script:StateDir 'update.lock'
$script:HostName = $env:COMPUTERNAME.ToLowerInvariant()
$script:EventSource = 'fleet-agent'
$script:UpdateTask = 'fleet-agent-update'
$script:PullDays = 7
$script:MaskText = '[MASKED]'
$script:LogCapChars = 4000
$script:R = $null
$script:JobTimedOut = $false
$script:JobDeadline = [DateTime]::MaxValue
$script:JobMaxMinutes = 120
$script:ExtraArgs = @($args)

# ------------------------------------------------------------------ utilities

function Get-NowIso {
    return (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
}

function Get-SafeLine {
    param([string]$Text, [int]$Max = 200)
    if ($null -eq $Text) { return '' }
    $clean = ($Text -replace '[^\x20-\x7E]', '')
    if ($clean.Length -gt $Max) { $clean = $clean.Substring(0, $Max) }
    return $clean
}

function Write-AgentLog {
    param(
        [string]$Message,
        [ValidateSet('Information', 'Warning', 'Error')][string]$Level = 'Information',
        [int]$EventId = 4000
    )
    $line = Get-SafeLine -Text $Message -Max 500
    try {
        Write-EventLog -LogName Application -Source $script:EventSource -EntryType $Level -EventId $EventId -Message $line
    }
    catch {
        # Event source missing (bootstrap not run): fall back to a file, never fail on logging.
        try {
            if (-not (Test-Path -LiteralPath $script:StateDir)) { [void](New-Item -ItemType Directory -Path $script:StateDir -Force) }
            $logPath = Join-Path $script:StateDir 'agent.log'
            if ((Test-Path -LiteralPath $logPath) -and ((Get-Item -LiteralPath $logPath).Length -gt $script:AgentLogMaxBytes)) {
                Move-Item -LiteralPath $logPath -Destination ($logPath + '.1') -Force
            }
            Add-Content -LiteralPath $logPath -Value ('{0} {1} {2}' -f (Get-NowIso), $Level, $line)
        }
        catch {
            [Console]::Error.WriteLine('fleet-agent: log unavailable')
        }
    }
}

function Get-ClientAddress {
    $conn = $env:SSH_CONNECTION
    if ([string]::IsNullOrEmpty($conn)) { return 'none' }
    return (Get-SafeLine -Text ($conn -split ' ')[0] -Max 45)
}

function Test-SshContext {
    $origin = [Environment]::GetEnvironmentVariable('SSH_ORIGINAL_COMMAND')
    return (-not [string]::IsNullOrEmpty($env:SSH_CONNECTION)) -or ($null -ne $origin)
}

function Exit-AgentRefused {
    param([string]$What)
    Write-AgentLog -Message ('REFUSED: {0} client={1}' -f $What, (Get-ClientAddress)) -Level Warning -EventId 4001
    [Console]::Error.WriteLine('fleet-agent: refused')
    exit 1
}

# ------------------------------------------------------------------ secret masking
# Masking is applied to DATA STRUCTURES (values and dictionary keys) before they
# are serialized, never to the serialized JSON text.

function Protect-Text {
    param([string]$Text)
    if ([string]::IsNullOrEmpty($Text)) { return $Text }
    $out = $Text -replace '\x1b\[[0-9;?]*[ -/]*[@-~]', ''
    $out = $out -replace '[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', ''
    $out = [regex]::Replace($out, '(?s)-----BEGIN [A-Z ]{0,40}PRIVATE KEY-----.*?(-----END [A-Z ]{0,40}PRIVATE KEY-----|\z)', '[MASKED PRIVATE KEY]')
    $out = [regex]::Replace($out, '([A-Za-z][A-Za-z0-9+.-]{0,31}://[^\s:/@]{1,256}:)\S{1,512}@', '$1[MASKED]@')
    $out = [regex]::Replace($out, 'tk_[A-Za-z0-9_-]{6,}', $script:MaskText)
    $out = [regex]::Replace($out, 'eyJ[A-Za-z0-9_-]{6,}(\.[A-Za-z0-9_-]*)*', $script:MaskText)
    $out = [regex]::Replace($out, '(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}', '$1 [MASKED]')
    $out = [regex]::Replace($out, '(?i)((?:password|passwd|passphrase|secret|token|api[_-]?key)[A-Za-z0-9_.-]*\s*[=:]\s*)\S+', '$1[MASKED]')
    return $out
}

function Protect-Data {
    param($Value)
    if ($null -eq $Value) { return $null }
    if ($Value -is [string]) { return (Protect-Text -Text $Value) }
    if ($Value -is [System.Collections.IDictionary]) {
        $dict = [ordered]@{}
        foreach ($key in $Value.Keys) {
            $safeKey = Protect-Text -Text ([string]$key)
            if ([string]$key -match '(?i)password|passwd|passphrase|secret|token|api[_-]?key') {
                $dict[$safeKey] = $script:MaskText
            }
            else {
                $dict[$safeKey] = Protect-Data -Value $Value[$key]
            }
        }
        return $dict
    }
    if ($Value -is [System.Collections.IEnumerable]) {
        $items = New-Object System.Collections.ArrayList
        foreach ($item in $Value) { [void]$items.Add((Protect-Data -Value $item)) }
        return , $items.ToArray()
    }
    return $Value
}

# ------------------------------------------------------------------ result (JSON v1)

function Initialize-AgentResult {
    $empty = [ordered]@{
        failed_units           = @()
        unhealthy_containers   = @()
        disk_free_pct          = [ordered]@{}
        critical_services_down = @()
    }
    $script:R = [ordered]@{
        schema           = 1
        host             = $script:HostName
        verb             = ''
        status           = 'failed'
        reason           = $null
        packages         = $null
        changes          = @()
        health_before    = $empty
        health_after     = $empty
        preflight        = [ordered]@{ ok = $true; blocked_by = $null }
        config_conflicts = @()
        job              = $null
        reboot_required  = $false
        reboot_since     = $null
        os               = $null
        kernel           = $null
        major_available  = $null
        started          = (Get-NowIso)
        ended            = $null
        log_tail         = ''
    }
}

# `ended` is stamped only when the result is final (-Final); the in-progress state.json of a
# running job keeps it null.
function Get-ResultJson {
    param([string]$Verb, [switch]$Final)
    $script:R['verb'] = $Verb
    if ($Final -and $null -eq $script:R['ended']) { $script:R['ended'] = Get-NowIso }
    foreach ($arrayKey in @('changes', 'config_conflicts')) { $script:R[$arrayKey] = @($script:R[$arrayKey]) }
    if ($null -eq $script:R['os']) {
        try {
            $os = Get-CimInstance -ClassName Win32_OperatingSystem
            $script:R['os'] = ('{0} {1}' -f $os.Caption, $os.Version)
        }
        catch {
            $script:R['os'] = 'Windows'
        }
    }
    if ($null -eq $script:R['kernel']) { $script:R['kernel'] = [Environment]::OSVersion.Version.ToString() }
    $safe = Protect-Data -Value $script:R
    return [string](ConvertTo-Json -InputObject $safe -Depth 8 -Compress)
}

function Get-ExitCodeFor {
    param([string]$Status)
    switch ($Status) {
        'failed' { return 2 }
        'busy' { return 3 }
        default { return 0 }
    }
}

function Complete-AgentVerb {
    param([string]$Verb)
    $inProgress = (@('started', 'running') -contains [string]$script:R['status'])
    if ($inProgress) { [Console]::Out.WriteLine((Get-ResultJson -Verb $Verb)) }
    else { [Console]::Out.WriteLine((Get-ResultJson -Verb $Verb -Final)) }
    exit (Get-ExitCodeFor -Status ([string]$script:R['status']))
}

function Save-JobState {
    param([string]$JobDir, [switch]$Final)
    $tmp = Join-Path $JobDir 'state.json.tmp'
    $final = Join-Path $JobDir 'state.json'
    if ($Final) { $json = Get-ResultJson -Verb 'update' -Final }
    else { $json = Get-ResultJson -Verb 'update' }
    [System.IO.File]::WriteAllText($tmp, $json, (New-Object System.Text.UTF8Encoding($false)))
    Move-Item -LiteralPath $tmp -Destination $final -Force
}

# ------------------------------------------------------------------ capped process runner

function Get-CappedTail {
    param([string]$Path, [int]$Lines = 200)
    if (-not (Test-Path -LiteralPath $Path)) { return '' }
    $text = (@(Get-Content -LiteralPath $Path -Tail $Lines -Encoding UTF8 -ErrorAction SilentlyContinue) -join "`n")
    if ($text.Length -gt $script:LogCapChars) { $text = $text.Substring($text.Length - $script:LogCapChars) }
    return $text
}

# Runs a program with stdout AND stderr redirected to temp files; only a capped,
# masked tail of each is kept in the job log. Returns the exit code (124 = timeout).
function Invoke-CappedProcess {
    param(
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$LogPath,
        [int]$TimeoutMinutes = 60
    )
    $outFile = [System.IO.Path]::GetTempFileName()
    $errFile = [System.IO.Path]::GetTempFileName()
    $code = 1
    try {
        $proc = Start-Process -FilePath $FilePath -ArgumentList $ArgumentList -NoNewWindow -PassThru `
            -RedirectStandardOutput $outFile -RedirectStandardError $errFile
        $remainingMs = [int][math]::Max(1000, [math]::Min([double]($TimeoutMinutes * 60000), ($script:JobDeadline - (Get-Date)).TotalMilliseconds))
        if ($proc.WaitForExit($remainingMs)) {
            $code = $proc.ExitCode
        }
        else {
            # Kill the whole tree (winget spawns installers), not only the direct child.
            & taskkill.exe /T /F /PID $proc.Id 2>&1 | Out-Null
            $script:JobTimedOut = $true
            $code = 124
        }
        $header = '--- {0} {1} (exit {2})' -f (Split-Path -Leaf $FilePath), ($ArgumentList -join ' '), $code
        $body = (Get-CappedTail -Path $outFile) + "`n" + (Get-CappedTail -Path $errFile)
        Add-Content -LiteralPath $LogPath -Value (Protect-Text -Text ($header + "`n" + $body))
    }
    finally {
        Remove-Item -LiteralPath $outFile, $errFile -Force -ErrorAction SilentlyContinue
    }
    return $code
}

# ------------------------------------------------------------------ probes

function Get-DiskFreePct {
    $drive = Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DeviceID='C:'"
    if ($null -eq $drive -or $drive.Size -le 0) { return 100 }
    return [int][math]::Floor(100 * $drive.FreeSpace / $drive.Size)
}

function Test-OnBattery {
    try {
        $bat = @(Get-CimInstance -ClassName Win32_Battery)
        foreach ($b in $bat) { if ($b.BatteryStatus -eq 1) { return $true } }
    }
    catch {
        return $false
    }
    return $false
}

function Test-MeteredNetwork {
    try {
        [void][Windows.Networking.Connectivity.NetworkInformation, Windows.Networking.Connectivity, ContentType = WindowsRuntime]
        $connProfile = [Windows.Networking.Connectivity.NetworkInformation]::GetInternetConnectionProfile()
        if ($null -eq $connProfile) { return $false }
        $cost = [int]$connProfile.GetConnectionCost().NetworkCostType
        return ($cost -eq 2 -or $cost -eq 3)
    }
    catch {
        return $false
    }
}

# Interactive sessions of the machine: Any = someone is logged on (needed by the
# scheduled task), Active = input within the last 5 minutes (do not disturb).
function Get-SessionInfo {
    $info = @{ Any = $false; Active = $false }
    try {
        $lines = @(& quser.exe 2>$null)
        foreach ($line in ($lines | Select-Object -Skip 1)) {
            $parts = @(($line.Trim().TrimStart('>')) -split '\s{2,}')
            if ($parts.Count -lt 4) { continue }
            $info['Any'] = $true
            $idle = $parts[$parts.Count - 2]
            if ($idle -eq '.' -or $idle -eq 'none' -or $idle -match '^[0-4]$') { $info['Active'] = $true }
        }
    }
    catch {
        return $info
    }
    return $info
}

function Test-UpdateInProgress {
    $busy = @(Get-Process -Name 'TiWorker', 'winget', 'WindowsUpdateBox' -ErrorAction SilentlyContinue)
    return ($busy.Count -gt 0)
}

function Get-Preflight {
    param([switch]$ForUpdate)
    $blocked = $null
    if ((Get-DiskFreePct) -lt 10) { $blocked = 'disk_low' }
    if ($null -eq $blocked -and (Test-OnBattery)) { $blocked = 'on_battery' }
    if ($null -eq $blocked -and (Test-MeteredNetwork)) { $blocked = 'metered_network' }
    if ($null -eq $blocked -and (Test-UpdateInProgress)) { $blocked = 'update_in_progress' }
    if ($null -eq $blocked -and $ForUpdate) {
        $sessions = Get-SessionInfo
        if ($sessions['Active']) { $blocked = 'user_active' }
        elseif (-not $sessions['Any']) { $blocked = 'no_interactive_session' }
    }
    $script:R['preflight'] = [ordered]@{ ok = ($null -eq $blocked); blocked_by = $blocked }
    return $blocked
}

function Get-HealthSnapshot {
    $down = @()
    $listFile = Join-Path $script:ConfDir 'critical-services'
    if (Test-Path -LiteralPath $listFile) {
        foreach ($name in (Get-Content -LiteralPath $listFile)) {
            if ($name -notmatch '^[A-Za-z0-9_.@-]+$') { continue }
            $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
            if ($null -ne $svc -and $svc.Status -ne 'Running') { $down += $name }
        }
    }
    return [ordered]@{
        failed_units           = @()
        unhealthy_containers   = @()
        disk_free_pct          = [ordered]@{ 'C:' = [int](Get-DiskFreePct) }
        critical_services_down = @($down)
    }
}

function Test-RebootPending {
    $keys = @(
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending',
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired'
    )
    foreach ($key in $keys) { if (Test-Path -LiteralPath $key) { return $true } }
    return $false
}

function Get-WindowsUpdateSearch {
    $session = New-Object -ComObject 'Microsoft.Update.Session'
    $searcher = $session.CreateUpdateSearcher()
    return @{ Session = $session; Result = $searcher.Search("IsInstalled=0 and IsHidden=0 and Type='Software'") }
}

function Test-FeatureUpdate {
    param($Update)
    foreach ($cat in $Update.Categories) { if ($cat.Name -eq 'Upgrades') { return $true } }
    return $false
}

# ------------------------------------------------------------------ lock (atomic CreateNew)

function Enter-AgentLock {
    param([string]$Owner)
    if (-not (Test-Path -LiteralPath $script:StateDir)) { [void](New-Item -ItemType Directory -Path $script:StateDir -Force) }
    for ($attempt = 0; $attempt -lt 3; $attempt++) {
        try {
            $stream = [System.IO.File]::Open($script:LockFile, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
            $bytes = [System.Text.Encoding]::ASCII.GetBytes(('{0}|{1}|{2}' -f $PID, $Owner, [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()))
            $stream.Write($bytes, 0, $bytes.Length)
            $stream.Close()
            return $true
        }
        catch [System.IO.IOException] {
            if (Test-LockAlive) { return $false }
            # Stale takeover, serialized by a machine-wide named mutex: without it, contender A could
            # move the stale lock aside and create its live lock, and contender B (which judged the
            # old lock stale earlier) would then move A's LIVE lock away. Staleness is re-checked
            # inside the mutex, so B sees A's live lock and backs off.
            $mutex = New-Object System.Threading.Mutex($false, 'Global\fleet-agent-lock-takeover')
            $held = $false
            try {
                try { $held = $mutex.WaitOne(15000) }
                catch [System.Threading.AbandonedMutexException] { $held = $true }
                if (-not $held) {
                    Write-AgentLog -Message 'lock: stale takeover mutex timeout' -EventId 4003
                    return $false
                }
                if (Test-LockAlive) { return $false }
                $aside = $script:LockFile + '.stale-' + [Guid]::NewGuid().ToString('N')
                try {
                    [System.IO.File]::Move($script:LockFile, $aside)
                    Remove-Item -LiteralPath $aside -Force -ErrorAction SilentlyContinue
                }
                catch {
                    Write-AgentLog -Message 'lock: stale takeover lost the race' -EventId 4003
                }
            }
            finally {
                if ($held) { $mutex.ReleaseMutex() }
                $mutex.Dispose()
            }
        }
    }
    return $false
}

# A lock owned by a job id stays alive while that job's state.json says started/running and
# was written less than 10 minutes ago (hand-off window before the job takes the lock over).
function Test-JobOwnerAlive {
    param([string]$Owner)
    if ($Owner -notmatch '^[0-9]{8}T[0-9]{6}Z-[0-9]+$') { return $false }
    $stateFile = Join-Path (Join-Path $script:JobsDir $Owner) 'state.json'
    if (-not (Test-Path -LiteralPath $stateFile)) { return $false }
    try {
        $state = ConvertFrom-Json -InputObject ([System.IO.File]::ReadAllText($stateFile))
        $young = ((Get-Item -LiteralPath $stateFile).LastWriteTimeUtc -gt (Get-Date).ToUniversalTime().AddMinutes(-10))
        return (($state.status -eq 'started' -or $state.status -eq 'running') -and $young)
    }
    catch {
        return $false
    }
}

function Test-LockAlive {
    if (-not (Test-Path -LiteralPath $script:LockFile)) { return $false }
    try {
        $parts = ([System.IO.File]::ReadAllText($script:LockFile)) -split '\|'
        $age = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - [int64]$parts[2]
        if ($age -lt 120) { return $true }
        if (Test-JobOwnerAlive -Owner $parts[1]) { return $true }
        return ($null -ne (Get-Process -Id ([int]$parts[0]) -ErrorAction SilentlyContinue))
    }
    catch {
        # Unreadable: another process is writing it right now, or it is garbage.
        return ((Get-Item -LiteralPath $script:LockFile).LastWriteTimeUtc -gt (Get-Date).ToUniversalTime().AddMinutes(-2))
    }
}

function Get-LockOwner {
    try {
        return (([System.IO.File]::ReadAllText($script:LockFile)) -split '\|')[1]
    }
    catch {
        return ''
    }
}

function Exit-AgentLock {
    Remove-Item -LiteralPath $script:LockFile -Force -ErrorAction SilentlyContinue
}

# ------------------------------------------------------------------ verbs

function Invoke-VerbCheck {
    Initialize-AgentResult
    $script:R['health_before'] = Get-HealthSnapshot
    $script:R['health_after'] = $script:R['health_before']
    if (Test-LockAlive) {
        $script:R['status'] = 'running'
        $script:R['reason'] = 'update_in_progress'
        Complete-AgentVerb -Verb 'check'
    }
    $blocked = Get-Preflight
    $script:R['reboot_required'] = Test-RebootPending
    try {
        $found = (Get-WindowsUpdateSearch)['Result']
        $pending = [int]$found.Updates.Count
        foreach ($u in $found.Updates) {
            if (Test-FeatureUpdate -Update $u) { $script:R['major_available'] = [string]$u.Title }
        }
        # winget is not queried here: it misbehaves under SSH (see the update task).
        $script:R['packages'] = $pending
        if ($pending -eq 0) {
            $script:R['status'] = 'up-to-date'
        }
        else {
            $script:R['status'] = 'skipped'
            $script:R['reason'] = $(if ($null -ne $blocked) { $blocked } else { 'updates_pending' })
        }
    }
    catch {
        $script:R['status'] = 'failed'
        $script:R['reason'] = 'check_failed'
        $script:R['packages'] = $null
    }
    Complete-AgentVerb -Verb 'check'
}

function Invoke-VerbRebootStatus {
    Initialize-AgentResult
    $script:R['reboot_required'] = Test-RebootPending
    if (Test-LockAlive) {
        $script:R['status'] = 'running'
        $script:R['reason'] = 'update_in_progress'
    }
    else {
        $script:R['status'] = 'up-to-date'
        $script:R['reason'] = $(if ($script:R['reboot_required']) { 'reboot_required' } else { 'no_reboot_required' })
    }
    Complete-AgentVerb -Verb 'reboot-status'
}

function Invoke-VerbReboot {
    Initialize-AgentResult
    if (-not (Enter-AgentLock -Owner 'reboot')) {
        $script:R['status'] = 'busy'
        $script:R['reason'] = 'update_in_progress'
        Complete-AgentVerb -Verb 'reboot'
    }
    try {
        $script:R['reboot_required'] = Test-RebootPending
        if (-not $script:R['reboot_required']) {
            $script:R['status'] = 'skipped'
            $script:R['reason'] = 'no_reboot_required'
        }
        else {
            Write-AgentLog -Message 'reboot requested and required: restarting in 30s' -EventId 4002
            $script:R['status'] = 'started'
            $script:R['reason'] = 'rebooting'
            # Delayed, so this answer reaches the master before the host goes down.
            & shutdown.exe /r /t 30 /c 'fleet-agent: restart required after updates'
            if ($LASTEXITCODE -ne 0) {
                $script:R['status'] = 'failed'
                $script:R['reason'] = 'shutdown_failed'
                Write-AgentLog -Message ('restart command failed with exit code {0}' -f $LASTEXITCODE) -Level Error -EventId 4001
            }
        }
    }
    finally {
        Exit-AgentLock
    }
    Complete-AgentVerb -Verb 'reboot'
}

function Invoke-VerbReport {
    Initialize-AgentResult
    $lastFile = Join-Path $script:StateDir 'last-job'
    $job = $null
    if (Test-Path -LiteralPath $lastFile) { $job = (Get-Content -LiteralPath $lastFile -TotalCount 1) }
    if ([string]::IsNullOrEmpty($job) -or $job -notmatch '^[0-9]{8}T[0-9]{6}Z-[0-9]+$' -or
        -not (Test-Path -LiteralPath (Join-Path (Join-Path $script:JobsDir $job) 'state.json'))) {
        $script:R['status'] = 'skipped'
        $script:R['reason'] = 'no_job'
        Complete-AgentVerb -Verb 'report'
    }
    $stateFile = Join-Path (Join-Path $script:JobsDir $job) 'state.json'
    try {
        $raw = [System.IO.File]::ReadAllText($stateFile)
        $state = ConvertFrom-Json -InputObject $raw
        if ($null -eq $state -or $null -eq $state.status) { throw 'no status' }
    }
    catch {
        $script:R['job'] = $job
        $script:R['status'] = 'failed'
        $script:R['reason'] = 'state_unreadable'
        Complete-AgentVerb -Verb 'report'
    }
    if (($state.status -eq 'started' -or $state.status -eq 'running') -and -not (Test-LockAlive)) {
        $script:R['job'] = $job
        $script:R['status'] = 'failed'
        $script:R['reason'] = 'job_died'
        Complete-AgentVerb -Verb 'report'
    }
    # Re-emit the stored state with the verb "report" (it was already masked when written).
    [Console]::Out.WriteLine($raw.Replace('"verb":"update"', '"verb":"report"'))
    exit (Get-ExitCodeFor -Status ([string]$state.status))
}

function Get-NewJobId {
    return ('{0}-{1}' -f (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ'), $PID)
}

# Shared by the update verb and the pull entry. Never reaches the restart code.
function Invoke-StartUpdate {
    param([switch]$FromPull)
    Initialize-AgentResult
    $job = Get-NewJobId
    if (-not (Enter-AgentLock -Owner $job)) {
        $script:R['status'] = 'busy'
        $script:R['reason'] = 'update_in_progress'
        Complete-AgentVerb -Verb 'update'
    }
    $handoff = $false
    try {
        $blocked = Get-Preflight -ForUpdate
        if ($null -ne $blocked) {
            $script:R['status'] = 'skipped'
            $script:R['reason'] = $blocked
            Complete-AgentVerb -Verb 'update'
        }
        $jobDir = Join-Path $script:JobsDir $job
        [void](New-Item -ItemType Directory -Path $jobDir -Force)
        Get-ChildItem -LiteralPath $script:JobsDir -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-31) } |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        $script:R['health_before'] = Get-HealthSnapshot
        $script:R['health_after'] = $script:R['health_before']
        $script:R['job'] = $job
        $script:R['status'] = 'started'
        $script:R['reboot_required'] = Test-RebootPending
        Set-Content -LiteralPath (Join-Path $jobDir 'started') -Value $script:R['started']
        if ($FromPull) { Set-Content -LiteralPath (Join-Path $jobDir 'pull') -Value '1' }
        Save-JobState -JobDir $jobDir
        Set-Content -LiteralPath (Join-Path $script:StateDir 'last-job') -Value $job
        Set-Content -LiteralPath (Join-Path $script:StateDir 'pending-job') -Value $job
        try {
            Start-ScheduledTask -TaskName $script:UpdateTask
            $handoff = $true
        }
        catch {
            $script:R['status'] = 'failed'
            $script:R['reason'] = 'task_missing'
            Save-JobState -JobDir $jobDir -Final
        }
    }
    finally {
        # The scheduled task now owns the lock and releases it when the job ends.
        if (-not $handoff) { Exit-AgentLock }
    }
    Complete-AgentVerb -Verb 'update'
}

# ------------------------------------------------------------------ update steps (run in the scheduled task)

function Add-JobChange {
    param([string]$Name, [string]$From, [string]$To)
    $script:Changes.Add([ordered]@{ name = $Name; from = $From; to = $To }) | Out-Null
}

function Invoke-StepWindowsUpdate {
    param([string]$Log)
    $search = Get-WindowsUpdateSearch
    $session = $search['Session']
    $wanted = New-Object -ComObject 'Microsoft.Update.UpdateColl'
    foreach ($u in $search['Result'].Updates) {
        if (Test-FeatureUpdate -Update $u) { $script:R['major_available'] = [string]$u.Title; continue }
        if ($u.InstallationBehavior.CanRequestUserInput) { continue }
        if (-not $u.EulaAccepted) { continue }
        [void]$wanted.Add($u)
    }
    if ($wanted.Count -eq 0) { return }
    $downloader = $session.CreateUpdateDownloader()
    $downloader.Updates = $wanted
    [void]$downloader.Download()
    $installer = $session.CreateUpdateInstaller()
    $installer.Updates = $wanted
    $result = $installer.Install()
    for ($i = 0; $i -lt $wanted.Count; $i++) {
        $code = $result.GetUpdateResult($i).ResultCode
        if ($code -eq 2 -or $code -eq 3) { Add-JobChange -Name ([string]$wanted.Item($i).Title) -From '' -To 'installed' }
    }
    Add-Content -LiteralPath $Log -Value ('--- windows update: result {0}, reboot required {1}' -f $result.ResultCode, $result.RebootRequired)
    if ($result.ResultCode -ge 4) { throw 'windows_update_failed' }
}

# Parses the table printed by `winget upgrade` (columns located from the header line, which is
# the line just above the dashes ruler, so it does not depend on the UI language).
# Columns: Name, Id, Version, Available[, Source]. Returns one object per package.
function ConvertFrom-WingetUpgradeTable {
    param([string[]]$Lines)
    $ruler = -1
    for ($i = 1; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i] -match '^-{5,}\s*$') { $ruler = $i; break }
    }
    $found = New-Object System.Collections.ArrayList
    if ($ruler -lt 1) { return , @() }
    $header = $Lines[$ruler - 1]
    $starts = @()
    foreach ($m in [regex]::Matches($header, '(?<=^|\s{2})\S')) { $starts += $m.Index }
    if ($starts.Count -lt 4) { return , @() }
    for ($i = $ruler + 1; $i -lt $Lines.Count; $i++) {
        $line = $Lines[$i]
        if ([string]::IsNullOrWhiteSpace($line)) { break }
        if ($line -match '^\d+\s' -and $line.Length -lt $starts[1]) { break }
        if ($line.Length -le $starts[3]) { continue }
        $cut = {
            param([int]$n)
            $from = $starts[$n]
            if ($n + 1 -lt $starts.Count) { $to = $starts[$n + 1] } else { $to = $line.Length }
            if ($from -ge $line.Length) { return '' }
            if ($to -gt $line.Length) { $to = $line.Length }
            return $line.Substring($from, $to - $from).Trim()
        }
        $id = [string](& $cut 1)
        if ($id -notmatch '^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$') { continue }
        [void]$found.Add([pscustomobject]@{
                Name      = (& $cut 0)
                Id        = $id
                Version   = (& $cut 2)
                Available = (& $cut 3)
            })
    }
    return , @($found.ToArray())
}

function Get-WingetUpgradeList {
    param([string]$WingetPath)
    $outFile = [System.IO.Path]::GetTempFileName()
    try {
        $proc = Start-Process -FilePath $WingetPath -ArgumentList @('upgrade', '--include-unknown', '--accept-source-agreements', '--disable-interactivity') `
            -NoNewWindow -PassThru -RedirectStandardOutput $outFile
        if (-not $proc.WaitForExit(300000)) { & taskkill.exe /T /F /PID $proc.Id 2>&1 | Out-Null }
        $lines = @(Get-Content -LiteralPath $outFile -Encoding UTF8 -ErrorAction SilentlyContinue)
    }
    finally {
        Remove-Item -LiteralPath $outFile -Force -ErrorAction SilentlyContinue
    }
    return , @(ConvertFrom-WingetUpgradeTable -Lines $lines)
}

function Invoke-StepWinget {
    param([string]$Log)
    $winget = Get-Command -Name 'winget.exe' -ErrorAction SilentlyContinue
    if ($null -eq $winget) {
        Add-Content -LiteralPath $Log -Value '--- winget not found, skipped'
        return
    }
    # List what is about to be upgraded BEFORE --all so that each package is one change.
    $before = @(Get-WingetUpgradeList -WingetPath $winget.Source)
    $args1 = @('upgrade', '--all', '--silent', '--accept-source-agreements', '--accept-package-agreements', '--disable-interactivity')
    $code = Invoke-CappedProcess -FilePath $winget.Source -ArgumentList $args1 -LogPath $Log -TimeoutMinutes 60
    # 0 = ok; -1978335189 (no applicable upgrade) is not a failure.
    if ($code -ne 0 -and $code -ne -1978335189) { throw 'winget_failed' }
    if ($code -eq 0) {
        foreach ($pkg in $before) { Add-JobChange -Name ('winget:' + $pkg.Id) -From $pkg.Version -To $pkg.Available }
    }
}

function Invoke-StepScoop {
    param([string]$Log)
    $scoop = Get-Command -Name 'scoop' -ErrorAction SilentlyContinue
    if ($null -eq $scoop) {
        Add-Content -LiteralPath $Log -Value '--- scoop not found, skipped'
        return
    }
    $ps = (Get-Command -Name 'powershell.exe').Source
    $steps = @('scoop update', 'scoop update --all')
    if (Test-Path -LiteralPath (Join-Path $env:ProgramData 'scoop\apps')) { $steps += 'scoop update --all --global' }
    foreach ($step in $steps) {
        $code = Invoke-CappedProcess -FilePath $ps -ArgumentList @('-NoProfile', '-NonInteractive', '-Command', $step) -LogPath $Log -TimeoutMinutes 30
        if ($code -ne 0) { throw 'scoop_failed' }
    }
    $text = [System.IO.File]::ReadAllText($Log)
    foreach ($m in [regex]::Matches($text, "Updating '([^']{1,80})' \(([^ ]{1,40}) -> ([^)]{1,40})\)")) {
        Add-JobChange -Name ('scoop:' + $m.Groups[1].Value) -From $m.Groups[2].Value -To $m.Groups[3].Value
    }
}

function Get-WslDistro {
    param([string[]]$WslArgs)
    $outFile = [System.IO.Path]::GetTempFileName()
    try {
        $proc = Start-Process -FilePath 'wsl.exe' -ArgumentList $WslArgs -NoNewWindow -PassThru -RedirectStandardOutput $outFile
        if (-not $proc.WaitForExit(30000)) { $proc.Kill() }
        # wsl.exe writes UTF-16LE.
        $text = [System.IO.File]::ReadAllText($outFile, [System.Text.Encoding]::Unicode)
    }
    finally {
        Remove-Item -LiteralPath $outFile -Force -ErrorAction SilentlyContinue
    }
    $names = @()
    foreach ($line in ($text -split "`r?`n")) {
        $name = $line.Trim()
        if ($name -match '^[A-Za-z0-9._-]{1,64}$' -and $name -notlike 'docker-desktop*') { $names += $name }
    }
    return $names
}

function Invoke-StepWsl {
    param([string]$Log)
    if ($null -eq (Get-Command -Name 'wsl.exe' -ErrorAction SilentlyContinue)) { return }
    $distros = @(Get-WslDistro -WslArgs @('-l', '-q'))
    if ($distros.Count -eq 0) { return }
    # wsl --update restarts the WSL VM: only when no distribution is running.
    $running = @(Get-WslDistro -WslArgs @('-l', '--running', '-q'))
    if ($running.Count -eq 0) {
        $code = Invoke-CappedProcess -FilePath 'wsl.exe' -ArgumentList @('--update') -LogPath $Log -TimeoutMinutes 15
        if ($code -ne 0) { throw 'wsl_failed' }
        Add-JobChange -Name 'wsl:kernel' -From '' -To 'updated'
    }
    else {
        Add-Content -LiteralPath $Log -Value '--- wsl --update skipped: a distribution is running (active session)'
    }
    $inner = 'if command -v sysup >/dev/null 2>&1; then sysup; ' +
    'elif command -v apt-get >/dev/null 2>&1; then apt-get update && apt-get -y dist-upgrade; ' +
    'elif command -v dnf >/dev/null 2>&1; then dnf -y upgrade; ' +
    'elif command -v pacman >/dev/null 2>&1; then pacman -Syu --noconfirm; fi'
    foreach ($distro in $distros) {
        $code = Invoke-CappedProcess -FilePath 'wsl.exe' -ArgumentList @('-d', $distro, '-u', 'root', '--', 'sh', '-c', ('"' + $inner + '"')) -LogPath $Log -TimeoutMinutes 30
        if ($code -ne 0) { throw ('wsl_distro_failed') }
        Add-JobChange -Name ('wsl:' + $distro) -From '' -To 'updated'
    }
}

function Invoke-StepDefender {
    param([string]$Log)
    if ($null -eq (Get-Command -Name 'Update-MpSignature' -ErrorAction SilentlyContinue)) { return }
    Update-MpSignature
    Add-Content -LiteralPath $Log -Value '--- defender signatures updated'
}

function Invoke-UpdateStep {
    param([string]$Name, [scriptblock]$Body, [string]$Log)
    if ((Get-Date) -gt $script:JobDeadline) { $script:JobTimedOut = $true }
    if ($script:JobTimedOut) {
        Add-Content -LiteralPath $Log -Value ('--- {0} skipped: job time limit reached' -f $Name)
        return
    }
    try {
        & $Body $Log
    }
    catch {
        Add-Content -LiteralPath $Log -Value (Protect-Text -Text ('--- {0} failed: {1}' -f $Name, $_.Exception.Message))
        if ($null -eq $script:FailedStep) { $script:FailedStep = $Name }
    }
}

# Detached job entry: scheduled task only (-RunJob), never from SSH.
function Invoke-AgentJob {
    $pendingFile = Join-Path $script:StateDir 'pending-job'
    $job = $null
    if (Test-Path -LiteralPath $pendingFile) { $job = (Get-Content -LiteralPath $pendingFile -TotalCount 1) }
    if ([string]::IsNullOrEmpty($job) -or $job -notmatch '^[0-9]{8}T[0-9]{6}Z-[0-9]+$') {
        Write-AgentLog -Message 'job runner: invalid or missing job id' -Level Warning -EventId 4001
        exit 1
    }
    $jobDir = Join-Path $script:JobsDir $job
    if (-not (Test-Path -LiteralPath $jobDir)) {
        Write-AgentLog -Message 'job runner: unknown job' -Level Warning -EventId 4001
        exit 1
    }
    Remove-Item -LiteralPath $pendingFile -Force -ErrorAction SilentlyContinue
    Initialize-AgentResult
    $script:R['job'] = $job
    $script:R['started'] = (Get-Content -LiteralPath (Join-Path $jobDir 'started') -TotalCount 1)
    if ((Get-LockOwner) -ne $job) {
        $script:R['status'] = 'failed'
        $script:R['reason'] = 'lock_lost'
        Save-JobState -JobDir $jobDir -Final
        Write-AgentLog -Message ('update job {0} aborted: lock_lost' -f $job) -Level Warning -EventId 4001
        exit 2
    }
    # Take the lock over for this process (pid), keeping the job id as owner.
    [System.IO.File]::WriteAllText($script:LockFile, ('{0}|{1}|{2}' -f $PID, $job, [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()))
    $log = Join-Path $jobDir 'update.log'
    New-Item -ItemType File -Path $log -Force | Out-Null
    $script:Changes = New-Object System.Collections.ArrayList
    $script:FailedStep = $null
    $script:JobDeadline = (Get-Date).AddMinutes($script:JobMaxMinutes)
    try {
        $script:R['health_before'] = Get-HealthSnapshot
        $script:R['health_after'] = $script:R['health_before']
        $script:R['status'] = 'running'
        Save-JobState -JobDir $jobDir
        Write-AgentLog -Message ('update job {0} started' -f $job)
        Invoke-UpdateStep -Name 'windows_update' -Log $log -Body { param($L) Invoke-StepWindowsUpdate -Log $L }
        Invoke-UpdateStep -Name 'winget' -Log $log -Body { param($L) Invoke-StepWinget -Log $L }
        Invoke-UpdateStep -Name 'scoop' -Log $log -Body { param($L) Invoke-StepScoop -Log $L }
        Invoke-UpdateStep -Name 'wsl' -Log $log -Body { param($L) Invoke-StepWsl -Log $L }
        Invoke-UpdateStep -Name 'defender' -Log $log -Body { param($L) Invoke-StepDefender -Log $L }
        $after = Get-HealthSnapshot
        $script:R['health_after'] = $after
        $script:R['changes'] = @($script:Changes.ToArray())
        $script:R['packages'] = [int]$script:Changes.Count
        $script:R['reboot_required'] = Test-RebootPending
        $script:R['log_tail'] = (Get-CappedTail -Path $log -Lines 20)
        $script:R['ended'] = Get-NowIso
        if ($script:JobTimedOut) {
            # 'timeout' is a master-only status: an agent reports failed + reason timeout.
            $script:R['status'] = 'failed'
            $script:R['reason'] = 'timeout'
        }
        elseif ($null -ne $script:FailedStep) {
            $script:R['status'] = 'failed'
            $script:R['reason'] = ($script:FailedStep + '_failed')
        }
        elseif (@($after['critical_services_down']).Count -gt 0) {
            $script:R['status'] = 'degraded'
            $script:R['reason'] = 'critical services down'
        }
        elseif ($script:Changes.Count -gt 0) {
            $script:R['status'] = 'updated'
        }
        else {
            $script:R['status'] = 'up-to-date'
        }
        Save-JobState -JobDir $jobDir -Final
        if ($script:R['status'] -eq 'updated' -or $script:R['status'] -eq 'up-to-date') {
            Set-Content -LiteralPath (Join-Path $script:StateDir 'last-success') -Value ([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())
        }
        Write-AgentLog -Message ('update job {0} finished: {1}' -f $job, $script:R['status'])
        if (Test-Path -LiteralPath (Join-Path $jobDir 'pull')) { Send-PullNotification }
    }
    finally {
        Exit-AgentLock
    }
    exit (Get-ExitCodeFor -Status ([string]$script:R['status']))
}

# ------------------------------------------------------------------ pull mode (local only)
# Pull mode is NOT a verb: it is selected by the -RunPull switch of the scheduled
# task, refused in an SSH context, and only ever reaches Invoke-StartUpdate. No
# restart code is reachable from here.

function Get-ConfValue {
    param([string]$Key)
    $file = Join-Path $script:ConfDir 'pull.conf'
    if (-not (Test-Path -LiteralPath $file)) { return '' }
    foreach ($line in (Get-Content -LiteralPath $file)) {
        if ($line.StartsWith($Key + '=')) { return $line.Substring($Key.Length + 1).Trim().Trim('"') }
    }
    return ''
}

function Get-PullDeniedReason {
    if (-not (Test-Path -LiteralPath (Join-Path $script:ConfDir 'pull-enabled'))) { return 'not_enabled' }
    if (Test-Path -LiteralPath (Join-Path $script:ConfDir 'no-pull')) { return 'denied' }
    if ($script:HostName -like '*guardian*') { return 'guardian' }
    return ''
}

function Send-PullNotification {
    $url = Get-ConfValue -Key 'NTFY_URL'
    $topic = Get-ConfValue -Key 'NTFY_TOPIC'
    $tokenFile = Get-ConfValue -Key 'NTFY_TOKEN_FILE'
    if ($url -notmatch '^https?://[A-Za-z0-9._:/-]+$' -or $topic -notmatch '^[A-Za-z0-9_-]+$') {
        Write-AgentLog -Message 'pull notify: no valid ntfy settings'
        return
    }
    $headers = @{ Priority = '2'; Title = 'fleet pull update' }
    if ($tokenFile -and (Test-Path -LiteralPath $tokenFile) -and $url -like 'https://*') {
        $token = (Get-Content -LiteralPath $tokenFile -TotalCount 1).Trim()
        if ($token -match '^[A-Za-z0-9_.-]+$') { $headers['Authorization'] = 'Bearer ' + $token }
    }
    $message = '{0}: pull-mode update {1}' -f $script:HostName, $script:R['status']
    if ($script:R['reboot_required']) { $message += '; restart required, NOT done (pull mode never restarts)' }
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        [void](Invoke-RestMethod -Uri ($url.TrimEnd('/') + '/' + $topic) -Method Post -Headers $headers -Body (Get-SafeLine -Text $message -Max 300) -TimeoutSec 15 -UseBasicParsing)
    }
    catch {
        Write-AgentLog -Message 'pull notify: delivery failed' -Level Warning
    }
}

function Invoke-AgentPull {
    Initialize-AgentResult
    $why = Get-PullDeniedReason
    if ($why) {
        $script:R['status'] = 'skipped'
        $script:R['reason'] = 'pull_' + $why
        Write-AgentLog -Message ('pull skipped: {0}' -f $why)
        Complete-AgentVerb -Verb 'pull'
    }
    $stamp = Join-Path $script:StateDir 'last-success'
    $last = 0
    if (Test-Path -LiteralPath $stamp) {
        $text = (Get-Content -LiteralPath $stamp -TotalCount 1)
        if ($text -match '^[0-9]{1,11}$') { $last = [int64]$text }
    }
    $age = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - $last
    # A future timestamp (age < 0) is treated as stale, never as "recent".
    if ($last -gt 0 -and $age -ge 0 -and $age -lt ($script:PullDays * 86400)) {
        $script:R['status'] = 'skipped'
        $script:R['reason'] = 'recent_update'
        Write-AgentLog -Message ('pull skipped: last successful update {0}s ago' -f $age)
        Complete-AgentVerb -Verb 'pull'
    }
    Write-AgentLog -Message 'pull: last successful update older than 7 days, updating'
    Invoke-StartUpdate -FromPull
}

# ------------------------------------------------------------------ main

function Invoke-AgentMain {
    if ($RunJob -or $RunPull) {
        if ((Test-SshContext) -or $script:ExtraArgs.Count -ne 0 -or ($RunJob -and $RunPull)) {
            Exit-AgentRefused -What 'local-only entry reached through ssh or with arguments'
        }
        if ($RunJob) { Invoke-AgentJob }
        Invoke-AgentPull
        return
    }
    if ($script:ExtraArgs.Count -ne 0) { Exit-AgentRefused -What 'unexpected arguments' }
    $verb = [Environment]::GetEnvironmentVariable('SSH_ORIGINAL_COMMAND')
    if ([string]::IsNullOrEmpty($verb)) { Exit-AgentRefused -What 'no command (interactive shell attempt)' }
    if ($script:Verbs -cnotcontains $verb) { Exit-AgentRefused -What ('verb not allowed: ' + (Get-SafeLine -Text $verb -Max 60)) }
    Write-AgentLog -Message ('call verb={0} client={1}' -f $verb, (Get-ClientAddress))
    switch -CaseSensitive ($verb) {
        'check' { Invoke-VerbCheck }
        'update' { Invoke-StartUpdate }
        'reboot-status' { Invoke-VerbRebootStatus }
        'reboot' { Invoke-VerbReboot }
        'report' { Invoke-VerbReport }
        default { Exit-AgentRefused -What 'unreachable verb' }
    }
}

Invoke-AgentMain
