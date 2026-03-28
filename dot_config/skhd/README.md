# skhd Configuration

Hotkey daemon for macOS. Launches applications and runs scripts via keyboard shortcuts.

## Files

- `skhdrc` — Hotkey bindings
- `applescripts/` — AppleScript utilities (date, notifications)

## Details

- **Tool**: skhd (simple hotkey daemon)
- **Platform**: macOS
- **Purpose**: Application launcher and script triggers
- **Theme**: N/A (keybinding utility)

## Hotkeys

| Binding | Action |
|---------|--------|
| `alt-s` | Open Safari |
| `alt-t` | Open Telegram |
| `alt-o` | Open Obsidian |
| `alt-n` | Open Notion (left-alt only) |
| `alt-m` | Open Min browser (right-alt) |
| `alt-q` | Open QuickTime |
| `alt-f` | Open Final Cut Pro |
| `alt-g` | Open Ghostty |
| `alt-d` | Show date popup |
| `ralt-n` | Close notifications |

## Usage

```bash
# skhd runs as background service
brew services start skhd

# Reload config
skhd -r
```

## Dependencies

- None (built-in macOS commands)
- Works with any terminal/application

## Notes

- Complements Aerospace (tiling WM) for window management
- Separate from Aerospace keybindings
- Uses `alt` and `ralt` (left/right alt) for flexibility
