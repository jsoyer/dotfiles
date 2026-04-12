@RTK.md

# Environment

- **OS**: macOS (darwin), Apple Silicon
- **Shell**: zsh with Oh-My-Zsh + Powerlevel10k
- **Terminal**: WezTerm — Catppuccin Mocha theme
- **Editor**: Neovim
- **Window manager**: Aerospace (tiling) + Sketchybar (status bar)
- **Dotfiles**: managed by chezmoi (`~/.local/share/chezmoi`)
- **Package manager**: Homebrew

# Languages

TypeScript, JavaScript, Python, Rust, Go, Shell/Bash/Zsh, Lua (Neovim config)

# Code Style

- No trailing whitespace, no commented-out code left behind
- Prefer explicit over clever
- Shell: `#!/usr/bin/env bash`, `set -euo pipefail` for scripts, double-quote variables
- No emojis in code or comments unless asked

# Git & Chezmoi

- Conventional commits: `feat:`, `fix:`, `style:`, `refactor:`, `chore:`
- chezmoi has `autoCommit` + `autoPush` enabled — `chezmoi re-add <file>` auto-syncs
- Apply only specific paths to avoid 1Password timeouts: `chezmoi apply ~/.config/sketchybar`
- Chezmoi naming: `dot_` → dotfile, `executable_` → chmod+x, `private_` → 0600, `.tmpl` → Go template

# Key Aliases

- `ca` → `chezmoi apply -v`
- `cu` → `chezmoi update -v`
- `c` → `chezmoi`

# MCP Servers

- **Notion**, **Asana**, **HuggingFace** — available via claude.ai
- **context7** — up-to-date library documentation (use with `use context7`)
- **fetch** — direct URL fetching
- **github** — GitHub API (requires `GITHUB_TOKEN`)
