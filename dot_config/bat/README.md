# bat Configuration

**Platform:** Cross-platform (macOS, Linux, Windows)
**Theme:** Catppuccin Mocha
**Purpose:** Syntax-highlighted cat replacement with Git integration

## Overview

bat is a cat alternative with syntax highlighting, Git integration, and line numbers. It's aliased as `cat` in shell config for seamless drop-in replacement. This config uses Catppuccin Mocha theme with italic text support.

## Key Files

- `config` — Main configuration file

## Configuration

```bash
--theme="Catppuccin Mocha"     # Color scheme
--italic-text=always            # Enable italic formatting
--pager="less -FR"              # Pager with mouse support
```

## Features

- **Syntax highlighting** for 100+ languages
- **Git integration** (shows modified/added/deleted lines)
- **Line numbers** (toggleable via config)
- **Mouse scrolling** support via less pager
- **Italic text** for better visual distinction
- **Catppuccin Mocha theme** consistent with system theming

## Customization

Uncomment or modify the `--style` flag for different output:
```bash
--style="numbers,changes,header"   # Line numbers, git changes, header
```

## Usage

```bash
bat file.js           # View file with syntax highlighting
cat file.js          # Alias works too (if aliased in shell)
bat --file-name=X    # View stdin with language detection
```

## Integration

- Aliased in shell config as `cat` for transparent replacement
- Works with pipe commands: `cat file | command`
- Part of command-line tools: bat, lazygit, atuin, btop, etc.
- Cross-platform configuration

## Related

- Shell aliases in `dot_zsh/` and `dot_bash/` (10-aliases)
- Complements other command-line tools
- Theme consistent across system: Catppuccin Mocha
