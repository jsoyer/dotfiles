# Zed Editor Configuration

Modern code editor settings with AI assistants, LaTeX support, and Discord presence.

## Files

- `private_settings.json.tmpl` — Editor configuration

## Details

- **Tool**: Zed Editor
- **Platform**: macOS, Linux
- **Purpose**: Code editing with AI and LaTeX support
- **Theme**: Catppuccin Mocha

## Configuration

### AI Assistants

- **Qwen Code** — Qwen integration
- **OpenCode** — OpenCode agent registry
- **Mistral Vibe** — Mistral integration
- **GitHub Copilot** — Code predictions (eager mode)

### LSP Servers

- **TeXpresso** — LaTeX live preview and building
- **Texlab** — LaTeX language server
- **Discord Presence** — Rich presence integration

### UI

- **Theme**: Catppuccin Mocha (dark) + One Light (light)
- **Font**: FiraCode Nerd Font
- **UI Size**: 16pt, Buffer: 11pt

### Features

- LaTeX editing with live preview (TeXpresso)
- Discord presence showing current file/workspace
- Idle detection (5-minute timeout)
- Git integration in presence

## Usage

```bash
zed file.rs             # Open file
zed .                   # Open workspace
```

## Dependencies

- Zed editor
- Language servers (texlab, texpresso optional)
- Discord (for presence integration)

## Notes

- LaTeX root: `~/Documents/LaTeX`
- Idle state shows "Idling" after 5 minutes
- Per-language Discord overrides configured (Rust example)
