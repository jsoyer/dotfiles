# Zellij Plugins Guide

> Guide for installing and configuring Zellij plugins

## 🔌 Recommended Plugins

Based on your Tmux workflow, here are the most useful plugins:

### 1. zjstatus - Custom Status Bar ⭐
**Replacement for:** Tmux catppuccin status bar  
**GitHub:** [dj95/zjstatus](https://github.com/dj95/zjstatus)

**Features:**
- Highly customizable status bar
- Catppuccin Mocha theme support
- Show session, tabs, time, etc.
- Replaces default Zellij status bar

**Installation:**
```bash
# Download latest release
wget https://github.com/dj95/zjstatus/releases/latest/download/zjstatus.wasm \
  -O ~/.config/zellij/plugins/zjstatus.wasm

# Or download manually from GitHub releases
```

**Configuration:** See zjstatus example layouts below

---

### 2. zellij-sessionizer - Session Manager ⭐
**Replacement for:** Tmux sessionx  
**GitHub:** [laperlej/zellij-sessionizer](https://github.com/laperlej/zellij-sessionizer)

**Features:**
- Quick session navigation with FZF
- Create sessions from folders
- Similar to ThePrimeagen's tmux-sessionizer

**Installation:**
```bash
# Download latest release
wget https://github.com/laperlej/zellij-sessionizer/releases/latest/download/zellij-sessionizer.wasm \
  -O ~/.config/zellij/plugins/zellij-sessionizer.wasm
```

**Alternative:** [cunialino/zellij-sessionizer](https://github.com/cunialino/zellij-sessionizer)

---

### 3. harpoon - Quick Pane Navigation
**GitHub:** Community plugin (check awesome-zellij)

**Features:**
- Mark and jump to panes quickly
- Like Neovim's harpoon

---

### 4. Monocle - Fuzzy File Finder
**Replacement for:** Tmux fzf  
**GitHub:** Check awesome-zellij

**Features:**
- Fuzzy find files and content
- Open results in $EDITOR

---

### 5. ghost - Floating Commands
**Replacement for:** Tmux floax  
**GitHub:** Community plugin

**Features:**
- Spawn floating command panes
- Quick terminal popups

---

## 📦 Installation Steps

### Method 1: Manual Installation (Recommended)

1. **Create plugins directory:**
```bash
mkdir -p ~/.config/zellij/plugins
```

2. **Download plugin .wasm files:**
```bash
# zjstatus
wget https://github.com/dj95/zjstatus/releases/latest/download/zjstatus.wasm \
  -O ~/.config/zellij/plugins/zjstatus.wasm

# zellij-sessionizer
wget https://github.com/laperlej/zellij-sessionizer/releases/latest/download/zellij-sessionizer.wasm \
  -O ~/.config/zellij/plugins/zellij-sessionizer.wasm
```

3. **Update config.kdl:**
```kdl
plugins {
    zjstatus location="file:~/.config/zellij/plugins/zjstatus.wasm"
    sessionizer location="file:~/.config/zellij/plugins/zellij-sessionizer.wasm" {
        cwd "~/"
    }
}
```

4. **Restart Zellij:**
```bash
zellij kill-all-sessions
zellij
```

5. **Grant permissions** when prompted (press `y`)

---

### Method 2: Auto-download (URL-based)

**Warning:** May cause download corruption with multiple tabs

```kdl
plugins {
    zjstatus location="https://github.com/dj95/zjstatus/releases/latest/download/zjstatus.wasm"
    sessionizer location="https://github.com/laperlej/zellij-sessionizer/releases/latest/download/zellij-sessionizer.wasm" {
        cwd "~/"
    }
}
```

---

## 🎨 zjstatus with Catppuccin Mocha

Create `~/.config/zellij/layouts/default.kdl`:

```kdl
layout {
    default_tab_template {
        children
        pane size=1 borderless=true {
            plugin location="file:~/.config/zellij/plugins/zjstatus.wasm" {
                format_left   "{mode}#[bg=#181825] {tabs}"
                format_center ""
                format_right  "#[bg=#181825,fg=#89b4fa]#[bg=#89b4fa,fg=#1e1e2e,bold] {session} #[bg=#181825] {datetime}"
                format_space  ""
                
                // Catppuccin Mocha colors
                mode_normal        "#[bg=#89b4fa,fg=#1e1e2e,bold] NORMAL#[bg=#181825,fg=#89b4fa]"
                mode_locked        "#[bg=#f38ba8,fg=#1e1e2e,bold] LOCKED#[bg=#181825,fg=#f38ba8]"
                mode_resize        "#[bg=#fab387,fg=#1e1e2e,bold] RESIZE#[bg=#181825,fg=#fab387]"
                mode_pane          "#[bg=#a6e3a1,fg=#1e1e2e,bold] PANE#[bg=#181825,fg=#a6e3a1]"
                mode_tab           "#[bg=#f9e2af,fg=#1e1e2e,bold] TAB#[bg=#181825,fg=#f9e2af]"
                mode_scroll        "#[bg=#cba6f7,fg=#1e1e2e,bold] SCROLL#[bg=#181825,fg=#cba6f7]"
                mode_enter_search  "#[bg=#94e2d5,fg=#1e1e2e,bold] SEARCH#[bg=#181825,fg=#94e2d5]"
                mode_search        "#[bg=#94e2d5,fg=#1e1e2e,bold] SEARCH#[bg=#181825,fg=#94e2d5]"
                mode_rename_tab    "#[bg=#f9e2af,fg=#1e1e2e,bold] RENAME#[bg=#181825,fg=#f9e2af]"
                mode_rename_pane   "#[bg=#a6e3a1,fg=#1e1e2e,bold] RENAME#[bg=#181825,fg=#a6e3a1]"
                mode_session       "#[bg=#f5c2e7,fg=#1e1e2e,bold] SESSION#[bg=#181825,fg=#f5c2e7]"
                mode_move          "#[bg=#fab387,fg=#1e1e2e,bold] MOVE#[bg=#181825,fg=#fab387]"
                mode_tmux          "#[bg=#cba6f7,fg=#1e1e2e,bold] TMUX#[bg=#181825,fg=#cba6f7]"
                
                tab_normal              "#[bg=#181825,fg=#cdd6f4] {index} {name} {fullscreen_indicator}{sync_indicator}{floating_indicator}"
                tab_active              "#[bg=#313244,fg=#89b4fa,bold] {index} {name} {fullscreen_indicator}{sync_indicator}{floating_indicator}"
                tab_fullscreen_indicator "□ "
                tab_sync_indicator       " "
                tab_floating_indicator   "󰉈 "
                
                datetime        "#[fg=#cdd6f4,bold] {format} "
                datetime_format "%H:%M"
                datetime_timezone "local"
            }
        }
    }
}
```

---

## 🎯 Keybinding Suggestions

Add to your `config.kdl` keybindings:

```kdl
shared_except "locked" {
    // Quick sessionizer access
    bind "Alt s" {
        LaunchPlugin "sessionizer" {
            floating true
        }
    }
}
```

---

## 🔧 Plugin Management

### List Running Plugins
```
Ctrl+o p    # Opens plugin manager (built-in)
```

### Clear Plugin Cache
If plugins misbehave after updates:
```bash
rm -rf ~/.cache/zellij/*
```

### Reload Plugin
Kill and restart Zellij session

---

## 📚 More Plugins

Visit [awesome-zellij](https://github.com/zellij-org/awesome-zellij) for complete list:

**Navigation:**
- harpoon - Quick pane navigation
- room - Tab search and switch
- zbuffers - Buffer-like tab management

**Development:**
- grab - Fuzzy finder for Rust
- Monocle - File and content search
- jbz - Just + Bacon integration

**Utilities:**
- zellij-autolock - Auto-lock by command
- zellij-forgot - Quick access lists
- zellij-bookmarks - Command bookmarks

**Status Bars:**
- zjstatus - Highly customizable (recommended)
- zj-status-bar - Compact alternative

---

## 🐛 Troubleshooting

### Plugin Won't Load
1. Check file path is correct
2. Verify .wasm file downloaded correctly
3. Grant permissions when prompted (press `y`)
4. Clear cache: `rm -rf ~/.cache/zellij/*`

### Download Corrupted
Use manual installation instead of URL-based

### Permission Denied
Press `y` when Zellij asks for plugin permissions

### Plugin Crashes
Check Zellij version compatibility
Update to latest Zellij: `brew upgrade zellij`

---

## 🔄 Comparison with Tmux Plugins

| Tmux Plugin | Zellij Equivalent | Status |
|-------------|-------------------|--------|
| catppuccin-tmux | zjstatus + layout | ✅ Available |
| tmux-sessionx | zellij-sessionizer | ✅ Available |
| tmux-floax | Built-in + ghost | ✅ Built-in |
| tmux-fzf-url | Not yet available | ⏳ Missing |
| tmux-thumbs | Not yet available | ⏳ Missing |
| tmux-resurrect | Built-in | ✅ Built-in |
| tmux-continuum | Built-in | ✅ Built-in |
| tmux-yank | Built-in clipboard | ✅ Built-in |

---

**Last updated:** 2025-12-26  
**Zellij version:** 0.43.1

**Sources:**
- [zjstatus](https://github.com/dj95/zjstatus)
- [zellij-sessionizer](https://github.com/laperlej/zellij-sessionizer)
- [awesome-zellij](https://github.com/zellij-org/awesome-zellij)
