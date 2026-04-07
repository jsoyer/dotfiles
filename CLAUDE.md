# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Chezmoi-managed dotfiles for cross-platform configuration (macOS, Fedora, Arch, Ubuntu, RPi, Windows). Theme: **Catppuccin Mocha** (Snazzy on Linux/RPi).

## Key Commands

```bash
chezmoi apply                     # Apply changes to home directory
chezmoi diff                      # Preview what would be applied
chezmoi update                    # Update from git and apply
chezmoi re-add ~/.config/tool/x   # Re-add file (auto-commits + auto-pushes)
```

Note: `chezmoi.toml` has `autoAdd`, `autoCommit`, and `autoPush` enabled.

## Chezmoi File Naming

- `dot_` → dotfile (`dot_zshrc` → `~/.zshrc`)
- `.tmpl` → Go template
- `executable_` → chmod+x
- `private_` → 0600 permissions
- `run_once_*.tmpl` → runs once on first apply
- `run_onchange_*.tmpl` → runs when content changes

## Templating Patterns

```go
{{- if eq .chezmoi.os "darwin" }}    # macOS-specific
{{- if lookPath "op" }}              # 1Password CLI available
{{- if env "TOOLBOX_PATH" }}         # Fedora Toolbox container
```

Available data: `.chezmoi.os`, `.chezmoi.arch`, `.chezmoi.hostname`, `.chezmoi.homeDir`, plus `.github_user`, `.name`, `.email`, `.work_email`, `.xdgDataDir`, `.xdgConfigDir`, `.xdgCacheDir`, `.xdgStateDir`.

## Architecture

### Shell Configuration (`dot_zsh/`, `dot_bash/`)
Numbered files loaded in order: `00-env`, `01-path`, `02-completions` (zsh), `10-aliases`, `20-functions`, `30-keybindings` (zsh), `99-integrations`.

### Platform Profiles
macOS, Fedora, Fedora Atomic, Toolbox, Arch, OmArchy, Ubuntu, RPi, Windows. GUI apps only install when display server detected (`_has_gui()`).

### Key Directories
- `dot_config/` — XDG configs (nvim, starship, tmux, wezterm, aerospace, sketchybar)
- `dot_claude/` — Claude Code config (agents, commands, rules, hooks, settings)
- `dot_agents/` — Shared AI skills (654, source of truth for .claude/.qwen/.vibe symlinks)
- `dot_private/` — Package manifests (Brewfile, Aptfile, Dnffile, Pacfile)
- `dot_local/bin/` — Custom scripts (breww, cm* commands, chezmoi-autoupdate)
- `tools/claude-context/` — cctx: per-project context manager (Rust)

### AI Tools (`dot_claude/`)
- 192 agents, 60 commands, 5 common rules + 12 language-specific rule sets
- 6 hooks (rtk-rewrite, claude-island-state, config-protection, console-log-check, desktop-notify, quality-gate)
- 19 MCP servers, statusline with usage bars

### Auto-Update System
Background daemon (`chezmoi-autoupdate`) runs hourly via launchd (macOS) / systemd (Linux). Auto-heals git conflicts, stale caches, SSH permissions. Notifications via ntfy/Telegram/Discord on errors only. `cm*` commands for monitoring.

### Secret Management
`secrets.zsh` auto-generated from 1Password (`op://Private/Shell Secrets`). Secrets single-quoted, file created with umask 077. Fallback: preserves existing file if 1Password unavailable.

## Security Notes

- Secrets via 1Password CLI or env vars, never hardcoded
- `private_` prefix → 0600 permissions
- MCP tokens use `${ENV_VAR}` resolved at runtime
- `secrets.zsh` excluded from chezmoi tracking

## Lua Diagnostics Note

`vim` global warnings in `dot_config/nvim/` are expected — runtime global provided by Neovim.

## Workflow

1. **Plan First** — Enter plan mode for non-trivial tasks (3+ steps)
2. **Research & Reuse** — GitHub search + Context7 docs before writing new code
3. **TDD** — Write tests first, verify 80%+ coverage
4. **Review** — Use code-reviewer agent after writing code
5. **Verify** — Never mark complete without proving it works
6. **Simplicity** — Make every change as simple as possible

## Core Principles

- **Simplicity First**: Impact minimal code. No temporary fixes.
- **Self-Improvement**: Update `tasks/lessons.md` after corrections.
- **Autonomous**: Fix bugs without hand-holding. Go fix failing CI.
