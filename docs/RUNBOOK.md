# Operational Runbook

Day-to-day operations, troubleshooting, and disaster recovery for the chezmoi dotfiles system.

## Daily Operations

### Sync all machines

On a secondary machine, pull latest changes and apply:

```bash
cu    # chezmoi update -v (git pull + apply)
```

On the master machine, apply after editing configs:

```bash
ca    # chezmoi apply -v
```

Full update (dotfiles + packages):

```bash
cup   # chezmoi update + brew upgrade/apt upgrade/dnf upgrade
```

### Edit and re-sync a config

```bash
vim ~/.config/starship.toml          # edit locally
chezmoi re-add ~/.config/starship.toml  # auto-commits + auto-pushes
```

### Check for drift

```bash
chezmoi diff      # show pending changes
chezmoi verify    # validate all managed files match
chezmoi doctor    # full health check
```

## Common Tasks

### Install a new package

Just use your package manager normally -- aliases intercept and track the manifest:

```bash
brew install ripgrep   # macOS/Linux: breww handles Brewfile sync
apt install ripgrep    # Debian/Ubuntu: aptw handles Aptfile sync
dnf install ripgrep    # Fedora: dnfw handles Dnffile sync
```

### Add a new dotfile

```bash
chezmoi add ~/.config/tool/config.toml
# autoAdd + autoCommit + autoPush handles the rest
```

### Convert a file to a template

```bash
cd ~/.local/share/chezmoi
mv dot_config/tool/config.toml dot_config/tool/config.toml.tmpl
# Edit to add template logic, then:
chezmoi execute-template < dot_config/tool/config.toml.tmpl  # test
chezmoi diff  # verify
chezmoi apply -v
```

### Re-run a run_once script

chezmoi tracks `run_once_` scripts by content hash. To re-run one:

```bash
chezmoi state delete-bucket --bucket=scriptState
chezmoi apply -v
```

This re-runs **all** `run_once_` scripts. To be more selective, modify the script content (e.g., add a comment) so its hash changes.

### Update Claude Code agents from upstream

```bash
update-claude-agents            # pulls from VoltAgent + msitarzewski
update-claude-agents --dry-run  # preview only
```

### Update skills from upstream

```bash
update-claude-skills            # pulls from skill sources
update-claude-skills --dry-run  # preview only
```

### Add a new MCP server

Edit `dot_claude/private_settings.json.tmpl`, add the server config under `mcpServers`, then:

```bash
chezmoi apply ~/.claude/settings.json
sync-mcp-servers  # propagate to OpenCode config
```

### Force-refresh external dependencies

Oh-My-Zsh, zsh plugins, and TPM auto-refresh weekly. To force:

```bash
chezmoi update --apply=false  # pull git changes
rm -rf ~/.oh-my-zsh            # remove cached clone
chezmoi apply -v               # re-clone
```

## Troubleshooting

### `chezmoi apply` hangs

**Cause**: 1Password CLI (`op`) timeout during template evaluation.

**Fix**: Apply specific paths instead of everything:

```bash
chezmoi apply ~/.config/sketchybar ~/.config/aerospace
chezmoi apply ~/.claude/settings.json
```

### Template error on apply

**Diagnose**:

```bash
chezmoi execute-template < dot_config/tool/config.toml.tmpl
```

**Common causes**:
- Missing closing `{{ end }}`
- Referencing undefined template data
- 1Password item not found (check `op item get <id>`)

### Wrong profile detected

**Check**:

```bash
chezmoi data | grep machine_profile
```

**Fix**: Edit `~/.config/chezmoi/chezmoi.toml` and set `machine_profile` manually, then `chezmoi apply -v`.

### Brew bundle fails

**Common causes**:
- Missing cask tap: `brew tap homebrew/cask`
- Rosetta not installed (Apple Silicon): `softwareupdate --install-rosetta`
- Stale formula: `brew update` then retry

### Skill symlinks broken

**Symptom**: `~/.claude/skills/` has dangling symlinks.

**Fix**: Re-trigger the sync script:

```bash
touch ~/.local/share/chezmoi/dot_agents/dot_skill-lock.json
chezmoi apply -v
```

### SSH config not generated

**Cause**: 1Password desktop app not running or not authenticated.

**macOS**: Open 1Password, authenticate, then:

```bash
chezmoi apply ~/.ssh/config
```

**Linux**: A minimal config is generated automatically. For full config, install 1Password CLI and authenticate.

### Git conflicts on secondary machine

```bash
cd ~/.local/share/chezmoi
git stash             # save local changes
git pull --rebase     # pull latest
git stash pop         # restore local changes (resolve conflicts if any)
chezmoi apply -v
```

### Chezmoi doctor warnings

Run `chezmoi doctor` and check each warning:

| Warning | Fix |
|---------|-----|
| `age` not found | `brew install age` |
| `op` not found | Install 1Password CLI |
| source dir not a git repo | `cd ~/.local/share/chezmoi && git init` |
| config file not found | `chezmoi init jsoyer` |

## Disaster Recovery

### Fresh machine from scratch

One command:

```bash
# macOS / Linux
curl -sL https://raw.githubusercontent.com/jsoyer/dotfiles/main/scripts/bootstrap.sh | bash

# Windows
irm https://raw.githubusercontent.com/jsoyer/dotfiles/main/scripts/bootstrap.ps1 | iex
```

### Restore from existing GitHub repo

```bash
chezmoi init --apply jsoyer
```

### Partial recovery (apply only shell configs)

```bash
chezmoi apply ~/.zshrc ~/.zsh/ ~/.bashrc ~/.bash/
```

### Partial recovery (only a specific tool)

```bash
chezmoi apply ~/.config/starship.toml
chezmoi apply ~/.config/tmux/
```

### Rollback a bad change

```bash
cd ~/.local/share/chezmoi
git log --oneline -10          # find the commit to revert
git revert <commit-sha>        # create a revert commit
chezmoi apply -v               # apply the rollback
```

### Lost age encryption key

1. Generate a new age identity:

```bash
age-keygen -o ~/.config/chezmoi/key.txt
```

2. Update the public key in 1Password (or `.chezmoi.toml`).

3. Re-encrypt all encrypted files:

```bash
chezmoi re-add --encrypt <each encrypted file>
```

## Maintenance Calendar

| Frequency | Task | Command |
|-----------|------|---------|
| **Weekly** | External deps auto-refresh | Automatic (168h interval) |
| **Monthly** | Full sync on all machines | `cup` on each machine |
| **Monthly** | Health check | `chezmoi doctor` |
| **Quarterly** | Audit Brewfiles for unused packages | Review `Brewfile_*` manually |
| **Quarterly** | Update agent sources | `update-claude-agents` |
| **Quarterly** | Review skill inventory | `update-claude-skills` |

## Script Reference

### Lifecycle Scripts (`.chezmoiscripts/`)

| Phase | Script | Trigger | Platform |
|-------|--------|---------|----------|
| 01-setup | `setup-macos.sh` | once | macOS |
| 01-setup | `setup-linux.sh` | once | Linux |
| 02-install | `install-1password.sh` | once | macOS, Linux |
| 02-install | `install-1password.ps1` | once | Windows |
| 02-install | `install-linuxbrew.sh` | once | Linux desktop |
| 02-install | `install-linux-flatpak.sh` | once | Linux (Flatpak) |
| 02-install | `install-toolboxes.sh` | once | Fedora Atomic |
| 02-install | `install-opencode-tools.sh` | once | Desktop profiles |
| 02-install | `install-claude-plugins.sh` | once | Desktop profiles |
| 02-install | `install-windows-packages.ps1` | once | Windows |
| 02-install | `brew-bundle.sh` | onchange | macOS, Linux (Homebrew) |
| 02-install | `install-linux-packages.sh` | onchange | Linux |
| 03-configure | `configure-atuin.sh` | once | All |
| 03-configure | `configure-gpg.sh` | once | macOS |
| 03-configure | `configure-linux.sh` | once | Linux |
| 03-configure | `configure-mail.sh` | onchange | All |
| 03-configure | `generate-ssh-config.sh` | onchange | All |
| 03-configure | `sync-skill-symlinks.sh` | onchange | All |
| 04-update | `update-appstore.sh` | onchange | mac-personal |
| 04-update | `update-homebrew.sh` | onchange | macOS |
| 04-update | `update-linux.sh` | onchange | Linux |
| 04-update | `update-windows.ps1` | onchange | Windows |
| 05-maintenance | `maintenance-container.sh` | always | All |

### Utility Scripts (`~/.local/bin/`)

| Script | Purpose | Usage |
|--------|---------|-------|
| `breww` | Homebrew wrapper, auto-syncs Brewfile | `brew install foo` (aliased) |
| `aptw` | APT wrapper, auto-syncs Aptfile | `apt install foo` (aliased) |
| `dnfw` | DNF wrapper, auto-syncs Dnffile | `dnf install foo` (aliased) |
| `pacmanw` | Pacman wrapper, auto-syncs Pacfile | `pacman -S foo` (aliased) |
| `yayw` | YAY/AUR wrapper, auto-syncs Pacfile_aur | `yay -S foo` (aliased) |
| `ostreew` | rpm-ostree wrapper, auto-syncs Pacfile | `ostreew install foo` |
| `scoopw` | Scoop wrapper, auto-syncs Scoopfile | `scoop install foo` (aliased) |
| `update-claude-agents` | Pull agents from upstream sources | `update-claude-agents [--dry-run]` |
| `update-claude-skills` | Pull skills from upstream sources | `update-claude-skills [--dry-run]` |
| `sync-mcp-servers` | Sync Claude MCP config to OpenCode | `sync-mcp-servers [--dry-run]` |
| `claude-init` | Generate CLAUDE.md for new projects | `claude-init` |
| `tbx-app` | Create .desktop wrapper for toolbox app | `tbx-app <container> <app>` |
| `tbx-export-apps` | Bulk export toolbox apps | `tbx-export-apps <container>` |
