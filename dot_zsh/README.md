# Zsh Configuration Documentation

> Modern, modular Zsh configuration with Oh-My-Zsh and Starship prompt

## Architecture

```
~/.zshrc                    # Main entry point (Oh-My-Zsh + modular load + Starship)
~/.zsh/                     # Modular configuration directory
  ├── 00-env.zsh            # Environment variables, platform detection, theming
  ├── 01-path.zsh           # PATH management with lazy loading
  ├── 02-completions.zsh    # Completion system (compinit cached 24h)
  ├── 10-aliases.zsh        # Command aliases & shortcuts
  ├── 20-functions.zsh      # Custom shell functions (fcd, fv, cx, ff...)
  ├── 30-keybindings.zsh    # Keyboard shortcuts (vi mode, autosuggestions)
  ├── 99-integrations.zsh   # External tool integrations (FZF, Atuin, Direnv...)
  └── secrets.zsh           # API keys via 1Password (gitignored, machine-local)
```

## Oh-My-Zsh Plugins

8 active plugins (loaded from `~/.zshrc`):

| Plugin | Purpose |
|--------|---------|
| `colored-man-pages` | Colorful man pages |
| `copybuffer` | Copy command line to clipboard (Ctrl+O) |
| `copyfile` | Copy file contents to clipboard |
| `extract` | Universal archive extraction |
| `encode64` | Base64 encoding/decoding |
| `sudo` | ESC ESC to prepend sudo |
| `ssh-agent` | SSH agent management |
| `kubectl` + `helm` | Kubernetes/Helm completion (macOS only) |

## Platform-Aware Theming

Detected via `uname` + `/proc/device-tree/model`:

| Platform | Theme | Starship Config |
|----------|-------|-----------------|
| macOS | Catppuccin Mocha | `starship-desktop.toml` |
| Raspberry Pi / Linux | Snazzy | `starship-ssh.toml` |

FZF colors, Vivid LS_COLORS, and Bat theme all switch automatically.

## Modern CLI Replacements

| Command | Tool | Description |
|---------|------|-------------|
| `ls`, `ll`, `l`, `lt` | eza | Modern ls with icons + git status |
| `cat` | bat | Syntax highlighting + git diff |
| `cd` | zoxide (`z`) | Smart cd that learns habits |
| `vim` / `v` | neovim | Modern vim |
| `http` | xh | Fast HTTP client |
| `find` | fd / fdfind | Fast file finder |
| `grep` | ripgrep | Fast grep alternative |
| `top` | btop | Rich system monitor |
| `du` | dust | Intuitive disk usage |
| `df` | duf | Modern df |
| `ps` | procs | Modern ps |

## Key Aliases

### Chezmoi
```zsh
ca    # chezmoi apply -v
cu    # chezmoi update -v
cup   # chezmoi update + system package upgrade (all platforms)
c     # chezmoi
cs    # chezmoi status
ccd   # chezmoi cd
```

### Git
```zsh
gst   # git status
ga    # git add -p
gc    # git commit -m
gp    # git push origin HEAD
glog  # pretty graph log
gco   # git checkout
gsw   # git switch
```

### Python / uv
```zsh
uvr   # uv run
uva   # uv add
uvs   # uv sync
venv  # uv venv .venv
activate  # source .venv/bin/activate
```

### Docker / Kubernetes
```zsh
dco   # docker compose
k     # kubectl
kl    # kubectl logs -f
ke    # kubectl exec -it
kc    # kubectx
kns   # kubens
```

### Claude Code
```zsh
cco   # claude --model opus
ccs   # claude --model sonnet
cch   # claude --model haiku
```

### Jujutsu
```zsh
j     # jj
js    # jj st
jl    # jj log -r 'all()'
jp    # jj git push
```

## Custom Functions

| Function | Description |
|----------|-------------|
| `cx <dir>` | cd + auto-list |
| `fcd` | FZF directory picker |
| `fv` | FZF file picker → open in nvim |
| `f` | FZF file picker → copy path to clipboard |
| `ff` | FZF Aerospace window picker (macOS only) |
| `venv [dir]` | Create uv virtualenv |
| `activate [dir]` | Activate virtualenv |
| `mkd <dir>` | mkdir -p + cd |
| `dupdel` | fdupes interactive dedup with confirmation |
| `cup` | chezmoi update + system packages + containers |

## Integrations (99-integrations.zsh)

Loaded last, all guarded with `command -v` checks:

- **FZF** — key bindings + completion (Catppuccin/Snazzy themed)
- **Zoxide** — `z` command, replaces cd
- **Atuin** — shell history sync (Ctrl+R)
- **Direnv** — per-directory env vars
- **Starship** — prompt (cached via `_cache_eval`)
- **OrbStack** — Docker/K8s for macOS (if installed)
- **Nix** — package manager (if installed)
- **TheFuck** — lazy-loaded command correction

## Secrets (secrets.zsh)

Loaded from 1Password at shell login. Gitignored, never tracked.

```zsh
GITHUB_TOKEN              # GitHub API + Homebrew rate limit
HOMEBREW_GITHUB_API_TOKEN # (= GITHUB_TOKEN)
NOTION_API_KEY            # Notion MCP server
LINEAR_ACCESS_TOKEN       # Linear MCP server
```

Auto-signs in via `op signin` if session expired. Falls back silently if `op` not available (Mac Pro, machines without 1Password).

## Performance Optimizations

- **Completion cache** — `compinit` full check only once per 24h (`compinit -C` otherwise)
- **`_cache_eval`** — caches `starship init`, `zoxide init` etc. for 24h
- **Lazy loading** — `pyenv` and `jenv` loaded only on first call (~200ms saved)
- **AWS completion** — `bashcompinit` only loaded if `aws_completer` is present (~30ms saved)

## Troubleshooting

```zsh
# Profile startup time
time zsh -i -c exit

# Rebuild completion cache
rm ~/.zcompdump* && compinit

# Reload config
source ~/.zshrc

# Check FZF colors
echo $FZF_DEFAULT_OPTS

# Check LS_COLORS
echo $LS_COLORS | tr ':' '\n' | head
```

---

**Last updated:** 2026-03-09
**Configuration:** Oh-My-Zsh + Starship + modular ~/.zsh/
**Theme:** Catppuccin Mocha (macOS) / Snazzy (Linux/RPi)
