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

This setup uses `chezmoi`'s templating capabilities to apply different configurations based on a `profile` attribute defined in `chezmoi.toml.tmpl`. This allows for a clean separation between machine types (professional, personal, Linux, etc.).

| Profile          | Hostname(s)      | OS       | Package Manager | Prompt Icon |
| ---------------- | ---------------- | -------- | --------------- | ----------- |
| `mac-pro`        | `jsoyer-macOS`   | macOS    | `brew`          | `💼`          |
| `mac-personal`   | *(default)*      | macOS    | `brew`          | `➜`           |
| `linux-atomic`   | `fedora-atomic`  | Fedora   | `flatpak`       | ``           |
| `linux-standard` | `fedora`         | Fedora   | `dnf`           | ``           |

---

## 📁 What's Included

### 🐚 Shells
- **Zsh** - Primary shell with Oh-My-Zsh + 48 plugins
- **Bash** - Universal fallback shell with matching configuration
- **Nushell** - Modern structured data shell
- **Fish** - Friendly interactive shell (backup)

### Terminal Emulators
- **WezTerm** - Primary (GPU-accelerated, Lua config)
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

### Other Tools
- **FZF** - Fuzzy finder
- **Vivid** - LS_COLORS generator
- **TheFuck** - Command corrector
- **Git** - Version control with aliases

---

---

## 🍓 Raspberry Pi / Linux Installation

This dotfiles repository supports both macOS and Raspberry Pi/Linux with automatic platform detection and different themes.

### Quick Install (One Command)

```bash
curl -sL https://raw.githubusercontent.com/jsoyer/dotfiles/main/scripts/install-rpi.sh | bash
```

This script will:
1. Install base packages (zsh, tmux, neovim, fzf, ripgrep, etc.)
2. Install modern CLI tools (starship, eza, bat, zoxide, vivid)
3. Install Oh-My-Zsh with plugins
4. Install Tmux Plugin Manager
5. Install JetBrains Mono Nerd Font
6. Apply dotfiles via chezmoi

### Alternative: Manual Chezmoi Install

If you already have Oh-My-Zsh installed:

```bash
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply jsoyer
```

### Platform Differences

| Feature | macOS | Raspberry Pi / Linux |
|---------|-------|----------------------|
| **Theme** | Catppuccin Mocha | Gruvbox Dark |
| **Prompt** | `~/path ➜` | `🍓 hostname:~/path ❯` |
| **Tmux Bar** | Top | Bottom |
| **Tmux Prefix** | `Ctrl+A` | `Ctrl+B` |
| **Colors** | Purple/Pink | Yellow/Orange |

### Visual Comparison

**macOS Terminal:**
```
~/projects ➜ git:(main) ✚
```

**Raspberry Pi Terminal:**
```
🍓 rpi-nas:~/projects main ❯
```

### Post-Installation Steps

1. **Log out and log back in** (or run `zsh`)
2. **Install tmux plugins**: Press `Ctrl+B` then `I` inside tmux
3. **Verify installation**:
   ```bash
   echo "Platform: $PLATFORM"
   echo "Is RPi: $IS_RPI"
   echo "Starship config: $STARSHIP_CONFIG"
   ```

### Supported Architectures

- `aarch64` - Raspberry Pi 4, Pi 5 (64-bit)
- `armv7l` - Raspberry Pi 3, Pi Zero 2 (32-bit)
- `x86_64` - Standard Linux (Intel/AMD)

### What Gets Installed

| Package | Description | Install Method |
|---------|-------------|----------------|
| `zsh` | Shell | apt |
| `tmux` | Terminal multiplexer | apt |
| `neovim` | Editor | apt |
| `fzf` | Fuzzy finder | apt |
| `bat` | cat replacement | apt |
| `ripgrep` | grep replacement | apt |
| `fd-find` | find replacement | apt |
| `starship` | Prompt | curl script |
| `eza` | ls replacement | binary/apt |
| `zoxide` | cd replacement | curl script |
| `vivid` | LS_COLORS | binary |


## 🚀 Quick Start - New Machine Setup

### One-Command Installation (Recommended)

```bash
# Installs chezmoi AND applies all dotfiles in one command
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply jsoyer
```

This will:
1. ✅ Install chezmoi
2. ✅ Clone your dotfiles from GitHub
3. ✅ Apply all configurations automatically
4. ✅ Run setup scripts (Xcode tools, Homebrew, etc.)

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
brew tap homebrew/cask-fonts
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

### Checking What's Changed

```bash
# See differences between chezmoi source and actual files
chezmoi diff

# Check status
chezmoi status

# List all managed files
chezmoi managed
```

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
├── .chezmoiscripts/
│   ├── 00_install-xcode-devtools.sh    # Auto-run on first apply
│   └── 01_install_homebrew.sh          # Auto-run on first apply
├── dot_config/
│   ├── alacritty/
│   │   └── alacritty.toml
│   ├── atuin/
│   │   └── config.toml
│   ├── bat/
│   │   └── config
│   ├── fish/
│   │   └── config.fish
│   ├── kitty/
│   │   └── kitty.conf
│   ├── nushell/
│   │   ├── config.nu
│   │   └── env.nu
│   ├── nvim/
│   │   └── (neovim config)
│   ├── starship/
│   │   ├── starship.toml
│   │   └── starship-nushell.toml
│   ├── tmux/
│   │   └── tmux.conf
│   ├── wezterm/
│   │   └── wezterm.lua
│   └── zellij/
│       └── config.kdl
├── dot_zsh/
│   ├── 00-env.zsh
│   ├── 01-path.zsh
│   ├── 02-completions.zsh
│   ├── 10-aliases.zsh
│   ├── 20-functions.zsh
│   ├── 30-keybindings.zsh
│   ├── 99-integrations.zsh
│   ├── README.md
│   └── secrets.zsh
├── dot_bash/
│   ├── 00-env.bash
│   ├── 01-path.bash
│   ├── 10-aliases.bash
│   ├── 20-functions.bash
│   ├── 99-integrations.bash
│   └── README.md
├── dot_bashrc
├── dot_zshrc
├── dot_zshenv
├── dot_zprofile
├── chezmoi.toml                        # Chezmoi configuration
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

## 🔐 Managing Secrets

For sensitive files like API keys or tokens:

```bash
# Add encrypted file
chezmoi add --encrypt ~/.zsh/secrets.zsh

# Chezmoi will prompt for a passphrase
# File will be encrypted in the repo
```

On new machines, chezmoi will decrypt automatically (with your passphrase).

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

**Last Updated:** 2025-12-30  
**Maintained by:** Jerome Soyer (@jsoyer)

---

## ⚡ Quick Reference

```bash
# Setup new machine
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply jsoyer

# Update configuration (master machine)
nvim ~/.config/tool/config
chezmoi re-add ~/.config/tool/config

# Sync to other machines
chezmoi update

# Check status
chezmoi status

# View managed files
chezmoi managed
```

Happy configuring! 🎉

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

