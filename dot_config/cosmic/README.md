# COSMIC DE Configuration

Desktop Environment configuration for COSMIC (System76's Rust-based DE).

## Directories

- `com.system76.CosmicComp/` — Compositor settings
- `com.system76.CosmicPanel.Panel/` — Top panel configuration
- `com.system76.CosmicPanel.Dock/` — Dock settings
- `com.system76.CosmicTerm/` — Terminal emulator config
- `com.system76.CosmicTheme.Dark/` — Dark theme settings
- `com.system76.CosmicTheme.Dark.Builder/` — Theme builder
- `com.system76.CosmicTk/` — Toolkit styling

## Details

- **Tool**: COSMIC Desktop Environment
- **Platform**: Fedora (Linux)
- **Purpose**: DE settings for COSMIC (Pop!_OS/Fedora Atomic)
- **Theme**: Dark theme (Catppuccin Mocha compatible)

## Configuration Format

Uses gsettings (GSettings) with individual files per setting:
- `/border_radius`, `/layer`, `/size`, `/background` — Dconf values

## Notes

- Primary DE for Fedora Atomic systems
- Replaces GNOME on Fedora Atomic installations
- Settings auto-applied via COSMIC itself
- No manual editing needed (use COSMIC Settings GUI)

## Dependencies

- cosmic-desktop
- cosmic-shell
- cosmic-comp
