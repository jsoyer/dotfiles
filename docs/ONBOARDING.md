# Onboarding Guide

This guide picks up where the [README Quick Start](../README.md#-quick-start) leaves off. It covers understanding, customizing, and extending the dotfiles system after your initial setup.

## Understanding Your Profile

Your machine profile drives which configs are applied, which packages are installed, and which scripts run.

```bash
# Check your current profile
chezmoi data | grep machine_profile

# Check all resolved template data
chezmoi data
```

To change your profile, edit `~/.config/chezmoi/chezmoi.toml` and update the `machine_profile` value, then re-apply:

```bash
chezmoi apply -v
```

See [ARCHITECTURE.md Profile Detection](ARCHITECTURE.md#profile-detection) for the full decision tree.

## Adding a New Tool Configuration

**Step 1: Configure the tool locally**

```bash
mkdir -p ~/.config/newtool
vim ~/.config/newtool/config.toml
```

**Step 2: Test that it works**

Make sure the config is correct before adding it to chezmoi.

**Step 3: Add to chezmoi**

```bash
chezmoi add ~/.config/newtool/config.toml
```

This copies the file to `dot_config/newtool/config.toml` in the source directory. Commit explicitly unless you intentionally rendered chezmoi config with `CHEZMOI_AUTO_GIT=1`.

**Step 4: Make it a template (if needed)**

If the config needs platform-specific values or secrets:

```bash
# Rename to .tmpl in the source directory
cd ~/.local/share/chezmoi
mv dot_config/newtool/config.toml dot_config/newtool/config.toml.tmpl
```

Then add template logic:

```toml
# dot_config/newtool/config.toml.tmpl
[settings]
{{- if eq .chezmoi.os "darwin" }}
font = "JetBrainsMono Nerd Font"
{{- else }}
font = "JetBrains Mono NF"
{{- end }}
```

Test with:

```bash
chezmoi execute-template < dot_config/newtool/config.toml.tmpl
chezmoi diff
```

## Adding a Package

Use the wrapper scripts -- they install the package **and** update the tracked manifest automatically.

| Platform | Command | What happens |
|----------|---------|-------------|
| macOS | `brew install foo` | `breww` installs + updates `Brewfile_*` + pushes wrapper-owned manifest changes |
| Debian/Ubuntu | `apt install foo` | `aptw` installs + updates `Aptfile_*` + pushes wrapper-owned manifest changes |
| Fedora | `dnf install foo` | `dnfw` installs + updates `Dnffile_*` + pushes wrapper-owned manifest changes |
| Arch | `pacman -S foo` | `pacmanw` installs + updates `Pacfile_*` + pushes wrapper-owned manifest changes |
| Arch (AUR) | `yay -S foo` | `yayw` installs + updates `Pacfile_aur_*` + pushes wrapper-owned manifest changes |
| Windows | `scoop install foo` | `scoopw` installs + updates `Scoopfile.json` + pushes wrapper-owned manifest changes |

The wrapper aliases are set up in `~/.zsh/10-aliases.zsh`.

## Understanding Templates

### Key template functions

| Function | Example | Purpose |
|----------|---------|---------|
| `eq` | `{{ if eq .chezmoi.os "darwin" }}` | Equality check |
| `lookPath` | `{{ if lookPath "op" }}` | Check if binary exists in PATH |
| `env` | `{{ if env "TOOLBOX_PATH" }}` | Check environment variable |
| `stat` | `{{ if stat "/proc/device-tree/model" }}` | Check if file exists |
| `onepasswordRead` | `{{ onepasswordRead "op://vault/item/field" }}` | Read secret from 1Password |

### Testing and debugging

```bash
# Render a template without applying
chezmoi execute-template < file.tmpl

# Preview all pending changes
chezmoi diff

# Show the rendered version of a managed file
chezmoi cat ~/.config/tool/config.toml

# Validate all templates
chezmoi verify
```

### Available template data

```bash
# List all available data
chezmoi data

# Common variables:
# .chezmoi.os          -> "darwin", "linux", "windows"
# .chezmoi.arch        -> "amd64", "arm64"
# .chezmoi.hostname    -> machine hostname
# .chezmoi.homeDir     -> home directory path
# .machine_profile     -> resolved profile name
# .github_user         -> "jsoyer"
# .name / .email       -> user identity
# .xdgConfigDir        -> XDG config path
```

## Adding a New Platform Profile

1. **Add detection logic** in `.chezmoi.toml.tmpl`:

```go
{{- else if eq .chezmoi.osRelease.id "nixos" -}}nixos
```

2. **Add ignore rules** in `.chezmoiignore.tmpl` to exclude files that don't apply to the new profile.

3. **Create a package manifest** in `dot_private/`:

```bash
# e.g., for NixOS
touch dot_private/Nixfile_desktop
```

4. **Add install logic** in `.chezmoiscripts/02-install/` scripts (or create a new one).

5. **Add the profile to desktop/server lists** in existing scripts if applicable.

6. **Test**:

```bash
chezmoi apply --dry-run -v   # preview without applying
chezmoi diff                  # see what would change
chezmoi apply -v              # apply for real
```

## Working with AI Agents and Skills

### Adding a custom Claude Code agent

Create a markdown file in `dot_claude/agents/`:

```bash
vim ~/.local/share/chezmoi/dot_claude/agents/my-agent.md
```

The agent definition follows this pattern:

```markdown
---
model: sonnet
---

Description of the agent's role and capabilities.
When to use this agent.
What tools it has access to.
```

### Adding a skill

Add a directory under `dot_agents/skills/`:

```bash
mkdir -p dot_agents/skills/my-skill
vim dot_agents/skills/my-skill/skill.md
```

Then update the lock file to trigger symlink sync:

```bash
# Optional: bump the lock file before running run_after_sync-aictx.sh
date > dot_agents/dot_skill-lock.json
chezmoi apply
```

> The cache/symlink workflow now runs after every `chezmoi apply` via `run_after_sync-aictx.sh`, so touching the lock file is only needed when forcing a rerun manually.

### Updating agents from upstream

```bash
update-claude-agents            # pull latest from VoltAgent + msitarzewski
update-claude-agents --dry-run  # preview changes
update-claude-skills            # pull latest skills
```

## Working with Secrets

### 1Password CLI

Most secrets are fetched via `op read` at template evaluation time:

```go
{{ onepasswordRead "op://Private/My Secret/password" }}
```

If 1Password is unavailable, templates with `op` calls are skipped (see `.chezmoiignore.tmpl`).

### Age encryption

For files that should be encrypted at rest in the git repo:

```bash
chezmoi add --encrypt ~/.config/sensitive/config.toml
```

This encrypts with age using the key configured in `.chezmoi.toml.tmpl`. The identity file is at `~/.config/chezmoi/key.txt`.

### What happens without 1Password?

Scripts gracefully degrade:
- SSH config falls back to a minimal config
- GPG import is skipped
- Encrypted files are still decrypted via age (separate key)
- Package installation works normally

## Quick Reference

| I want to... | Do this |
|-------------|---------|
| Apply dotfiles | `ca` (wrapper for `chezmoi apply -v` that flags warnings) |
| Sync from git + apply | `cu` (alias for `chezmoi update -v`) |
| Update everything | `cup` (update + upgrade packages) |
| Add a file to chezmoi | `chezmoi add ~/.config/tool/config` |
| Re-sync a changed file | `chezmoi re-add ~/.config/tool/config` |
| Preview changes | `chezmoi diff` |
| Check for issues | `chezmoi doctor` |
| Debug a template | `chezmoi execute-template < file.tmpl` |
| Install a brew package | `brew install foo` (wrapper handles the rest) |
| Update Claude agents | `update-claude-agents` |
| Sync MCP servers | `sync-mcp-servers` |
| Re-run a run_once script | `chezmoi state delete-bucket --bucket=scriptState` then `chezmoi apply` |
| Check your profile | `chezmoi data \| grep machine_profile` |
| Apply only one path | `chezmoi apply ~/.config/sketchybar` |
