#!/usr/bin/env pwsh
# Scoop syntax, with base + usage read-only and changes recorded for this machine.
#Requires -Version 5.1
param(
    [Parameter(Position=0)][string]$Subcommand,
    [Parameter(Position=1, ValueFromRemainingArguments)][string[]]$Arguments
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-AtomicUtf8([string]$Path, [string]$Content) {
    $parent = Split-Path -Parent $Path
    [System.IO.Directory]::CreateDirectory($parent) | Out-Null
    $temporary = Join-Path $parent ([System.IO.Path]::GetRandomFileName())
    try {
        [System.IO.File]::WriteAllText($temporary, $Content, [System.Text.UTF8Encoding]::new($false))
        if (Test-Path -LiteralPath $Path) {
            [System.IO.File]::Replace($temporary, $Path, $null)
        } else {
            [System.IO.File]::Move($temporary, $Path)
        }
    } finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary }
    }
}

$nativeScoop = Get-Command scoop -CommandType Function, ExternalScript, Application -ErrorAction Stop | Select-Object -First 1

if (-not $Subcommand -or $Subcommand -in @('--help', '-h')) {
    Write-Host 'scoopw install/uninstall/dump: sync only this machine; other commands pass through.'
    Write-Host 'Use package-plan preview, or package-plan promote --manager scoop NAME --to base|usage.'
    exit 0
}
if ($Subcommand -notin @('install', 'uninstall', 'dump')) {
    & $nativeScoop $Subcommand @Arguments
    exit $LASTEXITCODE
}
if ($Subcommand -ne 'dump' -and -not $Arguments) { throw 'Specify at least one package.' }
foreach ($package in $Arguments) {
    if ($package -notmatch '^(?:[a-zA-Z0-9._-]+/)?[a-zA-Z0-9][a-zA-Z0-9._+-]*$') {
        throw "Invalid Scoop package name: $package"
    }
}

$contextPath = Join-Path $HOME '.config/dotfiles/package-context.json'
$savedContext = if (Test-Path -LiteralPath $contextPath) { Get-Content -LiteralPath $contextPath -Raw -Encoding UTF8 | ConvertFrom-Json } else { $null }
$source = if ($env:CHEZMOI_SOURCE_PATH) { $env:CHEZMOI_SOURCE_PATH } elseif ($savedContext) { $savedContext.source_dir } else { Join-Path $HOME '.local/share/chezmoi' }
$directory = Join-Path $source 'dot_private'
# Chezmois own selector avoids a second mapping or Python dependency for legacy Windows.
$selectionJson = & chezmoi execute-template --source $source '{{ includeTemplate "package-files" (dict "data" . "manager" "scoop") }}'
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve Scoop package layers; no packages or manifests changed.' }
$selection = ($selectionJson -join "`n") | ConvertFrom-Json
if (-not $selection.supported) { throw 'Scoop is unsupported by the selected machine profile.' }
$hostFile = Join-Path $directory $selection.host
$excludeFile = Join-Path $directory $selection.exclude_file
$sharedApps = @{}
$sharedBuckets = @{}
foreach ($filename in $selection.shared) {
    $manifest = Get-Content -LiteralPath (Join-Path $directory $filename) -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($app in $manifest.apps) { $sharedApps[$app.name] = $app }
    foreach ($bucket in $manifest.buckets) { $sharedBuckets[$bucket.name] = $bucket }
}
$excludes = @{}
if (Test-Path -LiteralPath $excludeFile) {
    $data = Get-Content -LiteralPath $excludeFile -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($property in $data.PSObject.Properties) { $excludes[$property.Name] = $property.Value }
}
$excluded = @()
if ($excludes.ContainsKey('scoop')) { $excluded = @($excludes['scoop']) }

if ($Subcommand -ne 'dump') {
    & $nativeScoop $Subcommand @Arguments
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
# Never replace a valid manifest on export failure or malformed JSON.
$exportJson = & $nativeScoop export
if ($LASTEXITCODE -ne 0) { throw 'Scoop export failed; manifests left unchanged.' }
$export = ($exportJson -join "`n") | ConvertFrom-Json
if (-not $export -or -not $export.PSObject.Properties['apps'] -or -not $export.PSObject.Properties['buckets']) {
    throw 'Invalid Scoop export; manifests left unchanged.'
}
if ($Subcommand -ne 'dump') {
    foreach ($package in $Arguments) {
        $name = ($package -split '/')[-1]
        if ($Subcommand -eq 'uninstall' -and $sharedApps.ContainsKey($name)) {
            if ($excluded -notcontains $name) { $excluded += $name }
        } elseif ($Subcommand -eq 'install') {
            $excluded = @($excluded | Where-Object { $_ -ne $name })
        }
    }
}
$previousApps = @{}
if (Test-Path -LiteralPath $hostFile) {
    $previous = Get-Content -LiteralPath $hostFile -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($app in $previous.apps) { $previousApps[$app.name] = $app }
}
$apps = @()
foreach ($app in $export.apps) {
    if (-not $app.name) { throw 'Invalid app in Scoop export; manifests left unchanged.' }
    if ($sharedApps.ContainsKey($app.name) -or $excluded -contains $app.name) { continue }
    # Exported version is installed state, not an instruction to pin updates.
    # Explicit version/options already in a host declaration remain authoritative.
    if ($previousApps.ContainsKey($app.name)) { $apps += $previousApps[$app.name]; continue }
    $entry = [ordered]@{ name = $app.name }
    foreach ($key in @('bucket', 'architecture', 'global')) {
        if ($app.PSObject.Properties[$key]) { $entry[$key] = $app.$key }
    }
    $apps += $entry
}
$buckets = @($export.buckets | Where-Object { -not $sharedBuckets.ContainsKey($_.name) })
$content = ([ordered]@{buckets = $buckets; apps = $apps} | ConvertTo-Json -Depth 20) + "`n"
Write-AtomicUtf8 $hostFile $content
$changed = @($hostFile)
$before = @()
if ($excludes.ContainsKey('scoop')) { $before = @($excludes['scoop']) }
if ((@($before | Sort-Object) -join "`n") -cne (@($excluded | Sort-Object) -join "`n")) {
    $excludes['scoop'] = @($excluded | Sort-Object -Unique)
    Write-AtomicUtf8 $excludeFile (($excludes | ConvertTo-Json -Depth 20) + "`n")
    $changed += $excludeFile
}
Push-Location $source
try {
    $status = & git status --porcelain -- @changed
    if ($LASTEXITCODE -ne 0) { throw 'Cannot check manifest Git status.' }
    if ($status) {
        & git add -- @changed
        if ($LASTEXITCODE -ne 0) { throw 'Cannot stage machine manifests.' }
        & git commit --only -m "feat(scoopw): $Subcommand on $($selection.hostname)" -- @changed
        if ($LASTEXITCODE -ne 0) { throw 'Cannot commit machine manifests.' }
        & git push
        if ($LASTEXITCODE -ne 0) { throw 'Cannot push machine manifests.' }
    }
} finally { Pop-Location }
