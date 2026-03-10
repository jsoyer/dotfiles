# Dotfiles - Jerome Soyer

> Modern, comprehensive dotfiles managed with [chezmoi](https://www.chezmoi.io/) and synchronized via GitHub.

![Theme](https://img.shields.io/badge/Theme-Catppuccin%20Mocha-89b4fa?style=for-the-badge)
![Shell](https://img.shields.io/badge/Shell-Zsh%20%2B%20Bash%20%2B%20Nushell-a6e3a1?style=for-the-badge)
![Manager](https://img.shields.io/badge/Manager-Chezmoi-f38ba8?style=for-the-badge)

---

## 🎨 Theme & Philosophy

All configurations use the **Catppuccin Mocha** color palette for a consistent, eye-friendly visual experience across all tools. The setup emphasizes:

- 🎯 **Vim-first workflow** - Vim keybindings everywhere
- 🚀 **Modern CLI tools** - Replacements for traditional Unix tools
- 📦 **Modular configuration** - Clean, organized, well-documented
- 🔄 **Cross-machine sync** - Seamless setup on new machines

---

## ⚙️ Profile-Based Configuration

This setup uses `chezmoi`'s templating capabilities to apply different configurations based on `MACHINE_PROFILE`, detected at runtime from hostname, OS, and hardware. This allows for a clean separation between machine types.

| `MACHINE_PROFILE`  | Detection                              | OS       | Package Manager     | Theme          |
| ------------------ | -------------------------------------- | -------- | ------------------- | -------------- |
| `mac-pro`          | hostname `jsoyer-macOS`                | macOS    | Homebrew            | Catppuccin     |
| `mac-personal`     | macOS (other hosts)                    | macOS    | Homebrew            | Catppuccin     |
| `ubuntu-desktop`   | Ubuntu, hostname not `ubuntu-server*`  | Linux    | apt + Linuxbrew     | Catppuccin     |
| `ubuntu-server`    | Ubuntu, hostname `ubuntu-server*`      | Linux    | apt + Linuxbrew     | Snazzy         |
| `fedora-desktop`   | Fedora, hostname not `fedora-server*`  | Linux    | dnf + Linuxbrew     | Catppuccin     |
| `fedora-server`    | Fedora, hostname `fedora-server*`      | Linux    | dnf                 | Snazzy         |
| `fedora-atomic`    | `rpm-ostree` present                   | Linux    | rpm-ostree          | Snazzy         |
| `debian`           | Debian (non-RPi)                       | Linux    | apt                 | Snazzy         |
| `toolbox`          | `TOOLBOX_PATH` set                     | Linux    | (host tools)        | Snazzy         |
| `rpi`              | `/proc/device-tree/model` contains rpi | Linux    | apt + Linuxbrew     | Snazzy         |
| `windows`          | cygwin/msys/mingw                      | Windows  | Scoop               | N/A            |

---

## 📁 What's Included

### 🐚 Shells
- **Zsh** - Primary shell with Oh-My-Zsh + 48 plugins
- **Bash** - Universal fallback shell with matching configuration
- **Nushell** - Modern structured data shell
- **Fish** - Friendly interactive shell (backup)

### Terminal Emulators
- **WezTerm** - Primary (GPU-accelerated, Lua config)
- **Ghostty** - Fast, native alternative
- **Alacritty** - Lightweight alternative
- **Kitty** - Feature-rich option

### Multiplexers & Workspace Managers
- **Zellij** - Modern Rust-based multiplexer
- **Tmux** - Classic terminal multiplexer

### Development Tools
- **Neovim** - Primary editor
- **Starship** - Cross-shell prompt
- **Atuin** - Magical shell history with sync
- **Direnv** - Per-directory environment switching

### Modern CLI Replacements
| Traditional | Modern | Description |
|-------------|--------|-------------|
| `ls` | `eza` | File listings with icons & git |
| `cat` | `bat` | Syntax highlighting |
| `cd` | `zoxide` | Smart directory jumping |
| `find` | `fd` | Fast file finding |
| `grep` | `ripgrep` | Faster searching |
| `vim` | `neovim` | Hyperextensible Vim |

### macOS Desktop
- **Aerospace** - Tiling window manager (i3-like, vim keybindings)
- **Sketchybar** - Custom status bar (Catppuccin Mocha, pill-style)

### Email
- **NeoMutt** - Terminal email client
- **mbsync (isync)** - IMAP synchronization
- **msmtp** - SMTP relay
- **notmuch** - Email indexing and search

### AI Tools
- **Claude Code** - AI coding assistant (165 agents, 84 skills, 15 MCP servers)
- **OpenCode** - Alternative AI coding CLI (shared MCP config)
- **RTK** - Token optimization proxy for Claude Code
- **codecompanion.nvim** - Multi-provider AI in Neovim (Claude, OpenAI, Gemini, Mistral, Ollama + CLI agents)

### Other Tools
- **FZF** - Fuzzy finder
- **Vivid** - LS_COLORS generator
- **TheFuck** - Command corrector
- **LazyGit** - Terminal Git UI
- **gh** - GitHub CLI
- **Git, Jujutsu, Brew, Chezmoi** - Version control and system management with extensive custom aliases.

---

## 🚀 Quick Start - New Machine Setup

### One-Command Bootstrap (Recommended)

The bootstrap script detects your platform and installs everything automatically:

**macOS / Linux / Fedora / Raspberry Pi:**
```bash
curl -sL https://raw.githubusercontent.com/jsoyer/dotfiles/main/scripts/bootstrap.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/jsoyer/dotfiles/main/scripts/bootstrap.ps1 | iex
```

The bootstrap script will:
1. Detect your platform (macOS, Fedora, Debian/RPi, Windows)
2. Install prerequisites (git, package manager)
3. Install chezmoi
4. Install gh (GitHub CLI) via official repo (Debian/RPi/Fedora/Toolbox)
5. Apply all dotfiles and run platform-specific setup scripts

### Alternative: Manual Chezmoi Install

If you already have git and a package manager:

```bash
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply jsoyer
```

### Platform Differences

| Feature | macOS | Fedora Desktop | Fedora Server/Atomic | Ubuntu Desktop | Ubuntu Server / RPi | Windows |
|---------|-------|----------------|----------------------|----------------|---------------------|---------|
| **Theme** | Catppuccin Mocha | Catppuccin Mocha | Snazzy | Catppuccin Mocha | Snazzy | N/A |
| **Package Manager** | Homebrew | dnf + Linuxbrew | dnf / rpm-ostree | apt + Linuxbrew | apt + Linuxbrew | Scoop |
| **Editor** | Neovim | Neovim | Neovim | Neovim | nano | N/A |
| **Tmux Prefix** | `Ctrl+A` | `Ctrl+A` | `Ctrl+A` | `Ctrl+A` | `Ctrl+B` | `Ctrl+A` |

### Post-Installation Steps

1. **Log out and log back in** to apply shell changes
2. **Install tmux plugins**: Press tmux prefix then `I` inside tmux

---

## 📋 Manual Installation (Step-by-Step)

### 1. Install Homebrew (macOS/Linux)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install Chezmoi

```bash
brew install chezmoi
```

### 3. Initialize with Your Dotfiles

```bash
# Using GitHub username
chezmoi init jsoyer

# Or with full URL
chezmoi init https://github.com/jsoyer/dotfiles.git

# With SSH (if you have keys configured)
chezmoi init git@github.com:jsoyer/dotfiles.git
```

### 4. Preview Changes (Optional)

```bash
# See what will be applied
chezmoi diff

# List all managed files
chezmoi managed
```

### 5. Apply Configurations

```bash
# Apply all dotfiles
chezmoi apply

# Apply with verbose output
chezmoi apply -v
```

---

## 🔧 Installing Required Tools

After applying dotfiles, install the modern CLI tools:

### Core Tools

```bash
brew install \
  eza bat fd ripgrep vivid fzf zoxide atuin direnv \
  neovim starship git-delta
```

### 🐚 Shells

```bash
brew install zsh nushell fish
```

### Terminal Emulators

```bash
brew install --cask wezterm alacritty kitty
```

### Multiplexers

```bash
brew install tmux zellij
```

### Development Tools (Optional)

```bash
brew install \
  docker kubectl helm terraform \
  node npm yarn pnpm \
  python pyenv rbenv jenv \
  go rust cargo
```

### Fonts

```bash
brew install --cask \
  font-jetbrains-mono-nerd-font \
  font-fira-code-nerd-font \
  font-meslo-lg-nerd-font
```

---

## 📝 Daily Usage

### Master Machine (MacBook Pro)

This is your **source of truth** for configuration changes.

#### Approach 1: Modify in Real-time + Re-add (Recommended for Testing)

```bash
# 1. Edit config file directly
nvim ~/.config/alacritty/alacritty.toml

# 2. Test your changes
# (reload app, run commands, etc.)

# 3. Sync to chezmoi (auto-commits & pushes!)
chezmoi re-add ~/.config/alacritty/alacritty.toml
```

With `autoCommit` and `autoPush` enabled in your `chezmoi.toml`, this automatically:
- ✅ Adds changes to chezmoi
- ✅ Commits to git
- ✅ Pushes to GitHub

#### Approach 2: Edit via Chezmoi (For Simple Changes)

```bash
# 1. Edit in chezmoi
chezmoi edit ~/.config/alacritty/alacritty.toml

# 2. Apply changes
chezmoi apply

# 3. Test
```

### Secondary Machines (Mac Mini, etc.)

```bash
# Pull latest changes and apply
chezmoi update

# Or manually:
cd ~/.local/share/chezmoi
git pull
chezmoi apply
```

---

## 🎯 Common Workflows

### Adding a New Configuration File

```bash
# Add new file to chezmoi
chezmoi add ~/.config/newtool/config.toml

# Commit and push
cd ~/.local/share/chezmoi
git add .
git commit -m "feat(newtool): add initial configuration"
git push
```

### Editing an Existing Configuration

```bash
# Quick edit and test
nvim ~/.config/tool/config
chezmoi re-add ~/.config/tool/config  # Auto-commits & pushes

# Or via chezmoi
chezmoi edit ~/.config/tool/config
chezmoi apply
```

### Updating Homebrew Packages (macOS + Linux)

A custom `breww` script wraps the `brew` command. When you install a package with `breww install <package>`, it automatically:
1. Installs the package via Homebrew.
2. Dumps the machine's current list of packages into the correct profile-specific Brewfile.
3. Commits and pushes the change to GitHub.

**Brewfile profiles:**

| Profile | Brewfile | Content |
|---------|----------|---------|
| `mac-pro` | `Brewfile_common` + `Brewfile_pro` | Full workstation (casks, mas, go) |
| `mac-personal` | `Brewfile_common` + `Brewfile_personal` | Personal Mac (casks, mas) |
| `rpi` | `Brewfile_common` + `Brewfile_rpi` | Minimal RPi subset |

**Usage:**
```bash
# Instead of 'brew install ...', use 'breww install ...'
breww install ripgrep
```

### Checking What's Changed

```bash
# See differences between chezmoi source and actual files
chezmoi diff

# Check status
chezmoi status

# List all managed files
chezmoi managed
```

### Updating All Packages (All Platforms)

The `cup` command (chezmoi update + packages) updates everything:

```bash
# chezmoi update + Homebrew/DNF/Scoop + Docker/Podman
cup
```

This performs:
1. `chezmoi update` - Pull latest dotfiles
2. Package updates:
   - **macOS**: `brew upgrade` + `brew update` + `mas upgrade` (App Store)
   - **Linux (RPi)**: `apt dist-upgrade` + `apt autoremove`
   - **Linux (Fedora)**: `dnf upgrade` or `rpm-ostree upgrade`
   - **Windows**: `scoop update` + `scoop update --all`
3. **Docker/Podman** (if running): Update containers and prune images

### Syncing Multiple Machines

```bash
# On master machine (after changes)
cd ~/.local/share/chezmoi
git push

# On other machines
chezmoi update  # Pull + apply automatically
```

---

## 🗂️ Repository Structure

```
~/.local/share/chezmoi/
├── .chezmoiscripts/                    # Lifecycle scripts (numbered phases)
│   ├── 01-setup/                       # System prerequisites (Xcode, Homebrew)
│   ├── 02-install/                     # Package installation (1Password, brew, dnf)
│   ├── 03-configure/                   # Post-install config (GPG, mail)
│   ├── 04-update/                      # Package updates (Homebrew, App Store, dnf)
│   └── 05-maintenance/                 # Container maintenance
├── dot_claude/                         # Claude Code AI assistant
│   ├── agents/                         # 165 specialized sub-agents
│   ├── skills/                         # 84 skills (slash commands)
│   ├── hooks/                          # Event hooks (RTK, state tracking)
│   └── private_settings.json.tmpl      # Permissions, MCP servers
├── dot_config/
│   ├── aerospace/                      # Tiling window manager (macOS)
│   ├── alacritty/                      # Terminal emulator
│   ├── atuin/                          # Shell history sync
│   ├── bat/                            # Syntax-highlighted cat
│   ├── ghostty/                        # Terminal emulator
│   ├── isync/                          # IMAP sync (mbsync)
│   ├── kitty/                          # Terminal emulator
│   ├── lazygit/                        # Terminal Git UI
│   ├── msmtp/                          # SMTP relay
│   ├── neomutt/                        # Email client
│   ├── nushell/                        # Structured data shell
│   ├── nvim/                           # Neovim editor (LazyVim)
│   ├── opencode/                       # OpenCode AI assistant
│   ├── private_fish/                   # Fish shell (restricted)
│   ├── sketchybar/                     # macOS status bar
│   ├── starship/                       # Cross-shell prompt
│   ├── tmux/                           # Terminal multiplexer
│   ├── wezterm/                        # Terminal emulator (primary)
│   ├── zed/                            # Zed editor
│   ├── zellij/                         # Rust multiplexer
│   └── CONFIGURATION_INDEX.md          # Tool index documentation
├── dot_zsh/                            # Modular Zsh configuration
│   ├── 00-env.zsh                      # Environment variables
│   ├── 01-path.zsh                     # PATH management
│   ├── 02-completions.zsh              # Completion system
│   ├── 10-aliases.zsh                  # Command aliases
│   ├── 20-functions.zsh                # Custom functions
│   ├── 30-keybindings.zsh              # Vim-style keybindings
│   ├── 99-integrations.zsh             # FZF, Atuin, plugins
│   └── README.md                       # Zsh documentation
├── dot_bash/                           # Bash fallback configuration
├── dot_private/                        # Brewfiles: common, pro, personal, linux, rpi (0600)
├── dot_ssh/                            # SSH config (1Password-integrated)
├── dot_local/bin/                      # Custom scripts
│   ├── executable_breww                # Homebrew wrapper with auto-sync
│   ├── executable_update-claude-agents # Agent updater
│   └── executable_claude-init          # CLAUDE.md generator for new projects
├── scripts/
│   ├── bootstrap.sh                    # Multiplatform bootstrap (macOS/Linux)
│   └── bootstrap.ps1                   # Windows bootstrap (PowerShell/Scoop)
├── .chezmoi.toml.tmpl                  # Chezmoi configuration template
├── .chezmoiignore.tmpl                 # Platform-specific file exclusions
├── .chezmoiexternal.toml.tmpl          # External git repos (Oh-My-Zsh, TPM)
├── CLAUDE.md                           # Claude Code instructions
└── README.md                           # This file
```

---

## ⚙️ Chezmoi Configuration

Your `chezmoi.toml` is configured for **automatic synchronization**:

```toml
[git]
    autoAdd = true      # Automatically add changes
    autoCommit = true   # Automatically commit
    autoPush = true     # Automatically push to GitHub

[data]
    name = "Jerome Soyer"
    email = "jeromesoyer@gmail.com"
    github_user = "jsoyer"
```

This means when you use `chezmoi re-add`, it automatically:
1. Adds the file to chezmoi
2. Commits with a generated message
3. Pushes to GitHub

**No manual git commands needed!** ��

---

## 🔐 Security & Secrets

### Secret Management Strategy

| Method | Used For |
|--------|----------|
| **1Password CLI (`op`)** | SSH keys, mail passwords, GPG signing |
| **Environment variables** | API tokens (GitHub, Slack, etc.) |
| **chezmoi templates** | Machine-specific emails, hostnames |
| **`private_` prefix** | Files requiring 0600 permissions |
| **`secrets.zsh`** | Local-only tokens (excluded from git) |

### 1Password Integration

SSH config, git signing, and mail passwords are fetched from 1Password at apply time:

```go
// SSH config pulled from 1Password document
{{ onepasswordDocument "wf34z662n2u3kn5jhrmrmo3o4u" }}

// Mail password at runtime
passwordeval "op read 'op://Private/Gmail NeoMutt/password'"
```

Files depending on `op` are conditionally ignored when the CLI is unavailable.

### MCP Server Tokens

Claude Code and OpenCode MCP servers reference environment variables -- never hardcoded:

```json
"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
```

Required env vars: `GITHUB_TOKEN`, `SLACK_BOT_TOKEN`, `SLACK_TEAM_ID`, `BRAVE_API_KEY`, `LINEAR_API_KEY`, `DISCORD_TOKEN`, `OBSIDIAN_API_KEY`, `NOTION_API_KEY`.

### Adding Encrypted Files

```bash
chezmoi add --encrypt ~/.zsh/secrets.zsh
```

---

## 🔄 Syncing Workflow Summary

### Master Machine Workflow

```mermaid
graph LR
    A[Edit Config] --> B[Test]
    B --> C[chezmoi re-add]
    C --> D[Auto-commit]
    D --> E[Auto-push to GitHub]
```

### Secondary Machine Workflow

```mermaid
graph LR
    A[chezmoi update] --> B[Pull from GitHub]
    B --> C[Apply configs]
    C --> D[Reload apps]
```

---

## 🛠️ Useful Chezmoi Commands

### Basic Operations

```bash
chezmoi init <repo>          # Initialize with a repository
chezmoi apply               # Apply all changes
chezmoi apply -v            # Apply with verbose output
chezmoi update              # Pull from git + apply
chezmoi diff                # Show differences
```

### File Management

```bash
chezmoi add <file>          # Add new file
chezmoi re-add <file>       # Re-add modified file
chezmoi edit <file>         # Edit in chezmoi source
chezmoi remove <file>       # Remove from management
chezmoi forget <file>       # Untrack file (keep local copy)
```

### Status & Information

```bash
chezmoi status              # Show status
chezmoi managed             # List managed files
chezmoi cd                  # Go to chezmoi source directory
chezmoi doctor              # Check for potential issues
```

### Advanced

```bash
chezmoi apply --dry-run -v  # Preview what would be applied
chezmoi merge <file>        # Merge conflicts
chezmoi verify              # Verify all managed files
```

---

## 🎨 Catppuccin Mocha Theme

All tools are configured with consistent Catppuccin Mocha colors:

| Color | Hex | Usage |
|-------|-----|-------|
| Rosewater | `#f5e0dc` | - |
| Flamingo | `#f2cdcd` | - |
| Pink | `#f5c2e7` | Magenta |
| Mauve | `#cba6f7` | Purple |
| Red | `#f38ba8` | Errors |
| Maroon | `#eba0ac` | - |
| Peach | `#fab387` | Orange |
| Yellow | `#f9e2af` | Warnings |
| Green | `#a6e3a1` | Success |
| Teal | `#94e2d5` | Cyan |
| Sky | `#89dceb` | - |
| Sapphire | `#74c7ec` | - |
| Blue | `#89b4fa` | Info |
| Lavender | `#b4befe` | - |
| Text | `#cdd6f4` | Foreground |
| Subtext1 | `#bac2de` | - |
| Subtext0 | `#a6adc8` | - |
| Overlay2 | `#9399b2` | - |
| Overlay1 | `#7f849c` | - |
| Overlay0 | `#6c7086` | - |
| Surface2 | `#585b70` | - |
| Surface1 | `#45475a` | - |
| Surface0 | `#313244` | - |
| Base | `#1e1e2e` | Background |
| Mantle | `#181825` | - |
| Crust | `#11111b` | - |

---

## 📚 Documentation

### Per-Tool Documentation

Detailed documentation is available in each configuration directory:
- `~/.zsh/README.md` - Comprehensive Zsh setup guide
- `~/.config/starship/README.md` - Starship prompt documentation
- `~/.config/alacritty/README.md` - Alacritty configuration guide
- `~/.config/tmux/README.md` - Tmux configuration and usage
- `~/.config/wezterm/README.md` - WezTerm setup and features
- `~/.config/zellij/README.md` - Zellij layouts and keybindings

### External Resources

- [Chezmoi Documentation](https://www.chezmoi.io/)
- [Catppuccin Theme](https://github.com/catppuccin/catppuccin)
- [Oh-My-Zsh](https://ohmyz.sh/)
- [Starship](https://starship.rs/)
- [Neovim](https://neovim.io/)

---

## 🐛 Troubleshooting

### Chezmoi Issues

```bash
# Check for issues
chezmoi doctor

# Verify all files
chezmoi verify

# Force re-apply everything
chezmoi apply --force
```

### Git Conflicts

```bash
# If you have conflicts between machines
cd ~/.local/share/chezmoi
git status
git pull --rebase
chezmoi apply
```

### Missing Tools

```bash
# Check what's installed
which eza bat fd rg vivid fzf zoxide atuin

# Install missing tools
brew install <tool-name>
```

### Configuration Not Applied

```bash
# Check differences
chezmoi diff

# Re-apply specific file
chezmoi apply ~/.config/alacritty/alacritty.toml

# Force apply all
chezmoi apply --force
```

---

## 🤝 Contributing

This is a personal dotfiles repository, but feel free to:
- Fork and adapt for your own use
- Submit issues if you find problems
- Suggest improvements via pull requests

---

## 📄 License

These dotfiles are based on various open-source projects and personal customizations. Feel free to use and modify as needed.

---

## 🙏 Credits

- **Catppuccin** - Beautiful pastel theme
- **Chezmoi** - Dotfiles management
- **Oh-My-Zsh** - Zsh framework
- **Starship** - Cross-shell prompt
- All the amazing open-source tool creators

---

**Last Updated:** 2026-03-09
**Maintained by:** Jerome Soyer (@jsoyer)

---

## ⚡ Quick Reference

```bash
# Setup new machine (macOS/Linux)
curl -sL https://raw.githubusercontent.com/jsoyer/dotfiles/main/scripts/bootstrap.sh | bash

# Setup new machine (Windows PowerShell)
# irm https://raw.githubusercontent.com/jsoyer/dotfiles/main/scripts/bootstrap.ps1 | iex

# Update configuration (master machine)
nvim ~/.config/tool/config
chezmoi re-add ~/.config/tool/config

# Sync + update packages (all platforms)
cup

# Check status
chezmoi status

# View managed files
chezmoi managed
```

Happy configuring!

---

## 🐚 Bash Configuration

Bash configuration mirrors the Zsh setup for consistency when Zsh isn't available (e.g., minimal servers, containers, or recovery scenarios).

### 📁 Structure

```
~/.bashrc                    # Main entry point
~/.bash/                     # Modular configuration directory
  ├── 00-env.bash           # Environment & theme configurations
  ├── 01-path.bash          # PATH management with lazy loading
  ├── 10-aliases.bash       # Command aliases & shortcuts
  ├── 20-functions.bash     # Custom shell functions
  ├── 99-integrations.bash  # External tool integrations
  └── README.md             # Detailed documentation
```

### ✨ Features

| Feature | Description |
|---------|-------------|
| 🎨 **Themed** | Catppuccin Mocha (macOS) / Snazzy (Linux) |
| 🚀 **Modern Tools** | eza, bat, zoxide, fzf, starship |
| 🔄 **Zsh Parity** | Same aliases, functions, and integrations |
| ⚡ **Fast Startup** | Lazy loading for pyenv/jenv |
| 🌍 **Cross-Platform** | macOS, Linux, Raspberry Pi detection |

### 🔗 Zsh ↔ Bash Equivalence

| Zsh Feature | Bash Equivalent |
|-------------|-----------------|
| Oh-My-Zsh plugins | bash-completion + manual sources |
| `typeset -U path` | `path_prepend`/`path_append` functions |
| `unfunction` | `unset -f` |
| zsh-autosuggestions | N/A (use atuin for history) |
| zsh-syntax-highlighting | N/A |
| Starship prompt | Starship prompt ✅ |

### 📖 Documentation

See `~/.bash/README.md` for detailed documentation including:
- File-by-file breakdown
- All aliases and functions
- Customization guide
- Troubleshooting tips
