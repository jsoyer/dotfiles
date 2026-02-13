# =============================================================================
# Windows Bootstrap Script
# =============================================================================
# Installs Scoop, git, chezmoi, then applies dotfiles.
#
# Usage:
#   irm https://raw.githubusercontent.com/jsoyer/dotfiles/main/scripts/bootstrap.ps1 | iex
#
# =============================================================================

#Requires -Version 5.1

$EMOJI = "🪟"

Write-Host "$EMOJI [bootstrap] Starting Windows dotfiles setup..." -ForegroundColor Cyan

# =============================================================================
# Install Scoop
# =============================================================================
if (-not (Get-Command scoop -ErrorAction SilentlyContinue)) {
    Write-Host "🪣 [bootstrap] Installing Scoop..." -ForegroundColor Yellow
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
    Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression
} else {
    Write-Host "🪣 [bootstrap] Scoop already installed" -ForegroundColor Green
}

# =============================================================================
# Add buckets
# =============================================================================
Write-Host "📦 [bootstrap] Adding Scoop buckets..." -ForegroundColor Yellow
if (-not (scoop bucket list | Select-String -Quiet 'extras')) { scoop bucket add extras }
if (-not (scoop bucket list | Select-String -Quiet 'versions')) { scoop bucket add versions }

# =============================================================================
# Install git + chezmoi
# =============================================================================
Write-Host "🔧 [bootstrap] Installing git and chezmoi..." -ForegroundColor Yellow

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    scoop install git
}
if (-not (Get-Command chezmoi -ErrorAction SilentlyContinue)) {
    scoop install chezmoi
}

Write-Host "✅ [bootstrap] git and chezmoi installed" -ForegroundColor Green

# =============================================================================
# Apply dotfiles
# =============================================================================
Write-Host "✨ [bootstrap] Initializing chezmoi and applying dotfiles..." -ForegroundColor Yellow

$chezmoiDir = Join-Path $env:USERPROFILE ".local\share\chezmoi"
if (Test-Path $chezmoiDir) {
    Write-Host "🔄 [bootstrap] chezmoi already initialized, updating..." -ForegroundColor Yellow
    chezmoi update
} else {
    chezmoi init --apply jsoyer
}

# =============================================================================
# Done
# =============================================================================
Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host "  $EMOJI Bootstrap Complete!" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host ""
Write-Host "✅ [bootstrap] chezmoi has installed and configured everything." -ForegroundColor Cyan
Write-Host "✅ [bootstrap] Restart your terminal to apply all changes." -ForegroundColor Cyan
Write-Host ""
