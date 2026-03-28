# btop Configuration

**Platform:** Cross-platform (macOS, Linux)
**Theme:** Default (uses terminal colors)
**Purpose:** System monitor displaying CPU, memory, network, and process information

## Overview

btop is a modern resource monitor with a text-based GUI. This config displays CPU, memory, network, and process usage with customizable layouts, graph symbols, and Vim keybinding support.

## Key Files

- `btop.conf` — Main configuration file
- `themes/` — Directory for custom theme files

## Configuration Highlights

### Display
- **Layout presets:** 3 layouts (CPU/proc, CPU/mem/net, CPU/net)
- **Graph symbols:** Braille (highest resolution), block (common), or tty (compatibility)
- **Colors:** 24-bit truecolor with rounded corners
- **Shown boxes:** CPU, memory, network, processes

### Features
- **Vim keys:** hjkl navigation (disabled by default, can be enabled)
- **Rounded corners:** Yes (disabled in TTY mode)
- **Scroll:** Mouse wheel support
- **Refresh rate:** Configurable per-widget

### Graph Symbols
- **Default graph symbol:** `braille` (finest detail)
- **CPU graph:** default (braille resolution)
- **Memory graph:** default (braille resolution)
- **Network graph:** default (braille resolution)
- **Process graph:** default (braille resolution)

## Features

- Real-time system monitoring
- CPU, memory, network, and process statistics
- Process sorting and filtering
- Customizable layout with preset switching
- Network bandwidth monitoring
- Process list with resource usage
- GPU monitoring support (gpu0-gpu5)

## Customization

Toggle Vim keybindings:
```bash
vim_keys = True   # Enable hjkl navigation in lists
```

Switch layouts:
- Preset 0: All boxes with default settings
- Presets 1-2: Custom layout configurations
- Press keys to switch between presets

## Usage

```bash
btop              # Open system monitor
btop -p <pid>     # Focus on specific process
```

## Integration

- Standalone system monitoring tool
- Cross-platform: macOS and Linux
- Terminal-based UI works in any terminal
- Part of command-line tools ecosystem

## Related

- Complements other CLI tools: bat, lazygit, atuin, etc.
- No specific integration with other configs
- Can be run in Tmux or any terminal
