# Bootstrap Scripts

One-shot scripts for initializing fresh machines with git, chezmoi, and the dotfiles configuration.

## Overview

These scripts automate the bootstrap process across multiple platforms. They handle platform detection, prerequisite installation, and initial dotfiles apply.

## Scripts

### bootstrap.sh

**Usage:**
```bash
curl -sL https://raw.githubusercontent.com/jsoyer/dotfiles/main/scripts/bootstrap.sh | bash
```

**Supported Platforms:**
- **macOS** — Installs Xcode CLI tools, Homebrew, then chezmoi and gh via Homebrew
- **Arch Linux** — Installs git, chezmoi (via pacman or official script), gh (via AUR/pacman)
- **Fedora Standard** — Installs git, chezmoi, and gh via DNF
- **Fedora Atomic** — Minimal install (git, chezmoi) via official script
- **Fedora Toolbox** — Container-optimized (zsh only, minimal footprint)
- **Raspberry Pi / Debian / Ubuntu** — Installs git, chezmoi, and gh via APT

**What it does:**
1. **Detects platform and OS version** with emoji indicators
2. **Checks for OS updates** and prompts user to install if available
3. **Installs git and chezmoi** via platform-specific package managers
4. **Installs gh (GitHub CLI)** for repo operations
5. **Initializes chezmoi** and applies dotfiles from the GitHub repository
6. **Installs platform-specific dependencies** (Linuxbrew, 1Password CLI, etc.)
7. **Runs lifecycle scripts** (phase 01-setup through 05-maintenance)

**Key features:**
- Zero-dependency — only requires curl/bash
- Idempotent — safe to run multiple times
- Interactive — prompts for OS updates before proceeding
- Verbose — colored output showing each step

### bootstrap.ps1

**Usage:**
```powershell
irm https://raw.githubusercontent.com/jsoyer/dotfiles/main/scripts/bootstrap.ps1 | iex
```

**Supported Platforms:**
- **Windows** — PowerShell 5.1+

**What it does:**
1. Installs Scoop package manager
2. Adds Scoop buckets (extras, versions)
3. Installs git and chezmoi via Scoop
4. Initializes chezmoi with the GitHub repository
5. Applies dotfiles

**Requirements:**
- PowerShell 5.1 or later
- Internet connectivity
- Administrator prompt (for Scoop bucket operations)

### install-rpi.sh

**Status:** Placeholder (not yet implemented)

Post-bootstrap setup for Raspberry Pi. Currently handled by `bootstrap.sh` (rpi platform branch).

## Platform Profiles

The bootstrap process detects which platform profile to use and stores it in `~/.config/chezmoi/chezmoi.toml`. Profiles determine which packages are installed and which configs are applied.

See [ARCHITECTURE.md#profile-detection](../docs/ARCHITECTURE.md#profile-detection) for the full decision tree.

## Troubleshooting

### macOS

**Problem:** Xcode CLI tools hang indefinitely
**Solution:** Install manually: `xcode-select --install`, then re-run bootstrap

**Problem:** Homebrew install fails
**Solution:** Check `/var/log/install.log`, ensure disk space available, try: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`

### Linux (Fedora/Ubuntu/Debian)

**Problem:** `chezmoi` not found in repos
**Solution:** Bootstrap installs from official script if package unavailable

**Problem:** 1Password CLI not found
**Solution:** Install separately: `brew install 1password-cli` or `sudo dnf install 1password` (Fedora only)

### Windows

**Problem:** Scoop installation blocked by execution policy
**Solution:** PowerShell 5.1 bootstrap should handle this, or run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force`

**Problem:** `chezmoi init` fails
**Solution:** Ensure `$USERPROFILE` environment variable is set, or create `~/.local/share/chezmoi` manually

## Related Documentation

- [ONBOARDING.md](../docs/ONBOARDING.md) — Post-bootstrap setup and customization
- [RUNBOOK.md](../docs/RUNBOOK.md) — Daily operations and troubleshooting
- [ARCHITECTURE.md](../docs/ARCHITECTURE.md) — How the lifecycle scripts work
