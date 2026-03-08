# Alacritty Configuration

Customized Alacritty configuration based on Ghostty and WezTerm.

## Theme

**Catppuccin Mocha** - A dark and soothing theme with pastel colors.

## Font

- **Family:** JetBrainsMono Nerd Font
- **Size:** 12px
- **Styles:** Regular, Bold, Italic, Bold Italic

## Shell

By default, Nushell (nu) is configured as the shell.

```toml
[terminal.shell]
program = "/opt/homebrew/bin/nu"
```

**Note:** The configuration uses `terminal.shell` (new syntax) instead of `shell` (deprecated).

## Appearance

### Window
- **Padding:** 12px on each side (balanced)
- **Decorations:** Buttonless (no buttons)
- **Opacity:** 0.9 (90%)
- **Blur:** Enabled (blur effect on macOS)

### Cursor
- **Shape:** Block
- **Blinking:** Disabled

## Features

### Selection
- **Copy on select:** Enabled - Selected text is automatically copied to clipboard

### Scrollback
- **History:** 10,000 lines

### Terminal
- **TERM:** xterm-256color

## Keyboard Shortcuts

### Copy/Paste
- `Ctrl+Shift+C` - Copy
- `Ctrl+Shift+V` - Paste

### Search
- `Ctrl+Shift+F` - Forward search

### Font Size
- `Ctrl+=` - Increase size
- `Ctrl+-` - Decrease size
- `Ctrl+0` - Reset size

### Navigation
- `Shift+PageUp` - Scroll up
- `Shift+PageDown` - Scroll down

### Window
- `Ctrl+Shift+N` - New window

## Mouse

- **Right click:** Paste from selection
- **Hiding:** Cursor is not hidden when typing

## Catppuccin Mocha Color Palette

### Normal Colors
- Black: `#45475a`
- Red: `#f38ba8`
- Green: `#a6e3a1`
- Yellow: `#f9e2af`
- Blue: `#89b4fa`
- Magenta: `#f5c2e7`
- Cyan: `#94e2d5`
- White: `#bac2de`

### Bright Colors
- Black: `#585b70`
- Red: `#f38ba8`
- Green: `#a6e3a1`
- Yellow: `#f9e2af`
- Blue: `#89b4fa`
- Magenta: `#f5c2e7`
- Cyan: `#94e2d5`
- White: `#a6adc8`

### Primary Colors
- Background: `#1e1e2e`
- Text: `#cdd6f4`

## Customization

To modify the configuration, edit the file:
```bash
~/.config/alacritty/alacritty.toml
```

### Change shell

For Fish:
```toml
[terminal.shell]
program = "/opt/homebrew/bin/fish"
```

For Zsh:
```toml
[terminal.shell]
program = "/bin/zsh"
```

### Change opacity

```toml
[window]
opacity = 1.0  # Completely opaque
# or
opacity = 0.8  # More transparent
```

### Change font size

```toml
[font]
size = 14.0  # Larger
# or
size = 10.0  # Smaller
```

## Installation

1. Install Alacritty:
```bash
brew install --cask alacritty
```

2. Install JetBrains Mono Nerd Font:
```bash
brew tap homebrew/cask-fonts
brew install --cask font-jetbrains-mono-nerd-font
```

3. Configuration is already in place at `~/.config/alacritty/alacritty.toml`

## Resources

- [Alacritty Documentation](https://alacritty.org/)
- [Catppuccin](https://github.com/catppuccin/catppuccin)
- [JetBrains Mono](https://www.jetbrains.com/lp/mono/)
- [Nushell](https://www.nushell.sh/)
