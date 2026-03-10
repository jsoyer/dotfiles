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

### Bootstrap Scripts (`scripts/`)
- `bootstrap.sh` - Multiplatform bootstrap (macOS, Fedora, RPi/Debian)
- `bootstrap.ps1` - Windows bootstrap (Scoop + chezmoi)

### Platform Profiles
Configuration adapts based on:
- **macOS** (`darwin`): Full setup with Homebrew, pyenv
- **Fedora** (`linux` + `lookPath "dnf"`): DNF packages, Flatpak
- **Fedora Atomic** (`lookPath "rpm-ostree"`): Minimal bash, container-focused
- **Toolbox** (`env "TOOLBOX_PATH"`): Container environment, zsh-only
- **Raspberry Pi** (kernel detection): APT packages, Snazzy theme
- **Windows** (`eq .chezmoi.os "windows"`): Scoop packages, minimal config (git, tmux, bash)

### Key Directories
- `dot_config/` - XDG config files (nvim, starship, tmux, wezterm, aerospace, sketchybar, etc.)
- `dot_claude/` - Claude Code config (agents, skills, hooks, settings)
- `dot_config/opencode/` - OpenCode config (MCP servers mirror Claude)
- `dot_private/` - Brewfiles (`Brewfile_common`, `Brewfile_pro`, `Brewfile_personal`, `Brewfile_linux`, `Brewfile_rpi`)
- `dot_local/bin/` - Custom scripts (`breww`, `update-claude-agents`, `claude-init`)
- `dot_ssh/` - SSH config with 1Password integration (templated)

### AI Tools (`dot_claude/`)
- `agents/` - 165 specialized sub-agents (131 VoltAgent/awesome-claude-code-subagents + 22 msitarzewski/agency-agents + 9 custom + 3 cloud)
- `skills/` - 84 skills (from jeffallan/claude-skills + awesome-llm-apps)
- `hooks/` - `rtk-rewrite.sh` (token optimization), `claude-island-state.py` (state tracking)
- `private_settings.json.tmpl` - Permissions, hooks, MCP servers (15 configured)

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
- `cup` - chezmoi update + package updates (all platforms)
- `c` - chezmoi (shortcut)
- `apt` → `aptw` (Linux non-Fedora: tracks in Aptfile_*)
- `dnf`/`yum` → `dnfw` (Fedora desktop/server: tracks in Dnffile_*)
- `scoop` → `scoopw` (Windows: tracks in Scoopfile.json)

## Security Notes

- Secrets are managed via 1Password CLI (`op`) or environment variables -- never hardcoded
- Files with `private_` prefix get 0600 permissions
- SSH config is pulled from 1Password document (conditional on `op` being available)
- MCP server tokens use `${ENV_VAR}` references resolved at runtime
- `secrets.zsh` is excluded from chezmoi tracking via `.chezmoiignore.tmpl`

## Lua Diagnostics Note

The `vim` global warnings in Neovim Lua files (`dot_config/nvim/`) are expected - `vim` is a runtime global provided by Neovim, not defined in the files themselves.

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