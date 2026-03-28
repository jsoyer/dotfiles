# Flashspace Configuration

Virtual desktop manager for macOS. Organizes apps across workspaces with seamless switching.

## Files

- `profiles.json` — Workspace profiles and app assignments
- `settings.json` — Global behavior and integrations

## Details

- **Tool**: Flashspace
- **Platform**: macOS
- **Purpose**: Virtual desktop management with workspace profiles
- **Theme**: Integrates with sketchybar and Aerospace

## Configuration

### Profiles

- **Default Profile**: 3 workspaces on Studio Display
  - Main (empty workspace)
  - Browser (Brave, Chrome)
  - Editor (Zed)

### Settings

- **Workspace Switching**: Smooth transitions (0.3s fade)
- **Integrations**: Triggers sketchybar reloads on workspace/profile change
- **Gestures**: 3-finger swipe left/right for workspace navigation
- **Auto-Switching**: Moves to workspace when app assigned
- **Display Mode**: Static (workspace ordering)

## Key Features

- Cross-display workspace management
- App-based workspace assignment
- Sketchybar integration for status updates
- Gesture support (swipe navigation)
- Profile-based workspace layouts

## Usage

- Swipe left/right (3-finger) to switch workspaces
- Click workspace in menu bar
- App launch auto-switches to assigned workspace

## Dependencies

- Sketchybar (status bar)
- Aerospace (tiling WM, optional complement)
