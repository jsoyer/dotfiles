# Git Configuration

**Platform:** Cross-platform (macOS, Linux, Windows)
**Purpose:** Git user identity and configuration

## Overview

This directory contains Git user configuration including name and email settings. Configuration is templated to support cross-platform deployment and custom user data from `chezmoi.toml`.

## Key Files

- `empty_config.tmpl` — Git user configuration template

## Configuration

The template generates Git user identity:

```ini
[user]
    name = Jerome Soyer (default)
    email = jeromesoyer@gmail.com (default)
```

## Template Variables

Uses chezmoi template variables (from `chezmoi.toml`):
- `.name` — User full name (defaults to "Jerome Soyer")
- `.email` — User email (defaults to "jeromesoyer@gmail.com")

## Integration

- Processed by chezmoi during `apply` operations
- Creates standard `~/.gitconfig` (user section only)
- Works across all platforms: macOS, Linux, Windows
- Other Git config can be added as needed

## Customization

To customize for different users, update `chezmoi.toml`:
```toml
[data]
name = "Your Name"
email = "your.email@example.com"
```

Then run:
```bash
chezmoi apply ~/.gitconfig
```

## Related

- Part of Git workflow alongside lazygit, GitHub CLI
- Used by shell aliases: `cu` (chezmoi update), `ca` (chezmoi apply)
- Works with commit signing and SSH config in `dot_ssh/`
- Complements lazygit configuration in `lazygit/`
