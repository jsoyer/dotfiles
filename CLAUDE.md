# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Chezmoi-managed dotfiles for cross-platform configuration (macOS, Fedora, Arch, Ubuntu, RPi, Windows). Theme: **Catppuccin Mocha** (Snazzy on Linux/RPi).

## Key Commands

```bash
chezmoi apply                     # Apply changes to home directory
chezmoi diff                      # Preview what would be applied
chezmoi update                    # Update from git and apply
chezmoi re-add ~/.config/tool/x   # Re-add file to the source tree
```

Note: broad `chezmoi.toml` Git automation is opt-in via `CHEZMOI_AUTO_GIT=1`; package wrappers commit their owned manifests explicitly.

Linux system-level scripts (packages, repos, Tailscale, 1Password, Linuxbrew, updates) are gated by `.chezmoitemplates/can-sudo`: when the user cannot use sudo they render empty (so run_once/run_onchange stay pending) and `run_before_00-sudo-preflight` explains the fix. `CHEZMOI_ASSUME_SUDO=1` forces the gate for sudo granted by an explicit sudoers entry.

Container engine: `install-docker` (Docker Engine on Debian/Ubuntu/RPi/Arch, Podman on the Fedora family, Colima on macOS, Docker Desktop via winget on Windows), run by chezmoi only when the per-machine `install_docker` data flag is true.

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
- `dot_claude/` — Vendored Claude Workflow System (vinicius91carvalho/.claude@e1b64fc) with commands, rules, hooks, workflows
- `dot_aictx/` — AI resource cache (skills, agents, commands, rules, hooks, plugins) deployed to `~/.aictx/`, symlinked to CLI dirs by `aictx`
- `dot_private/` — Package manifests (Brewfile, Aptfile, Dnffile, Pacfile)
- `dot_local/bin/` — Custom scripts (breww, cm* commands, chezmoi-autoupdate)
- `tools/aictx/` — aictx/cctx: per-project context manager (Rust)
- `dot_local/share/fleet/` — `fleet` tailnet updater: `lib/*.py` (orchestrator, inventory, API clients), `agent/` (`fleet-agent.sh`, `fleet-agent.ps1`, `fleet-bootstrap.ps1`), `fleet.yml` (inventory); wrapper `dot_local/bin/executable_fleet`. Guide: `docs/FLEET.md`. Tests: `uvx pytest scripts/test_fleet_*.py` (Python 3.9-compatible, stdlib only). Sudoers/ACL changes need the user's review before merge: merging to `main` rolls out via chezmoi-autoupdate.

### AI Tools (`dot_claude/`)
`dot_claude/` now tracks the upstream [Claude Workflow System](https://github.com/vinicius91carvalho/.claude) (commit `e1b64fcb`) to take advantage of its aggressive token-saving defaults, enforcement hooks, and ready-made skills/agents. Key pieces to know:
- `CLAUDE.md`, `workflow/`, and `docs/` document the Compound/Context engineering process this workflow enforces.
- `settings.json` centralizes permissions and hook wiring (PostToolUse/Stop/PreToolUse/UserPromptSubmit/etc.).
- `hooks/` implements deterministic gates (quality, invariants, cleanup) that reference scripts in `hooks/lib/` and `workflow/`.
- Skills and agents are sourced from `~/.aictx/` (deployed by chezmoi from `dot_aictx/`). `aictx apply` and `aictx reset` manage symlinks to each CLI.
- `aictx` keeps per-project overrides aligned by re-linking `~/.claude` agents/skills on every directory change (`aictx apply --auto`).

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
- **Self-Improvement**: Update `docs/session-learnings.md` after corrections.
- **Autonomous**: Fix bugs without hand-holding. Go fix failing CI.

<!-- rtk-instructions v2 -->
# RTK (Rust Token Killer)

Prefix verbose shell commands (including inside `&&` chains) with `rtk` when available — unsupported commands pass through unchanged. Most relevant here:

- **Git / GitHub**: `rtk git status|log|diff|show|add|commit|push|pull`, `rtk gh pr|run|issue`
- **Rust (`tools/aictx`)**: `rtk cargo check|clippy|test|build`
- **Tests / Search**: `rtk test <cmd>`, `rtk ls`, `rtk grep`, `rtk find`, `rtk err <cmd>`
- **Debug**: `rtk proxy <cmd>` (raw unfiltered output), `rtk gain` (savings stats)
<!-- /rtk-instructions -->

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **Surface remaining work** - Call out anything needing follow-up in the handoff
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   git push
   git status  # MUST show "up to date with origin"
   ```
4. **Clean up** - Clear stashes, prune remote branches
5. **Verify** - All changes committed AND pushed
6. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
