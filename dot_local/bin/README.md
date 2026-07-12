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
4. Commits and pushes wrapper-owned manifest changes explicitly with Git
5. Other machines detect the manifest hash change and install missing packages

Chezmoi's broad `[git] autoAdd/autoCommit/autoPush` defaults are disabled unless `CHEZMOI_AUTO_GIT=1` is set while rendering `.chezmoi.toml.tmpl`. Package wrappers do not rely on those global settings.

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

### brew-deprecated

Lists installed Homebrew formulae and casks that upstream has flagged
**deprecated** or **disabled**, with the reason for each — so you can migrate or
remove them before a future `brew upgrade` breaks. Reads `brew info --json`,
takes no arguments. Aliased as `bdep`.

```bash
brew-deprecated            # scan installed packages; prints ⚠️ per flagged item
```

### brew-usage

Estimates real usage of installed Homebrew formulae and casks — Homebrew keeps no
usage counter. Formulae are dated by the newest `atime` of their Cellar binaries;
casks by Spotlight's last-used date (falling back to the installed binary's
`atime`). Old timestamps are reliable ("this package is idle"); recent ones less
so (a background scan can touch a file). Aliased as `buse`.

```bash
brew-usage                 # summary + full table, newest-idle first
brew-usage --stale         # only packages idle > 180 days (or never seen)
brew-usage --formulae      # formulae only  (--casks for casks only)
brew-usage --json          # machine-readable output
brew-usage --html --open   # write & open a self-contained interactive report
brew-usage --uninstall-script --stale 365 > purge.sh   # guarded by `brew uses`
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

### ca

**Purpose:** Safer `chezmoi apply` wrapper that captures output and highlights warnings.

**Usage:**
```bash
ca                  # Apply everything (same flags as chezmoi apply)
ca ~/.zshrc         # Apply a specific path
```

**What it does:**
1. Runs `chezmoi apply -v` with your arguments
2. Saves output to a temp log
3. Prints a reminder if “warning” appears anywhere in the log

### sync-mcp-servers

**Purpose:** Re-render `~/.config/opencode/opencode.json` from the chezmoi template after updating Claude settings.

**Usage:**
```bash
sync-mcp-servers           # Apply the template
sync-mcp-servers --dry-run # Preview changes (chezmoi diff)
```

**What it does:**
1. Runs `chezmoi diff/apply` against `~/.config/opencode/opencode.json`
2. Ensures OpenCode picks up the latest MCP list defined in chezmoi

## Configuration & Development

### cmupgrade

**Purpose:** Manual package/system upgrade entry point. This keeps unattended `chezmoi-autoupdate` lightweight while preserving an explicit command for full upgrades.

**Usage:**
```bash
cmupgrade --dry-run
cmupgrade --yes
```

**What it does:**
1. Runs available platform package upgrades (`brew`, `apt`, `dnf`, `pacman`, `rpm-ostree`, `flatpak`).
2. Updates selected developer tools when present (`uv`, `claude`).
3. Requires confirmation unless `--yes` or `--dry-run` is used.

### chezmoi-test-scripts

**Purpose:** Render `.chezmoiscripts/**/*.tmpl` and syntax-check rendered shell scripts.

**Usage:**
```bash
chezmoi-test-scripts
```

**What it does:**
1. Renders every script template with `chezmoi execute-template`.
2. Runs `bash -n` on rendered shell scripts.
3. Runs PowerShell parsing when `pwsh` is available.
4. Runs `chezmoi diff --no-tty --no-pager` against `CHEZMOI_DESTINATION_PATH` or `$HOME`.

### ai-resource-dedup-report

**Purpose:** Inventory duplicate AI resources between `dot_claude/` and `dot_aictx/` before any cleanup.

**Usage:**
```bash
ai-resource-dedup-report > docs/.artifacts-ai-resource-dedup.md
```

**What it does:**
1. Compares `skills`, `agents`, `commands`, `hooks`, and `rules` by relative path and SHA-256.
2. Reports identical, different, Claude-only, and aictx-only counts.
3. Does not delete or modify resources.

### update-claude-upstream

**Purpose:** Update vendored `dot_claude/` from `vinicius91carvalho/.claude` while preserving local patches.

**Usage:**
```bash
update-claude-upstream --check
update-claude-upstream --patch-report
update-claude-upstream --update --dry-run
update-claude-upstream --update
```

**What it does:**
1. Reads `docs/CLAUDE_UPSTREAM.json` for repo, branch, and pinned commit.
2. Builds a three-way merge: pinned upstream base, latest upstream, local `dot_claude/`.
3. Preserves local-only patches and writes conflict markers when upstream and local edits overlap.
4. Updates the upstream pin only after a clean update.
5. Reports local patch inventory against the pinned upstream snapshot with `--patch-report`, normalizing chezmoi prefixes such as `executable_` and `symlink_`.

### verify-claude-vendor

**Purpose:** Validate that `dot_claude/` is tracked as vendored content and provenance metadata matches.

**Usage:**
```bash
verify-claude-vendor
```

### update-zellij-plugins

**Purpose:** Verify and intentionally upgrade tracked Zellij WASM plugins using a pinned lockfile.

**Usage:**
```bash
update-zellij-plugins
update-zellij-plugins --check
update-zellij-plugins --bump zjstatus
update-zellij-plugins --bump zellij-datetime
```

**What it does:**
1. Reads `dot_config/zellij/plugins/plugins.lock.json`.
2. Downloads release assets to temporary files.
3. Verifies SHA-256 before replacing tracked `.wasm` files.
4. Keeps new GitHub releases opt-in via `--bump`.

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

**`cmaudit-packages`** — Audit unused brew packages

Checks last access time of brew formula binaries and flags packages unused for 30+ days:

```bash
cmaudit-packages               # Default 30-day threshold
cmaudit-packages --days 60     # Custom threshold
```

**`zsh-profiler`** — Per-file zsh startup profiler

Measures and ranks each config file's load time using `EPOCHREALTIME`:

```bash
zsh-profiler                   # Profile all zsh config files
```

**`config-search`** — FZF-powered config search

Search across all `~/.config/` files with bat preview:

```bash
config-search                  # Interactive browse
config-search "theme"          # Pre-filtered
```

### Security & State

**`chezmoi-state-backup`** — Backup chezmoi state (age-encrypted)

Dumps state, age key, and config into an encrypted archive. Auto-prunes old backups (keeps 5):

```bash
chezmoi-state-backup                    # Create backup
chezmoi-state-backup --restore FILE     # Restore from archive
```

**`mcp-health`** — MCP server health check

Validates env vars, HTTP endpoints, and CLI tools for all 20 MCP servers:

```bash
mcp-health                     # Full health check
```

**`secret-age`** — Secret staleness audit

Checks age of SSH keys, age encryption keys, tokens, and warns if older than threshold:

```bash
secret-age                     # Default 90-day threshold
secret-age --days 60           # Custom threshold
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
# Manifest updates + explicit wrapper commits
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
