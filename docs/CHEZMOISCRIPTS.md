# Chezmoi Scripts Pipeline

This directory contains the automated setup and maintenance scripts that run during `chezmoi apply` and `chezmoi update`. Scripts are organized into numbered stages that execute in sequence, each handling a specific phase of system configuration.

## Pipeline Stages

### 01-setup (First-time system setup)

Runs once on first apply to establish base system prerequisites per operating system.

| Script | Trigger | OS | Purpose |
|--------|---------|-----|---------|
| `run_once_setup-macos.sh` | Once | macOS | Install Xcode Command Line Tools and Homebrew |
| `run_once_setup-linux.sh` | Once | Linux | Configure locale, enable repos (COPR/APT/DNF/AUR), install Tailscale |

**Key behaviors:**
- **macOS**: Detects Xcode CLI tools, downloads if needed, accepts T&Cs, installs Homebrew
- **Linux**:
  - Generates en_US.UTF-8 locale on Raspberry Pi / Debian / Ubuntu / Arch
  - Enables third-party repos:
    - Ubuntu Desktop: Brave, Chrome, Signal, Zed
    - Fedora: COPR repos (eza, starship, vivid, nushell)
    - Arch: Automatic AUR access via pacman
  - Installs Tailscale on all profiles except toolbox

---

### 02-install (Package and tool installation)

Handles manifests-based package installation and CLI tool setup, runs on manifest changes.

| Script | Trigger | OS/Profiles | Purpose |
|--------|---------|-----|---------|
| `run_onchange_install-linux-packages.sh` | Manifest change | All Linux | Install packages from Aptfile/Dnffile/Pacfile manifests, GitHub CLI, 1Password CLI, uv |
| `run_onchange_after_brew-bundle.sh` | Manifest change | macOS | Run post-Homebrew tasks (setup Python, Node via version managers) |
| `run_once_install-linuxbrew.sh` | Once | Linux (non-standard) | Install Linuxbrew for systems without native package managers |
| `run_once_install-1password.sh` | Once | macOS, Linux | Install 1Password CLI via official repos |
| `run_once_install-1password.ps1` | Once | Windows | Install 1Password CLI via Scoop |
| `run_once_install-windows-packages.ps1` | Once | Windows | Install packages from Scoop manifests |
| `run_once_install-toolboxes.sh` | Once | Fedora (host) | Create and configure Fedora toolbox containers |
| `run_once_install-linux-flatpak.sh` | Once | Linux Desktop | Install Flatpak and optional Flatpak apps (fallback GUI apps) |
| `run_once_cleanup-flatpak-to-native.sh` | Once | Linux Desktop | Remove Flatpak duplicates when native packages become available |
| `run_once_install-pi-apps.sh` | Once | Raspberry Pi (GUI) | Install Pi-Apps manager and GUI applications (Brave, Signal, Obsidian, etc.) |
| `run_once_install-claude-plugins.sh` | Once | Desktop profiles | Install Claude Code plugins (octo@nyldn-plugins, LSP plugins) if `install_ocx` enabled |
| `run_once_install-opencode-tools.sh` | Once | Desktop profiles | Install OpenCode CLI tools (ocx, oh-my-openagent) if `install_ocx` enabled |

**Manifest system:**
All packages are declared in `dot_private/` manifest files:
- **Ubuntu/Debian**: `Aptfile_ubuntu_server`, `Aptfile_ubuntu_desktop`, `Aptfile_debian`, `Aptfile_rpi`, plus `_gui` variants
- **Fedora**: `Dnffile_fedora_server`, `Dnffile_fedora_desktop`, plus `_gui` variant
- **Arch/OmArchy**: `Pacfile_arch_desktop`, `Pacfile_arch_server`, `Pacfile_aur_desktop`, `Pacfile_aur_gui`, `Pacfile_omarchy`
- **Fedora Atomic**: `Rpmfile_fedora_atomic`

The scripts detect manifest changes via SHA256 checksums embedded in templates — when a manifest changes, the script automatically reruns.

**CLI tools installation logic:**
- **1Password CLI**: Installed via official apt/dnf/scoop repos (not from manifests)
- **GitHub CLI (gh)**: Installed via official apt keyring (not in standard repos)
- **uv (Python installer)**: Installed via `curl | sh` (provides `uvx` for Python-based MCP servers)
- **Starship (prompt)**: Installed via official `sh` script when not in package repos
- **eza (ls replacement)**: Installed via `cargo install` when not in package repos (Ubuntu Server, some others)

**GUI detection:**
The `_has_gui()` function detects display servers:
```bash
command -v Xorg &>/dev/null ||
command -v Xwayland &>/dev/null ||
command -v gnome-shell &>/dev/null ||
command -v plasmashell &>/dev/null ||
command -v hyprctl &>/dev/null ||
command -v sway &>/dev/null ||
command -v startx &>/dev/null
```

GUI-specific scripts (Pi-Apps, Flatpak, plugins) only run if a display server is detected.

**install_ocx toggle:**
Defined in `.chezmoi.toml.tmpl` (line 51), this boolean prompt appears on first apply for desktop profiles (mac-personal, fedora-desktop, toolbox, ubuntu-desktop, arch-desktop, omarchy). When enabled, it triggers:
- `run_once_install-claude-plugins.sh` — Install Claude Code plugins
- `run_once_install-opencode-tools.sh` — Install OpenCode extensions

---

### 03-configure (Configuration and dynamic setup)

Runs once or on manifest changes to configure services, generate configs, and sync external resources.

| Script | Trigger | OS | Purpose |
|--------|---------|-----|---------|
| `run_once_configure-gpg.sh` | Once | macOS, Linux | Configure GPG key trust settings |
| `run_once_configure-atuin.sh` | Once | All | Configure Atuin history server and sync |
| `run_once_configure-linux.sh` | Once | Linux Desktop | Install and configure desktop-specific tools (BTRFS snapshots, hypervisor, etc.) |
| `run_onchange_generate-ssh-config.sh` | Manifest change | macOS, Linux | Generate SSH config from template, read keys from 1Password |
| `run_onchange_configure-mail.sh` | Manifest change | macOS, Linux | Configure isync (mbsync), msmtp, neomutt using 1Password integration |
| `run_after_sync-aictx.sh` | Every apply | Non-Windows | Maintain `~/.aictx/{skills,agents,...}` cache and refresh CLI symlinks (`~/.claude`, `~/.qwen`, `~/.vibe`, `~/.codex`, `~/.opencode`, `~/.gemini`) |

**Key functionality:**

**AICTX Cache + Symlink Sync:**
- **Source**: `~/.aictx/{skills,agents}` populated from ChezMoi-managed `dot_agents/`
- **Consumers**: .claude, .qwen, .vibe, .codex, .opencode, .gemini
- **Mechanism**: Copies repo skills/agents into cache, then creates relative symlinks to `../../.aictx/*`
- **Trigger**: Runs after every `chezmoi apply` to keep cache and symlinks fresh
- **Cleanup**: Removes stale symlinks if cache entries disappear

**SSH Config Generation:**
- Reads SSH key passphrases from 1Password (skips gracefully if unavailable)
- Generates `~/.ssh/config` from template

**Mail Configuration:**
- Integrates with 1Password CLI for password retrieval
- Configures mbsync, msmtp, neomutt for IMAP/SMTP

---

### 04-update (Periodic update tasks)

Runs on manifest changes or when triggered by chezmoi update flow.

| Script | Trigger | OS | Purpose |
|--------|---------|-----|---------|
| `run_onchange_update-homebrew.sh` | Brewfile change | macOS | Run `brew bundle`, upgrade Homebrew and installed packages |
| `run_onchange_update-linux.sh` | Package manifest change | Linux (non-atomic) | Run `apt update && apt upgrade` or `dnf upgrade` or `pacman -Syu` |
| `run_onchange_update-appstore.sh` | Once | macOS | Enable automatic app updates via Mac App Store CLI |
| `run_onchange_update-windows.ps1` | Scoop manifest change | Windows | Run `scoop update` and upgrade installed packages |

---

### 05-maintenance (Always-running maintenance)

Runs every apply to maintain system health.

| Script | Trigger | OS | Purpose |
|--------|---------|-----|---------|
| `run_always_maintenance-container.sh` | Always | Fedora Atomic + Toolbox | Enable auto-updates, manage container resources, cleanup old images |

---

## Profile Detection

The system detects machine profile from multiple signals in `.chezmoi.toml.tmpl`:

| Profile | Detection | Example Hostname |
|---------|-----------|-----------------|
| `mac-personal` | macOS, not "jsoyer-macOS" | Standard Mac |
| `mac-pro` | macOS + "jsoyer-macOS" | Work MacBook Pro |
| `ubuntu-server` | Ubuntu without "desktop" in hostname | ubuntu-server-01 |
| `ubuntu-desktop` | Ubuntu + "desktop" in hostname | ubuntu-desktop-01 |
| `fedora-desktop` | Fedora DNF (not atomic) + "desktop" in hostname | fedora-desktop-01 |
| `fedora-server` | Fedora DNF + "server" in hostname | fedora-server-01 |
| `fedora-atomic` | rpm-ostree (immutable distros) | Fedora Silverblue/Kinoite |
| `toolbox` | Running in Fedora Toolbox container (/.toolboxenv exists) | Inside container |
| `arch-desktop` | Arch Linux + "desktop" in hostname | arch-desktop-01 |
| `arch-server` | Arch Linux + "server" in hostname | arch-server-01 |
| `omarchy` | OmArchy Linux distribution (osRelease.id = "omarchy") | OmArchy |
| `rpi` | Raspberry Pi (raspbian/raspios osRelease) | Detected by `/proc/device-tree/model` |
| `debian` | Generic Debian | debian-01 |
| `windows` | Windows OS | Standard Windows |

**Interactive prompts** ask for confirmation when hostname doesn't match patterns.

---

## Chezmoi Template Syntax

All `.sh.tmpl` and `.ps1.tmpl` scripts use Go text/template with chezmoi data:

```bash
{{- if eq .chezmoi.os "darwin" }}
# macOS-specific code
{{- else if eq .chezmoi.os "linux" }}
# Linux-specific code
{{- end }}

{{- if lookPath "command" }}
# 'command' is in PATH
{{- end }}

{{- if stat "/path/to/file" }}
# /path/to/file exists
{{- end }}

{{- if env "ENV_VAR" }}
# ENV_VAR is set
{{- end }}

# Include file contents with SHA256 for manifest-driven reruns
{{- include "dot_private/Aptfile_ubuntu_desktop" | sha256sum }}
```

Available template data:
- `.chezmoi.os` — "darwin", "linux", "windows"
- `.chezmoi.hostname` — system hostname
- `.chezmoi.homeDir` — home directory path
- `.chezmoi.arch` — "amd64", "arm64", etc.
- `.chezmoi.osRelease.id` — "ubuntu", "fedora", "arch", "raspbian", "omarchy", etc.
- `index . "machine_profile"` — detected profile (from data.machine_profile)
- `lookPath "cmd"` — true if cmd exists in PATH
- `stat "/path"` — true if path exists
- `env "VAR"` — environment variable value
- `has $profile $list` — true if profile in list
- `or`, `and`, `eq` — boolean operators
- `promptBoolOnce`, `promptStringOnce` — interactive prompts (cached in chezmoi state)

---

## Execution Order

Chezmoi executes scripts in alphabetical order within each stage directory. The pipeline flow:

```
01-setup/*.sh       → System prerequisites
   ↓
02-install/*.sh     → Package and tool installation
   ↓
03-configure/*.sh   → Configuration and secrets setup
   ↓
04-update/*.sh      → Manifest-based updates
   ↓
05-maintenance/*.sh → Maintenance tasks
```

Each stage completes before the next begins. Trigger conditions (`run_once_*` vs `run_onchange_*`) are checked per-script.

---

## Manifest Files

Located in `dot_private/` (not committed to reduce noise):

- `Aptfile_ubuntu_server` — Core CLI tools
- `Aptfile_ubuntu_desktop` — Ubuntu Desktop + GUI apps
- `Aptfile_ubuntu_gui` — Additional GUI apps
- `Aptfile_debian` — Debian minimal
- `Aptfile_rpi` — Raspberry Pi specific
- `Aptfile_rpi_gui` — Pi GUI apps
- `Dnffile_fedora_server` — Fedora Server CLI
- `Dnffile_fedora_desktop` — Fedora Desktop + GUI
- `Dnffile_fedora_gui` — Additional Fedora GUI apps
- `Pacfile_arch_desktop` — Arch Desktop CLI
- `Pacfile_arch_server` — Arch Server minimal
- `Pacfile_aur_desktop` — AUR packages (arch-desktop)
- `Pacfile_aur_gui` — AUR GUI packages
- `Pacfile_arch_gui` — Arch official GUI packages
- `Pacfile_omarchy` — OmArchy specific packages
- `Rpmfile_fedora_atomic` — Fedora Atomic/Silverblue
- `Brewfile_*` — Homebrew packages (macOS)
- `Scoopfile.json` — Scoop packages (Windows)

Each package list is simple, one per line, with comment lines starting with `#`.

---

## Error Handling

Scripts use `set -euo pipefail` (shell) for fail-fast behavior:
- `-e` — Exit on first error
- `-u` — Error on undefined variables
- `-o pipefail` — Fail if any command in pipeline fails

Non-fatal operations use `|| true` to continue:
```bash
sudo systemctl enable --now tailscaled || true
```

GUI-detection scripts check `_has_gui()` and exit cleanly (code 0) if no display:
```bash
if ! _has_gui; then
    echo "No display server detected, skipping"
    exit 0
fi
```

---

## User Output

All scripts use emoji prefixes for visual feedback (kept as per user preference):
- 🍎 macOS-specific
- 🍺 Homebrew
- 📦 Package installation
- 🔒 Security/Tailscale
- 📔 Configuration
- ✅ Completion messages

---

## Integration with Chezmoi State

Scripts can use chezmoi's state caching for interactive prompts:
```bash
machine_profile = "{{ promptStringOnce . "machine_profile" "Machine profile [ubuntu-server/ubuntu-desktop]" "ubuntu-server" }}"
install_ocx = {{ promptBoolOnce . "install_ocx" "Install OpenCode extensions?" false }}
```

These are stored in `~/.local/share/chezmoi/state.buc` (encrypted if age is available) and reused across applies.

---

## Customization

To add a new script:
1. Create `NX-description/run_once_or_onchange_name.sh.tmpl` in appropriate stage
2. Add platform detection using Go templates
3. Include manifest checksums for manifest-driven reruns
4. Use `set -euo pipefail` for error handling
5. Add emoji prefixes to echo statements
6. Test on target profile: `chezmoi apply --diff` then `chezmoi apply`

---

## Related Files

- `.chezmoi.toml.tmpl` — Configuration templates and profile detection
- `.chezmoiignore.tmpl` — Files excluded per profile
- `.chezmoiexternal.toml.tmpl` — External Git repos auto-refreshed weekly
- `dot_private/` — Manifest files (packages, Brewfiles, etc.)
- `dot_agents/dot_skill-lock.json` — AI skill dependency tracking
