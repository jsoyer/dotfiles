# Utility Scripts

Custom scripts installed to `~/.local/bin/` for package management, configuration syncing, and AI agent updates.

## Package Manager Wrappers

These scripts intercept package manager commands, auto-update manifests in the chezmoi source, and commit changes. They transform imperative package commands into declarative tracked state.

| Script | Command | Manifest | Platforms |
|--------|---------|----------|-----------|
| `breww` | `brew install/remove foo` | `Brewfile_*` | macOS, Linux (Homebrew) |
| `aptw` | `apt install/remove foo` | `Aptfile_*` | Debian, Ubuntu, Raspberry Pi |
| `dnfw` | `dnf install/remove foo` | `Dnffile_*` | Fedora |
| `pacmanw` | `pacman -S/-R foo` | `Pacfile_*` | Arch Linux |
| `yayw` | `yay -S/-R foo` | `Pacfile_aur_*` | Arch Linux (AUR) |
| `ostreew` | `ostreew install/remove foo` | `Rpmfile_fedora_atomic` | Fedora Atomic |
| `scoopw` | `scoop install/uninstall foo` | `Scoopfile.json` | Windows |

### Wrapper Behavior

Each wrapper:
1. Intercepts package manager command (via shell alias)
2. Runs the actual package manager (e.g., `apt install`)
3. Updates the profile-specific manifest file
4. Commits and pushes to Git automatically (via chezmoi `autoCommit` + `autoPush`)
5. Other machines detect the manifest hash change and install missing packages

**Example workflow:**
```bash
brew install ripgrep       # Command
breww intercepts          # Wrapper runs
brew install ripgrep      # Actual install
Brewfile_personal updated # Add ripgrep
git commit + push         # Auto-sync to Git
other machines run:       # chezmoi apply detects change
  brew bundle install     # Install ripgrep on other machines
```

## AI Agent & Skill Tools

### update-claude-agents

**Purpose:** Pull latest Claude Code agents from upstream sources

**Sources:**
- VoltAgent/awesome-claude-code-subagents (132 agents)
- msitarzewski/agency-agents (22 agents)
- Additional custom agents

**Usage:**
```bash
update-claude-agents           # Update all agents from sources
update-claude-agents --dry-run # Preview changes without writing
```

**What it does:**
1. Fetches agent definitions from GitHub (VoltAgent + msitarzewski)
2. Organizes by category (core-development, language-specialists, infrastructure, etc.)
3. Saves to `~/.claude/agents/`
4. Syncs to chezmoi source at `~/.local/share/chezmoi/dot_claude/agents/`
5. Commits changes to chezmoi repo

### update-claude-skills

**Purpose:** Pull latest Claude Code skills from upstream sources

**Sources:**
- Jeffallan/claude-skills (90+ skills)
- Shubhamsaboo/awesome-llm-apps (15+ skills)
- Plus 646 additional skills in the dotfiles repo

**Usage:**
```bash
update-claude-skills           # Update all skills from sources
update-claude-skills --dry-run # Preview changes without writing
```

**What it does:**
1. Fetches skill definitions from GitHub repositories
2. Saves to `~/.claude/skills/`
3. Syncs to chezmoi source
4. Commits changes

### sync-mcp-servers

**Purpose:** Keep Claude Code and OpenCode MCP server configs in sync

**Usage:**
```bash
sync-mcp-servers           # Sync MCP config from Claude to OpenCode
sync-mcp-servers --dry-run # Preview changes
```

**What it does:**
1. Reads MCP server definitions from `~/.claude/settings.json`
2. Converts format from Claude to OpenCode
3. Writes to `~/.config/opencode/opencode.json`
4. Syncs to chezmoi source
5. Claude settings is the source of truth

## Configuration & Development

### claude-init

**Purpose:** Generate a `CLAUDE.md` file for the current project

**Usage:**
```bash
cd /path/to/project
claude-init
```

**What it does:**
1. Detects project tech stack (TypeScript, Rust, Go, Python, etc.)
2. Identifies frameworks (Next.js, React, Django, etc.)
3. Generates `CLAUDE.md` with:
   - Stack summary
   - Key dev commands (install, test, build, lint)
   - Relevant Claude Code guidelines
4. Prompts to overwrite if file already exists

**Example detection:**
- `package.json` + `pnpm-lock.yaml` → TypeScript/JavaScript (pnpm)
- `Cargo.toml` → Rust (cargo build/test/clippy)
- `go.mod` → Go (go build/test/golangci-lint)
- `pyproject.toml` → Python (uv sync/test/lint)

## Toolbox Helpers

### tbx-app

**Purpose:** Create a `.desktop` wrapper for a GUI app running in a toolbox container

**Usage:**
```bash
tbx-app <container> <app>
tbx-app fedora-43 firefox
tbx-app arch-rolling gimp
```

**What it does:**
1. Looks for `.desktop` file inside the container
2. Extracts Name, Icon, Exec, and Categories
3. Creates wrapper at `~/.local/share/applications/<app>-<container>.desktop`
4. Updates desktop database so app appears in application menu
5. Wrapper executes: `toolbox run --container <container> <app>`

**Result:** GUI apps in containers appear in your desktop app menu and launch seamlessly.

### tbx-export-apps

**Purpose:** Bulk export GUI apps from a toolbox container to your desktop

**Usage:**
```bash
tbx-export-apps fedora-43
tbx-export-apps arch-rolling
```

**What it does:**
1. Finds all `.desktop` files in the container's `/usr/share/applications/`
2. Creates individual app launchers for each
3. Updates desktop database
4. All apps now available in your application menu

## Auto-Update & Health Monitoring

Central auto-update system with notifications, auto-healing, and fleet monitoring.

### Core Auto-Update Script

**`chezmoi-autoupdate`** (Primary daemon)

Runs periodically (every 1 hour on Linux/macOS) via systemd timer or launchd. Performs:

1. **Auto-update**: `git pull --rebase` in chezmoi source, `chezmoi apply`
2. **Auto-heal**: Git conflict resolution, stale cache cleanup, SSH permissions fix, deprecated brew removal, TPM plugin sync
3. **Notifications**: Desktop (osascript/notify-send), ntfy.sh, Telegram, Discord (on error only)
4. **Post-apply validation**: Test zsh/bash startup, starship version, tmux launch
5. **Auto-rollback**: If validation fails, revert to previous commit
6. **Status tracking**: Save result JSON to `~/.cache/chezmoi-autoupdate/status.json`
7. **Heartbeat**: Silent POST to ntfy.sh with hostname + timestamp (fleet tracking)

**Usage:**
```bash
chezmoi-autoupdate             # Run once manually
chezmoi-autoupdate --dry-run   # Preview without applying
chezmoi-autoupdate --rollback  # Force rollback to previous commit
```

### Configuration Validation

**`chezmoi-validate`** (Pre-apply validation)

Run before applying changes to catch errors early:
```bash
chezmoi-validate               # Full validation suite
chezmoi-validate --strict      # Fail on warnings
```

### Fleet Dead-Man Switch

**`chezmoi-deadman`** — Alert if any machine hasn't updated in N days

Runs on a hub machine (e.g., a Raspberry Pi that is always on) via cron. It discovers fleet machines through Tailscale and SSHes into each to read their `status.json`. If a machine hasn't updated within the threshold (default 7 days) or is unreachable, it fires alerts via ntfy/Telegram/Discord.

**Cron example:**
```cron
0 9 * * * chezmoi-deadman
```

**Usage:**
```bash
chezmoi-deadman                    # Check all fleet machines
CHEZMOI_DEADMAN_DAYS=3 chezmoi-deadman  # Custom threshold
```

**Env vars:**
```
CHEZMOI_DEADMAN_DAYS   — stale threshold in days (default: 7)
CHEZMOI_FLEET_MACHINES — comma-separated fallback hostnames (no Tailscale)
CHEZMOI_SSH_USER       — SSH user for remote machines (default: current user)
CHEZMOI_SSH_KEY        — path to SSH key (default: ~/.ssh/id_ed25519)
CHEZMOI_SSH_TIMEOUT    — SSH connect timeout in seconds (default: 10)
CHEZMOI_NTFY_TOPIC     — ntfy topic for alerts
TELEGRAM_BOT_TOKEN     — Telegram bot token
TELEGRAM_CHAT_ID       — Telegram chat ID
DISCORD_WEBHOOK_URL    — Discord webhook URL
```

State is written to `~/.cache/chezmoi-autoupdate/deadman-state.json` and consumed by `chezmoi-dashboard`.

### Fleet Dashboard

**`chezmoi-dashboard`** — Generate a static HTML fleet status page

Collects `status.json` from all machines (local + Tailscale peers via SSH, or from a recent `deadman-state.json`) and renders a self-contained HTML page with Catppuccin Mocha styling.

**Output:** `~/.cache/chezmoi-autoupdate/dashboard.html` (path is printed to stdout)

**Usage:**
```bash
chezmoi-dashboard                  # Generate dashboard.html
chezmoi-dashboard --open           # Generate and open in browser
chezmoi-dashboard --local-only     # Only include this machine (no SSH)
chezmoi-dashboard --output /tmp/fleet.html  # Custom output path
```

The page auto-refreshes every 5 minutes. Fleet data sources are tried in order:
1. Recent `deadman-state.json` (< 30 min old) — zero additional SSH calls
2. Tailscale peer discovery + live SSH into each peer
3. `CHEZMOI_FLEET_MACHINES` env var fallback

### Health & Diagnostics

**`cmhealth`** — Complete system health check

Validates:
- Git repository clean (no uncommitted changes)
- Auto-update timer active and running
- Last update < 2 hours ago
- No deprecated brew packages
- No stale caches
- SSH permissions correct (700 dirs, 600 files)
- Required environment variables present (MCP server tokens)
- Nerd Fonts installed
- No config drift (`chezmoi verify`)
- Network connectivity (ping)
- Shell startup time < 1s
- Tmux/zsh/bash can launch

**Usage:**
```bash
cmhealth                       # Full check
cmhealth --machine-profile     # Show detected profile
```

**`cmwho`** — Show last pusher

```bash
cmwho                          # "Author (hash) 5 hours ago: commit message"
```

**`cminventory`** — Fleet status (if heartbeats collected)

```bash
cminventory                    # List all machines with last update time
```

### Performance & Auditing

**`cmbench`** — Shell startup performance

Measures startup time for multiple shells and alerts if > 1 second:

```bash
cmbench                        # Benchmark zsh, bash, fish, nushell
```

**`cmaudit`** — Audit missing command dependencies

Parses all alias files, extracts referenced commands, checks if they're installed:

```bash
cmaudit                        # List missing commands referenced in aliases
```

### Maintenance & Recovery

**`cmrollback`** — Interactive commit rollback

Shows last 5 commits, choose one to revert:

```bash
cmrollback                     # Interactive menu to select commit
```

After rollback, automatically re-applies configuration.

**`cmreload`** — Live reload of modified configs

Sources changed files in active shell, reloads tmux, restarts shell:

```bash
cmreload                       # Source modified files + reload shell
cmreload --tmux-only          # Just reload tmux sessions
```

### Package Management Enhancements

**Wrapper updates** (`breww`, `masw`, `snapw`, `aptw`, `dnfw`, `pacmanw`, `yayw`, `ostreew`)

All wrappers now include:

1. **Blacklist checking** (`breww` only): Skip packages in `Brewfile_blacklist`
2. **Git pull before push**: Sync latest from remote before updating manifest
3. **Conflict resolution**: Auto-rebase if remote has changes

**Blacklist example** (`dot_private/Brewfile_blacklist`):
```
go@1.19
python@3.10
neofetch
temurin@8
```

Prevents these packages from being automatically re-added.

### Starship Integration

Custom Chezmoi status indicator in prompt:
- Starship modules: `starship-desktop.toml.tmpl` + `starship-ssh.toml.tmpl`
- Shows `✗` in red if last auto-update failed
- No indicator if everything is healthy

## Related Documentation

- [RUNBOOK.md](../docs/RUNBOOK.md#script-reference) — Script reference
- [ARCHITECTURE.md](../docs/ARCHITECTURE.md#package-management) — Package management system
- [ONBOARDING.md](../docs/ONBOARDING.md#working-with-ai-agents-and-skills) — Adding custom agents and skills

## Example Workflows

### Install a new package and sync to all machines

```bash
brew install ripgrep              # macOS/Linux: breww intercepts
# OR
apt install ripgrep               # Debian/Ubuntu: aptw intercepts
# Manifest updates + auto-commits
# Other machines run chezmoi apply and install ripgrep automatically
```

### Update all Claude agents quarterly

```bash
update-claude-agents
# Fetches latest agents from VoltAgent + msitarzewski
# Commits to chezmoi repo
# Other machines pull on next chezmoi update
```

### Create desktop launchers for toolbox apps

```bash
tbx-export-apps fedora-43
# All .desktop files from fedora-43 appear in your app menu
# Click to launch directly from desktop
```

### Set up a new project with Claude Code

```bash
cd my-new-project
npm init vite@latest .
claude-init
# Generates CLAUDE.md with tech stack and dev commands
```
