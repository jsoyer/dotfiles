# Atuin Configuration

**Platform:** Cross-platform (macOS, Linux, Windows)
**Theme:** Catppuccin Mocha (inherits from terminal)
**Purpose:** Shell history sync and search across machines

## Overview

Atuin replaces your shell history with a SQLite database and provides smart search, sync, and statistics. This config emphasizes fuzzy search, compact UI, and keyboard-first navigation consistent with Vim and Neovim.

## Key Files

- `config.toml` — Main configuration with search behavior, UI style, and keybindings

## Configuration Highlights

### Search Behavior
- **Search mode:** Fuzzy (flexible matching, like Telescope/fzf in Neovim)
- **Filter mode:** Global (search across all sessions)
- **Up-key behavior:** Session-filtered search (recent commands in current session)
- **Preview:** Enabled (shows command context)
- **Tabs:** Visible (switch between search modes)

### UI Style
- **Style:** Compact (minimal visual clutter)
- **Inline height:** 20 lines
- **Help:** Visible
- **Theme:** Inherits Catppuccin Mocha from terminal colors

### Keybindings
- Vim-style navigation configured for consistency with editor setup
- Keyboard-first approach (no mouse required)

## Features

- Search shell history fuzzy and contextually
- Sync history across machines (with optional server)
- Statistics on command usage
- Backup and restore functionality
- Session-aware filtering

## Usage

```bash
<Ctrl-R>   # Open Atuin search (configured in shell)
up         # Filter to current session history
```

## Integration

- Works with all shells (zsh, bash, fish)
- Configured in `dot_zsh/` shell initialization
- Complements other history tools and shell configuration
- Cross-platform: same behavior on macOS, Linux, Windows

## Related

- Shell configuration in `dot_zsh/` and `dot_bash/`
- Pairs with other prompt tools (Starship, Powerlevel10k)
- Part of command-line tooling ecosystem (bat, lazygit, fzf, etc.)
