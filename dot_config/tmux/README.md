# Tmux Configuration Documentation

> Modern tmux configuration with platform-specific theming for macOS and Raspberry Pi/Linux

## File Structure

```
~/.config/tmux/
├── tmux.conf              # Main config (auto-detects platform via chezmoi template)
├── tmux-rpi.conf          # RPi/Linux config (Snazzy theme)
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

## Platform Differences

| Feature | macOS | RPi/Linux |
|---------|-------|-----------|
| **Theme** | Catppuccin Mocha | Snazzy |
| **Status Bar** | Top | Bottom |
| **Prefix Key** | `Ctrl+A` | `Ctrl+B` |
| **Plugins** | Full (11 plugins) | Lightweight (4 plugins) |
| **Status Left** | Session name | 🍓 + Session name |
| **Status Right** | Directory + Time | Hostname + Date + Time |

### Platform Detection

The `tmux.conf.tmpl` chezmoi template auto-detects the platform at install time:

- **RPi**: detected via `contains "rpi" .chezmoi.kernel.osrelease` — generates a `tmux.conf` that sources `tmux-rpi.conf`
- **macOS / other Linux**: generates the full Catppuccin config inline

No shell alias is needed — tmux always loads `~/.config/tmux/tmux.conf` and the template takes care of the rest.

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

## RPi/Linux Configuration (Snazzy)

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
- Snazzy color palette (vibrant blues, pinks, cyans)
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
| `Alt+h/l` | Previous/Next window without prefix |
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

### Snazzy (RPi)

| Element | Color | Hex |
|---------|-------|-----|
| Background | bg | `#282a36` |
| Foreground | fg | `#eff0eb` |
| Active border | Blue | `#57c7ff` |
| Inactive border | Gray | `#3a3d4d` |
| Red | RPi icon | `#ff5c57` |
| Green | Separators | `#5af78e` |
| Yellow | Session name | `#f3f99d` |
| Magenta | Date | `#ff6ac1` |
| Cyan | Window tabs | `#9aedfe` |

## Customization

### Change RPi Status Bar Color

Edit `tmux-rpi.conf`:
```bash
# Change status bar background
set -g status-style "bg=#57c7ff fg=#282a36"  # Blue instead of dark
```

### Add Module to RPi Status

```bash
# Add CPU temperature (RPi specific)
set -g status-right "#[fg=#5af78e]│ #[fg=#f3f99d]CPU: #(cat /sys/class/thermal/thermal_zone0/temp | awk '{print $1/1000}')°C #[fg=#5af78e]│ #[fg=#57c7ff]#H #[fg=#ff6ac1]%H:%M "
```

### Change Window Format

```bash
# Show window flags
set -g window-status-current-format "#[fg=#282a36,bg=#57c7ff,bold] #I:#W#F "
```

## Troubleshooting

### Wrong Config Loading on RPi

Verify the generated config sources the RPi file:
```bash
head -1 ~/.config/tmux/tmux.conf
# Should show: source-file ~/.config/tmux/tmux-rpi.conf
```

Force re-generation via chezmoi:
```bash
chezmoi apply ~/.config/tmux/tmux.conf
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

**Last Updated**: 2026-02-16
**macOS Theme**: Catppuccin Mocha (top bar, Ctrl+A)
**RPi Theme**: Snazzy (bottom bar, Ctrl+B)
