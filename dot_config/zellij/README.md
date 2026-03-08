# Zellij Configuration

Customized Zellij configuration - A modern terminal multiplexer written in Rust.

## Theme

**Catppuccin Mocha** - A dark and soothing theme with pastel colors.

## Shell

By default, Nushell (nu) is configured as the shell.

```kdl
default_shell "nu"
```

## Appearance

### Interface
- **Simplified UI:** Enabled (no arrow glyphs)
- **Pane frames:** Disabled
- **Session name:** Visible in frames

### Tips on startup
- **Tips:** Disabled (`session_serialization false`)
- No welcome messages or tips on launch

## Features

### Copy/Paste
- **Copy command:** `pbcopy` (macOS)
- **Copy on select:** Enabled by default

### Scrollback
- **Buffer:** 10,000 lines (default)

### Behavior
- **Force close:** `detach` - Detaches instead of quitting
- **Editor:** Set by `$EDITOR` or `$VISUAL`

## Keyboard Shortcuts

### Main Modes
Zellij uses modal modes (like Vim). Here are the shortcuts to change modes:

- `Ctrl+G` - Locked mode
- `Ctrl+A` - Pane mode
- `Ctrl+N` - Resize mode
- `Ctrl+S` - Scroll mode
- `Ctrl+T` - Tab mode
- `Ctrl+X` - Session mode
- `Ctrl+B` - Tmux mode

### Pane Mode (Ctrl+A)
- `h/j/k/l` or arrows - Move focus
- `n` - New pane
- `d` - New pane below
- `r` - New pane right
- `x` - Close pane
- `z` - Toggle fullscreen
- `f` - Toggle frames
- `w` - Toggle floating panes
- `e` - Toggle embed/floating
- `R` - Rename pane
- `S` - Next swap layout

### Tab Mode (Ctrl+T)
- `n` - New tab
- `x` - Close tab
- `h/l` or arrows - Navigate between tabs
- `r` - Rename tab
- `s` - Toggle sync tab
- `b` - Break pane (move to new tab)
- `[` - Break pane left
- `]` - Break pane right
- `1-9` - Go to tab 1-9
- `a` - Toggle previous tab

### Resize Mode (Ctrl+N)
- `h/j/k/l` or arrows - Resize
- `H/J/K/L` - Resize (decrease)
- `=` or `+` - Increase
- `-` - Decrease

### Scroll Mode (Ctrl+S)
- `j/k` or arrows - Scroll line by line
- `Ctrl+F` / `PageDown` - Next page
- `Ctrl+B` / `PageUp` - Previous page
- `d` - Half page down
- `u` - Half page up
- `G` - Go to end
- `s` - Search mode
- `e` - Edit scrollback

### Search Mode (Ctrl+/)
- `n` - Next result
- `p` - Previous result
- `c` - Toggle case sensitivity
- `w` - Toggle whole word
- `o` - Toggle wrap

### Session Mode (Ctrl+X)
- `d` - Detach from session
- `w` - Session manager

### Tmux Mode (Ctrl+B)
Compatible with classic tmux shortcuts:
- `[` - Scroll mode
- `"` - Split horizontal
- `%` - Split vertical
- `z` - Toggle fullscreen
- `c` - New tab
- `n/p` - Next/previous tab
- `x` - Close pane
- `d` - Detach

### Global Shortcuts (all modes except locked)
- `Alt+N` - New pane
- `Alt+H/L` or `Alt+Left/Right` - Navigate focus or tab
- `Alt+J/K` or `Alt+Up/Down` - Navigate focus
- `Alt+=` or `Alt++` - Increase size
- `Alt+-` - Decrease size
- `Alt+[` - Previous layout
- `Alt+]` - Next layout
- `Alt+R` - Rename tab

## Available Themes

Your configuration includes:
- **Catppuccin Mocha** (active) - `~/.config/zellij/themes/catppuccin.kdl`
- **Dracula** - `~/.config/zellij/themes/dracula.kdl`

To change theme, modify the line in `config.kdl`:
```kdl
theme "catppuccin-mocha"
// or
theme "dracula"
```

## Plugins

### Default Plugins
- `tab-bar` - Tab bar
- `status-bar` - Status bar
- `strider` - File browser
- `compact-bar` - Compact bar

### Available Custom Plugins
- `zjstatus` - Highly customizable status bar
- `zellij-sessionizer` - Quick navigation between sessions

**Note:** WASM plugins must be downloaded and placed in `~/.config/zellij/plugins/`

## Layouts

Layouts available in `~/.config/zellij/layouts/`:
- `default.kdl` - Default layout
- `datetime.kdl` - Layout with date/time

## Customization

### Directory Structure
```
~/.config/zellij/
├── config.kdl              # Main configuration
├── layouts/
│   ├── default.kdl
│   └── datetime.kdl
├── themes/
│   ├── catppuccin.kdl
│   └── dracula.kdl
└── plugins/
    ├── zellij-sessionizer.wasm
    └── zellij-datetime.wasm
```

### Change shell

For Fish:
```kdl
default_shell "fish"
```

For Zsh:
```kdl
default_shell "zsh"
```

### Enable/Disable frames

```kdl
pane_frames true   # With frames
# or
pane_frames false  # Without frames
```

### Enable tips

If you want to re-enable tips:
```kdl
session_serialization true
```

## Installation

1. Install Zellij:
```bash
brew install zellij
```

2. Configuration is already in place at `~/.config/zellij/`

## Usage

### Start Zellij
```bash
zellij
```

### Named sessions
```bash
zellij -s my-session          # Create/attach session
zellij attach my-session      # Attach to existing session
zellij list-sessions          # List sessions
zellij delete-session my-session  # Delete session
```

### Layouts
```bash
zellij --layout default       # Use a layout
zellij --layout datetime      # Layout with datetime
```

### Detach
In Zellij: `Ctrl+X` then `d`

## Recommended Workflows

### Quick navigation
1. `Ctrl+T` + `1-9` to switch between tabs
2. `Alt+H/L` to navigate between panes/tabs
3. `Ctrl+A` + `z` to fullscreen a pane

### Organization
1. `Ctrl+T` + `n` to create thematic tabs
2. `Ctrl+A` + `d/r` to split horizontally/vertically
3. `Ctrl+A` + `S` to change layout

### Productivity
1. `Ctrl+T` + `s` to synchronize commands on all panes
2. `Ctrl+S` to view history
3. `Ctrl+X` + `w` to switch between projects

## Resources

- [Zellij Documentation](https://zellij.dev/)
- [Catppuccin](https://github.com/catppuccin/catppuccin)
- [Nushell](https://www.nushell.sh/)
- [zjstatus](https://github.com/dj95/zjstatus)
- [zellij-sessionizer](https://github.com/laperlej/zellij-sessionizer)

## Tips

- Keybindings are fully customized with `clear-defaults=true`
- Tmux mode available for easy transition from tmux
- Alt shortcuts work in all modes (except locked)
- `Ctrl+G` to lock the interface and use native shortcuts
- Sessions persist after closing terminal (with `detach`)
