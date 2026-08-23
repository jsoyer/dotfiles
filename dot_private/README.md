# Package Manifest System

This directory contains **package manifests** for all supported platforms. Each manifest is a text file (or JSON) listing packages to be installed on specific machine profiles.

## Overview

The manifest system provides:

- **Profile-specific package management** - Different packages for different machine types
- **GUI app separation** - Base and GUI manifests install only when needed
- **Automatic tracking** - Package wrappers (`aptw`, `dnfw`, `pacmanw`, `yayw`, `breww`, `ostreew`, `scoopw`) automatically update manifests when you install/remove packages
- **Display server detection** - GUI apps are only installed when a graphical environment is present (`_has_gui()` check in install scripts)
- **Version control** - All manifest changes are automatically committed and pushed to GitHub

---

## Layered cascade: shared base + per-machine overlay

Every manager reads two layers and installs their **union**:

| Layer | Filename | Who edits it | Scope |
| ----- | -------- | ------------ | ----- |
| **Base** | `<Manager>file_<profile>` (e.g. `Aptfile_ubuntu_desktop`, `Dnffile_fedora_desktop`, `Brewfile_brew_only`) | curated by hand | shared by every machine of that profile |
| **Overlay** | `<Manager>file_<hostname>` (e.g. `Brewfile_jsoyer-macOS`, `Pacfile_<host>`) | written automatically by the wrappers | extras specific to one machine |

- `<hostname>` = `{{ .chezmoi.hostname }}` in templates, `uname -n \| cut -d. -f1` in wrappers.
- **Install** = base, then the host overlay **only if it exists** (`[[ -f ]]` guard → a machine with no overlay behaves exactly as before).
- **Wrappers** write `installed − base − blacklist` to the overlay and **never touch the base**, so two machines of the same profile never clobber each other's package list.
- **Promote** a package to the shared base by moving its line from `<Manager>file_<hostname>` into the profile base (or `breww --promote <name>`), then commit.

Overlay filenames per manager: `Brewfile_<host>`, `Aptfile_<host>`, `Dnffile_<host>`,
`Pacfile_<host>` (+ `Pacfile_aur_<host>`), `Rpmfile_<host>`, `Snapfile_<host>`,
`Flatpakfile_<host>` (mas apps live in `Brewfile_<host>`).

---

## Manifest Files by Platform

### macOS (Homebrew)

| File | Purpose | Platform |
|------|---------|----------|
| `Brewfile.tmpl` | Templated entry point (routes to profile-specific files) | macOS all |
| `Brewfile_macos` | Core formulae (shared by all macOS profiles) | macOS all |
| `Brewfile_pro` | Additional packages (included for `mac-pro` profile) | mac-pro |
| `Brewfile_personal` | Personal machine extras (included for `mac-personal` profile) | mac-personal |

**Usage:** Installed via `brew bundle` in `run_after_brew-bundle.sh.tmpl`

---

### Linux - Ubuntu/Debian

| File | Purpose | Profile | Type |
|------|---------|---------|------|
| `Aptfile_ubuntu_desktop` | Ubuntu desktop base packages | ubuntu-desktop | Base |
| `Aptfile_ubuntu_gui` | Ubuntu desktop GUI apps (Brave, Chrome, Signal, Zed, VLC, etc.) | ubuntu-desktop | GUI only |
| `Aptfile_ubuntu_server` | Ubuntu server packages | ubuntu-server | Base |
| `Aptfile_debian` | Generic Debian packages | debian | Base |
| `Aptfile_rpi` | Raspberry Pi packages | rpi | Base |
| `Aptfile_rpi_gui` | Raspberry Pi GUI apps (VLC, etc.) | rpi | GUI only |

**GUI apps only install when:** `_has_gui()` returns true (display server detected)

**Wrapper:** `aptw` (shell alias `apt` on Ubuntu/Debian/RPi)

**Installation:** Via `run_onchange_install-linux-packages.sh.tmpl`

---

### Linux - Fedora

| File | Purpose | Profile | Type |
|------|---------|---------|------|
| `Dnffile_fedora_desktop` | Fedora desktop base packages | fedora-desktop | Base |
| `Dnffile_fedora_gui` | Fedora desktop GUI apps (Brave, Chrome, VLC, etc.) | fedora-desktop | GUI only |
| `Dnffile_fedora_server` | Fedora server packages | fedora-server | Base |
| `Rpmfile_fedora_atomic` | Fedora Atomic rpm-ostree packages | fedora-atomic | Base |

**GUI apps only install when:** `_has_gui()` returns true (display server detected)

**Wrappers:**
- `dnfw` (shell alias `dnf`/`yum` on Fedora)
- `ostreew` (shell function `rpm-ostree` on Fedora Atomic)

**Installation:** Via `run_onchange_install-linux-packages.sh.tmpl`

---

### Linux - Arch / OmArchy

| File | Purpose | Profile | Type |
|------|---------|---------|------|
| `Pacfile_arch_desktop` | Arch desktop base packages (pacman) | arch-desktop, omarchy | Base |
| `Pacfile_arch_gui` | Arch desktop GUI apps (pacman) | arch-desktop, omarchy | GUI only |
| `Pacfile_aur_desktop` | Arch desktop AUR packages (yay) | arch-desktop, omarchy | Base |
| `Pacfile_aur_gui` | Arch desktop GUI apps from AUR (yay) | arch-desktop, omarchy | GUI only |
| `Pacfile_arch_server` | Arch server packages (pacman) | arch-server | Base |

**GUI apps only install when:** `_has_gui()` returns true (display server detected)

**Wrappers:**
- `pacmanw` (shell alias `pacman` on Arch/OmArchy)
- `yayw` (shell alias `yay` on Arch desktop/OmArchy)

**OmArchy special support:** Prompts for optional config overrides (shell, nvim, tmux, git, window manager)

**Installation:** Via `run_onchange_install-linux-packages.sh.tmpl`

---

### Linux - Flatpak (desktop & Atomic)

| File | Purpose | Profile | Type |
|------|---------|---------|------|
| `Flatpakfile_fedora_atomic` | Flatpak apps (system-wide) | fedora-atomic | Base |
| `Flatpakfile_ubuntu_desktop` | Flatpak apps (`--user`) | ubuntu-desktop | Base |
| `Flatpakfile_fedora_desktop` | Flatpak apps (`--user`) | fedora-desktop | Base |
| `Flatpakfile_rpi` | Flatpak apps (`--user`), aarch64-capable only | rpi | Base |
| `Flatpakfile_<hostname>` | Per-machine extras | any | Overlay |

**Wrapper:** `flatpakw` (install/remove/dump → host overlay)

**Installation:** Via `run_onchange_05-install-linux-flatpak.sh.tmpl` (flathub remote auto-added)

> **Flatpaks never belong in a Brewfile.** `Brewfile_brew_only` is included
> unconditionally by `Brewfile.tmpl` for every Linux profile, so anything in it
> also reaches the RPi. Discord and Signal sat there and are x86_64-only on
> Flathub, which made `brew bundle` fail on arm64. Flatpaks belong in the
> per-profile `Flatpakfile_*` manifests, where the architecture is known.

---

### Linux - Raspberry Pi (Pi-Apps)

Pi-Apps integration is handled by `run_once_install-pi-apps.sh.tmpl`:

- Installs Pi-Apps package manager if not present
- Provides GUI for selecting pre-vetted apps
- Includes multimedia, programming, office, utilities categories

**Installation:** Via `run_once_install-pi-apps.sh.tmpl`

---

### Windows (Scoop)

| File | Purpose | Profile |
|------|---------|---------|
| `Scoopfile.json` | Windows Scoop packages | windows |

**Wrapper:** `scoopw` (PowerShell alias `scoop`)

**Installation:** Via `run_once_install-windows-packages.ps1.tmpl`

---

### Linux - Linuxbrew (All Linux Profiles)

| File | Purpose | Profile |
|------|---------|---------|
| `Brewfile_brew_only` | Linuxbrew packages (non-macOS specific) | All Linux desktop profiles |
| `Brewfile_rpi` | Additional Linuxbrew packages for RPi | rpi |

**Wrapper:** `breww` (shell alias `b`)

**Installation:** Via `run_after_brew-bundle.sh.tmpl`

---

## Format & Syntax

### Standard Text Format (Apt, Dnf, Pacman, Yay)

```bash
# Comments start with #
# Blank lines are ignored

# List each package on its own line
package-name
another-package
third-package
```

**Example (Aptfile_ubuntu_desktop):**
```bash
# Ubuntu desktop essentials
build-essential
curl
git
neovim
tmux
zsh
```

### GUI Manifest Format

Same as above, but contains only GUI applications:

```bash
# Ubuntu GUI apps (apt) — installed only when display server is present
brave-browser
google-chrome-stable
signal-desktop
zed
vlc
```

### MacOS Brewfile Format

Uses Homebrew's standard format:

```ruby
# Formulae (CLI tools)
brew "git"
brew "neovim"
brew "tmux"

# Casks (GUI apps)
cask "wezterm"
cask "alacritty"

# App Store apps
mas "Xcode", id: 497799835
```

### Windows Scoopfile Format

JSON format:

```json
{
  "buckets": ["main", "versions"],
  "apps": ["git", "neovim", "tmux"]
}
```

---

## How Installation Works

### 1. Manifest Checksums

Installation scripts track manifests via checksums (in `run_onchange_install-linux-packages.sh.tmpl`):

```bash
# These checksums trigger script re-runs when any manifest changes
# Aptfile_ubuntu_desktop: <sha256>
# Aptfile_ubuntu_gui:     <sha256>
```

When a manifest changes, chezmoi re-runs the install script automatically.

### 2. GUI Detection (`_has_gui()`)

The install script checks for a display server before installing GUI packages:

```bash
_has_gui() {
    command -v Xorg &>/dev/null || \
    command -v Xwayland &>/dev/null || \
    command -v gnome-shell &>/dev/null || \
    # ... more checks ...
}

# Usage in install script
if _has_gui; then
    # Install GUI packages from Aptfile_ubuntu_gui
fi
```

This prevents installing GUI packages on headless/server systems.

### 3. Package Manager Wrappers

All package managers have wrapper scripts that:

1. **Install/remove** packages via the native package manager
2. **Extract** the full package list after changes
3. **Update** the relevant manifest file
4. **Commit & push** the manifest change to GitHub

**Wrapper scripts location:** `dot_local/bin/`

| Wrapper | Command | Package Manager |
|---------|---------|-----------------|
| `aptw` | `apt` | Ubuntu/Debian/RPi |
| `dnfw` | `dnf`/`yum` | Fedora desktop |
| `pacmanw` | `pacman` | Arch/OmArchy |
| `yayw` | `yay` | Arch AUR |
| `breww` | `brew` | macOS/Linuxbrew |
| `ostreew` | `rpm-ostree` | Fedora Atomic |
| `snapw` | `snap` | Ubuntu desktop |
| `masw` | `mas` | macOS App Store |
| `flatpakw` | `flatpak` | Linux desktop/Atomic |
| `scoopw` | `scoop` | Windows |

> All wrappers now write the **per-hostname overlay** (`<Manager>file_<hostname>`),
> not the shared profile base. See "Layered cascade" above.

#### Example: Installing a Package

```bash
# Direct install (no wrapper)
apt install htop

# Gets aliased to wrapper (Linux non-Fedora)
apt install htop  # → aptw install htop

# Steps that happen automatically:
# 1. aptw install htop
# 2. Detect MACHINE_PROFILE (ubuntu-desktop) -> base = Aptfile_ubuntu_desktop
# 3. Compute delta: installed (apt-mark showmanual) minus the base
# 4. Write the delta to the HOST OVERLAY: Aptfile_<hostname>  (base is untouched)
# 5. git add / commit / pull --rebase / push the overlay
```

---

## Shell Aliases

Wrappers are transparently integrated via shell aliases (set in `10-aliases.zsh`, `10-aliases.bash`, etc.):

### Ubuntu/Debian/RPi
```bash
apt() { command aptw "$@"; }
```

### Fedora Desktop
```bash
dnf() { command dnfw "$@"; }
yum() { command dnfw "$@"; }
```

### Fedora Atomic
```bash
function rpm-ostree() { ostreew "$@"; }
```

### Arch/OmArchy
```bash
pacman() { pacmanw "$@"; }
yay() { yayw "$@"; }
```

### All Platforms
```bash
alias b='breww'
```

---

## Workflow: Adding a New Package

### 1. Install via wrapper (automatic sync)

```bash
# Ubuntu/Debian
apt install newtool

# Fedora
dnf install newtool

# Arch
pacman -S newtool      # → pacmanw -S newtool

# Homebrew (macOS/Linuxbrew)
breww install newtool
```

### 2. Wrapper automatically updates manifest

The wrapper:
- Installs the package
- Extracts the full package list
- Writes to the correct manifest file
- Commits and pushes automatically

### 3. Verify the change

```bash
# Check what was committed
git log -1

# Preview the manifest change
chezmoi diff dot_private/Aptfile_ubuntu_desktop
```

### 4. Manual verification (optional)

Edit a manifest directly to audit/adjust:

```bash
# Edit manifest in chezmoi source
chezmoi edit dot_private/Aptfile_ubuntu_desktop

# Or directly in source
nvim ~/.local/share/chezmoi/dot_private/Aptfile_ubuntu_desktop
```

Then sync:
```bash
chezmoi re-add dot_private/Aptfile_ubuntu_desktop
```

---

## Workflow: Removing a Package

### 1. Remove via wrapper

```bash
# Ubuntu/Debian
apt remove oldtool

# Fedora
dnf remove oldtool

# Arch
pacman -R oldtool      # → pacmanw -R oldtool
```

### 2. Wrapper automatically updates manifest

Same process as installation — the package is removed from the manifest and synced.

---

## Platform-Specific Notes

### macOS

- Uses `Brewfile.tmpl` as entry point (routes to `Brewfile_macos`, `Brewfile_pro`, `Brewfile_personal`)
- `mas` (Mac App Store) is used for App Store apps on personal profile only
- Desktop casks are NOT in GUI manifests (they install via `brew bundle`)

### Ubuntu/Fedora Desktop

- **Hybrid native/Flatpak approach:**
  - Base packages from native package manager (apt/dnf)
  - GUI apps from native repos (not Flatpak by default)
- Separate manifests for base vs GUI apps
- GUI manifests only processed when display server detected

### Arch/OmArchy

- Separate base (pacman) and AUR (yay) manifests
- OmArchy supports optional config overrides for:
  - Shell configuration (zsh/bash/starship)
  - Neovim configuration
  - Tmux configuration
  - Git configuration
  - Window manager configuration (Hyprland/etc.)

### Raspberry Pi

- Base packages via apt
- GUI packages via apt (limited GUI support on RPi)
- Pi-Apps integration for curated graphical applications
- Limited Neovim support (runs on RPi but slower)

### Fedora Atomic

- Uses `rpm-ostree` for immutable package management
- No package wrapper (uses `ostreew` but less aggressive auto-sync)

---

## File Permissions

All manifest files in `dot_private/` have `0600` permissions (read/write owner only):

```bash
# These are private to the user
-rw------- Aptfile_ubuntu_desktop
-rw------- Dnffile_fedora_desktop
-rw------- Pacfile_arch_desktop
```

This is enforced by chezmoi's `private_` prefix in the source directory naming convention.

---

## Integration with Installation Scripts

### Main Install Script
**File:** `.chezmoiscripts/02-install/run_onchange_install-linux-packages.sh.tmpl`

This script:
1. Detects platform (Ubuntu/Fedora/Arch/RPi/Debian)
2. Checks for display server via `_has_gui()`
3. Installs base packages from appropriate manifest
4. Installs GUI packages only if display server present
5. Installs CLI tools (gh, uv, starship, etc.)

### Homebrew Install Script
**File:** `.chezmoiscripts/02-install/run_after_brew-bundle.sh.tmpl`

This script:
1. Runs `brew bundle` with `Brewfile`
2. Handles Linuxbrew on Linux
3. Auto-syncs after installation

---

## Troubleshooting

### Manifest Not Updating

**Problem:** You installed a package but the manifest didn't update.

**Solution:** Check if you used the wrapper:
```bash
# Wrong - doesn't trigger wrapper
/usr/bin/apt install htop

# Correct - uses wrapper via alias
apt install htop
```

Verify the alias is active:
```bash
which apt
# Should output: apt: aliased to aptw
```

### Wrapper Script Not Found

**Problem:** `aptw` command not found.

**Solution:** Verify the script exists:
```bash
ls -la ~/.local/bin/apt*
ls -la ~/.local/share/chezmoi/dot_local/bin/
```

If missing, re-apply dotfiles:
```bash
chezmoi apply
```

### Manual Manifest Sync

**Problem:** You edited a manifest manually and need to sync.

**Solution:** Use `chezmoi re-add`:
```bash
chezmoi re-add dot_private/Aptfile_ubuntu_desktop
```

Wrapper scripts commit and push owned manifest changes explicitly. Plain `chezmoi re-add` updates the source tree; commit explicitly unless `CHEZMOI_AUTO_GIT=1` was used when rendering chezmoi config.

---

## Last Updated

**Date:** 2026-05-31
**Changes:** Layered cascade — shared per-profile base + per-hostname overlay across all managers (brew/apt/dnf/pacman/AUR/rpm-ostree/snap/mas/flatpak); wrappers now dump the machine delta to `<Manager>file_<hostname>` instead of clobbering the shared base; flatpak onboarded into manifests with `flatpakw`.
