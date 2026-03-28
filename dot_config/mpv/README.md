# mpv Configuration

Minimal video player configuration with Catppuccin Mocha theme.

## Files

- `mpv.conf` — Player settings and color configuration

## Details

- **Tool**: mpv (media player)
- **Platform**: Linux, macOS, Windows
- **Purpose**: Video playback with customized colors
- **Theme**: Catppuccin Mocha

## Configuration

### Colors

- **Background**: Catppuccin Mocha base (#1e1e2e)
- **OSD**: Text (#cdd6f4), shadow (#1e1e2e), border (#11111b)
- **Stats overlay**: Mocha palette (borders, fonts, plots)
- **UOSC UI**: Foreground (#cba6f7), background (#1e1e2e)

### Scripts

- **stats** — Performance/codec statistics overlay
- **UOSC** — Modern UI with seeking and controls

## Usage

```bash
mpv video.mp4
mpv --no-audio video.mp4      # Video only
mpv --fullscreen video.mp4    # Fullscreen
```

## Key Features

- Minimal config (sensible defaults)
- Stats and UOSC script support
- Catppuccin Mocha theming
- No complex keybindings configured

## Dependencies

- mpv binary
- Optional: UOSC script for UI
- Optional: stats script for overlays
