# Shell Aliases & Functions Cheat Sheet

Complete reference of all aliases and functions across Zsh, Bash, Fish, and Nushell.

**Last Updated:** 2026-03-28
**Shells:** Zsh, Bash, Fish, Nushell
**Configuration Files:** `dot_zsh/10-aliases.zsh`, `dot_bash/10-aliases.bash`, `dot_config/private_fish/config.fish.tmpl`, `dot_config/nushell/config.nu`

---

## Quick Reference

| Category | Alias | Command | Shells | Notes |
|----------|-------|---------|--------|-------|
| **Config** | `zshconfig` | `nvim ~/.zshrc` | Z/B | Edit shell config |
| **Config** | `bashconfig` | `nvim ~/.bashrc` | B | Edit bash config |
| **Config** | `ohmyzsh` | `nvim ~/.oh-my-zsh` | Z | Edit Oh-My-Zsh |
| **Editor** | `v` / `vim` | `nvim` | All | Neovim (raises fd limit to 4096) |
| **Editor** | `cat` | `bat` | All | Syntax-highlighted cat |
| **HTTP** | `http` | `xh` | All | Modern curl replacement |

---

## Modern CLI Tool Replacements

Zsh, Bash, Fish all share the same modern CLI replacements.

| Alias | Command | Purpose |
|-------|---------|---------|
| `v`, `vim` | `nvim` | Neovim with raised fd limit (4096) |
| `la` | `tree` | Tree-like directory listing |
| `cat` | `bat` | Syntax-highlighted cat with themes |
| `http` | `xh` | Modern curl alternative |
| `asr` | `atuin scripts run` | Run Atuin scripts |
| `as` | `aerospace` | Aerospace tiling WM (macOS only) |

---

## Listing & Navigation

| Alias | Command | Purpose | Shells |
|-------|---------|---------|--------|
| `ls` | `eza --color=always --icons` | Modern ls with icons | All |
| `ll` | `eza -l --color=always --icons --git -a` | Long ls with git status | All |
| `l` | `eza -l --icons --git -a` | Long ls with git status | All |
| `lt` | `eza --tree --level=2 --long --icons --git` | Tree view (depth 2) | All |
| `ltree` | `eza --tree --level=2 --icons --git` | Tree view (depth 2) | All |
| `zl` | `eza -lagX --icons --color=always` | Comprehensive listing | All |
| `..` | `cd ..` | Up one directory | All |
| `...` | `cd ../..` | Up two directories | All |
| `....` | `cd ../../..` | Up three directories | All |
| `.....` | `cd ../../../..` | Up four directories | All |
| `......` | `cd ../../../../..` | Up five directories | All |
| `cl` | `clear` | Clear screen | All |
| `iclouddrive` | `cd ~/Library/Mobile\ Documents/com~apple~CloudDocs/` | iCloud Drive (macOS only) | All |

---

## Navigation Functions (FZF-powered)

All shells support these FZF-powered functions for interactive navigation and file selection.

| Function | Purpose | Shells |
|----------|---------|--------|
| `cx [path]` | cd and list (combines cd + l) | All |
| `fcd` | FZF directory navigation — fuzzy find directory and cd | All |
| `f` | Copy file path to clipboard via FZF | All |
| `fv` | Open file in nvim via FZF | All |
| `ff` | Aerospace window picker via FZF (macOS only) | Fish, Zsh |

---

## Git Aliases

Standard git shortcuts available in all shells.

| Alias | Command | Purpose |
|-------|---------|---------|
| `gc` | `git commit -m` | Commit with message |
| `gca` | `git commit -a -m` | Commit all staged with message |
| `gp` | `git push origin HEAD` | Push to origin |
| `gpu` | `git pull origin` | Pull from origin |
| `gst` | `git status` | Full status |
| `gs` | `git status -s` | Short status |
| `glog` | `git log --graph --topo-order --pretty='...'` | Fancy log graph |
| `gdiff` | `git diff` | Show diff |
| `gco` | `git checkout` | Checkout branch |
| `gcoall` | `git checkout -- .` | Discard all changes |
| `gb` | `git branch` | List branches |
| `gba` | `git branch -a` | List all branches |
| `gadd` | `git add` | Stage files |
| `ga` | `git add -p` | Interactive staging |
| `gr` | `git remote` | Remote management |
| `gre` | `git reset` | Reset commits |
| `gsw` | `git switch` | Switch branch (modern) |
| `gswc` | `git switch -c` | Create and switch branch |
| `grs` | `git restore` | Restore files |
| `grbi` | `git rebase -i` | Interactive rebase |
| `gcl` | `git clone` | Clone repository |

---

## Docker / Podman

Conditional based on installed container runtime (Docker or Podman).

### Basic Commands
| Alias | Command | Purpose |
|-------|---------|---------|
| `dco` | `docker/podman compose` | Docker Compose |
| `dl` | `docker ps -l -q` | Last container ID |
| `dps` | Container list with status/ports/image | Pretty-printed table format |
| `dpsa` | All containers (including stopped) | Pretty-printed table format |

### Docker Compose
| Alias | Command | Purpose |
|-------|---------|---------|
| `dcpl` | `docker/podman compose pull` | Pull image updates |
| `dcup` | `docker/podman compose up -d` | Start services (detached) |
| `dcl` | `docker/podman compose logs -f` | Stream logs |
| `dcd` | `docker/podman compose down` | Stop services |
| `dcr` | `docker/podman compose restart` | Restart services |
| `dcp` | `docker/podman compose ps` | List services |
| `dce` | `docker/podman compose exec` | Execute in container |
| `dcb` | `docker/podman compose build` | Build images |

### Docker Compose Utility
| Function | Purpose | Shells |
|----------|---------|--------|
| `dcua [path]` | Update all docker-compose projects in directory tree — pull images, restart if changed, prune | All |

---

## Kubernetes

| Alias | Command | Purpose |
|-------|---------|---------|
| `k` | `kubectl` | Kubernetes CLI |
| `ka` | `kubectl apply -f` | Apply manifest |
| `kg` | `kubectl get` | Get resources |
| `kd` | `kubectl describe` | Describe resource |
| `kdel` | `kubectl delete` | Delete resource |
| `kl` | `kubectl logs -f` | Stream logs |
| `kgpo` | `kubectl get pod` | List pods |
| `kgd` | `kubectl get deployments` | List deployments |
| `kc` | `kubectx` | Switch context |
| `kns` | `kubens` | Switch namespace |
| `ke` | `kubectl exec -it` | Execute in pod |
| `kcns` | `kubectl config set-context --current --namespace` | Set namespace |

---

## Chezmoi

Dotfiles management aliases and functions.

| Alias | Command | Purpose |
|-------|---------|---------|
| `c` | `chezmoi` | Chezmoi shorthand |
| `cdiff` | `chezmoi diff` | Preview changes |
| `cedit` | `chezmoi edit` | Edit dotfile |
| `cadd` | `chezmoi add` | Add file to chezmoi |
| `creadd` | `chezmoi re-add` | Re-add file (auto-commits + auto-pushes) |
| `cs` | `chezmoi status` | Status of managed files |
| `ccd` | `chezmoi cd` | Navigate to chezmoi source |

### Chezmoi Functions
| Function | Purpose | Notes |
|----------|---------|-------|
| `ca` | `chezmoi apply -v` | Apply with verbose output |
| `cu` | `chezmoi update -v` | Update and apply with verbose output |
| `cpurge` | Remove chezmoi source + config, keep deployed files | Confirmation required |
| `cdestroy` | Remove chezmoi AND all managed files | Type "destroy" to confirm |

---

## Chezmoi Auto-Update & Monitoring (`cm*` Commands)

Fleet management aliases and utilities for checking health, status, and performing maintenance.

### Monitoring Aliases
| Alias | Command | Purpose | Notes |
|-------|---------|---------|-------|
| `cmstatus` | `jq . ~/.cache/chezmoi-autoupdate/status.json` | Show last auto-update status | JSON output with timestamp, duration, result |
| `cmlog` | Display `~/.cache/chezmoi-autoupdate/last-run.log` | View last auto-update execution log | Full output including errors |
| `cmdiff` | `chezmoi diff \| delta` | Show pending changes with colors | Uses delta for syntax highlighting |
| `cmchangelog` | Git log since last seen commit | Show recent dotfile updates | 20 most recent commits |
| `cmwho` | `git -C ~/.local/share/chezmoi log -1` | Show who made last push | Author, commit hash, timestamp |

### Maintenance & Diagnostics Scripts
| Script | Purpose | Usage |
|--------|---------|-------|
| `cmhealth` | Comprehensive health check | `cmhealth` - validates git, timer, caches, permissions, secrets, fonts, drift |
| `cmbench` | Benchmark shell startup time | `cmbench` - test zsh/bash/fish/nu startup performance |
| `cmaudit` | Audit missing command dependencies | `cmaudit` - check if aliased commands are installed |
| `cmrollback` | Interactive rollback to previous commit | `cmrollback` - choose from last 5 commits to revert |
| `cmreload` | Reload modified configs in active shell | `cmreload` - source changed files + reload tmux sessions + restart shell |
| `cminventory` | Fleet status (if heartbeats configured) | `cminventory` - show all machines' last update status |

---

## Package Manager Wrappers

All package managers are wrapped to track installations in manifest files (`Brewfile*`, `Aptfile*`, `Dnffile*`, `Pacfile*`, `Scoopfile.json`).

### Homebrew (macOS)

| Alias | Command | Purpose |
|-------|---------|---------|
| `b` | `breww` | Homebrew wrapper |
| `bi` | `breww install` | Install package |
| `bu` | `breww update` | Update package list |
| `bup` | `breww upgrade` | Upgrade packages |
| `bcu` | `breww cu -a` | Upgrade casks (uses brew-cask-upgrade) |
| `bs` | `breww search` | Search packages |
| `bl` | `breww list` | List installed |
| `bun` | `breww uninstall` | Uninstall package |
| `bci` | `breww cleanup` | Clean up |
| `binfo` | `breww info` | Show package info |
| `bd` | `breww doctor` | Diagnose issues |

### APT (Ubuntu, Debian, Raspberry Pi)

| Wrapper | Command | Purpose | Platforms |
|---------|---------|---------|-----------|
| `apt()` | `aptw` | Redefined to `aptw` | Ubuntu, Debian, RPi (non-Fedora) |

### DNF (Fedora)

| Wrapper | Command | Purpose | Platforms |
|---------|---------|---------|-----------|
| `dnf()` | `dnfw` | Redefined to `dnfw` | Fedora Desktop/Server |
| `yum()` | `dnfw` | Alias to `dnfw` | Fedora |

### Pacman (Arch Linux)

| Wrapper | Command | Purpose | Platforms |
|---------|---------|---------|-----------|
| `pacman()` | `pacmanw` | Redefined to `pacmanw` | Arch Desktop/Server, OmArchy |
| `yay()` | `yayw` | Redefined to `yayw` | Arch Desktop, OmArchy |

### RPM-OSTree (Fedora Atomic)

| Wrapper | Command | Purpose | Platforms |
|---------|---------|---------|-----------|
| `rpm-ostree()` | `ostreew` | Redefined to `ostreew` | Fedora Atomic |

---

## System Update Functions

### `sysup` — System Update

Updates all package managers for the detected platform. Conditional by machine profile.

```bash
sysup
```

**macOS behavior:**
- Upgrades Homebrew packages (`bup`)
- Upgrades Homebrew casks (`bcu`)
- Upgrades App Store apps (`mas upgrade`)

**Linux behavior (by profile):**
- **RPi / Ubuntu / Debian:** `sudo apt-get update && dist-upgrade -y && autoremove -y`
- **Arch / OmArchy:** `sudo pacman -Syu --noconfirm` + AUR via `yay -Sua --noconfirm`
- **Fedora Desktop/Server/Toolbox:** `sudo dnf upgrade --refresh -y`
- **Fedora Atomic:** `rpm-ostree upgrade`
- **All Linux:** Flatpak updates if installed
- **All Linux:** Linuxbrew updates if installed
- **All Linux:** Calls `update-ai` after package updates

**Windows behavior:**
- `scoop update --all`

### `update-ai` — Update CLI AI Tools

Updates installed AI tools: Claude Code, Copilot CLI, Codex CLI.

```bash
update-ai
```

Updates:
- `claude update` (Claude Code)
- Copilot CLI via `https://gh.io/copilot-install`
- Codex CLI via `npm update -g @openai/codex`

### `cup` — Complete Update

Full system update: chezmoi + packages + Docker Compose projects.

```bash
cup [path]
```

1. Calls `cu` (chezmoi update -v)
2. Calls `sysup` (system package updates)
3. Calls `dcua "$HOME"` (Docker Compose project updates)
4. Prints completion message

---

## SSH

| Alias | Command | Purpose | Notes |
|-------|---------|---------|-------|
| `sshpw` | `ssh -o PreferredAuthentications=password` | SSH with password auth | All shells |
| `ssh-sync` | Sync SSH config to 1Password | Via `op document edit` | macOS only |

**Enhanced SSH wrapper** (custom function in Zsh/Bash):
- Automatically renames tmux window to hostname
- Uses Kitty kitten ssh if running inside Kitty terminal
- Restores window name after SSH exits

---

## Tmux

| Alias | Command | Purpose |
|-------|---------|---------|
| `t` | `tmux` | Tmux shorthand |
| `ta` | `tmux attach -t` | Attach to session |
| `tl` | `tmux list-sessions` | List sessions |
| `tk` | `tmux kill-session -t` | Kill session |
| `tns` | `tmux new-session -s` | Create session |

---

## Jujutsu (VCS Alternative to Git)

| Alias | Command | Purpose |
|-------|---------|---------|
| `j` | `jj` | Jujutsu main command |
| `js` | `jj st` | Status |
| `jl` | `jj log -r 'all()'` | Log all revisions |
| `jd` | `jj diff` | Show diff |
| `jn` | `jj new` | Create new change |
| `jui` | `jjui` | UI (interactive) |
| `jundo` | `jj undo` | Undo last operation |
| `jp` | `jj git push` | Push to git |
| `jf` | `jj git fetch` | Fetch from git |

---

## Claude Code

| Alias | Command | Purpose |
|-------|---------|---------|
| `cco` | `claude --model opus` | Claude Opus (deepest reasoning) |
| `ccs` | `claude --model sonnet` | Claude Sonnet (best for coding) |
| `cch` | `claude --model haiku` | Claude Haiku (fastest, 90% capable) |

---

## Disk & System Information

Conditional based on installed tools. Falls back to standard commands if modern CLI tools unavailable.

| Alias | Command | Purpose | Fallback |
|-------|---------|---------|----------|
| `du` | `dust` | Disk usage with tree view | `du -sh` |
| `df` | `duf` | Disk free with columns | `df -h` |
| `top` | `btop` | Modern process monitor | `top` |
| `ps` | `procs` | Modern process list | `ps aux` |
| `ports` | System port listener check | `ss -tlnp` (Linux) / `lsof` (macOS) |
| `myip` | `curl -s ifconfig.me` | Show public IP address |
| `path` | Print `$PATH` (one per line) | Readable PATH formatting |

---

## Search & Find

Optimized ripgrep and fd shortcuts.

| Alias | Command | Purpose |
|-------|---------|---------|
| `rgf` | `rg --files-with-matches` | Files matching pattern |
| `rgi` | `rg --ignore-case` | Case-insensitive ripgrep |
| `fdf` | `fd --type f` | Find files only |
| `fdd` | `fd --type d` | Find directories only |

---

## Markdown

| Alias | Command | Purpose | Condition |
|-------|---------|---------|-----------|
| `md` | `glow` | Render Markdown in terminal | If glow installed |

---

## Python / Node.js / Virtual Environments

### UV (Python Package Manager)

| Alias | Command | Purpose |
|-------|---------|---------|
| `uvi` | `uv init` | Initialize new project |
| `uva` | `uv add` | Add dependency |
| `uvr` | `uv run` | Run command in project |
| `uvs` | `uv sync` | Sync dependencies |
| `uvp` | `uv pip` | Pip-compatible interface |
| `uvpi` | `uv pip install` | Install package via pip |
| `uvvenv` | `uv venv` | Create virtual environment |

### Poetry (Python)

| Alias | Command | Purpose |
|-------|---------|---------|
| `po` | `poetry` | Poetry CLI |
| `poi` | `poetry install` | Install dependencies |
| `poa` | `poetry add` | Add dependency |
| `por` | `poetry run` | Run command in venv |
| `pos` | `poetry shell` | Activate venv shell |
| `pou` | `poetry update` | Update dependencies |
| `pol` | `poetry lock` | Update lock file |

### Virtual Environment Functions

| Function | Purpose | Shells |
|----------|---------|--------|
| `venv [path]` | Create venv with `uv venv` (default: `.venv`) | All |
| `activate [path]` | Activate venv from `bin/activate` (default: `.venv`) | All |

---

## Tailscale

Conditional on `tailscale` command being available.

| Alias | Command | Purpose |
|-------|---------|---------|
| `ts` | `tailscale` | Tailscale CLI |
| `tss` | `tailscale status` | Show status |
| `tsu` | `sudo tailscale up` | Connect |
| `tsd` | `sudo tailscale down` | Disconnect |
| `tssh` | `tailscale ssh` | SSH via Tailscale |
| `tsip` | `tailscale ip -4` | Show IPv4 address |
| `tsping` | `tailscale ping` | Ping via Tailscale |
| `tsnet` | Tailscale peer table (hostname, IP, connected/disconnected) | Formatted via jq + column |

---

## Systemd (Linux only)

Available on Linux systems only.

| Alias | Command | Purpose |
|-------|---------|---------|
| `sc` | `sudo systemctl` | Control services |
| `scs` | `sudo systemctl status` | Service status |
| `scr` | `sudo systemctl restart` | Restart service |
| `sce` | `sudo systemctl enable --now` | Enable and start service |
| `jfl` | `journalctl -fu` | Follow system journal |

---

## Duplicate File Management

Wrappers around `fdupes` for finding and deleting duplicates.

| Alias | Command | Purpose |
|-------|---------|---------|
| `dup` | `fdupes -r` | Find duplicates recursively |
| `dupsize` | `fdupes -rS` | Find duplicates with size |
| `dupsum` | `fdupes -rm` | Find duplicates with summary |

### Duplicate Deletion Function
| Function | Purpose | Notes |
|----------|---------|-------|
| `dupdel [path]` | Delete duplicate files (keeps one copy) | Confirmation required |

---

## Security & Pentesting

Conditional on profile and installed tools. Disabled on `mac-pro` profile.

| Alias | Command | Purpose | Condition |
|-------|---------|---------|-----------|
| `gobust` | `gobuster dir --wordlist ~/security/wordlists/diccnoext.txt --wildcard --url` | Directory brute force | If gobuster installed |
| `dirsearch` | `python dirsearch.py -w db/dicc.txt -b -u` | Directory search | If dirsearch installed |
| `massdns` | Custom massdns with resolver list | DNS enumeration | If tool exists |
| `server` | `python -m http.server 4445` | Quick HTTP server on :4445 | All non-mac-pro |
| `tunnel` | `ngrok http 4445` | Expose local:4445 to internet | If ngrok installed |
| `fuzz` | `ffuf -w ~/hacking/SecLists/content_discovery_all.txt -mc all -u` | Web fuzzer | If ffuf installed |
| `nm` | `nmap -sC -sV -oN nmap` | Network scanner | If nmap installed |

---

## Lazygit / Lazydocker

| Alias | Command | Purpose |
|-------|---------|---------|
| `lg` | `lazygit` | Git TUI |
| `ld` | `lazydocker` | Docker TUI |

---

## Utility Functions

### `mkd`

Create directory and cd into it.

```bash
mkd path/to/dir    # mkdir -p + cd in one command
```

---

## Platform-Specific Notes

### Toolbox (Fedora Atomic)

| Alias | Command | Purpose | Notes |
|-------|---------|---------|-------|
| `tbx` | `/usr/bin/toolbox run zsh` | Enter toolbox with zsh | Fedora Atomic only |
| `fedora()` | Toolbox container manager | Enter fedora container | Fedora Atomic only |
| `arch()` | Toolbox container manager | Enter arch-rolling container | Fedora Atomic only |

---

## Shell-Specific Notes

### Zsh-specific Features
- All aliases defined in `dot_zsh/10-aliases.zsh`
- Functions in `dot_zsh/20-functions.zsh`
- Cache helper `_cache_eval` defined in `dot_zshrc.tmpl`
- Supports `(( $+commands[cmd] ))` syntax for checking command availability (no fork)

### Bash-specific Features
- All aliases defined in `dot_bash/10-aliases.bash`
- Uses `command -v` syntax for checking command availability

### Fish-specific Features
- All aliases and functions in `dot_config/private_fish/config.fish.tmpl`
- Functions use `function` keyword (not `alias`)
- Uses `command -q` for checking command availability
- Has `_fish_cache_eval` function for caching (similar to Zsh's `_cache_eval`)
- Lazy-loaded version managers: `pyenv`, `jenv`, `rbenv`

### Nushell-specific Features
- Minimal alias coverage in `dot_config/nushell/config.nu`
- Nushell is primarily a configuration file (themes, keybindings, menus)
- No dedicated shell aliases file yet (focus is on core config)

---

## Machine Profile Detection

Aliases and functions conditionally activate based on `$MACHINE_PROFILE`:

| Profile | OS | Characteristics |
|---------|----|----|
| `mac-pro` | macOS | Work machine (specific branch/email) |
| `mac-personal` | macOS | Personal machine |
| `fedora-desktop` | Linux (Fedora) | Desktop environment |
| `fedora-server` | Linux (Fedora) | Server (SSH config, compact theme) |
| `fedora-atomic` | Linux (Fedora Atomic) | Immutable OS with rpm-ostree |
| `toolbox` | Linux (Fedora container) | Toolbox container environment |
| `arch-desktop` | Linux (Arch) | Arch desktop |
| `arch-server` | Linux (Arch) | Arch server |
| `omarchy` | Linux (Arch-based) | OmArchy desktop flavor |
| `ubuntu-desktop` | Linux (Ubuntu) | Ubuntu desktop |
| `ubuntu-server` | Linux (Ubuntu) | Ubuntu server |
| `debian` | Linux (Debian) | Debian-based |
| `rpi` | Linux (Raspberry Pi) | Raspberry Pi (any OS) |
| `windows` | Windows | Windows (Scoop) |

---

## Environment Variables

Key variables exported in `dot_zsh/00-env.zsh` and `dot_config/private_fish/config.fish.tmpl`:

| Variable | Purpose | Platform-specific |
|----------|---------|---|
| `MACHINE_PROFILE` | Machine profile (see above) | Auto-detected |
| `IS_MACOS`, `IS_LINUX`, `IS_RPI`, `IS_UBUNTU`, `IS_FEDORA`, `IS_ARCH` | Boolean flags for platform | Auto-detected |
| `STARSHIP_CONFIG` | Starship prompt config | Desktop vs SSH-specific |
| `STARSHIP_ICON`, `STARSHIP_ICON_COLOR` | Prompt icon theming | Per-profile |
| `FZF_DEFAULT_OPTS` | FZF colors (Catppuccin Mocha / Snazzy) | Desktop vs server |
| `BAT_THEME` | Syntax highlighting theme | Desktop vs server |
| `LS_COLORS` | Color scheme for `ls` | Desktop vs server |
| `EDITOR` | Default editor | `nvim` or `nano` (RPi) |

---

## Related Files

- Zsh config: `/home/jeromesoyer/github/jsoyer/dotfiles/dot_zsh/10-aliases.zsh`
- Bash config: `/home/jeromesoyer/github/jsoyer/dotfiles/dot_bash/10-aliases.bash`
- Fish config: `/home/jeromesoyer/github/jsoyer/dotfiles/dot_config/private_fish/config.fish.tmpl`
- Nushell config: `/home/jeromesoyer/github/jsoyer/dotfiles/dot_config/nushell/config.nu`
- Zsh env: `/home/jeromesoyer/github/jsoyer/dotfiles/dot_zsh/00-env.zsh`
- Zsh functions: `/home/jeromesoyer/github/jsoyer/dotfiles/dot_zsh/20-functions.zsh`
- Zsh rc template: `/home/jeromesoyer/github/jsoyer/dotfiles/dot_zshrc.tmpl`

---

## Notes

- All package manager wrappers (`breww`, `aptw`, `dnfw`, `pacmanw`, `yayw`, `ostreew`, `scoopw`) track installations in manifest files for reproducible environments.
- FZF-powered functions (`fcd`, `f`, `fv`, `ff`) exclude `.git` directories by default.
- Docker/Podman detection is automatic — if Docker is available, Docker aliases are created; if only Podman, Podman aliases are created.
- SSH wrapper intelligently renames tmux windows and uses Kitty kitten ssh when appropriate.
- All functions follow immutability patterns — they create new state rather than modifying existing state.
- Cache evaluation helpers (`_cache_eval` in Zsh, `_fish_cache_eval` in Fish) regenerate initialization scripts only when tools move or after 24 hours.
