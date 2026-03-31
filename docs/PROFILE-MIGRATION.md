# Profile Migration Guide

> Guide to changing machine profiles in the dotfiles repository. Useful when transitioning between server/desktop, distros, or hardware configurations.

**Last Updated:** 2026-03-28

---

## Table of Contents

1. [Understanding Profiles](#understanding-profiles)
2. [Available Profiles](#available-profiles)
3. [How Profiles Are Detected](#how-profiles-are-detected)
4. [Changing Your Profile](#changing-your-profile)
5. [Migration Scenarios](#migration-scenarios)
6. [Cleanup Procedures](#cleanup-procedures)
7. [Troubleshooting](#troubleshooting)

---

## Understanding Profiles

This dotfiles repository uses **machine profiles** to automatically adapt configurations based on:

- **Operating system** (macOS, Linux, Windows)
- **Linux distribution** (Ubuntu, Fedora, Arch, OmArchy, Debian, Raspberry Pi)
- **Hardware** (Mac Pro vs. MacBook, Raspberry Pi detection)
- **Environment** (server, desktop, container, CI/CD)
- **Hostname pattern** (e.g., `ubuntu-server*` triggers server profile)

The profile determines:

| Profile Element | Examples |
|---|---|
| **Theme** | Catppuccin Mocha (desktop) vs. Snazzy (server/RPi) |
| **Package Manager** | apt, dnf, pacman, brew, Scoop |
| **GUI Support** | Graphical tools only on desktop profiles |
| **Shell Config** | Full config on desktop, minimal on servers |
| **Tools Installed** | Desktop: GUI apps, Neovim, fancy terminals. Server: CLI only |
| **Aliases** | Same across all profiles, tmux prefix depends on profile |

---

## Available Profiles

### macOS Profiles

| Profile | Detection | Package Manager | Theme | GUI Support |
|---|---|---|---|---|
| **mac-pro** | Hostname: `jsoyer-macOS` | Homebrew | Catppuccin Mocha | Native (Aerospace WM) |
| **mac-personal** | macOS (all other hosts) | Homebrew | Catppuccin Mocha | Native (Aerospace WM) |

### Ubuntu Profiles

| Profile | Detection | Package Manager | Theme | GUI Support |
|---|---|---|---|---|
| **ubuntu-desktop** | Ubuntu, hostname not `ubuntu-server*` | apt + Linuxbrew | Catppuccin Mocha | Hybrid (native apt) |
| **ubuntu-server** | Ubuntu, hostname matches `ubuntu-server*` | apt | Snazzy | None (SSH-friendly) |

### Fedora Profiles

| Profile | Detection | Package Manager | Theme | GUI Support |
|---|---|---|---|---|
| **fedora-desktop** | Fedora, hostname not `fedora-server*` | dnf + Linuxbrew | Catppuccin Mocha | Hybrid (native dnf) |
| **fedora-server** | Fedora, hostname matches `fedora-server*` | dnf | Snazzy | None (SSH-friendly) |
| **fedora-atomic** | `rpm-ostree` command available | rpm-ostree | Snazzy | None (immutable) |

### Arch & OmArchy Profiles

| Profile | Detection | Package Manager | Theme | GUI Support |
|---|---|---|---|---|
| **arch-desktop** | Arch Linux, hostname not `arch-server*` | pacman + Linuxbrew | Catppuccin Mocha | Hybrid (native pacman) |
| **arch-server** | Arch Linux, hostname matches `arch-server*` | pacman | Snazzy | None (SSH-friendly) |
| **omarchy** | `/etc/os-release` ID = `omarchy` | pacman + Linuxbrew | Catppuccin Mocha | Hybrid (native pacman) |

### Other Profiles

| Profile | Detection | Package Manager | Theme | GUI Support |
|---|---|---|---|---|
| **debian** | Debian (non-RPi) | apt | Snazzy | None (minimal) |
| **rpi** | Hardware: `/proc/device-tree/model` contains "raspberry pi" | apt + Linuxbrew | Snazzy | Pi-Apps |
| **toolbox** | Running in Fedora Toolbox container (`TOOLBOX_PATH` env var set) | dnf + Linuxbrew | Snazzy | None (container) |
| **windows** | Windows (cygwin/msys/mingw) | Scoop | N/A | Native |

---

## How Profiles Are Detected

Profiles are detected in this order (first match wins):

### Detection Flow (in `.chezmoi.toml.tmpl`)

```
1. Windows? → windows
2. macOS?
   a. Hostname jsoyer-macOS? → mac-pro
   b. Otherwise → mac-personal
3. Linux?
   a. Raspberry Pi hardware? → rpi (ask if ambiguous)
   b. In CI? → ubuntu-server
   c. Ubuntu?
      i. Hostname ubuntu-server*? → ubuntu-server
      ii. Hostname ubuntu-desktop*? → ubuntu-desktop
      iii. Otherwise → ask user
   d. Fedora Atomic (rpm-ostree present, not in toolbox)? → fedora-atomic
   e. Fedora Toolbox? → toolbox
   f. Fedora (dnf present)?
      i. Hostname fedora-server*? → fedora-server
      ii. Otherwise → fedora-desktop (ask if ambiguous)
   g. OmArchy? → omarchy
   h. Arch Linux?
      i. Hostname arch-server*? → arch-server
      ii. Otherwise → arch-desktop (ask if ambiguous)
   i. Debian? → debian
   j. Otherwise → ask user
```

### Runtime Detection (in shell)

Once applied, the shell detects the profile at startup via:

**Zsh** (`~/.zsh/00-env.zsh`): Sets `MACHINE_PROFILE` environment variable
**Bash** (`~/.bash/00-env.bash`): Sets `MACHINE_PROFILE` environment variable

The runtime detection uses the same logic as chezmoi and ensures consistency across sessions.

---

## Changing Your Profile

You have **three methods** to change your profile:

### Method 1: Edit chezmoi Configuration (Recommended)

Most reliable and controllable approach:

```bash
# 1. Find your chezmoi config
chezmoi status | head -5  # Shows the source directory

# 2. Edit the config file
nvim ~/.config/chezmoi/chezmoi.toml

# 3. Find the machine_profile line and change it:
# OLD:
#   machine_profile = "ubuntu-server"
# NEW:
#   machine_profile = "ubuntu-desktop"

# 4. Apply the new configuration
chezmoi apply -v
```

The `machine_profile` key in `chezmoi.toml` is the source of truth. Changing it directly bypasses all detection logic.

### Method 2: Re-run Chezmoi Init (Interactive)

Chezmoi will re-ask you all questions:

```bash
chezmoi init
```

This will:
- Detect your OS and distro
- Prompt for machine profile if ambiguous
- Update `~/.config/chezmoi/chezmoi.toml`
- NOT apply changes automatically

After confirming the new profile looks correct:

```bash
chezmoi apply -v
```

### Method 3: Change Hostname (Automatic Detection)

For server/desktop transitions where hostname is the determining factor:

```bash
# Change hostname (requires sudo/root)
sudo hostnamectl set-hostname ubuntu-desktop-01

# Or on macOS
sudo scutil -set ComputerName "ubuntu-desktop-01"

# Then re-run init to re-detect
chezmoi init
chezmoi apply -v
```

Chezmoi will detect the new hostname and change the profile automatically. This works for:

- `ubuntu-server*` → `ubuntu-desktop` or vice versa
- `fedora-server*` → `fedora-desktop` or vice versa
- `arch-server*` → `arch-desktop` or vice versa

---

## Migration Scenarios

### Scenario 1: Server → Desktop (Same Distro)

**Example:** `ubuntu-server` → `ubuntu-desktop`

#### Changes:

- Theme: Snazzy → Catppuccin Mocha
- GUI apps installed: Yes
- Desktop config (`~/.config/aerospace`, `~/.config/sketchybar`, etc.)
- Additional desktop development tools

#### Steps:

```bash
# 1. Verify current profile
echo $MACHINE_PROFILE

# 2. Method A: Change hostname (simplest for server→desktop)
sudo hostnamectl set-hostname ubuntu-desktop-01

# 3. Re-detect profile
chezmoi init

# 4. Verify the change
cat ~/.config/chezmoi/chezmoi.toml | grep machine_profile

# 5. Apply new configuration
chezmoi apply -v

# 6. Cleanup old theme settings
rm -rf ~/.config/starship/starship-ssh.toml*
mkdir -p ~/.cache/vivid && rm -f ~/.cache/vivid/ls-colors-snazzy.txt
rm -f ~/.cache/shell/*

# 7. Reload shell
exec zsh
# or
exec bash

# 8. Verify new theme applied
echo $BAT_THEME  # Should be: Catppuccin Mocha
echo $FZF_DEFAULT_OPTS  # Should show Catppuccin colors
```

#### Verify Desktop Was Applied:

```bash
# Desktop config should exist
ls -la ~/.config/aerospace/           # macOS only
ls -la ~/.config/sketchybar/          # macOS only
ls -la ~/.config/wezterm/

# Shell should use full config
cat ~/.config/starship/starship.toml | head -5

# Theme should be Catppuccin Mocha
vivid generate catppuccin-mocha >/dev/null 2>&1 && echo "Theme OK" || echo "Theme failed"
```

### Scenario 2: Desktop → Server (Same Distro)

**Example:** `ubuntu-desktop` → `ubuntu-server`

#### Changes:

- Theme: Catppuccin Mocha → Snazzy (SSH-friendly, darker)
- GUI apps: Removed
- GUI configs: Ignored (but kept on disk)
- Minimal shell config
- Focus on CLI-only tools

#### Steps:

```bash
# 1. Change hostname to trigger server profile
sudo hostnamectl set-hostname ubuntu-server-01

# 2. Re-detect
chezmoi init

# 3. Verify change
cat ~/.config/chezmoi/chezmoi.toml | grep machine_profile

# 4. Apply (will ignore GUI configs but keep them)
chezmoi apply -v

# 5. Clear desktop-specific caches
rm -f ~/.cache/vivid/ls-colors-catppuccin-mocha.txt
rm -f ~/.cache/shell/*

# 6. Optionally remove GUI packages
apt remove --purge wezterm ghostty kitty alacritty  # or your GUI apps
# or
pacman -R wezterm ghostty kitty alacritty
# or
dnf remove wezterm ghostty kitty alacritty

# 7. Reload shell
exec zsh
# or
exec bash
```

#### Verify Server Config Applied:

```bash
# Shell should use compact config
cat ~/.config/starship/starship.toml | head -5
# Should reference "starship-ssh.toml" or be minimal

# Theme should be Snazzy
echo $BAT_THEME  # Should be: ansi
echo $FZF_DEFAULT_OPTS | grep "57c7ff"  # Snazzy blue color

# GUI configs should be ignored
ls ~/.config/aerospace/ 2>&1  # Should not be tracked if server
```

### Scenario 3: Ubuntu → Arch (Distro Change)

**Example:** `ubuntu-desktop` → `arch-desktop`

#### Critical Steps:

1. Install Arch Linux (or OmArchy) on the machine
2. Change **both** OS and hostname patterns
3. Clean old package manager caches
4. Re-apply configuration with new package manager

#### Steps:

```bash
# 1. Bootstrap the new Arch system
# (Usually done during Arch install)
pacman -S base linux linux-firmware

# 2. Install chezmoi on new Arch system
pacman -S chezmoi

# 3. Initialize with dotfiles and new profile
chezmoi init jsoyer
# When prompted: machine_profile → arch-desktop

# 4. Verify profile
cat ~/.config/chezmoi/chezmoi.toml | grep machine_profile

# 5. Apply configuration
chezmoi apply -v

# 6. Install packages from Arch manifest
# The manifest files are:
#   ~/.local/share/chezmoi/dot_private/Pacfile_arch_desktop (base)
#   ~/.local/share/chezmoi/dot_private/Pacfile_arch_gui (GUI)
# These are installed via your post-apply scripts

# 7. Clear old caches
rm -rf ~/.cache/vivid/*
rm -rf ~/.cache/shell/*

# 8. Reload shell
exec zsh

# 9. Verify arch packages
pacman -Q | grep "vim\\|git\\|neovim"
```

#### Package Manager Differences:

| Feature | Ubuntu | Arch |
|---|---|---|
| Base package manager | apt | pacman |
| AUR packages | N/A | yay (AUR helper) |
| Wrapper script | aptw | pacmanw / yayw |
| Manifest file | Aptfile_ubuntu_desktop | Pacfile_arch_desktop |
| GUI manifest | Aptfile_ubuntu_gui | Pacfile_arch_gui |

### Scenario 4: Arch → OmArchy

**Example:** `arch-desktop` → `omarchy`

OmArchy is Arch-based with some additional packages and community defaults. It provides an opportunity to **override specific configs** while respecting OmArchy's defaults.

#### Special Considerations:

OmArchy allows you to selectively override system configurations via `chezmoi.toml`:

```toml
[data.omarchy]
    override_shell = true    # Use your shell config (not OmArchy's)
    override_nvim = false    # Use OmArchy's Neovim (keep theirs)
    override_tmux = true     # Use your tmux config
    override_git = true      # Use your git config
    override_wm = false      # Use OmArchy's window manager
```

#### Steps:

```bash
# 1. Install OmArchy (distro image or installer)

# 2. Install chezmoi
pacman -S chezmoi

# 3. Initialize dotfiles
chezmoi init jsoyer
# When prompted, choose:
#   machine_profile → omarchy
#   Then answer the OmArchy-specific prompts:
#     override_shell: true
#     override_nvim: false (or true if you want your config)
#     override_tmux: true
#     override_git: true
#     override_wm: false (keep OmArchy's Hyprland)

# 4. Verify settings
cat ~/.config/chezmoi/chezmoi.toml | grep -A 10 "omarchy"

# 5. Apply configuration
chezmoi apply -v

# 6. Reload shell
exec zsh

# 7. Check what was applied/ignored
chezmoi status  # Shows overridden files
```

#### What Gets Skipped:

If you set `override_shell = false`, these are ignored:

```
.zsh/
.zshrc
.zprofile
.config/starship/
```

This allows OmArchy to provide its own shell setup while you keep other configs (nvim, tmux, etc.).

### Scenario 5: Fedora → OmArchy (Major Distro Change)

**Example:** `fedora-desktop` → `omarchy`

Similar to Arch → OmArchy, but requires fresh OmArchy install first.

#### Steps:

```bash
# 1. Install OmArchy (fresh)

# 2. Install chezmoi
pacman -S chezmoi

# 3. Initialize
chezmoi init jsoyer

# 4. Verify you're detecting omarchy
cat ~/.config/chezmoi/chezmoi.toml | grep machine_profile
# Should show: machine_profile = "omarchy"

# 5. Answer OmArchy-specific prompts if this is first time
# (or edit chezmoi.toml manually to set overrides)

# 6. Apply
chezmoi apply -v

# 7. Clear old dnf caches
rm -rf ~/.cache/dnf*
rm -rf ~/.cache/vivid/*

# 8. Reload
exec zsh

# 9. Verify pacman packages (not dnf)
pacman -Q | grep neovim
```

---

## Cleanup Procedures

After migrating to a new profile, clean up orphaned files and caches:

### 1. Remove Old Package Manager Artifacts

```bash
# If migrating away from Ubuntu/Debian
sudo apt clean
sudo apt autoclean
rm -f ~/.cache/apt*

# If migrating away from Fedora
sudo dnf clean all
sudo dnf autoremove
rm -f ~/.cache/dnf*

# If migrating away from Arch
sudo pacman -Sc      # Clean cache
sudo pacman -Rns $(pacman -Qdtq)  # Remove orphans
rm -f ~/.cache/pacman*

# If migrating away from Homebrew
brew cleanup
brew autoremove
rm -rf ~/Library/Caches/Homebrew/*
```

### 2. Clear Shell Caches

```bash
# Remove cached colors
rm -rf ~/.cache/vivid/*

# Remove cached shell environment
rm -rf ~/.cache/shell/*

# Clear FZF cache
rm -rf ~/.cache/fzf-cache

# Clear temporary shell files
rm -f ~/.zsh_history.lock
rm -f ~/.bash_history.lock
```

### 3. Clear Application Caches (Optional)

These are safe to remove but non-critical:

```bash
# Neovim
rm -rf ~/.cache/nvim

# Starship
rm -rf ~/.cache/starship

# Zoxide
rm -rf ~/.local/share/zoxide/*

# Atuin
rm -rf ~/.local/share/atuin/
```

### 4. Remove Old Desktop/Server Specific Files

If transitioning between desktop/server, the `chezmoiignore` prevents these from being applied, but they may exist on disk:

```bash
# If server → desktop (safe to keep, just ignored)
# If desktop → server (safe to keep, will be ignored by chezmoi)

# To remove old theme caches manually:
rm -f ~/.config/starship/starship-ssh.toml
rm -f ~/.config/starship/starship-desktop.toml

# To remove old WM configs (desktop only):
rm -rf ~/.config/aerospace/     # macOS only
rm -rf ~/.config/sketchybar/    # macOS only
rm -rf ~/.config/hypr/          # OmArchy only
rm -rf ~/.config/waybar/        # OmArchy only
```

### 5. Verify Profile Applied Correctly

```bash
# Check environment variables
echo "Profile: $MACHINE_PROFILE"
echo "Is Linux: $IS_LINUX"
echo "Is macOS: $IS_MACOS"
echo "Is Arch: $IS_ARCH"

# Check shell configuration
cat ~/.config/starship/starship.toml | head -10

# Check package manager
which apt dnf pacman brew scoop 2>/dev/null | sort -u

# Check installed tools
which neovim starship fzf bat eza

# Full health check
chezmoi doctor
```

---

## Troubleshooting

### Problem: Profile Not Detected Correctly

**Symptom:** `echo $MACHINE_PROFILE` shows wrong profile

**Root Causes:**
- chezmoi's `machine_profile` in config is wrong
- Shell is caching old profile from `~/.zsh_history` or `~/.bash_history`
- Hostname doesn't match expected pattern for auto-detection

**Solutions:**

```bash
# 1. Check what chezmoi thinks
cat ~/.config/chezmoi/chezmoi.toml | grep machine_profile

# 2. Check what shell thinks
echo $MACHINE_PROFILE

# 3. If different, reload shell
exec zsh  # or bash

# 4. If still wrong, check hostname pattern
hostname
# Should match pattern like: ubuntu-server*, arch-desktop*, etc.

# 5. If hostname is correct but still wrong, chezmoi needs update
chezmoi init
# Chezmoi will re-detect and update chezmoi.toml

# 6. Apply changes
chezmoi apply -v

# 7. Verify again
exec zsh && echo $MACHINE_PROFILE
```

### Problem: GUI Configs Applied to Server

**Symptom:** Server profile but `~/.config/aerospace` exists (macOS)

**Root Cause:** `chezmoiignore` isn't filtering correctly

**Solution:**

```bash
# 1. Verify profile
echo $MACHINE_PROFILE  # Should be ubuntu-server, fedora-server, etc.

# 2. Verify ignores are working
chezmoi status | grep aerospace

# 3. Manually remove the files (chezmoi won't auto-delete)
rm -rf ~/.config/aerospace
rm -rf ~/.config/sketchybar
rm -rf ~/.config/hypr
rm -rf ~/.config/waybar

# 4. Verify they don't reappear on next apply
chezmoi apply -v
chezmoi status | grep aerospace  # Should return nothing

# 5. If they reappear, your profile might still be wrong
echo $MACHINE_PROFILE
cat ~/.config/chezmoi/chezmoi.toml | grep machine_profile
```

### Problem: Old Theme Colors Still in Use

**Symptom:** Colors are wrong (Snazzy on desktop, Catppuccin on server)

**Root Cause:** Shell caches not cleared, or shell not reloaded

**Solutions:**

```bash
# 1. Check cached colors
ls ~/.cache/vivid/
# Should have: ls-colors-catppuccin-mocha.txt (desktop) or ls-colors-snazzy.txt (server)

# 2. Clear ALL shell caches
rm -rf ~/.cache/vivid
rm -rf ~/.cache/shell
rm -rf ~/.cache/starship
rm -rf ~/.cache/fzf*

# 3. Reload shell (creates new caches)
exec zsh
# or
exec bash

# 4. Verify correct theme
echo $BAT_THEME
echo $FZF_DEFAULT_OPTS | head -c 50  # First 50 chars

# 5. If still wrong, verify profile
echo $MACHINE_PROFILE
# Should show correct profile

# 6. If profile is correct but colors wrong, manually source environment
source ~/.zsh/00-env.zsh
# or
source ~/.bash/00-env.bash
```

### Problem: Package Manager Mismatch

**Symptom:** Trying to use apt on Fedora, or pacman on Ubuntu

**Root Cause:** Aliases not detecting profile correctly

**Solutions:**

```bash
# 1. Check profile
echo $MACHINE_PROFILE

# 2. Check what aliases are set
alias apt dnf pacman brew 2>/dev/null

# 3. Reload aliases
# The aliases are set based on MACHINE_PROFILE in:
#   ~/.zsh/10-aliases.zsh
#   ~/.bash/10-aliases.bash

# Reload shell
exec zsh
# or
exec bash

# 4. Verify correct aliases now
alias apt   # If ubuntu/debian
alias dnf   # If fedora
alias pacman  # If arch/omarchy
```

### Problem: Chezmoi Apply Fails with "File already exists"

**Symptom:** `chezmoi apply` fails saying file exists but shouldn't be managed

**Root Cause:** File conflict between old and new profile

**Solutions:**

```bash
# 1. See what conflict
chezmoi apply -v 2>&1 | grep -i "error\|conflict"

# 2. Check chezmoi status
chezmoi status

# 3. Remove the conflicting file manually
rm ~/path/to/conflicting/file

# 4. Try applying again
chezmoi apply -v

# 5. If still fails, use --force (careful!)
chezmoi apply --force -v

# 6. Verify with doctor
chezmoi doctor
```

### Problem: OmArchy Override Prompts Asking Again

**Symptom:** `chezmoi init` asks for omarchy overrides every time

**Root Cause:** Prompts configured with `promptBoolOnce` but data not persisted

**Solution:**

```bash
# 1. Edit chezmoi.toml directly
cat ~/.config/chezmoi/chezmoi.toml | grep -A 10 "omarchy"

# 2. Add your overrides manually to [data.omarchy]
nvim ~/.config/chezmoi/chezmoi.toml

# Add or update:
# [data.omarchy]
#     override_shell = true
#     override_nvim = false
#     override_tmux = true
#     override_git = true
#     override_wm = false

# 3. Save and apply
chezmoi apply -v

# 4. Next time init runs, it should remember
chezmoi init  # Should not prompt again
```

### Problem: Migration Stuck or Failed

**Last-Resort Recovery:**

```bash
# 1. Backup current chezmoi state
cp -r ~/.local/share/chezmoi ~/.local/share/chezmoi.backup

# 2. Remove chezmoi and start fresh
rm -rf ~/.local/share/chezmoi ~/.config/chezmoi

# 3. Re-initialize
chezmoi init jsoyer

# 4. When prompted, choose the NEW profile you want
# machine_profile → [your new profile]

# 5. Apply
chezmoi apply -v

# 6. Run health check
chezmoi doctor

# 7. If successful, you can delete the backup
rm -rf ~/.local/share/chezmoi.backup
```

---

## Quick Reference

### Change Profile (3 Methods)

```bash
# Method 1: Edit directly (most control)
nvim ~/.config/chezmoi/chezmoi.toml
# Edit machine_profile line
chezmoi apply -v

# Method 2: Re-init with prompts
chezmoi init
chezmoi apply -v

# Method 3: Change hostname (auto-detect)
sudo hostnamectl set-hostname ubuntu-desktop-01
chezmoi init
chezmoi apply -v
```

### Verify Profile

```bash
echo $MACHINE_PROFILE
cat ~/.config/chezmoi/chezmoi.toml | grep machine_profile
```

### Common Cleanups

```bash
# After any profile change
rm -rf ~/.cache/vivid ~/.cache/shell ~/.cache/starship
exec zsh

# Verify health
chezmoi doctor
```

### Profile Characteristics

```bash
# Check what you're working with
echo "Theme: $BAT_THEME"
echo "FZF: $FZF_DEFAULT_OPTS" | head -c 80
echo "Architecture: $(uname -m)"
echo "OS: $(uname -s)"
```

---

## Additional Resources

- [Main README](../README.md) - Overview of profiles and quick start
- [Architecture Guide](ARCHITECTURE.md) - Deep dive into profile detection and lifecycle
- [Runbook](RUNBOOK.md) - Operations and troubleshooting
- [Chezmoi Documentation](https://www.chezmoi.io/) - Official chezmoi docs
- [chezmoi Config Reference](https://www.chezmoi.io/reference/configuration-file/)

---

**Next Steps:**

- For general setup help, see [README.md](../README.md)
- For system architecture details, see [ARCHITECTURE.md](ARCHITECTURE.md)
- For day-to-day operations, see [RUNBOOK.md](RUNBOOK.md)
- For troubleshooting migrations, check the [Troubleshooting](#troubleshooting) section above
