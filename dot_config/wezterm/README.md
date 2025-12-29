# WezTerm Configuration

WezTerm is a powerful GPU-accelerated terminal emulator with modern features. This configuration sets up WezTerm with **Catppuccin Mocha** theme and extensive keybindings for productivity.

## Overview

- **Version**: WezTerm 20240203-110809-5046fc22
- **Theme**: Catppuccin Mocha
- **Font**: JetBrains Mono (12pt)
- **Shell**: Fish
- **Location**: `~/.config/wezterm/`

## File Structure

```
~/.config/wezterm/
├── wezterm.lua    # Main configuration file
└── README.md      # This file
```

## Features

### 🐚 Fish Shell Integration
- Fish configured as default shell
- User-friendly interactive shell with autosuggestions
- Consistent with Catppuccin Mocha theme
- Enhanced productivity with syntax highlighting and completions

### ✨ Modern Terminal Experience
- GPU-accelerated rendering
- Ligature support with JetBrains Mono
- Built-in multiplexer (panes and tabs)
- Cross-platform consistency
- Image protocol support

### 🎨 Catppuccin Mocha Theme
- Soothing pastel colors
- Consistent with your entire development environment
- Custom tab bar styling
- Inactive pane dimming for better focus

### ⌨️ Comprehensive Keybindings
- tmux/zellij-style pane management
- Vim-style navigation
- Tab management
- Copy/paste shortcuts
- Search functionality

## Catppuccin Mocha Colors

### Tab Bar Colors
| Element           | Color     | Hex       |
|-------------------|-----------|-----------|
| Background        | Base      | `#1e1e2e` |
| Active Tab BG     | Blue      | `#89b4fa` |
| Active Tab FG     | Base      | `#1e1e2e` |
| Inactive Tab BG   | Surface0  | `#313244` |
| Inactive Tab FG   | Text      | `#cdd6f4` |
| Hover BG          | Surface1  | `#45475a` |

### Color Palette
All Catppuccin Mocha colors are available:
- Base: `#1e1e2e`, Mantle: `#181825`, Crust: `#11111b`
- Text: `#cdd6f4`, Subtext: `#bac2de`, `#a6adc8`
- Surfaces: `#313244`, `#45475a`, `#585b70`
- Blue: `#89b4fa`, Red: `#f38ba8`, Green: `#a6e3a1`
- Yellow: `#f9e2af`, Mauve: `#cba6f7`, Pink: `#f5c2e7`
- Teal: `#94e2d5`, Peach: `#fab387`, Flamingo: `#f2cdcd`

## Keybindings Reference

All keybindings use `Ctrl+Shift` unless otherwise noted.

### Window Management

| Keybinding      | Action                    |
|-----------------|---------------------------|
| `Ctrl+Shift+F`  | Toggle fullscreen         |
| `Ctrl+'`        | Clear scrollback          |
| `Ctrl+=`        | Increase font size        |
| `Ctrl+-`        | Decrease font size        |
| `Ctrl+0`        | Reset font size           |

### Pane Splitting

| Keybinding      | Action                    |
|-----------------|---------------------------|
| `Ctrl+Shift+\|` | Split horizontal (left/right) |
| `Ctrl+Shift+_`  | Split vertical (top/bottom) |
| `Ctrl+Shift+D`  | Split horizontal (alt)    |
| `Ctrl+Shift+Shift+D` | Split vertical (alt) |

### Pane Navigation (Vim-style)

| Keybinding      | Action                    |
|-----------------|---------------------------|
| `Ctrl+Shift+H`  | Move to left pane         |
| `Ctrl+Shift+L`  | Move to right pane        |
| `Ctrl+Shift+K`  | Move to pane above        |
| `Ctrl+Shift+J`  | Move to pane below        |

### Pane Resizing

| Keybinding              | Action                    |
|-------------------------|---------------------------|
| `Ctrl+Shift+LeftArrow`  | Resize pane left          |
| `Ctrl+Shift+RightArrow` | Resize pane right         |
| `Ctrl+Shift+UpArrow`    | Resize pane up            |
| `Ctrl+Shift+DownArrow`  | Resize pane down          |

### Pane Management

| Keybinding      | Action                    |
|-----------------|---------------------------|
| `Ctrl+Shift+W`  | Close current pane        |
| `Ctrl+Shift+Z`  | Toggle pane zoom (fullscreen) |
| `Ctrl+Shift+R`  | Rotate panes clockwise    |

### Tab Management

| Keybinding      | Action                    |
|-----------------|---------------------------|
| `Ctrl+Shift+T`  | New tab                   |
| `Ctrl+Shift+X`  | Close current tab         |
| `Ctrl+Shift+[`  | Previous tab              |
| `Ctrl+Shift+]`  | Next tab                  |
| `Ctrl+Shift+{`  | Move tab left             |
| `Ctrl+Shift+}`  | Move tab right            |
| `Ctrl+Shift+1-9`| Jump to tab 1-9           |

### Copy/Paste

| Keybinding      | Action                    |
|-----------------|---------------------------|
| `Ctrl+Shift+C`  | Copy to clipboard         |
| `Ctrl+Shift+V`  | Paste from clipboard      |

### Search

| Keybinding      | Action                    |
|-----------------|---------------------------|
| `Ctrl+F`        | Search (current selection or empty) |

### Scrollback

| Keybinding      | Action                    |
|-----------------|---------------------------|
| `Shift+PageUp`  | Scroll up one page        |
| `Shift+PageDown`| Scroll down one page      |

## Mouse Bindings

| Action              | Effect                    |
|---------------------|---------------------------|
| `Ctrl+Click`        | Open link under cursor    |
| `Right Click`       | Paste from clipboard      |
| `Select + Release`  | Auto-copy to clipboard    |

## Configuration Details

### Shell Configuration
```lua
default_prog = { "/opt/homebrew/bin/fish" }
```

WezTerm launches Fish by default, providing:
- Intelligent autosuggestions based on command history
- Syntax highlighting with instant feedback
- Web-based configuration interface
- Integration with your Catppuccin Mocha environment

**Note**: The path `/opt/homebrew/bin/fish` is for Homebrew installations on Apple Silicon Macs. For Intel Macs, use `/usr/local/bin/fish`. Verify your Fish path with `which fish`.

### Font Configuration
```lua
font = wezterm.font("JetBrains Mono")
font_size = 12.0
```

JetBrains Mono provides:
- Excellent code ligatures
- Clear distinction between similar characters (0/O, 1/l/I)
- Optimized for long coding sessions

### Window Styling
```lua
window_decorations = "RESIZE"
window_background_opacity = 0.9
macos_window_background_blur = 30
```

- Minimal decorations (no title bar)
- Solid background for better readability
- macOS blur effect for aesthetic integration

### Window Padding
```lua
window_padding = {
  left = 12,
  right = 12,
  top = 12,
  bottom = 12,
}
```

Comfortable spacing around content.

### Tab Bar
```lua
enable_tab_bar = true
hide_tab_bar_if_only_one_tab = true
use_fancy_tab_bar = false
```

- Tab bar appears when you have multiple tabs
- Native style for consistency
- Catppuccin Mocha colors

### Pane Dimming
```lua
inactive_pane_hsb = {
  saturation = 0.8,
  brightness = 0.6,
}
```

Inactive panes are dimmed to help you focus on the active pane.

### Performance
```lua
animation_fps = 60
max_fps = 60
scrollback_lines = 10000
```

- Smooth 60fps animations
- 10,000 lines of scrollback history

## Common Workflows

### Workflow 1: Side-by-Side Editing
```
1. Open WezTerm
2. Ctrl+Shift+| - Split horizontally
3. Ctrl+Shift+H/L - Navigate between panes
4. Edit in both panes simultaneously
```

### Workflow 2: Multi-Project Tabs
```
1. Ctrl+Shift+T - New tab for each project
2. Ctrl+Shift+1-9 - Jump between projects
3. Ctrl+Shift+_ - Split vertically within a project
```

### Workflow 3: Code + Server
```
1. Ctrl+Shift+| - Split horizontal
2. Left pane: Edit code with vim/nvim
3. Right pane: Run development server
4. Ctrl+Shift+Z - Zoom active pane when needed
```

### Workflow 4: Research Mode
```
1. Ctrl+Shift+_ - Split vertical
2. Top: Documentation/reference
3. Bottom: Implement code
4. Ctrl+Shift+K/J - Navigate quickly
```

## Tips & Tricks

### 1. Quick Splits
Instead of typing the full split commands:
- `Ctrl+Shift+|` for horizontal (side-by-side)
- `Ctrl+Shift+_` for vertical (top-bottom)

### 2. Pane Zoom
Working in a small pane? `Ctrl+Shift+Z` toggles fullscreen for current pane.

### 3. Font Size Adjustment
Quick font changes without config edits:
- `Ctrl+=` to increase
- `Ctrl+-` to decrease
- `Ctrl+0` to reset

### 4. Link Opening
`Ctrl+Click` any URL to open in your default browser.

### 5. Tab Switching
Use `Ctrl+Shift+1-9` for instant tab access instead of cycling with `[` and `]`.

### 6. Quick Paste
Right-click anywhere to paste - faster than keyboard for quick operations.

### 7. Search History
`Ctrl+F` opens search - type to find text in scrollback.

## Customization

### Change Default Shell
To use a different shell (bash, zsh, nushell, etc.):
```lua
-- For zsh
default_prog = { "/bin/zsh" }

-- For nushell
default_prog = { "/opt/homebrew/bin/nu" }

-- For bash
default_prog = { "/bin/bash" }

-- To use system default (no override)
-- Simply comment out or remove the default_prog line
```

### Change Font
```lua
font = wezterm.font("Fira Code")  -- or "Hack", "Source Code Pro", etc.
font_size = 14.0
```

### Adjust Transparency
```lua
window_background_opacity = 0.95  -- 0.0 (transparent) to 1.0 (opaque)
```

### Modify Blur
```lua
macos_window_background_blur = 40  -- 0 (no blur) to 100 (max blur)
```

### Change Padding
```lua
window_padding = {
  left = 20,
  right = 20,
  top = 20,
  bottom = 20,
}
```

### Disable Pane Dimming
```lua
inactive_pane_hsb = {
  saturation = 1.0,
  brightness = 1.0,
}
```

### Always Show Tab Bar
```lua
hide_tab_bar_if_only_one_tab = false
```

## Troubleshooting

### Configuration Not Loading

**Check syntax:**
```bash
wezterm --config-file ~/.config/wezterm/wezterm.lua
```

**View errors:**
```bash
wezterm show-config
```

### Fish Not Launching

**Verify Fish is installed:**
```bash
which fish
```

**Install Fish:**
```bash
brew install fish
```

**Wrong path in config:**
If Fish is installed but not launching, check the path:
```bash
which fish  # Shows actual Fish location
```

Then update `wezterm.lua`:
```lua
default_prog = { "/path/shown/by/which/fish" }
```

### Font Not Rendering

**List available fonts:**
```bash
wezterm ls-fonts
```

**Verify JetBrains Mono is installed:**
```bash
wezterm ls-fonts | grep -i jetbrains
```

**Install JetBrains Mono:**
```bash
brew install --cask font-jetbrains-mono
```

### Keybindings Not Working

1. Check for conflicts with macOS system shortcuts
2. Try in a new tab/pane
3. Restart WezTerm completely

### Tab Bar Not Showing

If you want it always visible:
```lua
hide_tab_bar_if_only_one_tab = false
```

### Colors Look Wrong

1. Verify theme is set:
   ```lua
   color_scheme = "Catppuccin Mocha"
   ```
2. Check terminal color profile in macOS preferences
3. Restart WezTerm

### Performance Issues

**Reduce animation:**
```lua
animation_fps = 30
max_fps = 30
```

**Reduce scrollback:**
```lua
scrollback_lines = 5000
```

## Comparison with Other Terminals

| Feature              | WezTerm  | iTerm2   | Alacritty | Kitty    |
|----------------------|----------|----------|-----------|----------|
| GPU Accelerated      | ✅       | ✅       | ✅        | ✅       |
| Built-in Multiplexer | ✅       | ✅       | ❌        | ✅       |
| Ligatures            | ✅       | ✅       | ✅        | ✅       |
| Config Language      | Lua      | GUI      | TOML      | Config   |
| Image Support        | ✅       | ✅       | ❌        | ✅       |
| Cross-platform       | ✅       | ❌       | ✅        | ✅       |
| Tabs                 | ✅       | ✅       | ❌        | ✅       |
| Splits               | ✅       | ✅       | ❌        | ✅       |

## Advanced Features

### 1. Hyperlinks
WezTerm automatically detects and highlights URLs. `Ctrl+Click` to open.

### 2. Image Display
Supports kitty graphics protocol for inline images in terminal.

### 3. Unicode Support
Full emoji and unicode character support with proper rendering.

### 4. Custom Domains
Create isolated shell environments with domains (advanced usage).

### 5. SSH Integration
WezTerm can manage SSH connections with preserved theming.

## Resources

- **WezTerm Documentation**: https://wezfurlong.org/wezterm/
- **Catppuccin for WezTerm**: Built-in theme
- **WezTerm GitHub**: https://github.com/wez/wezterm
- **Keybindings Reference**: https://wezfurlong.org/wezterm/config/keys.html

## Theme Consistency

This WezTerm configuration uses **Catppuccin Mocha** to match your entire environment:

- ✅ **Neovim**: Catppuccin Mocha
- ✅ **Bat**: Catppuccin Mocha
- ✅ **Starship**: Catppuccin Mocha palette
- ✅ **Zsh/FZF/Eza**: Catppuccin Mocha
- ✅ **Tmux**: Catppuccin Mocha
- ✅ **Ghostty**: Catppuccin Mocha
- ✅ **Zellij**: Catppuccin Mocha
- ✅ **Nushell**: Catppuccin Mocha
- ✅ **Fish**: Catppuccin Mocha
- ✅ **OBS Studio**: Catppuccin Mocha
- ✅ **WezTerm**: Catppuccin Mocha

## Quick Reference Card

### Most Used Commands
```
Splits:     Ctrl+Shift+|  Ctrl+Shift+_
Navigate:   Ctrl+Shift+H/J/K/L
Tabs:       Ctrl+Shift+T  Ctrl+Shift+1-9
Copy:       Ctrl+Shift+C
Paste:      Ctrl+Shift+V  or  Right Click
Search:     Ctrl+F
Zoom:       Ctrl+Shift+Z
Close:      Ctrl+Shift+W
```

---

**Updated**: 2025-12-26  
**Theme**: Catppuccin Mocha  
**Shell**: Fish  
**Terminal**: WezTerm 20240203-110809-5046fc22

## Synchronization with Ghostty

WezTerm is configured to match Ghostty for a consistent visual experience:

| Setting              | Value | Notes                           |
|----------------------|-------|---------------------------------|
| Font                 | JetBrains Mono | Same font in both terminals |
| Font Size            | 12pt  | Matches Ghostty exactly         |
| Background Opacity   | 0.9   | 90% opaque, 10% transparent     |
| macOS Blur           | 30    | Same blur effect                |
| Theme                | Catppuccin Mocha | Consistent colors        |

This ensures that switching between WezTerm and Ghostty provides a seamless experience with identical appearance.

