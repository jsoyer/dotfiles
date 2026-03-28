# AeroSpace Configuration

**Platform:** macOS only
**Theme:** Catppuccin Mocha
**Purpose:** Tiling window manager configuration

## Overview

AeroSpace is a lightweight tiling window manager for macOS that organizes windows in a grid-based layout. This config provides workspace management, keybindings, and integration with Sketchybar.

## Key Files

- `aerospace.toml` — Main configuration file with layout, keybindings, and workspace settings

## Features

- Tiling window layout (tiles mode) with auto-orientation based on monitor dimensions
- Workspace-based organization with AeroSpace workspace change triggers
- Mouse follows focus: cursor automatically moves when switching windows or monitors
- Integration with Sketchybar status bar (`exec-on-workspace-change` triggers icon updates)
- Auto-unhide macOS hidden apps (prevents accidental `Cmd+H` behavior)
- Starts automatically at login

## Key Configuration

```toml
default-root-container-layout = 'tiles'
default-root-container-orientation = 'auto'
start-at-login = true
on-focused-monitor-changed = ['move-mouse monitor-lazy-center']
```

## Integration

- **Sketchybar:** Updates workspace icons when switching between workspaces
- **Shell:** AeroSpace starts after login, then launches Sketchybar
- **Keybindings:** Configure in `aerospace.toml` (see AeroSpace documentation)

## Related

- macOS-only tool, depends on Sketchybar for status bar display
- Part of desktop environment: Aerospace + Sketchybar + Catppuccin Mocha theme
