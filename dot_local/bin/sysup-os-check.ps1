#Requires -Version 5.1
<#
sysup-os-check (Windows) - NOTIFY-ONLY check for a newer Windows feature update.
Never installs anything, never prompts, always exits 0. Run by sysup (msys
branch) and by the chezmoi update-windows script. Skip with SYSUP_NO_OS_CHECK=1.
PowerShell 5.1 compatible.
#>
$ErrorActionPreference = 'SilentlyContinue'

# Pure formatter: installed version + offered feature update titles -> one line.
function Format-FeatureUpdateNotice {
    param([string]$Installed, [string[]]$Titles)
    $Titles = @($Titles | Where-Object { $_ })
    if ($Titles.Count -eq 0) { return $null }
    return ("OS: Windows feature update available: {0} (installed: {1}). Install it from Settings > Windows Update; this script never installs it." -f ($Titles -join '; '), $Installed)
}

function Invoke-OsReleaseCheck {
    try {
        if ($env:SYSUP_NO_OS_CHECK -eq '1') { return }
        $cv = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
        $installed = $cv.DisplayVersion
        if (-not $installed) { $installed = $cv.ReleaseId }
        # The Windows Update search can hang on a bad network: hard 60 s limit via a job.
        $job = Start-Job -ScriptBlock {
            $searcher = (New-Object -ComObject 'Microsoft.Update.Session').CreateUpdateSearcher()
            $result = $searcher.Search("IsInstalled=0 and IsHidden=0 and Type='Software'")
            foreach ($u in $result.Updates) {
                foreach ($c in $u.Categories) { if ($c.Name -eq 'Upgrades') { $u.Title; break } }
            }
        }
        if (Wait-Job $job -Timeout 60) {
            $titles = @(Receive-Job $job)
            $line = Format-FeatureUpdateNotice -Installed $installed -Titles $titles
            if ($line) { Write-Host $line -ForegroundColor Yellow }
            else { Write-Host ("OS: Windows {0} - no feature update on offer" -f $installed) -ForegroundColor DarkGray }
        }
        Remove-Job $job -Force
    }
    catch { }
}

Invoke-OsReleaseCheck
exit 0
