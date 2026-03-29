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
