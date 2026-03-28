# Komorebi Configuration

Tiling window manager for Windows. Mirrors Aerospace (macOS) keybindings for cross-platform consistency.

## Files

- `komorebi.json` — Main WM configuration (layout, workspaces, borders)
- `whkdrc` — Hotkey definitions (vim-style bindings)

## Details

- **Tool**: Komorebi (Windows tiling WM)
- **Platform**: Windows
- **Purpose**: Tiling window management (BSP/VerticalStack layouts)
- **Theme**: Catppuccin Mocha borders

## Configuration

### Komorebi

- **Workspaces**: 7 per monitor (I-VII, BSP/VerticalStack layouts)
- **Border**: Catppuccin Mocha colors (4px, vim-friendly)
- **Padding**: 8px workspace and container padding
- **Float Rules**: Calculator, System Settings, 1Password, PiP windows

### Whkd (Hotkeys)

Vim-style navigation matching Aerospace:
- `alt-hjkl` — Focus window
- `alt-shift-hjkl` — Move window
- `alt-1..7` — Switch workspace
- `alt-shift-1..7` — Move to workspace
- `alt-e` — Cycle layout
- `alt-f` — Toggle monocle
- `alt-q` — Close window

## Usage

```powershell
# Start Komorebi (admin required)
komorebic.exe

# Reload config
alt + shift + r
```

## Dependencies

- Komorebi (Windows)
- whkd (hotkey daemon)
