# Quick Reference

## Chezmoi

| Command | Action |
|---------|--------|
| `ca` | `chezmoi apply -v` |
| `cu` | `chezmoi update -v` |
| `cup` | update + sysup + docker update |
| `c add FILE` | Track a file |
| `c re-add FILE` | Re-sync tracked file (auto-commit) |
| `c diff` | Preview pending changes |
| `c edit FILE` | Edit source + apply |

## System

| Command | Action |
|---------|--------|
| `sysup` | Update all packages + flatpak + brew + AI tools |
| `update-ai` | Update Claude Code, Copilot, Codex |
| `dcua` | Docker compose pull + up + prune |

## Monitoring (cm* commands)

| Command | Action |
|---------|--------|
| `cmstatus` | Last auto-update status (JSON) |
| `cmlog` | Last auto-update log |
| `cmdiff` | Pending changes (syntax highlighted) |
| `cmchangelog` | Recent dotfile commits |
| `cmwho` | Who pushed last |
| `cmhealth` | 10-point system health check |
| `cmbench` | Shell startup benchmark |
| `cmbench --history` | Benchmark history over time |
| `cmaudit` | Missing command dependencies |
| `cmaudit-packages` | Unused brew packages (30+ days) |
| `cmrollback` | Interactive rollback |
| `cmreload` | Reload tmux + shell configs |

## Security & Tools

| Command | Action |
|---------|--------|
| `secret-age` | Audit age of secrets/tokens |
| `mcp-health` | MCP server health check |
| `chezmoi-state-backup` | Backup chezmoi state (age encrypted) |
| `config-search` | FZF search across configs |
| `zsh-profiler` | Per-file zsh startup profiler |

## Navigation

| Command | Action |
|---------|--------|
| `cx DIR` | cd + list |
| `fcd` | FZF directory picker |
| `fv` | FZF file → open in nvim |
| `f` | FZF file → copy path |
| `ff` | Aerospace window picker (macOS) |

## Package Wrappers

All wrappers auto-track installs in manifest files.

| Alias | Wraps | Manifest |
|-------|-------|----------|
| `breww` | `brew` | Brewfile_* |
| `aptw` | `apt` | Aptfile_* |
| `dnfw` | `dnf` | Dnffile_* |
| `pacmanw` | `pacman` | Pacfile_* |
| `yayw` | `yay` | Pacfile_aur_* |
| `scoopw` | `scoop` | Scoopfile.json |

## Git

| Shortcut | Action |
|----------|--------|
| `gs` | `git status` |
| `gl` | `git log --oneline` |
| `gd` | `git diff` |
| `gco` | `git checkout` |
| `gcm` | `git commit -m` |
| `gp` | `git push` |
| `gpu` | `git pull` |
