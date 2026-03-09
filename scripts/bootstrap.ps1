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
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

Write-Host "[bootstrap] Starting Windows dotfiles setup..." -ForegroundColor Cyan

# =============================================================================
# Install Scoop
# =============================================================================
if (-not (Get-Command scoop -ErrorAction SilentlyContinue)) {
    Write-Host "[bootstrap] Installing Scoop..." -ForegroundColor Yellow
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force
    Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression
    if (-not (Get-Command scoop -ErrorAction SilentlyContinue)) {
        Write-Error "[bootstrap] Scoop installation failed"; exit 1
    }
} else {
    Write-Host "[bootstrap] Scoop already installed" -ForegroundColor Green
}

# =============================================================================
# Add buckets
# =============================================================================
Write-Host "[bootstrap] Adding Scoop buckets..." -ForegroundColor Yellow
if (-not (scoop bucket list | Select-String -Quiet 'extras')) { scoop bucket add extras 2>$null }
if (-not (scoop bucket list | Select-String -Quiet 'versions')) { scoop bucket add versions 2>$null }

# =============================================================================
# Install git + chezmoi
# =============================================================================
Write-Host "[bootstrap] Installing git and chezmoi..." -ForegroundColor Yellow

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    scoop install git
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Error "[bootstrap] git installation failed"; exit 1
    }
}
if (-not (Get-Command chezmoi -ErrorAction SilentlyContinue)) {
    scoop install chezmoi
    if (-not (Get-Command chezmoi -ErrorAction SilentlyContinue)) {
        Write-Error "[bootstrap] chezmoi installation failed"; exit 1
    }
}

Write-Host "[bootstrap] git and chezmoi installed" -ForegroundColor Green

# =============================================================================
# Apply dotfiles
# =============================================================================
Write-Host "[bootstrap] Initializing chezmoi and applying dotfiles..." -ForegroundColor Yellow

if (-not $env:USERPROFILE) { Write-Error "USERPROFILE not set"; exit 1 }
$chezmoiDir = Join-Path $env:USERPROFILE ".local\share\chezmoi"
if (Test-Path $chezmoiDir) {
    Write-Host "[bootstrap] chezmoi already initialized, updating..." -ForegroundColor Yellow
    chezmoi update
} else {
    chezmoi init --apply jsoyer
}

# =============================================================================
# Done
# =============================================================================
Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host "  Bootstrap Complete!" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host ""
Write-Host "[bootstrap] chezmoi has installed and configured everything." -ForegroundColor Cyan
Write-Host "[bootstrap] Restart your terminal to apply all changes." -ForegroundColor Cyan
Write-Host ""
