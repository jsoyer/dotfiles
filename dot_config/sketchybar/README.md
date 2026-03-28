# Sketchybar Configuration

**Platform:** macOS only
**Theme:** Catppuccin Mocha
**Purpose:** Status bar and system information display

## Overview

Sketchybar is a customizable macOS status bar that displays system information, application status, and workspace information. This config provides a pill-style design with Catppuccin Mocha colors.

## Directory Structure

- `executable_sketchybarrc` — Main configuration file (bar setup, defaults, item imports)
- `colors.sh` — Catppuccin Mocha color definitions
- `icons.sh` — Icon definitions
- `items/` — Individual status bar items (10+ modules):
  - `apple.sh` — macOS menu button
  - `aerospace.sh` — Workspace indicator from AeroSpace
  - `battery.sh`, `cpu.sh`, `ram.sh` — System monitors
  - `wifi.sh`, `volume.sh`, `mic.sh` — Hardware status
  - `front_app.sh` — Active application name
  - `media.sh` — Music player controls
  - `calendar.sh`, `timer.sh` — Calendar and timer
  - `github.sh` — GitHub notification badge
  - `spaces.sh` — Desktop spaces
- `plugins/` — Additional helper scripts
- `helper/` — Shared utilities

## Key Features

- **Bar Layout:** Top-positioned, 35px height, pill-style items with rounded corners
- **Theme:** Catppuccin Mocha with blue icons and custom label colors
- **Font:** Hack Nerd Font for icons, SF Pro for labels
- **Workspace Integration:** Updates via AeroSpace workspace change triggers
- **System Monitoring:** CPU, RAM, battery, WiFi, volume, microphone
- **Application Display:** Shows active application name
- **Media Controls:** Music player integration

## Configuration

Bar styling in `executable_sketchybarrc`:
- Position: top, height: 35px
- Padding: 8px left/right
- Blur radius: 50 (transparent effect)
- Icon font: Hack Nerd Font, 14pt bold
- Label font: SF Pro, 13pt semibold
- Background: Pill-style with 6px corner radius

## Integration

- **AeroSpace:** Sketchybar launched by AeroSpace on startup
- **Updates:** Workspace icons updated via `update_workspace_icons.sh` on workspace change
- **Colors:** All colors defined in `colors.sh` (Catppuccin Mocha palette)

## Related

- macOS desktop environment: AeroSpace (window manager) + Sketchybar (status bar)
- Part of desktop customization alongside Aerospace, WezTerm, Neovim
