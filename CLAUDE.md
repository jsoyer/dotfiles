# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a chezmoi-managed dotfiles repository for cross-platform configuration (macOS, Fedora, Raspberry Pi, Windows). All configurations use **Catppuccin Mocha** theme (Snazzy on Linux/RPi).

## Key Commands

```bash
# Apply changes to home directory
chezmoi apply

# Preview what would be applied
chezmoi diff

# Update from git and apply
chezmoi update

# Add/re-add a file to chezmoi
chezmoi add ~/.config/tool/config
chezmoi re-add ~/.config/tool/config  # Auto-commits + auto-pushes

# Validate configuration
chezmoi doctor
chezmoi verify
```

Note: `chezmoi.toml` has `autoAdd`, `autoCommit`, and `autoPush` enabled - changes are automatically synced to GitHub.

## Chezmoi File Naming Conventions

- `dot_` prefix → creates dotfile (e.g., `dot_zshrc` → `~/.zshrc`)
- `.tmpl` suffix → processed as Go template
- `executable_` prefix → file gets executable permissions
- `private_` prefix → restricted permissions (0600)
- `run_once_*.tmpl` → scripts that run once on first apply
- `run_onchange_*.tmpl` → scripts that run when file content changes

## Templating Patterns

Templates use Go text/template with chezmoi data. Common patterns:

```go
{{- if eq .chezmoi.os "darwin" }}
# macOS-specific
{{- else if eq .chezmoi.os "linux" }}
# Linux-specific
{{- end }}

{{- if lookPath "op" }}
# 1Password CLI available
{{- end }}

{{- if env "TOOLBOX_PATH" }}
# Running in Fedora Toolbox container
{{- end }}
```

Available data in templates: `.chezmoi.os`, `.chezmoi.arch`, `.chezmoi.hostname`, `.chezmoi.homeDir`, plus custom data from `chezmoi.toml` (`.github_user`, `.name`, `.email`, `.work_email`, `.xdgDataDir`, `.xdgConfigDir`, `.xdgCacheDir`, `.xdgStateDir`).

## Architecture

### Shell Configuration (`dot_zsh/`, `dot_bash/`)
Numbered files loaded in order:
- `00-env` - Platform detection, environment variables
- `01-path` - PATH management with lazy loading
- `02-completions` - Completion system (zsh only)
- `10-aliases` - Command aliases (eza, bat, nvim, etc.)
- `20-functions` - Custom shell functions
- `30-keybindings` - Vim-style keybindings
- `99-integrations` - FZF, Atuin, autosuggestions, syntax highlighting

### External Dependencies (`.chezmoiexternal.toml`)
Git repos auto-refreshed weekly:
- Oh-My-Zsh + Powerlevel10k theme
- zsh-autosuggestions, zsh-syntax-highlighting
- Tmux Plugin Manager (TPM)

### Skills Sync (`dot_agents/`, `.chezmoiscripts/03-configure/`)
- Source of truth: `dot_agents/skills/` (654 skills)
- `run_onchange_sync-skill-symlinks.sh` creates symlinks in `~/.claude/skills/`, `~/.qwen/skills/`, `~/.vibe/skills/`
- Triggered by changes to `dot_agents/dot_skill-lock.json`
- OpenCode tools (`ocx`, `oh-my-openagent`) install only on desktop profiles when `install_ocx` is true (default false, `promptBoolOnce`)
- Claude Code plugins (`octo@nyldn-plugins`, LSP plugins) install only on desktop profiles via `run_once_install-claude-plugins.sh`

### Bootstrap Scripts (`scripts/`)
- `bootstrap.sh` - Multiplatform bootstrap (macOS, Fedora, RPi/Debian)
- `bootstrap.ps1` - Windows bootstrap (Scoop + chezmoi)

### Platform Profiles
Configuration adapts based on:
- **macOS** (`darwin`): Full setup with Homebrew, pyenv
- **Fedora** (`linux` + `lookPath "dnf"`): DNF packages, hybrid native/Flatpak for GUI apps
- **Fedora Atomic** (`lookPath "rpm-ostree"`): Minimal bash, container-focused, full Flatpak
- **Toolbox** (`env "TOOLBOX_PATH"`): Container environment, zsh-only
- **Arch Linux** (`osRelease.id "arch"`): Pacman + AUR (yay), GUI apps via pacman/AUR when display server detected
- **OmArchy** (`osRelease.id "omarchy"`): Arch-based desktop, same packages as arch-desktop, promptBoolOnce overrides for shell/nvim/tmux/git/wm
- **Ubuntu** (`osRelease.id "ubuntu"`): APT packages, hybrid native/Flatpak for GUI apps
- **Raspberry Pi** (kernel detection): APT packages, Pi-Apps for GUI apps when display server detected, Snazzy theme
- **Windows** (`eq .chezmoi.os "windows"`): Scoop packages, minimal config (git, tmux, bash)

GUI apps only install when a display server is detected (`_has_gui()` check). CLI AI tools (Claude Code, Copilot CLI, Codex CLI) install on all profiles via AUR (Arch) or native scripts (others), updated via `update-ai` alias.

### Key Directories
- `dot_config/` - XDG config files (nvim, starship, tmux, wezterm, aerospace, sketchybar, etc.) (desktop profiles only)
- `dot_claude/` - Claude Code config (agents, commands, rules, hooks, settings)
- `dot_agents/` - Shared AI agent skills (654 skills, source of truth for `.claude/`, `.qwen/`, `.vibe/` symlinks)
- `dot_config/opencode/` - OpenCode config (MCP servers mirror Claude)
- `dot_private/` - Brewfiles (`Brewfile_macos`, `Brewfile_brew_only`, `Brewfile_pro`, `Brewfile_personal`, `Brewfile_rpi`), Aptfile_*, Dnffile_*, Pacfile_*
- `dot_local/bin/` - Custom scripts (`breww`, `update-claude-agents`, `claude-init`)
- `dot_ssh/` - SSH config directory

### AI Tools (`dot_claude/`)
- `agents/` - 192 specialized sub-agents (132 VoltAgent/awesome-claude-code-subagents + 22 msitarzewski/agency-agents + 27 ECC/everything-claude-code + 11 custom)
- `commands/` - 60 slash commands (from ECC: `/plan`, `/verify`, `/code-review`, `/tdd`, `/build-fix`, language builds/reviews, etc.)
- `rules/` - 64 rule files (common best practices + 12 language-specific: TypeScript, Python, Rust, Go, Swift, C++, C#, Java, Kotlin, Perl, PHP)
- Skills are symlinked from `~/.agents/skills/` (654 skills) via `run_onchange_sync-skill-symlinks.sh`
- `hooks/` - `rtk-rewrite.sh` (token optimization), `claude-island-state.py` (state tracking), `console-log-check.sh`, `config-protection.sh`, `desktop-notify.sh`, `quality-gate.sh`
- `private_settings.json.tmpl` - Permissions, hooks, MCP servers (26 configured)
- Plugins: `octo@nyldn-plugins` (Claude Octopus multi-AI orchestrator), LSP plugins (lua, pyright, swift, typescript, gopls)

### macOS Desktop (`dot_config/aerospace/`, `dot_config/sketchybar/`)
- Aerospace tiling WM config at `~/.config/aerospace/aerospace.toml`
- Sketchybar status bar with Catppuccin Mocha pill-style items
- Workspace icons updated via polling script

### Mail (`dot_config/isync/`, `dot_config/msmtp/`, `dot_config/neomutt/`)
- mbsync (isync) for IMAP sync, msmtp for SMTP
- neomutt as mail client
- Passwords via 1Password CLI (`op read`)

### Shell Aliases
- `ca` - chezmoi apply -v
- `cu` - chezmoi update -v
- `cup` - chezmoi update + sysup + docker compose update (all platforms)
- `sysup` - update all system packages + flatpak + brew + AI tools
- `update-ai` - update Claude Code, Copilot CLI, Codex CLI
- `sshpw` - SSH with password-only authentication
- `c` - chezmoi (shortcut)
- `apt` → `aptw` (Linux non-Fedora: tracks in Aptfile_*)
- `dnf`/`yum` → `dnfw` (Fedora desktop/server: tracks in Dnffile_*)
- `pacman` → `pacmanw` (Arch: tracks in Pacfile_*)
- `yay` → `yayw` (Arch AUR: tracks in Pacfile_aur_*)
- `scoop` → `scoopw` (Windows: tracks in Scoopfile.json)

### Auto-Update System (`cm*` commands)
Auto-update monitoring and fleet management via background daemon:
- `cmstatus` - Show last auto-update status (JSON)
- `cmlog` - View last auto-update execution log
- `cmdiff` - Show pending changes with syntax highlighting
- `cmchangelog` - Show recent dotfile updates
- `cmwho` - Show who made last push
- `cmhealth` - Comprehensive system health check
- `cmbench` - Benchmark shell startup performance
- `cmaudit` - Audit missing command dependencies
- `cmrollback` - Interactive rollback to previous commit
- `cmreload` - Reload modified configs in active shell
- `cminventory` - Fleet status (if heartbeats configured)

## Auto-Update System

Autonomous background daemon that keeps configurations current with periodic updates, auto-healing, notifications, and fleet monitoring.

### Timers & Activation

| Platform | Mechanism | Interval | Activation | Machines |
|----------|-----------|----------|------------|----------|
| **macOS** | launchd agent (`com.jsoyer.chezmoi-autoupdate`) | 1 hour | `run_once_enable-chezmoi-autoupdate.sh` | `mac-personal` only (not `mac-pro`) |
| **Linux** | systemd user timer + service | 1 hour | `run_once_enable-chezmoi-autoupdate.sh` | Desktop, server, RPi, Fedora Atomic, Toolbox |
| **Windows** | Task Scheduler | 1x daily | `run_once_enable-chezmoi-autoupdate.ps1` | All Windows profiles |

### Auto-Healing

When `chezmoi-autoupdate` runs, it auto-heals:
- **Git conflicts**: `rebase --abort` + `reset --hard origin/main`
- **Stale caches**: Purge old package manager caches
- **SSH permissions**: Fix 700 (dirs) / 600 (files) automatically
- **Brew lock stale**: Remove locks older than 30 minutes
- **Deprecated brew**: Auto-uninstall blacklisted packages (see `Brewfile_blacklist`)
- **Missing TPM plugins**: Run `~/.tmux/plugins/tpm/bin/install_plugins`

### Notifications

Errors (only, no noise on success):
- **Desktop**: osascript (macOS) / notify-send (Linux)
- **ntfy.sh**: Silent heartbeat POST (fleet tracking)
- **Telegram**: API sendMessage (if token in `secrets.zsh`)
- **Discord**: Webhook POST (if webhook URL in `secrets.zsh`)

Tokens stored in environment variables, never in repo.

### Post-Apply Validation & Auto-Rollback

After `chezmoi apply`:
1. Test `zsh -i -c 'exit 0'` — shell starts?
2. Test `starship --version` — prompt works?
3. Test `tmux -c 'exit'` — tmux launches?

If any test fails → `git reset --hard HEAD~1 && chezmoi apply` (automatic rollback with notification).

### Status Tracking

Save to `~/.cache/chezmoi-autoupdate/`:
- `status.json` — Last run: timestamp, duration, exit code, result
- `last-run.log` — Full output including errors
- `last-seen-commit` — Baseline for `cmchangelog`

Queryable via `cmstatus` and `cmlog` aliases.

### Heartbeat & Fleet Monitoring

Silent POST to ntfy.sh after successful update:
```
POST https://ntfy.sh/chezmoi-fleet-<org>
hostname=macbook-pro&timestamp=2026-03-28T10:30:00Z
```

Enables dashboard/deadman-switch detection (machine offline > 7 days).

### Starship Integration

Custom module in `starship-desktop.toml.tmpl` + `starship-ssh.toml.tmpl`:
- **✗ (red)** if last auto-update failed
- **silent** if healthy

Shows visual status at command prompt.

### Configuration

**Enable/disable**: Pass `chezmoi_autoupdate_enabled` during init or edit `chezmoi.toml`
**Timers**: View status with `systemctl --user status chezmoi-autoupdate.timer` (Linux) or `launchctl list com.jsoyer.chezmoi-autoupdate` (macOS)
**Logs**: `journalctl --user -u chezmoi-autoupdate -f` (Linux) or Console.app (macOS)

## Security Notes

- Secrets are managed via 1Password CLI (`op`) or environment variables -- never hardcoded
- Files with `private_` prefix get 0600 permissions
- SSH config is generated via `run_onchange_` script, skips gracefully when 1Password is unavailable
- MCP server tokens use `${ENV_VAR}` references resolved at runtime
- `secrets.zsh` is excluded from chezmoi tracking via `.chezmoiignore.tmpl`
- Auto-update notifications use environment variables for API keys, no secrets in code

## Lua Diagnostics Note

The `vim` global warnings in Neovim Lua files (`dot_config/nvim/`) are expected - `vim` is a runtime global provided by Neovim, not defined in the files themselves.

## Workflow

### 1. Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately -- don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes -- don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests -- then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.

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