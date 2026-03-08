# Fish Shell Configuration

## Overview

- **Shell**: Fish Shell
- **Theme**: Catppuccin Mocha
- **Prompt**: Tide (via Fisher)
- **Location**: `~/.config/fish/`

## File Structure

```
~/.config/fish/
├── config.fish           # Main config (env, aliases, integrations)
├── conf.d/               # Auto-loaded config snippets (Tide, FZF, NVM, gitnow)
├── functions/             # Custom + plugin functions
├── completions/           # Custom completions (Fisher, FZF, NVM, Tide)
├── themes/                # Catppuccin Mocha theme
├── fish_plugins           # Fisher plugin list
└── fish_variables         # Universal variables (managed by fish)
```

## Integrations

Initialized in `config.fish`:
- **Zoxide**: smart `cd` replacement
- **Atuin**: shell history with sync
- **Direnv**: per-directory environment
- **TheFuck**: command correction (lazy-loaded)
- **OrbStack**: Docker/K8s alternative (macOS)
- **Pyenv/Jenv/Rbenv/NVM**: language version managers

## Key Aliases

Same aliases as zsh/bash/nushell — see `config.fish` for the full list.
Categories: git, docker, kubernetes, chezmoi, homebrew, tmux, lazygit,
python (uv/poetry), search (rg/fd), security, jujutsu, Claude Code, fdupes.

## FZF Functions

- `cx <dir>` — cd + list
- `fcd` — fuzzy directory navigation
- `f` — copy file path to clipboard via FZF
- `fv` — open file in nvim via FZF
- `ff` — Aerospace window picker

## Fisher Plugins

Managed via `fish_plugins`. Install/update: `fisher update`
