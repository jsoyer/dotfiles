# Ghostty Configuration

**Platform:** Cross-platform (macOS, Linux)
**Theme:** Catppuccin Mocha
**Purpose:** Modern terminal emulator configuration

## Overview

Ghostty is a fast, feature-rich terminal emulator written in Zig. This config provides Catppuccin Mocha theming, shell integration, and cross-platform compatibility.

## Key Files

- `config.tmpl` — Main configuration (Go template for platform-specific shell paths)

## Configuration Highlights

### Theme & Appearance
- **Theme:** Catppuccin Mocha (dark, warm color scheme)
- **Font:** JetBrainsMono Nerd Font, 12pt
- **Background opacity:** 90% (semi-transparent)
- **Window:** No decorations, system-native theme
- **Padding:** Balanced window padding

### Shell Integration
- **Shell:** zsh (platform-specific paths)
  - macOS: `/opt/homebrew/bin/zsh`
  - Linux: `/usr/bin/zsh`
- **Shell Integration:** zsh (enables shell prompt injection, command tracking)
- **Term:** xterm-256color

### Input & Selection
- **Copy-on-select:** Enabled (auto-copy highlighted text to clipboard)
- **Pager:** Less with scroll support

## Features

- Fast GPU-accelerated rendering
- Native tab and split support (commented out keybindings available)
- Shell integration for better prompt handling
- Mouse scrolling support
- Clean, minimalist UI

## Customization

To enable keybindings, uncomment sections in the template:
```
# New window, tab, split operations
# Tab navigation and switching
# Workspace management
```

## Integration

- Cross-platform terminal for macOS and Linux
- Works seamlessly with zsh shell configuration
- Part of desktop environment alongside Neovim, tmux, WezTerm
- Catppuccin Mocha theme consistent with system-wide theme

## Related

- Primary terminal emulator (alternative: WezTerm)
- Complements shell config in `dot_zsh/` and `dot_bash/`
- Works with shell aliases and functions
