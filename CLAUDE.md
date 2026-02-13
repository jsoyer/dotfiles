# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a chezmoi-managed dotfiles repository for cross-platform configuration (macOS, Fedora, Raspberry Pi, Windows). All configurations use **Catppuccin Mocha** theme (Snazzy on Linux/RPi).

## Key Commands

```bash
# Apply changes to home directory
chezmoi apply

# Preview what would be applied
chezmoi diff

# Update from git and apply
chezmoi update

# Add/re-add a file to chezmoi
chezmoi add ~/.config/tool/config
chezmoi re-add ~/.config/tool/config  # Auto-commits + auto-pushes

# Validate configuration
chezmoi doctor
chezmoi verify
```

Note: `chezmoi.toml` has `autoAdd`, `autoCommit`, and `autoPush` enabled - changes are automatically synced to GitHub.

## Chezmoi File Naming Conventions

- `dot_` prefix → creates dotfile (e.g., `dot_zshrc` → `~/.zshrc`)
- `.tmpl` suffix → processed as Go template
- `executable_` prefix → file gets executable permissions
- `private_` prefix → restricted permissions (0600)
- `run_once_*.tmpl` → scripts that run once on first apply
- `run_onchange_*.tmpl` → scripts that run when file content changes

## Templating Patterns

Templates use Go text/template with chezmoi data. Common patterns:

```go
{{- if eq .chezmoi.os "darwin" }}
# macOS-specific
{{- else if eq .chezmoi.os "linux" }}
# Linux-specific
{{- end }}

{{- if lookPath "op" }}
# 1Password CLI available
{{- end }}

{{- if env "TOOLBOX_PATH" }}
# Running in Fedora Toolbox container
{{- end }}
```

Available data in templates: `.chezmoi.os`, `.chezmoi.arch`, `.chezmoi.hostname`, `.chezmoi.homeDir`, plus custom data from `chezmoi.toml` (`.github_user`, `.name`, `.email`).

## Architecture

### Shell Configuration (`dot_zsh/`, `dot_bash/`)
Numbered files loaded in order:
- `00-env` - Platform detection, environment variables
- `01-path` - PATH management with lazy loading
- `02-completions` - Completion system (zsh only)
- `10-aliases` - Command aliases (eza, bat, nvim, etc.)
- `20-functions` - Custom shell functions
- `30-keybindings` - Vim-style keybindings
- `99-integrations` - FZF, Atuin, autosuggestions, syntax highlighting

### External Dependencies (`.chezmoiexternal.toml`)
Git repos auto-refreshed weekly:
- Oh-My-Zsh + Powerlevel10k theme
- zsh-autosuggestions, zsh-syntax-highlighting
- Tmux Plugin Manager (TPM)

### Bootstrap Scripts (`scripts/`)
- `bootstrap.sh` - Multiplatform bootstrap (macOS, Fedora, RPi/Debian)
- `bootstrap.ps1` - Windows bootstrap (Scoop + chezmoi)

### Setup Scripts (`.chezmoiscripts/`)
- `run_once_00_install-xcode-devtools.sh.tmpl` - macOS Xcode CLI tools
- `run_once_01_install_homebrew.sh.tmpl` - Homebrew installation
- `run_once_00_install-linux-deps.sh.tmpl` - APT packages + fonts + chsh for RPi
- `run_once_10_setup_fedora_standard.sh.tmpl` - DNF packages for Fedora
- `run_once_10_setup_fedora_atomic.sh.tmpl` - rpm-ostree packages for Fedora Atomic
- `run_once_install_scoop_packages.ps1.tmpl` - Scoop packages for Windows
- `run_once_install_flatpak_packages.sh.tmpl` - Flatpak packages for Fedora Atomic
- `run_onchange_after_brew-bundle.sh.tmpl` - Runs `brew bundle` when Brewfile changes

### Platform Profiles
Configuration adapts based on:
- **macOS** (`darwin`): Full setup with Homebrew, pyenv
- **Fedora** (`linux` + `lookPath "dnf"`): DNF packages, Flatpak
- **Fedora Atomic** (`lookPath "rpm-ostree"`): Minimal bash, container-focused
- **Toolbox** (`env "TOOLBOX_PATH"`): Container environment, zsh-only
- **Raspberry Pi** (kernel detection): APT packages, Gruvbox theme
- **Windows** (`eq .chezmoi.os "windows"`): Scoop packages, minimal config (git, tmux, bash)

### Key Directories
- `dot_config/` - XDG config files (nvim, starship, tmux, wezterm, etc.)
- `dot_private/` - Brewfiles (`Brewfile_pro`, `Brewfile_personal`, `Brewfile_common`)
- `dot_local/bin/` - Custom scripts (e.g., `breww` - Homebrew wrapper with auto-sync)
- `dot_ssh/` - SSH config with 1Password integration (templated)

## Lua Diagnostics Note

The `vim` global warnings in Neovim Lua files (`dot_config/nvim/`) are expected - `vim` is a runtime global provided by Neovim, not defined in the files themselves.
