# Complete Configuration Index

This document provides an overview of all configured tools in your development environment, all using the **Catppuccin Mocha** theme for a consistent, beautiful experience.

## 📚 Table of Contents

1. [Overview](#overview)
2. [Terminals](#terminals)
3. [Shells](#shells)
4. [Multiplexers](#multiplexers)
5. [Editors](#editors)
6. [CLI Tools](#cli-tools)
7. [Other Applications](#other-applications)
8. [Theme Consistency](#theme-consistency)
9. [Quick Links](#quick-links)

---

## Overview

**Total Configured Tools**: 15+
**Theme**: Catppuccin Mocha across all tools
**Configuration Location**: `~/.config/`
**Dotfiles Manager**: Chezmoi with GitHub sync

### Theme Philosophy

All tools use **Catppuccin Mocha** for:
- **Consistency**: Same colors across all applications
- **Eye comfort**: Soothing pastel colors reduce eye strain
- **Productivity**: Clear visual hierarchy and contrast
- **Aesthetics**: Beautiful, modern design language

---

## Terminals

### 1. WezTerm
**Location**: `~/.config/wezterm/`
**Documentation**: [README.md](wezterm/README.md)

**Features**:
- GPU-accelerated rendering
- Built-in multiplexer (tabs + panes)
- Lua configuration
- Catppuccin Mocha theme
- JetBrains Mono font (16pt)
- 50+ keybindings

**Key Files**:
- `wezterm.lua` - Main configuration
- `README.md` - Complete documentation

**Quick Start**:
```bash
open -a WezTerm
# Splits: Ctrl+Shift+| or Ctrl+Shift+_
# Navigate: Ctrl+Shift+H/J/K/L
```

### 2. Alacritty
**Location**: `~/.config/alacritty/`
**Documentation**: [README.md](alacritty/README.md)

**Features**:
- GPU-accelerated, minimal config
- Catppuccin Mocha colors integrated
- JetBrainsMono Nerd Font
- Nushell as default shell
- Opacity 0.9 with blur

**Key Files**:
- `alacritty.toml` - Main configuration
- `README.md` - Documentation

### 3. Kitty
**Location**: `~/.config/kitty/`

**Features**:
- Fast, feature-rich terminal
- Catppuccin Mocha theme
- Dracula theme (alternative)

**Quick Start**:
```bash
open -a Kitty
```

---

## Shells

### 1. Zsh (Primary Shell)
**Location**: `~/.zsh/` and `~/.zshrc`
**Documentation**: [README.md](.zsh/README.md)

**Features**:
- 48 Oh-My-Zsh plugins
- Modular configuration (9 files)
- Catppuccin Mocha colors via Vivid
- Starship prompt
- Modern CLI tools integration
- Vivid for LS_COLORS generation

**Configuration Files**:
```
~/.zsh/
├── 00-env.zsh           # Environment variables + Vivid
├── 01-path.zsh          # PATH management
├── 02-completions.zsh   # Completion setup
├── 10-aliases.zsh       # Aliases (ls, ll with eza)
├── 20-functions.zsh     # Custom functions
├── 30-keybindings.zsh   # Key bindings
├── 99-integrations.zsh  # External integrations
├── secrets.zsh          # Private tokens
└── README.md            # Documentation (588 lines)
```

**Modern Aliases**:
```bash
ls='eza --color=always --icons'           # Colorized ls
ll='eza -l --color=always --icons --git -a'  # Long listing
vim='nvim'                                 # Neovim
cat='bat'                                  # Bat with syntax highlighting
http='xh'                                  # Modern HTTP client
```

### 2. Fish
**Location**: `~/.config/fish/`
**Documentation**: [README.md](fish/README.md)

**Features**:
- Friendly interactive shell
- Built-in autosuggestions
- Syntax highlighting
- Catppuccin Mocha theme
- Starship prompt integration

**Key Files**:
- `config.fish` - Main configuration
- `themes/Catppuccin Mocha.theme` - Official theme
- `README.md` - Documentation

**Quick Start**:
```bash
fish
# Autosuggestions: → to accept
```

### 3. Nushell
**Location**: `~/.config/nushell/`
**Documentation**: [README.md](nushell/README.md)

**Features**:
- Structured data shell
- Pipeline-oriented
- Strong typing
- Catppuccin Mocha theme
- Starship prompt
- Default shell in Alacritty

**Key Files**:
- `config.nu` - Main configuration
- `env.nu` - Environment setup
- `catppuccin_mocha.nu` - Complete theme
- `README.md` - Documentation

**Quick Start**:
```bash
nu
# Structured output: ls | where size > 1mb
# JSON/CSV native: open data.json | get items
```

---

## Multiplexers

### 1. Zellij
**Location**: `~/.config/zellij/`
**Documentation**: [README.md](zellij/README.md), [PLUGINS.md](zellij/PLUGINS.md)

**Features**:
- Modern terminal multiplexer
- Modal interface
- WASM plugins
- Catppuccin Mocha theme
- Layouts with zjstatus + datetime

**Configuration Files**:
```
~/.config/zellij/
├── config.kdl            # Main config
├── layouts/
│   ├── default.kdl       # Default with zjstatus
│   └── datetime.kdl      # With datetime plugin
├── plugins/
│   ├── zjstatus.wasm     # Status bar
│   └── zellij-datetime.wasm  # Date/time
├── README.md             # Main docs
└── PLUGINS.md            # Plugin docs
```

**Quick Start**:
```bash
zellij                    # Default layout
zellij --layout datetime  # With datetime
# Modes: Ctrl+A (Pane), Ctrl+T (Tab), Ctrl+S (Scroll)
```

### 2. Tmux
**Location**: `~/.config/tmux/`
**Documentation**: [README.md](tmux/README.md)

**Features**:
- Traditional multiplexer
- 11+ plugins via TPM
- Catppuccin Mocha theme
- Prefix-based bindings

**Plugins**:
- tmux-sensible, tmux-yank, tmux-resurrect
- tmux-continuum, tmux-battery-status
- tmux-cpu, tmux-prefix-highlight
- Catppuccin theme

**Quick Start**:
```bash
tmux
# Prefix: Ctrl+B
# Split: Prefix + | or -
```

---

## Editors

### Neovim (LazyVim)
**Location**: `~/.config/nvim/`
**Documentation**: [KEYBINDINGS.md](nvim/KEYBINDINGS.md)

**Features**:
- LazyVim distribution
- Catppuccin Mocha theme
- Extensive plugin ecosystem
- Custom keybindings

**Key Features**:
- Split management: `<leader>sv/sh`
- Buffer navigation: `Tab/Shift-Tab`
- Direct buffer access: `<leader>1-9`
- Telescope fuzzy finding
- LSP integration

**Configuration**:
```
~/.config/nvim/
├── lua/
│   ├── config/
│   │   └── keymaps.lua
│   └── plugins/
│       └── core/
│           └── colorscheme.lua
└── KEYBINDINGS.md
```

---

## CLI Tools

### 1. Starship (Prompt)
**Location**: `~/.config/starship/`
**Documentation**: [README.md](starship/README.md)

**Features**:
- Cross-shell prompt
- Fast (<10ms)
- Catppuccin Mocha colors
- Git integration
- Language version display

**Quick Start**:
```bash
# Already loaded in Zsh, Fish, Nushell
# Config: ~/.config/starship/starship.toml
starship config  # Edit config
```

### 2. Bat (Modern Cat)
**Location**: `~/.config/bat/`
**Theme**: Catppuccin Mocha

**Configuration**:
```bash
# ~/.config/bat/config
--theme="Catppuccin Mocha"
--italic-text=always
--pager="less -FR"
```

**Features**:
- Syntax highlighting
- Git integration
- Line numbers
- Italic text support
- Mouse scrolling in pager

**Usage**:
```bash
bat file.txt      # Syntax highlighted output
bat -A file.txt   # Show all characters
```

### 3. Atuin (Shell History)
**Location**: `~/.config/atuin/`
**Documentation**: `config.toml`

**Features**:
- Magical shell history with sync
- Vim keybindings (vim-insert mode)
- Fuzzy search with preview
- Compact UI aligned with other tools
- Secrets filtering
- History filtering (ls, cd, exit, clear)
- Sync frequency: instant (after every command)
- Stats tracking for dev tools

**Configuration**:
```toml
search_mode = "fuzzy"
keymap_mode = "vim-insert"
style = "compact"
secrets_filter = true
sync_frequency = "0"
```

**Quick Start**:
```bash
# Ctrl+R to search history
# Vim keys to navigate
# Enter to execute
```

### 4. FZF (Fuzzy Finder)
**Configuration**: In shell configs
**Theme**: Catppuccin Mocha colors

**Environment**:
```bash
export FZF_DEFAULT_OPTS="--color=bg+:#313244,bg:#1e1e2e..."
export FZF_DEFAULT_COMMAND='fd --type f --hidden --follow --exclude .git'
```

### 5. Vivid (LS_COLORS Generator)
**Configuration**: In `~/.zsh/00-env.zsh`
**Theme**: Catppuccin Mocha

**Features**:
- Generates rich LS_COLORS
- Used by eza automatically
- Consistent file type colors

**Configuration**:
```bash
export LS_COLORS="$(vivid generate catppuccin-mocha)"
```

### 6. Eza (Modern ls)
**Theme**: Catppuccin Mocha (via Vivid LS_COLORS)

**Aliases**:
```bash
ls='eza --color=always --icons'
ll='eza -l --color=always --icons --git -a'
l='eza -l --icons --git -a'
lt='eza --tree --level=2 --long --icons --git'
```

### 7. Zoxide (Smart cd)
**Configuration**: In shell configs

**Usage**:
```bash
z project  # Jump to frequently used directory
zi         # Interactive selection
```

### 8. Direnv (Environment Switching)
**Configuration**: Auto-loaded in shells

**Usage**:
```bash
# .envrc files automatically loaded per directory
```

---

## Other Applications

### OBS Studio
**Location**: `~/Library/Application Support/obs-studio/themes/`
**Documentation**: [README.md](../Library/Application\ Support/obs-studio/themes/README.md)

**Features**:
- Catppuccin theme (all 4 flavors)
- Mocha active by default
- Themed UI elements
- Recording/streaming indicators

**Activation**:
```
OBS → Settings → Appearance
Theme: Catppuccin
Style: Mocha
```

---

## Theme Consistency

All tools use **Catppuccin Mocha**:

| Tool          | Type         | Config Location              | Status |
|---------------|--------------|------------------------------|--------|
| WezTerm       | Terminal     | `~/.config/wezterm/`         | ✅     |
| Alacritty     | Terminal     | `~/.config/alacritty/`       | ✅     |
| Kitty         | Terminal     | `~/.config/kitty/`           | ✅     |
| Zsh           | Shell        | `~/.zsh/`                    | ✅     |
| Fish          | Shell        | `~/.config/fish/`            | ✅     |
| Nushell       | Shell        | `~/.config/nushell/`         | ✅     |
| Zellij        | Multiplexer  | `~/.config/zellij/`          | ✅     |
| Tmux          | Multiplexer  | `~/.config/tmux/`            | ✅     |
| Neovim        | Editor       | `~/.config/nvim/`            | ✅     |
| Starship      | Prompt       | `~/.config/starship/`        | ✅     |
| Atuin         | History      | `~/.config/atuin/`           | ✅     |
| Bat           | CLI Tool     | `~/.config/bat/`             | ✅     |
| Vivid         | CLI Tool     | Zsh config                   | ✅     |
| FZF           | CLI Tool     | Zsh config                   | ✅     |
| OBS Studio    | Streaming    | `~/Library/.../obs-studio/`  | ✅     |

### Catppuccin Mocha Color Reference

| Color      | Hex       | RGB           | Usage                    |
|------------|-----------|---------------|--------------------------|
| Base       | `#1e1e2e` | 30, 30, 46    | Background               |
| Mantle     | `#181825` | 24, 24, 37    | Darker background        |
| Crust      | `#11111b` | 17, 17, 27    | Darkest background       |
| Text       | `#cdd6f4` | 205, 214, 244 | Primary text             |
| Subtext1   | `#bac2de` | 186, 194, 222 | Secondary text           |
| Subtext0   | `#a6adc8` | 166, 173, 200 | Tertiary text            |
| Surface0   | `#313244` | 49, 50, 68    | Surface                  |
| Surface1   | `#45475a` | 69, 71, 90    | Surface elevated         |
| Surface2   | `#585b70` | 88, 91, 112   | Surface more elevated    |
| Overlay0   | `#6c7086` | 108, 112, 134 | Overlay                  |
| Overlay1   | `#7f849c` | 127, 132, 156 | Overlay elevated         |
| Overlay2   | `#9399b2` | 147, 153, 178 | Overlay more elevated    |
| Blue       | `#89b4fa` | 137, 180, 250 | Primary accent           |
| Lavender   | `#b4befe` | 180, 190, 254 | Secondary accent         |
| Sapphire   | `#74c7ec` | 116, 199, 236 | Tertiary accent          |
| Sky        | `#89dceb` | 137, 220, 235 | Info                     |
| Teal       | `#94e2d5` | 148, 226, 213 | Hint                     |
| Green      | `#a6e3a1` | 166, 227, 161 | Success                  |
| Yellow     | `#f9e2af` | 249, 226, 175 | Warning                  |
| Peach      | `#fab387` | 250, 179, 135 | Warning elevated         |
| Maroon     | `#eba0ac` | 235, 160, 172 | Error subtle             |
| Red        | `#f38ba8` | 243, 139, 168 | Error                    |
| Mauve      | `#cba6f7` | 203, 166, 247 | Purple accent            |
| Pink       | `#f5c2e7` | 245, 194, 231 | Pink accent              |
| Flamingo   | `#f2cdcd` | 242, 205, 205 | Rosewater elevated       |
| Rosewater  | `#f5e0dc` | 245, 224, 220 | Warmest accent           |

---

## Quick Links

### Documentation Files
- [WezTerm](wezterm/README.md) - Terminal configuration
- [Alacritty](alacritty/README.md) - Lightweight terminal
- [Zsh](../.zsh/README.md) - Primary shell
- [Fish](fish/README.md) - Friendly shell
- [Nushell](nushell/README.md) - Structured shell
- [Zellij](zellij/README.md) - Modern multiplexer
- [Zellij Plugins](zellij/PLUGINS.md) - Plugin guide
- [Tmux](tmux/README.md) - Traditional multiplexer
- [Neovim](nvim/KEYBINDINGS.md) - Editor keybindings
- [Starship](starship/README.md) - Prompt configuration

### Configuration Files
```
~/.config/
├── alacritty/
│   └── alacritty.toml
├── atuin/
│   └── config.toml
├── bat/
│   └── config
├── fish/
│   ├── config.fish
│   └── themes/Catppuccin Mocha.theme
├── kitty/
│   └── kitty.conf
├── nvim/
│   └── lua/plugins/core/colorscheme.lua
├── nushell/
│   ├── config.nu
│   ├── env.nu
│   └── catppuccin_mocha.nu
├── starship/
│   ├── starship.toml
│   └── starship-nushell.toml
├── tmux/
│   └── tmux.conf
├── wezterm/
│   └── wezterm.lua
└── zellij/
    ├── config.kdl
    └── layouts/
```

### External Resources
- **Catppuccin Official**: https://github.com/catppuccin/catppuccin
- **Catppuccin Palette**: https://catppuccin.com/palette
- **WezTerm**: https://wezfurlong.org/wezterm/
- **Zellij**: https://zellij.dev/
- **Starship**: https://starship.rs/
- **Nushell**: https://www.nushell.sh/
- **Fish**: https://fishshell.com/
- **Atuin**: https://atuin.sh/
- **Chezmoi**: https://www.chezmoi.io/

---

## Dotfiles Management with Chezmoi

All configurations are managed with **Chezmoi** and synced to GitHub:

**Repository**: `github.com/jsoyer/dotfiles`
**Master Machine**: MacBook Pro
**Auto-sync**: Enabled (autoCommit + autoPush)

### Quick Commands
```bash
# On master machine (MacBook)
nvim ~/.config/tool/config
chezmoi re-add ~/.config/tool/config  # Auto-commits & pushes

# On other machines
chezmoi update  # Pull latest + apply
```

---

## Switching Between Tools

### Shells
```bash
# Switch to Fish
fish

# Switch to Nushell
nu

# Back to Zsh
zsh
```

### Multiplexers
```bash
# Start Zellij
zellij

# Start Tmux
tmux
```

### Terminals
```bash
# Launch WezTerm
open -a WezTerm

# Launch Alacritty
open -a Alacritty

# Launch Kitty
open -a Kitty
```

---

## Maintenance

### Update All Configs
```bash
# Via Chezmoi (recommended)
chezmoi update

# Or manually
cd ~/.local/share/chezmoi
git pull
chezmoi apply
```

### Backup Configuration
```bash
# Chezmoi handles backups via GitHub
# Manual backup:
tar -czf ~/dotfiles-backup-$(date +%Y%m%d).tar.gz ~/.config ~/.zshrc ~/.zsh
```

### Check for Theme Consistency
```bash
# Verify all tools use Catppuccin Mocha
grep -r "catppuccin" ~/.config/
grep -r "mocha" ~/.config/
grep -r "#1e1e2e" ~/.config/  # Base color
```

---

## Summary Statistics

**Total Configured Tools**: 15+
**Total Documentation**: ~5,000+ lines
**Configuration Files**: 50+ files
**Theme**: Catppuccin Mocha (100% consistent)
**Dotfiles Manager**: Chezmoi with GitHub sync

### Recent Updates (2025-12-30)
- ✅ Added Vivid for LS_COLORS generation
- ✅ Enhanced Bat with italic text & mouse scroll
- ✅ Updated Atuin with vim keybindings & fuzzy search
- ✅ Improved Alacritty with Nushell integration
- ✅ Added comprehensive README for dotfiles repo

---

**Last Updated**: 2025-12-30
**Theme**: Catppuccin Mocha
**Configured Tools**: 15+
**Status**: ✅ All documented, themed, and synced

---

## Visual Consistency

All terminals, shells, and tools share:
- **Same font**: JetBrainsMono Nerd Font (12-16pt)
- **Same opacity**: 0.9 with blur
- **Same colors**: Catppuccin Mocha palette
- **Same prompt**: Starship with consistent format
- **Same keybindings**: Vim-first approach everywhere

This creates a seamless, beautiful development environment! 🎨✨
