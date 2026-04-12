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
- `dot_claude/` — Claude Code config (commands, rules, hooks, settings)
- `dot_skills/` — 648 AI skills (source of truth, symlinked to .claude/.qwen/.vibe/.codex/.kimi)
- `dot_agents/` — 192 AI agents (source of truth, symlinked to .claude/agents/)
- `dot_private/` — Package manifests (Brewfile, Aptfile, Dnffile, Pacfile)
- `dot_local/bin/` — Custom scripts (breww, cm* commands, chezmoi-autoupdate)
- `tools/claude-context/` — cctx: per-project context manager (Rust)

### AI Tools (`dot_claude/`)
- 192 agents, 60 commands, 5 common rules + 12 language-specific rule sets
- 6 hooks (rtk-rewrite, claude-island-state, config-protection, console-log-check, desktop-notify, quality-gate)
- 19 MCP servers, statusline with usage bars

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

<!-- rtk-instructions v2 -->
# RTK (Rust Token Killer) - Token-Optimized Commands

## Golden Rule

**Always prefix commands with `rtk`**. If RTK has a dedicated filter, it uses it. If not, it passes through unchanged. This means RTK is always safe to use.

**Important**: Even in command chains with `&&`, use `rtk`:
```bash
# ❌ Wrong
git add . && git commit -m "msg" && git push

# ✅ Correct
rtk git add . && rtk git commit -m "msg" && rtk git push
```

## RTK Commands by Workflow

### Build & Compile (80-90% savings)
```bash
rtk cargo build         # Cargo build output
rtk cargo check         # Cargo check output
rtk cargo clippy        # Clippy warnings grouped by file (80%)
rtk tsc                 # TypeScript errors grouped by file/code (83%)
rtk lint                # ESLint/Biome violations grouped (84%)
rtk prettier --check    # Files needing format only (70%)
rtk next build          # Next.js build with route metrics (87%)
```

### Test (90-99% savings)
```bash
rtk cargo test          # Cargo test failures only (90%)
rtk vitest run          # Vitest failures only (99.5%)
rtk playwright test     # Playwright failures only (94%)
rtk test <cmd>          # Generic test wrapper - failures only
```

### Git (59-80% savings)
```bash
rtk git status          # Compact status
rtk git log             # Compact log (works with all git flags)
rtk git diff            # Compact diff (80%)
rtk git show            # Compact show (80%)
rtk git add             # Ultra-compact confirmations (59%)
rtk git commit          # Ultra-compact confirmations (59%)
rtk git push            # Ultra-compact confirmations
rtk git pull            # Ultra-compact confirmations
rtk git branch          # Compact branch list
rtk git fetch           # Compact fetch
rtk git stash           # Compact stash
rtk git worktree        # Compact worktree
```

Note: Git passthrough works for ALL subcommands, even those not explicitly listed.

### GitHub (26-87% savings)
```bash
rtk gh pr view <num>    # Compact PR view (87%)
rtk gh pr checks        # Compact PR checks (79%)
rtk gh run list         # Compact workflow runs (82%)
rtk gh issue list       # Compact issue list (80%)
rtk gh api              # Compact API responses (26%)
```

### JavaScript/TypeScript Tooling (70-90% savings)
```bash
rtk pnpm list           # Compact dependency tree (70%)
rtk pnpm outdated       # Compact outdated packages (80%)
rtk pnpm install        # Compact install output (90%)
rtk npm run <script>    # Compact npm script output
rtk npx <cmd>           # Compact npx command output
rtk prisma              # Prisma without ASCII art (88%)
```

### Files & Search (60-75% savings)
```bash
rtk ls <path>           # Tree format, compact (65%)
rtk read <file>         # Code reading with filtering (60%)
rtk grep <pattern>      # Search grouped by file (75%)
rtk find <pattern>      # Find grouped by directory (70%)
```

### Analysis & Debug (70-90% savings)
```bash
rtk err <cmd>           # Filter errors only from any command
rtk log <file>          # Deduplicated logs with counts
rtk json <file>         # JSON structure without values
rtk deps                # Dependency overview
rtk env                 # Environment variables compact
rtk summary <cmd>       # Smart summary of command output
rtk diff                # Ultra-compact diffs
```

### Infrastructure (85% savings)
```bash
rtk docker ps           # Compact container list
rtk docker images       # Compact image list
rtk docker logs <c>     # Deduplicated logs
rtk kubectl get         # Compact resource list
rtk kubectl logs        # Deduplicated pod logs
```

### Network (65-70% savings)
```bash
rtk curl <url>          # Compact HTTP responses (70%)
rtk wget <url>          # Compact download output (65%)
```

### Meta Commands
```bash
rtk gain                # View token savings statistics
rtk gain --history      # View command history with savings
rtk discover            # Analyze Claude Code sessions for missed RTK usage
rtk proxy <cmd>         # Run command without filtering (for debugging)
rtk init                # Add RTK instructions to CLAUDE.md
rtk init --global       # Add RTK to ~/.claude/CLAUDE.md
```

## Token Savings Overview

| Category | Commands | Typical Savings |
|----------|----------|-----------------|
| Tests | vitest, playwright, cargo test | 90-99% |
| Build | next, tsc, lint, prettier | 70-87% |
| Git | status, log, diff, add, commit | 59-80% |
| GitHub | gh pr, gh run, gh issue | 26-87% |
| Package Managers | pnpm, npm, npx | 70-90% |
| Files | ls, read, grep, find | 60-75% |
| Infrastructure | docker, kubectl | 85% |
| Network | curl, wget | 65-70% |

Overall average: **60-90% token reduction** on common development operations.
<!-- /rtk-instructions -->

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->
