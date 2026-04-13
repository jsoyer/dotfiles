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
vim ~/.config/starship/starship-desktop.toml          # edit locally
chezmoi re-add ~/.config/starship/starship-desktop.toml  # auto-commits + auto-pushes
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

Edit `dot_claude/settings.json` (vendored Claude Workflow System), add the server config under `mcpServers`, then:

```bash
chezmoi apply ~/.claude/settings.json
sync-mcp-servers  # propagate to OpenCode config
```

### RTK hook health check

`dot_claude/hooks/rtk-rewrite.sh` and the matching PreToolUse block in `dot_claude/settings.json`
ensure every Bash command flows through RTK automatically. If a future upstream update drops
either file, restore the vendored snapshot and re-run:

```bash
chezmoi apply ~/.claude/hooks/rtk-rewrite.sh ~/.claude/settings.json
```

Then restart Claude Code to pick up the hook (verify with `jq '.hooks.PreToolUse[0]' ~/.claude/settings.json`).

### Refresh Claude workflow after pulling upstream

```bash
aictx apply --auto --yes   # relink agents/skills + apply profile overrides
sync-mcp-servers           # render ~/.config/opencode/opencode.json from chezmoi
chezmoi apply ~/.claude    # ensure the vendored snapshot is on disk
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

### Auto-update fails with SSH "Permission denied" on headless machines

**Cause**: No SSH key for GitHub on this machine (common on RPi/servers).

The auto-update script auto-heals this by switching the git remote from SSH to HTTPS. HTTPS works without auth for public repos. After the next run, the status should turn green.

**Manual fix** (if auto-heal hasn't run yet):
```bash
cd ~/.local/share/chezmoi
git remote set-url origin https://github.com/jsoyer/dotfiles.git
chezmoi-autoupdate
```

**To set up SSH properly instead** (optional, enables push from this machine):
```bash
ssh-keygen -t ed25519 -C "$(hostname)" -f ~/.ssh/id_ed25519 -N ""
ssh-keyscan github.com >> ~/.ssh/known_hosts
cat ~/.ssh/id_ed25519.pub
# Add the public key to GitHub: Settings → SSH and GPG keys → New SSH key
# Then switch back to SSH:
cd ~/.local/share/chezmoi
git remote set-url origin git@github.com:jsoyer/dotfiles.git
```

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
chezmoi apply ~/.config/starship/starship-desktop.toml
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
| 03-configure | `sync-aictx.sh` | after apply | All |
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
| `chezmoi-autoupdate` | Central auto-update + auto-heal daemon | `chezmoi-autoupdate [--dry-run] [--rollback]` |
| `chezmoi-validate` | Pre-apply validation suite | `chezmoi-validate [--strict]` |
| `cmhealth` | Full system health check | `cmhealth` |
| `cmbench` | Shell startup performance benchmark | `cmbench` |
| `cmaudit` | Audit missing command dependencies | `cmaudit` |
| `cmrollback` | Interactive commit rollback | `cmrollback` |
| `cmreload` | Live reload configs in active shell | `cmreload [--tmux-only]` |
| `cmwho` | Show last dotfile pusher | `cmwho` |
| `cminventory` | Fleet status from heartbeats | `cminventory` |

---

## Auto-Update System Troubleshooting

### Check Timer Status

**Linux (systemd):**
```bash
# View timer
systemctl --user list-timers chezmoi-autoupdate.timer

# View service status
systemctl --user status chezmoi-autoupdate.service

# View logs (last 50 lines, follow in real-time)
journalctl --user -u chezmoi-autoupdate -n 50 -f

# Check timer enabled
systemctl --user is-enabled chezmoi-autoupdate.timer
```

**macOS (launchd):**
```bash
# View agent
launchctl list | grep chezmoi

# Check if running
launchctl list com.jsoyer.chezmoi-autoupdate

# View logs
log stream --predicate 'process == "chezmoi-autoupdate"'

# Manually trigger
launchctl start com.jsoyer.chezmoi-autoupdate
```

**Windows (Task Scheduler):**
```powershell
# View task
Get-ScheduledTask -TaskName "ChezmoidAutoupdate" | fl

# View recent runs
Get-ScheduledTaskInfo -TaskName "ChezmoidAutoupdate"

# Manually trigger
Start-ScheduledTask -TaskName "ChezmoidAutoupdate"
```

### View Auto-Update Status

```bash
# Last run status (JSON)
cmstatus

# Full execution log
cmlog

# Human-readable health check
cmhealth

# Recent changes
cmchangelog
```

### Disable Auto-Update

**Temporarily** (until next system reboot):
```bash
# Linux
systemctl --user stop chezmoi-autoupdate.timer

# macOS
launchctl stop com.jsoyer.chezmoi-autoupdate
```

**Permanently**:
```bash
# Linux
systemctl --user disable chezmoi-autoupdate.timer

# macOS
launchctl unload ~/Library/LaunchAgents/com.jsoyer.chezmoi-autoupdate.plist

# Windows (in PowerShell as admin)
Disable-ScheduledTask -TaskName "ChezmoidAutoupdate"
```

### Force Manual Update

```bash
# Run once immediately
chezmoi-autoupdate

# Preview what would happen
chezmoi-autoupdate --dry-run

# Force rollback to previous commit
chezmoi-autoupdate --rollback
```

### Debug Notification Failures

**Check notification environment variables:**
```bash
# Required for Telegram
echo $TELEGRAM_BOT_TOKEN $TELEGRAM_CHAT_ID

# Required for Discord
echo $DISCORD_WEBHOOK_URL

# ntfy (self-hosted)
echo $CHEZMOI_NTFY_TOPIC
echo $CHEZMOI_NTFY_URL
echo $CHEZMOI_NTFY_TOKEN
```

Set in `~/.zsh/secrets.zsh` (auto-generated from 1Password via `chezmoi apply`):
```bash
export CHEZMOI_NTFY_TOPIC="chezmoi-fleet"
export CHEZMOI_NTFY_URL="https://ntfy.bbhome.wf"
export CHEZMOI_NTFY_TOKEN="tk_xxx"
export TELEGRAM_BOT_TOKEN="xxx"
export TELEGRAM_CHAT_ID="xxx"
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
```

**ntfy user/topic setup (on the ntfy host):**
```bash
docker exec -it ntfy ntfy user add --role=admin jsoyer
docker exec -it ntfy ntfy token add jsoyer
docker exec -it ntfy ntfy access jsoyer 'chezmoi-fleet' rw
docker exec -it ntfy ntfy access jsoyer 'watchtower-updates' rw
docker exec -it ntfy ntfy access jsoyer 'diun-updates' rw
```

**Test notification manually:**
```bash
# Test desktop notification
notify-send "Test" "This is a test notification"

# Test ntfy (self-hosted with auth)
curl -H "Authorization: Bearer $CHEZMOI_NTFY_TOKEN" \
  -d "Testing" "$CHEZMOI_NTFY_URL/$CHEZMOI_NTFY_TOPIC"

# Test Discord webhook
curl -X POST -H "Content-Type: application/json" \
  -d '{"content":"Test from chezmoi"}' \
  "$DISCORD_WEBHOOK_URL"
```

### Rollback a Bad Update

```bash
# Interactive: choose from last 5 commits
cmrollback

# Or manually:
cd ~/.local/share/chezmoi
git log --oneline -5          # find commit to revert
git reset --hard <commit>     # go back to that state
chezmoi apply -v              # re-apply configuration
```

### Auto-Heal Not Working

**Check git status:**
```bash
cd ~/.local/share/chezmoi
git status                     # should be clean
git log -1 --oneline          # should be recent
```

**Manually trigger auto-heal:**
```bash
chezmoi-autoupdate --dry-run  # preview what would be fixed
chezmoi-autoupdate            # actually fix it
```

**Common auto-heal issues:**
- **Merge conflicts**: Auto-resolved via `rebase --abort` + `reset --hard origin/main`
- **Stale brew locks**: Removed if > 30 minutes old
- **SSH permissions**: Fixed to 700 (dirs) / 600 (files)
- **Deprecated packages**: Auto-uninstalled if in `Brewfile_blacklist`
- **Missing TPM plugins**: Installed via `~/.tmux/plugins/tpm/bin/install_plugins`

### Test Validation

After update, auto-validation tests:
```bash
# Manually test what auto-update validates
zsh -i -c 'exit 0'           # Shell starts?
starship --version           # Prompt works?
tmux -c 'exit'               # Tmux launches?
```

If any fails, auto-update auto-rolls back with notification.

### Deadman Switch (Fleet Monitoring)

If using heartbeats, monitor fleet health:
```bash
cminventory                   # Show all machines' last update time
```

Dashboard (if configured):
- Checks ntfy.sh topic for heartbeats
- Alerts if machine offline > 7 days
- Tracks hostname, profile, OS, last update time
