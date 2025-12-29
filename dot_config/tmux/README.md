# Tmux Configuration Documentation

> Modern tmux configuration with Catppuccin Mocha theme and productivity plugins

## 📁 Configuration Files

```
~/.config/tmux/
  ├── tmux.conf              # Main configuration file
  ├── tmux.reset.conf        # Reset/base configuration
  ├── plugins/               # TPM plugins directory
  │   ├── catppuccin-tmux    # Catppuccin theme
  │   ├── tmux-sessionx      # Session manager with FZF
  │   ├── tmux-floax         # Floating windows
  │   ├── tmux-resurrect     # Session persistence
  │   ├── tmux-continuum     # Automatic session save/restore
  │   ├── tmux-yank          # Enhanced copy/paste
  │   ├── tmux-thumbs        # Hint-based copy/paste
  │   ├── tmux-fzf           # FZF integration
  │   ├── tmux-fzf-url       # URL opener with FZF
  │   ├── tmux-sensible      # Sensible defaults
  │   └── tpm                # Tmux Plugin Manager
  └── scripts/               # Custom scripts
      └── cal.sh             # Calendar/meetings script
```

**Symlink:** `~/.tmux.conf -> ~/.config/tmux/tmux.conf`

## 🎨 Theme: Catppuccin Mocha

Configuration uses **Catppuccin Mocha** flavor explicitly:
```bash
set -g @catppuccin_flavour 'mocha'
```

### Status Bar Configuration

**Position:** Top (macOS style)

**Left side:**
- Session name

**Right side:**
- Current directory (basename)
- Time (HH:MM format)

**Window indicators:**
- Separators: `` (left), ` ` (right)
- Current window indicator: ` █`
- Zoom indicator: `()`

## ⚙️ Core Configuration

### Prefix Key
```bash
Ctrl+A  # Changed from default Ctrl+B (more ergonomic)
```

### Essential Settings

| Setting | Value | Description |
|---------|-------|-------------|
| `base-index` | 1 | Windows start at 1 (not 0) |
| `escape-time` | 0 | No ESC delay (crucial for Vim) |
| `history-limit` | 1,000,000 | Massive scrollback buffer |
| `mode-keys` | vi | Vim-style navigation |
| `renumber-windows` | on | Auto-renumber after closing |
| `set-clipboard` | on | System clipboard integration |
| `detach-on-destroy` | off | Stay in tmux after session close |
| `status-position` | top | macOS-style status bar |
| `set-titles` | on | Dynamic terminal titles |

### Terminal Settings
```bash
default-terminal: screen-256color
terminal-overrides: RGB support (true color)
default-shell: /opt/homebrew/bin/zsh
default-command: reattach-to-user-namespace (macOS clipboard)
```

### Visual Styling
```bash
pane-active-border: magenta
pane-border: brightblack
set-titles-string: #{pane_title}
```

## 🔌 Plugins (11 active)

### 1. TPM - Tmux Plugin Manager
**Repository:** `tmux-plugins/tpm`

**Purpose:** Manages all tmux plugins

**Key bindings:**
- `prefix + I` - Install plugins
- `prefix + U` - Update plugins
- `prefix + alt + u` - Uninstall plugins

---

### 2. tmux-sensible
**Repository:** `tmux-plugins/tmux-sensible`

**Purpose:** Sensible default settings

**Features:**
- Increased scrollback
- Better mouse support
- Improved window/pane management
- Faster command sequences

---

### 3. tmux-yank
**Repository:** `tmux-plugins/tmux-yank`

**Purpose:** Enhanced copy/paste with system clipboard

**Key bindings (in copy mode):**
- `y` - Copy selection to clipboard
- `Y` - Copy selection and paste
- Works seamlessly with macOS clipboard

---

### 4. tmux-resurrect
**Repository:** `tmux-plugins/tmux-resurrect`

**Purpose:** Save and restore tmux sessions

**Configuration:**
```bash
@resurrect-strategy-nvim 'session'  # Save Neovim sessions
```

**Key bindings:**
- `prefix + Ctrl+s` - Save session
- `prefix + Ctrl+r` - Restore session

**Saves:**
- Panes, windows, layouts
- Running programs
- Neovim sessions
- Working directories

---

### 5. tmux-continuum
**Repository:** `tmux-plugins/tmux-continuum`

**Purpose:** Automatic session save/restore

**Configuration:**
```bash
@continuum-restore 'on'  # Auto-restore on tmux start
```

**Features:**
- Automatic save every 15 minutes
- Automatic restore on tmux start
- Works with tmux-resurrect

---

### 6. tmux-thumbs
**Repository:** `fcsonline/tmux-thumbs`

**Purpose:** Hint-based copy/paste (like Vimium for tmux)

**Usage:**
1. `prefix + Space` (or configured key)
2. Hints appear over text
3. Type hint to copy text

**Features:**
- Copy file paths
- Copy URLs
- Copy commands
- Copy hashes/IDs

---

### 7. tmux-fzf
**Repository:** `sainnhe/tmux-fzf`

**Purpose:** FZF integration for tmux commands

**Features:**
- Fuzzy find sessions
- Fuzzy find windows
- Fuzzy find panes
- Command palette

---

### 8. tmux-fzf-url
**Repository:** `wfxr/tmux-fzf-url`

**Purpose:** Extract and open URLs with FZF

**Configuration:**
```bash
@fzf-url-fzf-options '-p 60%,30% --prompt="   " --border-label=" Open URL "'
@fzf-url-history-limit '2000'
```

**Usage:**
- `prefix + u` (default) - Open URL picker
- Select URL with FZF
- Opens in default browser

---

### 9. catppuccin-tmux
**Repository:** `omerxx/catppuccin-tmux`

**Purpose:** Catppuccin theme for tmux

**Configuration:**
```bash
@catppuccin_flavour 'mocha'  # Mocha flavor
@catppuccin_window_left_separator ""
@catppuccin_window_right_separator " "
@catppuccin_window_middle_separator " █"
@catppuccin_status_modules_right "directory date_time"
@catppuccin_status_modules_left "session"
@catppuccin_date_time_text "%H:%M"
```

**Available modules:**
- session, directory, date_time, battery, weather, cpu, ram, etc.

---

### 10. tmux-sessionx
**Repository:** `omerxx/tmux-sessionx`

**Purpose:** Advanced session manager with FZF and zoxide

**Configuration:**
```bash
@sessionx-bind 'o'                              # prefix + o
@sessionx-zoxide-mode 'on'                      # Use zoxide for smart navigation
@sessionx-custom-paths '/Users/jsoyer/dotfiles' # Custom search paths
@sessionx-window-height '85%'
@sessionx-window-width '75%'
@sessionx-auto-accept 'off'                     # Confirm before switching
@sessionx-filter-current 'false'                # Show current session
```

**Key bindings:**
- `prefix + o` - Open session picker
- `prefix + Ctrl+y` - Create session in new window

**Features:**
- Fuzzy find sessions
- Create new sessions
- Kill sessions
- Zoxide integration (smart directory jumping)
- Preview pane

---

### 11. tmux-floax
**Repository:** `omerxx/tmux-floax`

**Purpose:** Floating terminal windows

**Configuration:**
```bash
@floax-bind 'b'                  # prefix + b
@floax-width '80%'
@floax-height '80%'
@floax-border-color 'magenta'
@floax-text-color 'blue'
@floax-change-path 'true'        # Follow current path
```

**Key bindings:**
- `prefix + b` - Toggle floating window

**Use cases:**
- Quick terminal popup
- Run commands without leaving context
- Temporary calculations/notes

---

## 🎯 Common Workflows

### Session Management

```bash
# Create new session
tmux new -s project-name

# List sessions
tmux ls

# Attach to session
tmux attach -t project-name

# Switch sessions (in tmux)
prefix + o                    # Open sessionx (FZF picker)

# Save session manually
prefix + Ctrl+s

# Restore session manually
prefix + Ctrl+r
```

### Window Management

```bash
prefix + c                    # Create new window
prefix + ,                    # Rename window
prefix + n                    # Next window
prefix + p                    # Previous window
prefix + 0-9                  # Go to window number
prefix + &                    # Kill window
```

### Pane Management

```bash
prefix + %                    # Split vertically
prefix + "                    # Split horizontally
prefix + arrow keys           # Navigate panes
prefix + z                    # Zoom/unzoom pane
prefix + x                    # Kill pane
prefix + {                    # Move pane left
prefix + }                    # Move pane right
prefix + space                # Cycle layouts
```

### Copy Mode (Vi-style)

```bash
prefix + [                    # Enter copy mode
/pattern                      # Search forward
?pattern                      # Search backward
n                             # Next match
N                             # Previous match
v                             # Start selection
y                             # Copy selection
q                             # Exit copy mode
```

### Plugin-specific

```bash
# Sessionx
prefix + o                    # Open session picker

# Floax
prefix + b                    # Toggle floating window

# FZF-URL
prefix + u                    # Open URL picker

# Thumbs
prefix + Space                # Activate hints
```

## 🚀 Advanced Features

### 1. Session Persistence
Sessions are automatically saved every 15 minutes and restored on tmux start.

**Manual save/restore:**
```bash
prefix + Ctrl+s              # Save
prefix + Ctrl+r              # Restore
```

### 2. Zoxide Integration
Sessionx integrates with zoxide for smart directory jumping:
```bash
prefix + o
# Type partial directory name
# Zoxide finds most frecent match
```

### 3. Neovim Session Restoration
Neovim sessions are automatically saved and restored with tmux sessions.

### 4. Floating Windows
Quick popup terminal without disrupting layout:
```bash
prefix + b                   # Toggle floax
```

### 5. URL Extraction
Extract all URLs from scrollback and open with browser:
```bash
prefix + u                   # Opens FZF with 2000 recent URLs
```

### 6. Clipboard Integration
- Copy mode selections automatically go to system clipboard
- Works seamlessly on macOS with `reattach-to-user-namespace`

## ⌨️ Complete Keybinding Reference

### Prefix
```bash
Ctrl+A                       # Prefix key
```

### Sessions
```bash
prefix + o                   # Session picker (sessionx)
prefix + Ctrl+s              # Save session
prefix + Ctrl+r              # Restore session
prefix + d                   # Detach from session
prefix + $                   # Rename session
```

### Windows
```bash
prefix + c                   # Create window
prefix + ,                   # Rename window
prefix + &                   # Kill window
prefix + n                   # Next window
prefix + p                   # Previous window
prefix + 0-9                 # Go to window N
prefix + l                   # Last window
prefix + w                   # List windows
```

### Panes
```bash
prefix + %                   # Split vertical
prefix + "                   # Split horizontal
prefix + x                   # Kill pane
prefix + z                   # Zoom/unzoom pane
prefix + arrow               # Navigate panes
prefix + {                   # Move pane left
prefix + }                   # Move pane right
prefix + space               # Cycle layouts
prefix + !                   # Break pane to new window
```

### Copy Mode
```bash
prefix + [                   # Enter copy mode
q                            # Exit copy mode
Space                        # Start selection
Enter                        # Copy selection
y                            # Copy to clipboard
/                            # Search forward
?                            # Search backward
n                            # Next search match
N                            # Previous search match
```

### Plugins
```bash
prefix + b                   # Toggle floax (floating window)
prefix + u                   # FZF URL picker
prefix + Space               # Tmux thumbs (hints)
prefix + I                   # Install plugins
prefix + U                   # Update plugins
prefix + alt+u               # Uninstall plugins
```

### Other
```bash
prefix + :                   # Command prompt
prefix + ?                   # List all keybindings
prefix + t                   # Show clock
prefix + r                   # Reload config
```

## 🔧 Customization

### Change Prefix Key
Edit `tmux.conf`:
```bash
set -g prefix ^A             # Change to your preferred key
```

### Change Theme Flavor
Available flavors: mocha, latte, frappe, macchiato
```bash
set -g @catppuccin_flavour 'mocha'
```

### Add Status Bar Modules
```bash
set -g @catppuccin_status_modules_right "directory meetings weather date_time"
set -g @catppuccin_status_modules_left "session"
```

### Modify Floax Size
```bash
set -g @floax-width '90%'
set -g @floax-height '90%'
```

### Add Custom Keybindings
```bash
bind-key -n C-t new-window   # Ctrl+t creates new window (no prefix)
```

## 🐛 Troubleshooting

### Plugins not loading
```bash
# Install TPM first
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm

# In tmux, install plugins
prefix + I
```

### Colors not working
```bash
# Check terminal supports true color
echo $TERM

# Should be: screen-256color or tmux-256color
# In your shell config, ensure:
export TERM=xterm-256color
```

### Sessions not restoring
```bash
# Check continuum is running
tmux show-options -g | grep continuum

# Manually restore
prefix + Ctrl+r
```

### Clipboard not working on macOS
```bash
# Install reattach-to-user-namespace
brew install reattach-to-user-namespace

# Already configured in tmux.conf
```

### Floax not appearing
```bash
# Check if bound correctly
tmux list-keys | grep floax

# Try manually
prefix + b
```

## 📚 Plugin Documentation Links

- [TPM](https://github.com/tmux-plugins/tpm)
- [tmux-sensible](https://github.com/tmux-plugins/tmux-sensible)
- [tmux-yank](https://github.com/tmux-plugins/tmux-yank)
- [tmux-resurrect](https://github.com/tmux-plugins/tmux-resurrect)
- [tmux-continuum](https://github.com/tmux-plugins/tmux-continuum)
- [tmux-thumbs](https://github.com/fcsonline/tmux-thumbs)
- [tmux-fzf](https://github.com/sainnhe/tmux-fzf)
- [tmux-fzf-url](https://github.com/wfxr/tmux-fzf-url)
- [catppuccin-tmux](https://github.com/catppuccin/tmux)
- [tmux-sessionx](https://github.com/omerxx/tmux-sessionx)
- [tmux-floax](https://github.com/omerxx/tmux-floax)

## 🔄 Updating

### Update tmux
```bash
brew upgrade tmux
```

### Update plugins
```bash
# In tmux
prefix + U
```

### Reload configuration
```bash
# In tmux
tmux source ~/.config/tmux/tmux.conf

# Or with keybinding (if configured)
prefix + r
```

## 💡 Tips & Tricks

### 1. Quick session switching
Use `prefix + o` with sessionx to quickly jump between projects using zoxide's smart ranking.

### 2. Floating terminal for quick commands
`prefix + b` gives you a floating terminal perfect for:
- Quick calculations (`bc`)
- Looking up man pages
- Running one-off commands
- Taking temporary notes

### 3. Extract all URLs from scrollback
`prefix + u` shows all URLs from the last 2000 lines. Perfect for finding that link you saw earlier.

### 4. Copy/paste without mouse
Use thumbs (`prefix + Space`) to get hints over any text - faster than mouse selection.

### 5. Session persistence
Never lose your work - sessions auto-save every 15 minutes and restore on tmux start.

### 6. Vim-style navigation
With `mode-keys vi`, you can navigate copy mode like Vim:
- `hjkl` for movement
- `w/b` for word jumping
- `/` for search
- `v` for visual selection

## 🎨 Theme Consistency

Tmux is configured with **Catppuccin Mocha** to match your entire development environment:

| Tool | Theme | Status |
|------|-------|--------|
| Neovim | Catppuccin Mocha | ✅ |
| Bat | Catppuccin Mocha | ✅ |
| Starship | Catppuccin Mocha | ✅ |
| FZF | Catppuccin Mocha | ✅ |
| Eza | Catppuccin Mocha | ✅ |
| Ghostty | Catppuccin Mocha | ✅ |
| **Tmux** | **Catppuccin Mocha** | ✅ |

---

**Last updated:** 2025-12-26
**Maintained by:** Jerome Soyer
**Tmux version:** 3.x+
