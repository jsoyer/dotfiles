# Kitty Configuration

Customized Kitty configuration based on Ghostty, WezTerm and Alacritty.

## Theme

**Catppuccin Mocha** - A dark and soothing theme with pastel colors.

## Font

- **Family:** JetBrainsMono Nerd Font
- **Size:** 12px
- **Ligatures:** Enabled

## Shell

By default, Nushell (nu) is configured as the shell.

```conf
shell /opt/homebrew/bin/nu
```

**Important note:** Make sure the Homebrew PATH is configured in your `env.nu` before initializing Starship and other tools.

## Appearance

### Window
- **Padding:** 12px on each side
- **Decorations:** Title bar hidden (titlebar-only)
- **Opacity:** 0.9 (90%)
- **Blur:** Enabled with intensity of 30

### Cursor
- **Shape:** Block
- **Blinking:** Disabled

### Tab Bar
- **Position:** Top
- **Style:** Powerline with slanted effect
- **Display:** Always visible

## Features

### Selection
- **Copy on select:** Enabled - Selected text is automatically copied to clipboard

### Scrollback
- **History:** 10,000 lines
- **Scroll multiplier:** 5x

### Terminal
- **TERM:** xterm-256color

### Bell
- **Audio:** Disabled
- **Visual:** Disabled

## Keyboard Shortcuts

### Copy/Paste
- `Cmd+C` / `Ctrl+Shift+C` - Copy
- `Cmd+V` / `Ctrl+Shift+V` - Paste
- `Ctrl+Alt+F1` / `Ctrl+Alt+F2` - Copy/paste from internal buffer `a`
- `Ctrl+Alt+F3` / `Ctrl+Alt+F4` - Copy/paste from internal buffer `b`
- `Ctrl+Alt+F5` / `Ctrl+Alt+F6` - Copy/paste from internal buffer `c`

### Search
- `Cmd+F` / `Ctrl+Shift+F` - Search with fzf

### Font Size
- `Cmd+=` / `Ctrl+=` - Increase size
- `Cmd+-` / `Ctrl+-` - Decrease size
- `Cmd+0` / `Ctrl+0` - Reset size

### Navigation
- `Shift+PageUp` - Scroll up
- `Shift+PageDown` - Scroll down
- `Cmd+Home` - Go to beginning
- `Cmd+End` - Go to end

### Window Management
- `Cmd+N` / `Ctrl+Shift+N` - New window
- `Cmd+W` / `Ctrl+Shift+W` - Close window

### Splits Layout
- `F4` - New split, automatic direction based on current window shape
- `F5` - New horizontal split, windows stacked one above the other
- `F6` - New vertical split, windows side by side
- `F7` - Rotate the current split axis
- `Shift+Up/Left/Right/Down` - Move the active window in that direction
- `Ctrl+Up/Left/Right/Down` - Focus the neighboring window in that direction
- `Ctrl+Shift+Up/Left/Right/Down` - Move the active window to the matching screen edge
- `Ctrl+.` - Set the current split bias to 80%
- `Ctrl+,` - Reset the current split bias to 50%
- `Ctrl+Alt+H` - Toggle horizontal maximization for the active window
- `Ctrl+Alt+V` - Toggle vertical maximization for the active window

### Window Resizing
- `Ctrl+Alt+Left` - Make the active window narrower
- `Ctrl+Alt+Right` - Make the active window wider
- `Ctrl+Alt+Up` - Make the active window taller
- `Ctrl+Alt+Down` - Make the active window shorter by 3 cells
- `Ctrl+Alt+Home` - Reset all window sizes in the current tab

The resizing shortcuts add `Alt` compared to Kitty's documentation because `Ctrl+Arrow` is reserved for Splits focus navigation. On macOS, the right Option key is configured as Alt so left Option remains available for normal text input.

### Tab Management
- `Cmd+T` / `Ctrl+Shift+T` - New tab
- `Cmd+W` / `Ctrl+Shift+X` - Close tab
- `Cmd+]` / `Ctrl+Shift+]` - Next tab
- `Cmd+[` / `Ctrl+Shift+[` - Previous tab
- `Cmd+Shift+]` - Move tab forward
- `Cmd+Shift+[` - Move tab backward
- `Cmd+1` to `Cmd+9` - Go to tab 1-9

### Configuration
- `Cmd+Shift+R` / `Ctrl+Shift+R` - Reload configuration

## Mouse

- **Hiding:** Cursor is never hidden
- **URLs:** Underline style with curly effect
- **Opening:** Cmd+click to open links

## Catppuccin Mocha Color Palette

### Normal Colors
- Black (0): `#45475a`
- Red (1): `#f38ba8`
- Green (2): `#a6e3a1`
- Yellow (3): `#f9e2af`
- Blue (4): `#89b4fa`
- Magenta (5): `#f5c2e7`
- Cyan (6): `#94e2d5`
- White (7): `#bac2de`

### Bright Colors
- Black (8): `#585b70`
- Red (9): `#f38ba8`
- Green (10): `#a6e3a1`
- Yellow (11): `#f9e2af`
- Blue (12): `#89b4fa`
- Magenta (13): `#f5c2e7`
- Cyan (14): `#94e2d5`
- White (15): `#a6adc8`

### Primary Colors
- Background: `#1e1e2e`
- Text: `#cdd6f4`
- Selection (bg): `#f5e0dc`
- Selection (fg): `#1e1e2e`
- Cursor: `#f5e0dc`

### Tab Colors
- Active tab (bg): `#89b4fa`
- Active tab (fg): `#1e1e2e`
- Inactive tab (bg): `#313244`
- Inactive tab (fg): `#cdd6f4`

## Customization

To modify the configuration, edit the file:
```bash
~/.config/kitty/kitty.conf
```

### Change shell

For Fish:
```conf
shell /opt/homebrew/bin/fish
```

For Zsh:
```conf
shell /bin/zsh
```

### Change opacity

```conf
background_opacity 1.0  # Completely opaque
# or
background_opacity 0.8  # More transparent
```

### Change font size

```conf
font_size 14.0  # Larger
# or
font_size 10.0  # Smaller
```

### Change tab bar style

```conf
tab_bar_style fade      # Fade style
# or
tab_bar_style separator # Separator style
# or
tab_bar_style hidden    # Hide bar
```

## Installation

1. Install Kitty:
```bash
brew install --cask kitty
```

2. Install JetBrains Mono Nerd Font:
```bash
brew tap homebrew/cask-fonts
brew install --cask font-jetbrains-mono-nerd-font
```

3. (Optional) Install fzf for search:
```bash
brew install fzf
```

4. Configuration is already in place at `~/.config/kitty/kitty.conf`

## Advanced Kitty Features

### Image Support
Kitty supports displaying images directly in the terminal with the Kitty graphics protocol.

### Hints (Link Detection)
Kitty can detect and automatically open URLs, file paths, etc.

### Layouts
Kitty supports multiple layouts to organize your windows (splits, stack, etc.)

### Marks
You can mark text in the terminal to return to it easily.

## Nushell Configuration

If you use Nushell, make sure your `env.nu` configures the PATH before initializing Starship:

```nu
# In ~/Library/Application Support/nushell/env.nu
$env.PATH = ($env.PATH | split row (char esep) | prepend '/opt/homebrew/bin')
```

This avoids "starship command not found" errors on startup.

## Resources

- [Kitty Documentation](https://sw.kovidgoyal.net/kitty/)
- [Catppuccin](https://github.com/catppuccin/catppuccin)
- [JetBrains Mono](https://www.jetbrains.com/lp/mono/)
- [Nushell](https://www.nushell.sh/)
- [fzf](https://github.com/junegunn/fzf)

## Tips

- Use `Cmd+Shift+R` to reload the config without restarting Kitty
- Font ligatures are enabled for better code rendering
- Search with fzf allows quick navigation through scrollback
- Kitty is GPU-accelerated for optimal performance
