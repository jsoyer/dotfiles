# Tmux Configuration Documentation

> Modern tmux configuration with platform-specific theming for macOS and Raspberry Pi/Linux

## File Structure

```
~/.config/tmux/
├── tmux.conf              # Main config (macOS - Catppuccin Mocha)
├── tmux-rpi.conf          # RPi/Linux config (Gruvbox Dark)
├── tmux.reset.conf        # Base keybindings reset
├── plugins/               # TPM plugins directory
│   ├── tpm/               # Tmux Plugin Manager
│   ├── tmux-sensible/     # Sensible defaults
│   ├── tmux-yank/         # Copy/paste enhancements
│   ├── tmux-resurrect/    # Session persistence
│   ├── tmux-continuum/    # Auto save/restore
│   ├── catppuccin-tmux/   # Catppuccin theme (macOS)
│   ├── tmux-sessionx/     # Session manager
│   ├── tmux-floax/        # Floating windows
│   ├── tmux-fzf/          # FZF integration
│   └── tmux-fzf-url/      # URL opener
└── scripts/
    └── cal.sh             # Calendar script
```

**Symlink:** `~/.tmux.conf -> ~/.config/tmux/tmux.conf`

## Platform Differences

| Feature | macOS | RPi/Linux |
|---------|-------|-----------|
| **Config File** | `tmux.conf` | `tmux-rpi.conf` |
| **Theme** | Catppuccin Mocha | Gruvbox Dark |
| **Status Bar** | Top | Bottom |
| **Prefix Key** | `Ctrl+A` | `Ctrl+B` |
| **Plugins** | Full (11 plugins) | Lightweight (4 plugins) |
| **Status Left** | Session name | 🍓 + Session name |
| **Status Right** | Directory + Time | Hostname + Date + Time |

### Platform Detection

On RPi/Linux, the tmux alias in `~/.zsh/00-env.zsh` automatically uses the correct config:

```bash
if [[ "${IS_RPI}" == "true" ]]; then
  alias tmux='tmux -f ~/.config/tmux/tmux-rpi.conf'
fi
```

## macOS Configuration (Catppuccin Mocha)

### Appearance

```
┌─────────────────────────────────────────────────────────────────┐
│  session   │ 1:zsh  2:nvim █ 3:git          │ ~/projects  14:30 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                     Terminal content                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Features
- Catppuccin Mocha color palette
- Status bar at top (macOS style)
- Powerline separators
- SessionX for session management
- Floax for floating windows
- Full plugin set

### Prefix: Ctrl+A

More ergonomic than default Ctrl+B, easier to reach.

## RPi/Linux Configuration (Gruvbox Dark)

### Appearance

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                     Terminal content                            │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ 🍓 main │ 1:zsh  2:nvim  3:htop         │ rpi-nas │ 17/01 14:30 │
└─────────────────────────────────────────────────────────────────┘
```

### Features
- Gruvbox Dark color palette (yellow/orange tones)
- Status bar at bottom (traditional style)
- Simple separators (no powerline)
- Raspberry icon in status bar
- Hostname always visible
- Lightweight plugin set (faster on RPi)

### Prefix: Ctrl+B

Default tmux prefix, distinguishes RPi sessions from macOS.

## Core Settings (Both Platforms)

### Essential Options

| Setting | Value | Description |
|---------|-------|-------------|
| `base-index` | 1 | Windows start at 1 |
| `escape-time` | 0 | No ESC delay (for Vim) |
| `history-limit` | 100,000+ | Large scrollback |
| `mode-keys` | vi | Vim-style navigation |
| `renumber-windows` | on | Auto-renumber windows |
| `set-clipboard` | on | System clipboard |

### Keybindings (Same on Both)

| Key | Action |
|-----|--------|
| `prefix + \|` | Vertical split |
| `prefix + -` | Horizontal split |
| `prefix + v` | Vertical split (alt) |
| `prefix + s` | Horizontal split (alt) |
| `prefix + c` | New window (keeps path) |
| `prefix + h/j/k/l` | Navigate panes (vim-style) |
| `prefix + H/L` | Previous/Next window |
| `prefix + R` | Reload config |
| `prefix + z` | Zoom pane |
| `prefix + K` | Clear screen |

## Plugin Installation

### Install TPM (Tmux Plugin Manager)

```bash
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
```

### Install Plugins

Inside tmux, press:
- **macOS:** `Ctrl+A` then `I` (capital i)
- **RPi:** `Ctrl+B` then `I`

### Update Plugins

- **macOS:** `Ctrl+A` then `U`
- **RPi:** `Ctrl+B` then `U`

## Plugins

### macOS (Full Set)

| Plugin | Description |
|--------|-------------|
| `tpm` | Plugin manager |
| `tmux-sensible` | Sensible defaults |
| `tmux-yank` | Copy to system clipboard |
| `tmux-resurrect` | Save/restore sessions |
| `tmux-continuum` | Auto save sessions |
| `catppuccin-tmux` | Catppuccin theme |
| `tmux-sessionx` | Session manager with FZF |
| `tmux-floax` | Floating terminal windows |
| `tmux-fzf` | FZF integration |
| `tmux-fzf-url` | Open URLs with FZF |
| `tmux-thumbs` | Hint-based copy |

### RPi/Linux (Lightweight)

| Plugin | Description |
|--------|-------------|
| `tpm` | Plugin manager |
| `tmux-sensible` | Sensible defaults |
| `tmux-yank` | Copy to clipboard |
| `tmux-resurrect` | Save/restore sessions |

## Color Reference

### Catppuccin Mocha (macOS)

| Element | Color | Hex |
|---------|-------|-----|
| Background | Base | `#1e1e2e` |
| Foreground | Text | `#cdd6f4` |
| Active border | Magenta | `#cba6f7` |
| Inactive border | Surface0 | `#313244` |
| Status bg | Mantle | `#181825` |

### Gruvbox Dark (RPi)

| Element | Color | Hex |
|---------|-------|-----|
| Background | bg | `#282828` |
| Foreground | fg | `#ebdbb2` |
| Active border | Yellow | `#d79921` |
| Inactive border | bg3 | `#665c54` |
| Status bg | bg1 | `#3c3836` |
| RPi icon | Red | `#cc241d` |

## Customization

### Change RPi Status Bar Color

Edit `tmux-rpi.conf`:
```bash
# Change status bar background
set -g status-style "bg=#458588 fg=#ebdbb2"  # Blue instead of gray
```

### Add Module to RPi Status

```bash
# Add CPU temperature (RPi specific)
set -g status-right "#[fg=#665c54]│ #[fg=#98971a]CPU: #(cat /sys/class/thermal/thermal_zone0/temp | awk '{print $1/1000}')°C #[fg=#665c54]│ #[fg=#458588]#H #[fg=#d79921]%H:%M "
```

### Change Window Format

```bash
# Show window flags
set -g window-status-current-format "#[fg=#282828,bg=#d79921,bold] #I:#W#F "
```

## Troubleshooting

### Wrong Config Loading on RPi

Verify the alias is set:
```bash
alias tmux
# Should show: tmux='tmux -f ~/.config/tmux/tmux-rpi.conf'
```

Force specific config:
```bash
tmux -f ~/.config/tmux/tmux-rpi.conf
```

### Plugins Not Installing

1. Check TPM is installed:
```bash
ls ~/.tmux/plugins/tpm
```

2. Press prefix + I inside tmux

3. Check for errors:
```bash
~/.tmux/plugins/tpm/bin/install_plugins
```

### Colors Look Wrong

Ensure terminal supports true color:
```bash
echo $TERM
# Should be: screen-256color or tmux-256color
```

### Prefix Key Not Working

Check which config is loaded:
```bash
tmux show-options -g prefix
```

## Quick Reference

### Session Management

```bash
tmux new -s name      # New session
tmux ls               # List sessions
tmux attach -t name   # Attach to session
tmux kill-session -t name  # Kill session
```

### Inside Tmux

| macOS | RPi | Action |
|-------|-----|--------|
| `C-a d` | `C-b d` | Detach |
| `C-a c` | `C-b c` | New window |
| `C-a ,` | `C-b ,` | Rename window |
| `C-a w` | `C-b w` | List windows |
| `C-a &` | `C-b &` | Kill window |

---

**Last Updated**: 2025-01-17
**macOS Theme**: Catppuccin Mocha (top bar, Ctrl+A)
**RPi Theme**: Gruvbox Dark (bottom bar, Ctrl+B)
