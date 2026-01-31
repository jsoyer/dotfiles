# Starship Prompt Configuration

Starship is a fast, customizable, and cross-shell prompt. This configuration includes platform-specific theming for both macOS and Raspberry Pi/Linux systems.

## Overview

- **Prompt**: Starship
- **macOS Theme**: Catppuccin Mocha
- **RPi/Linux Theme**: Gruvbox Dark
- **Shells**: Zsh, Fish, Nushell, Bash
- **Location**: `~/.config/starship/`

## File Structure

```
~/.config/starship/
├── starship.toml         # Main config (macOS - Catppuccin Mocha)
├── starship-rpi.toml     # RPi/Linux config (Gruvbox Dark)
├── starship-nushell.toml # Nushell-specific config
└── README.md             # This file
```

## Platform Detection

The correct configuration is automatically selected based on platform detection in `~/.zsh/00-env.zsh`:

| Platform | Config File | Theme | Prompt Style |
|----------|-------------|-------|--------------|
| macOS | `starship.toml` | Catppuccin Mocha | `~/path ➜` |
| RPi/Linux | `starship-rpi.toml` | Gruvbox Dark | `🍓 hostname:~/path ❯` |

### How It Works

The master logic lives in `~/.zsh/00-env.zsh`. It detects the machine's profile and exports two key environment variables:
1.  `STARSHIP_CONFIG`: Points to the correct `.toml` file to use (e.g., `starship.toml` for macOS, `starship-rpi.toml` for Linux).
2.  `STARSHIP_ICON`: Sets the main icon character for the prompt (``, ``, `🍓`, etc.).

This icon is then displayed by the `[env_var.STARSHIP_ICON]` section in `starship.toml`.

## Configuration Comparison

### macOS (Catppuccin Mocha)

```
~/projects ➜ git:(main) ✚
```

Features:
- Minimalist left prompt with directory
- Git info and language versions on right
- Purple/pink color scheme
- Full module set (AWS, K8s, etc.)

### RPi/Linux (Gruvbox Dark)

```
🍓 rpi-nas:~/projects main ❯
```

Features:
- Raspberry icon prefix
- Hostname always visible
- Git branch inline
- Yellow/orange color scheme
- Lightweight module set

## Color Palettes

### Catppuccin Mocha (macOS)

| Color      | Hex       | Usage                |
|------------|-----------|----------------------|
| Blue       | `#89b4fa` | Directories          |
| Green      | `#a6e3a1` | Success              |
| Yellow     | `#f9e2af` | Warnings             |
| Red        | `#f38ba8` | Errors               |
| Mauve      | `#cba6f7` | Git branch           |
| Pink       | `#f5c2e7` | Special indicators   |

### Gruvbox Dark (RPi/Linux)

| Color      | Hex       | Usage                |
|------------|-----------|----------------------|
| Blue       | `#458588` | Directories          |
| Green      | `#98971a` | Success              |
| Yellow     | `#d79921` | Hostname, warnings   |
| Red        | `#cc241d` | Errors, RPi icon     |
| Purple     | `#b16286` | Git branch           |
| Orange     | `#d65d0e` | Special indicators   |

## Modules Enabled

### Both Platforms

- `directory` - Current working directory
- `git_branch` - Current git branch
- `git_status` - Repository status
- `character` - Prompt character (changes on error)
- `cmd_duration` - Command execution time
- `python` - Python version
- `nodejs` - Node.js version
- `docker_context` - Docker context

### macOS Only

- `aws` - AWS profile and region
- `kubernetes` - K8s context and namespace
- `golang` - Go version
- `rust` - Rust version

### RPi/Linux Only

- `hostname` - Always shows hostname (useful for SSH)

## Shell Integration

### Zsh (both platforms)

Starship is loaded in `~/.zshrc`:
```zsh
eval "$(starship init zsh)"
```

The correct config is set via `STARSHIP_CONFIG` environment variable.

### Fish

```fish
starship init fish | source
```

### Nushell

Uses `starship-nushell.toml`:
```nushell
$env.STARSHIP_CONFIG = "~/.config/starship/starship-nushell.toml"
starship init nu | save -f ~/.cache/starship/init.nu
source ~/.cache/starship/init.nu
```

### Bash

```bash
eval "$(starship init bash)"
```

## Customization Examples

### Change RPi Icon

Edit `starship-rpi.toml`:
```toml
# Current
format = """[🍓](bold red) $hostname$directory..."""

# Alternative icons
format = """[🐧](bold yellow) $hostname$directory..."""  # Linux penguin
format = """[💻](bold blue) $hostname$directory..."""    # Computer
format = """[🏠](bold green) $hostname$directory..."""   # Home server
```

### Add Module to RPi Config

```toml
# Add Docker context
[docker_context]
disabled = false
format = "via [🐋 $context](bold blue) "
```

### Change Hostname Color

```toml
[hostname]
format = "[$hostname](bold cyan):"  # Change from yellow to cyan
```

## Troubleshooting

### Wrong Theme Loading

Check which config is being used:
```bash
echo $STARSHIP_CONFIG
```

Verify platform detection:
```bash
echo "IS_RPI: $IS_RPI"
echo "PLATFORM: $PLATFORM"
```

### Icons Not Displaying

Install a Nerd Font:
```bash
# macOS
brew install --cask font-jetbrains-mono-nerd-font

# Linux/RPi
# Nerd fonts are installed by the install-rpi.sh script
```

### Prompt Slow on RPi

Disable expensive modules:
```toml
[git_status]
disabled = true  # Can be slow on large repos
```

## Quick Reference

### Useful Commands

```bash
starship config          # Edit current config
starship print-config    # View full resolved config
starship explain         # Explain current prompt segments
starship timings         # Show module load times
```

### Test Different Config

```bash
# Temporarily use RPi config on macOS
STARSHIP_CONFIG=~/.config/starship/starship-rpi.toml zsh
```

## Resources

- **Starship Documentation**: https://starship.rs/
- **Catppuccin Starship**: https://github.com/catppuccin/starship
- **Gruvbox Colors**: https://github.com/morhetz/gruvbox

---

**Last Updated**: 2025-01-17
**Themes**: Catppuccin Mocha (macOS) / Gruvbox Dark (RPi)
