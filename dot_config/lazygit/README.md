# Lazygit Configuration

**Platform:** Cross-platform (macOS, Linux, Windows)
**Theme:** Catppuccin Mocha
**Purpose:** Git TUI (Text User Interface) for interactive Git operations

## Overview

Lazygit is a simple and fast terminal UI for Git commands. This config provides Catppuccin Mocha theming, delta pager integration, and optimized keybindings for interactive staging, committing, and rebasing.

## Key Files

- `config.yml` — Main configuration with theme, git behavior, and UI settings

## Configuration Highlights

### Theme (Catppuccin Mocha)
- Active borders: Mauve (`#cba6f7`)
- Inactive borders: Subtext (`#a6adc8`)
- Search borders: Yellow (`#f9e2af`)
- Default text: Text (`#cdd6f4`)
- Unstaged changes: Red (`#f38ba8`)

### Git Integration
- **Pager:** `delta --dark --paging=never` (syntax-highlighted diffs)
- **Color:** Always enabled for rich output
- **Sign-off:** Disabled for cleaner commits

### UI Style
- Minimal and focused interface
- Configured for quick navigation and operations
- Status display for modified files

## Key Features

- Interactive staging/unstaging of hunks
- Rebase, cherry-pick, and merge management
- Search and filter commits
- Branch management UI
- Stash operations
- Author color coding (blue for all authors)

## Usage

```bash
lazygit   # Opens interactive Git UI
```

## Integration

- Works alongside the `git` config for user details
- Complements shell aliases: `ca`, `cu`, `c` for chezmoi operations
- Part of Git workflow with delta for better diff visualization

## Related

- Works with `git/` config for user name/email
- Pairs with delta for colored diffs
- Cross-platform: same config on macOS, Linux, Windows
