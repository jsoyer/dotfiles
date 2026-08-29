#!/usr/bin/env sh
# Shared aliases and functions - sourced by bash and zsh
# Shell-specific aliases go in dot_zsh/10-aliases.zsh or dot_bash/10-aliases.bash

# ============================================================================
# Modern CLI tool replacements
# ============================================================================
# Neovim with raised file descriptor limit
nvim() {
  ulimit -n 4096
  command nvim "$@"
}
alias vim='nvim'
alias v='nvim'
alias la='tree'
alias cat='bat'
alias catp='bat --plain'
alias http='xh'
alias asr='atuin scripts run'
[[ "${IS_MACOS:-false}" == "true" ]] && alias as='aerospace'

# Eza (modern ls replacement)
alias ls='eza --color=always --icons=auto'
alias ll='eza -l --color=always --icons=auto --git -a'
alias l='eza -l --icons=auto --git -a'
alias lt='eza --tree --level=2 --long --icons=auto --git'
alias ltree='eza --tree --level=2 --icons=auto --git'
alias zl='eza -lagX --icons=auto --color=always'

# ============================================================================
# System
# ============================================================================
alias cl='clear'

# Toolbox - enter with zsh
alias tbx='/usr/bin/toolbox run zsh'

# Toolbox shortcuts (Fedora Atomic host only, not inside a toolbox)
if command -v rpm-ostree &>/dev/null && [[ ! -f /.toolboxenv ]] && [[ -z "$TOOLBOX_PATH" ]]; then
    _tbx_enter() {
        local name="$1"
        if toolbox run --container "$name" sh -c 'command -v zsh' &>/dev/null 2>&1; then
            toolbox run --container "$name" zsh
        else
            toolbox enter "$name"
        fi
    }
    fedora() { _tbx_enter "fedora-$(rpm -E %fedora)"; }
    arch() { _tbx_enter arch-rolling; }
fi

# ============================================================================
# Navigation
# ============================================================================
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias .....='cd ../../../..'
alias ......='cd ../../../../..'
[[ "${IS_MACOS:-false}" == "true" ]] && alias iclouddrive='cd ~/Library/Mobile\ Documents/com~apple~CloudDocs/'

# ============================================================================
# Git
# ============================================================================
alias gc='git commit -m'
alias gca='git commit -a -m'
alias gp='git push origin HEAD'
alias gpu='git pull origin'
alias gst='git status'
alias glog="git log --graph --topo-order --pretty='%w(100,0,6)%C(yellow)%h%C(bold)%C(black)%d %C(cyan)%ar %C(green)%an%n%C(bold)%C(white)%s %N' --abbrev-commit"
alias gdiff='git diff'
alias gco='git checkout'
alias gb='git branch'
alias gba='git branch -a'
alias gadd='git add'
alias ga='git add -p'
alias gcoall='git checkout -- .'
alias gr='git remote'
alias gre='git reset'

# ============================================================================
# Docker / Podman (legacy — see conditional dc*/dps aliases below)
# ============================================================================
alias dco='docker compose'
alias dl='docker ps -l -q'

# docker-compose -> docker compose (function for compatibility)
docker-compose() {
    docker compose "$@"
}

# Podman Compose
podman-compose() {
    podman compose "$@"
}

# ============================================================================
# Kubernetes
# ============================================================================
alias k='kubectl'
alias ka='kubectl apply -f'
alias kg='kubectl get'
alias kd='kubectl describe'
alias kdel='kubectl delete'
alias kl='kubectl logs -f'
alias kgpo='kubectl get pod'
alias kgd='kubectl get deployments'
alias kc='kubectx'
alias kns='kubens'
alias ke='kubectl exec -it'
alias kcns='kubectl config set-context --current --namespace'

# ============================================================================
# Security & Pentesting tools (not on mac-pro)
# ============================================================================
if [[ "$MACHINE_PROFILE" != "mac-pro" ]]; then
  command -v gobuster &>/dev/null && alias gobust='gobuster dir --wordlist ~/security/wordlists/diccnoext.txt --wildcard --url'
  command -v dirsearch &>/dev/null && alias dirsearch='python dirsearch.py -w db/dicc.txt -b -u'
  [[ -x ~/hacking/tools/massdns/bin/massdns ]] && alias massdns='~/hacking/tools/massdns/bin/massdns -r ~/hacking/tools/massdns/lists/resolvers.txt -t A -o S bf-targets.txt -w livehosts.txt -s 4000'
  alias server='python -m http.server 4445'
  command -v ngrok &>/dev/null && alias tunnel='ngrok http 4445'
  command -v ffuf &>/dev/null && alias fuzz='ffuf -w ~/hacking/SecLists/content_discovery_all.txt -mc all -u'
  command -v nmap &>/dev/null && alias nm='nmap -sC -sV -oN nmap'
fi

# ============================================================================
# SSH wrapper for tmux window naming + Kitty kitten ssh
# ============================================================================
ssh() {
  # Use kitten ssh when running inside Kitty
  local ssh_cmd=(command ssh)
  [[ "$TERM" == "xterm-kitty" ]] && ssh_cmd=(kitten ssh)

  # Extract hostname from ssh arguments
  local host=""
  for arg in "$@"; do
    # Skip flags
    [[ "$arg" == -* ]] && continue
    # First non-flag argument is the destination
    if [[ "$arg" == *@* ]]; then
      host="${arg##*@}"  # user@host -> host
    else
      host="$arg"
    fi
    break
  done

  # Remove domain if present (user@host.domain -> host)
  host="${host%%.*}"

  # Rename tmux window if in tmux
  if [[ -n "$TMUX" ]] && [[ -n "$host" ]]; then
    tmux rename-window "$host"
    "${ssh_cmd[@]}" "$@"
    # Restore window name after SSH exits
    tmux rename-window "${SHELL_NAME:-sh}"
  else
    "${ssh_cmd[@]}" "$@"
  fi
}

# Sync local SSH config to 1Password (macOS only)
if [[ "$OSTYPE" == darwin* ]] && command -v op &>/dev/null; then
  alias ssh-sync='op document edit --vault "Private" "SSH Config" ~/.ssh/config && echo "SSH config synced to 1Password"'
fi
alias sshpw='ssh -o PreferredAuthentications=password'

# ============================================================================
# Homebrew (via breww wrapper) + Mac App Store (via masw)
# ============================================================================
alias b='breww'
if [[ "$OSTYPE" == darwin* ]]; then
    mas() { command masw "$@"; }
fi
# Mac Pro is a non-admin account: raw `brew upgrade` must still hit breww
# so Brewfile_cu_skip_mac-pro is applied. subprocess in breww calls the
# real brew binary via PATH, so this does not recurse.
if [[ "${MACHINE_PROFILE:-}" == "mac-pro" ]]; then
    brew() { command breww "$@"; }
fi
alias bi='breww install'
alias bu='breww update'
alias bup='breww upgrade'
alias bcu='breww cu -a' # Uses brew-cask-upgrade
alias bs='breww search'
alias bl='breww list'
alias brm='breww uninstall'
alias bci='breww cleanup'
# Aggressive reclaim: every cached download + the download cache itself.
# `bci` (breww cleanup) keeps Homebrew's 120-day retention; this one does not.
alias bcp='brew cleanup --prune=all -s'
alias bcpn='brew cleanup --prune=all -s --dry-run'  # what would be freed
alias binfo='breww info'
alias bdo='breww doctor'
alias bdep='brew-deprecated'

# ============================================================================
# Package manager wrappers
# ============================================================================
if [[ "${IS_LINUX:-false}" == "true" ]] && [[ "${MACHINE_PROFILE:-}" != fedora* ]]; then
  apt() { command aptw "$@"; }
fi

if [[ "${IS_FEDORA:-false}" == "true" ]] && [[ "${MACHINE_PROFILE:-}" != "fedora-atomic" ]]; then
  dnf() { command dnfw "$@"; }
  yum() { command dnfw "$@"; }
fi

# Arch Linux package manager wrappers
if [[ "${MACHINE_PROFILE:-}" == arch-desktop || "${MACHINE_PROFILE:-}" == arch-server || "${MACHINE_PROFILE:-}" == "omarchy" ]]; then
    pacman() { pacmanw "$@"; }
fi

if [[ "${MACHINE_PROFILE:-}" == arch-desktop || "${MACHINE_PROFILE:-}" == "omarchy" ]]; then
    yay() { yayw "$@"; }
fi

# Ubuntu snap wrapper
if [[ "${IS_UBUNTU:-false}" == "true" ]]; then
    snap() { command snapw "$@"; }
fi

# Fedora Atomic wrapper
if [[ "${MACHINE_PROFILE:-}" == fedora-atomic ]]; then
    function rpm-ostree() { ostreew "$@"; }
fi

# ============================================================================
# Git (Additions)
# ============================================================================
alias gs='git status -s'
alias gsw='git switch'
alias gswc='git switch -c'
alias grs='git restore'
alias grbi='git rebase -i'
alias gcl='git clone'

# ============================================================================
# Chezmoi
# ============================================================================
alias c='chezmoi'
alias cdiff='chezmoi diff'
alias cedit='chezmoi edit'
alias cadd='chezmoi add'
alias creadd='chezmoi re-add'
alias cs='chezmoi status'
alias ccd='chezmoi cd'

# Auto-update monitoring
alias cmstatus='jq . ~/.cache/chezmoi-autoupdate/status.json 2>/dev/null || echo "No status yet"'
alias cmlog='cat ~/.cache/chezmoi-autoupdate/last-run.log 2>/dev/null || echo "No logs yet"'
alias cmdiff='chezmoi diff | delta 2>/dev/null || chezmoi diff'
alias cmchangelog='git -C ~/.local/share/chezmoi log --oneline -20'

# Chezmoi apply/update with verbose mode
ca() {
  chezmoi apply -v "$@"
}

cu() {
  chezmoi update -v "$@"
}

# Chezmoi purge (remove chezmoi source + config, keep deployed files)
cpurge() {
  echo "WARNING: This will remove chezmoi source directory and config."
  echo "  - Deletes: ~/.local/share/chezmoi (source repo)"
  echo "  - Deletes: ~/.config/chezmoi/chezmoi.toml (config)"
  echo "  - Keeps:   All deployed dotfiles in your home directory"
  echo ""
  echo -n "Are you sure? (y/N) "
  read -r reply
  if [[ "$reply" =~ ^[Yy]$ ]]; then
    chezmoi purge --force
    echo "chezmoi purged."
  else
    echo "Aborted."
  fi
}

# Chezmoi destroy (purge + remove ALL managed files)
cdestroy() {
  echo "DANGER: This will remove chezmoi AND all managed dotfiles!"
  echo "  - Deletes: ~/.local/share/chezmoi (source repo)"
  echo "  - Deletes: ~/.config/chezmoi/chezmoi.toml (config)"
  echo "  - Deletes: ALL files managed by chezmoi in your home"
  echo ""
  echo -n "Type 'destroy' to confirm: "
  read -r reply
  if [[ "$reply" == "destroy" ]]; then
    chezmoi destroy --force
    echo "chezmoi destroyed. All managed files removed."
  else
    echo "Aborted."
  fi
}

# ============================================================================
# Claude Code
# ============================================================================
alias cc='claude --dangerously-skip-permissions'
alias ccc='claude --dangerously-skip-permissions -c'
alias cco='claude --model opus'
alias ccs='claude --model sonnet'
alias cch='claude --model haiku'

# AI Context Manager
if command -v aictx &>/dev/null; then
  # aictx is the binary name now
  alias cctx='aictx'  # compat alias
fi

# ============================================================================
# fdupes (duplicate file finder)
# ============================================================================
alias dup='fdupes -r'
alias dupsize='fdupes -rS'
alias dupsum='fdupes -rm'
dupdel() {
  echo "WARNING: this will DELETE duplicate files (keeping one copy) in: ${*:-.}"
  echo -n "Continue? (y/N) "
  read -r reply
  if [[ "$reply" =~ ^[Yy]$ ]]; then
    fdupes -rdN "$@"
  else
    echo "Aborted."
  fi
}

# ============================================================================
# Tmux
# ============================================================================
alias t='tmux'
alias ta='tmux attach -t'
alias tl='tmux list-sessions'
alias tk='tmux kill-session -t'
alias tns='tmux new-session -s'

# ============================================================================
# lazygit / lazydocker
# ============================================================================
alias lg='lazygit'
alias ld='lazydocker'

# ============================================================================
# Disk / System
# ============================================================================
if command -v dust &>/dev/null; then
  alias du='dust'
fi
if command -v duf &>/dev/null; then
  alias df='duf'
fi
if command -v btop &>/dev/null; then
  alias top='btop'
fi
if command -v procs &>/dev/null; then
  alias ps='procs'
fi
alias path='echo "$PATH" | tr ":" "\n"'

# ============================================================================
# Markdown (glow)
# ============================================================================
if command -v glow &>/dev/null; then
  alias md='glow'
fi

# ============================================================================
# Search (ripgrep / fd)
# ============================================================================
alias rgf='rg --files-with-matches'
alias rgi='rg --ignore-case'
alias fdf='fd --type f'
alias fdd='fd --type d'

# ============================================================================
# Python (uv / poetry / venv)
# ============================================================================
# uv
alias uvi='uv init'
alias uva='uv add'
alias uvr='uv run'
alias uvs='uv sync'
alias uvp='uv pip'
alias uvpi='uv pip install'
alias uvvenv='uv venv'

# poetry
alias po='poetry'
alias poi='poetry install'
alias poa='poetry add'
alias por='poetry run'
alias pos='poetry shell'
alias pou='poetry update'
alias pol='poetry lock'

# venv shortcuts
venv() {
  uv venv "${1:-.venv}"
}
activate() {
  local dir="${1:-.venv}"
  if [[ -f "$dir/bin/activate" ]]; then
    source "$dir/bin/activate"
  else
    echo "No virtualenv found at $dir/bin/activate"
    return 1
  fi
}

# ============================================================================
# Misc
# ============================================================================
mkd() {
  mkdir -p "$@" && cd "${@: -1}" || return
}

sysup() {
  local os
  case "$OSTYPE" in
    darwin*) os="darwin" ;;
    linux*)  os="linux" ;;
    cygwin*|msys*|mingw*) os="windows" ;;
    *) return ;;
  esac

  case "$os" in
    darwin)
      bup
      bcu
      if command -v mas &>/dev/null; then
        echo "📱 Updating App Store apps..."
        mas upgrade
      fi
      # bup/bcu upgrade but never reclaim: do it explicitly. See the Linux
      # branch below for what --prune=all -s actually removes.
      if command -v brew &>/dev/null; then
        echo "🍺 Cleaning up Homebrew cache..."
        brew cleanup --prune=all -s
      fi
      echo "🐚 Updating oh-my-zsh..."
      update-omz
      # The AI CLIs update on macOS too — this call only existed in the
      # Linux branch, so Macs never updated any of them through sysup.
      update-ai
      _update_herdr_if_present
      ;;
    linux)
      case "${MACHINE_PROFILE:-}" in
        rpi|ubuntu-desktop|ubuntu-server|debian)
          echo "📦 Updating apt packages..."
          sudo apt-get update && sudo apt-get dist-upgrade -y && sudo apt-get autoremove -y
          ;;
        arch-desktop|arch-server|omarchy)
          echo "📦 Updating pacman packages..."
          sudo pacman -Syu --noconfirm
          if command -v yay &>/dev/null; then
            echo "📦 Updating AUR packages..."
            yay -Sua --noconfirm
          fi
          ;;
        fedora-desktop|fedora-server|toolbox)
          echo "📦 Updating dnf packages..."
          sudo dnf upgrade --refresh -y
          ;;
        fedora-atomic)
          echo "🔒 Updating Fedora Atomic..."
          rpm-ostree upgrade
          ;;
      esac

      if command -v flatpak &>/dev/null; then
        echo "📦 Updating Flatpak apps..."
        # Split by scope. A bare `flatpak update` also targets system-scope
        # installs, and polkit refuses a non-interactive deploy for a normal
        # user: "Flatpak system operation Deploy not allowed for user", which
        # then makes the whole command exit non-zero.
        flatpak update --user -y || true
        if flatpak list --system --columns=application 2>/dev/null | grep -q .; then
          sudo flatpak update --system -y || true
        fi
      fi

      if command -v brew &>/dev/null; then
        eval "$(brew shellenv)"
        echo "🍺 Updating Linuxbrew packages..."
        brew update && brew upgrade
        # --prune=all removes ALL cached downloads (not just those older than 120
        # days), -s also clears the download cache itself. On a Pi with a small
        # SD card this is the difference between a few hundred MB and a few GB.
        brew cleanup --prune=all -s
      fi

      echo "🐚 Updating oh-my-zsh..."
      update-omz
      update-ai
      _update_herdr_if_present
      ;;
    windows)
      echo "🪣 Updating Scoop packages..."
      scoop update --all
      ;;
  esac
}

# Update CLI AI tools (claude-code, copilot-cli, codex)
# A CLI whose binary resolves under the brew prefix is brew-managed (macOS
# casks: claude-code, copilot-cli, cursor-cli, grok-build…): bup/bcu already
# updates it, and running its own updater would install a second copy that
# fights the cask — the pi/qwen duplicate disease.
_ai_brew_owned() {
  local t bp
  t="$(readlink -f "$(command -v "$1" 2>/dev/null)" 2>/dev/null)" || return 1
  bp="$(brew --prefix 2>/dev/null)" || return 1
  [[ -n "$bp" && "$t" == "$bp"/* ]]
}

# oh-my-zsh and its custom plugins are chezmoi git-repo externals refreshed
# only every 168h — pull them now so sysup means "everything is current".
update-omz() {
  local d
  for d in "$HOME/.oh-my-zsh" \
           "$HOME/.oh-my-zsh/custom/plugins/zsh-autosuggestions" \
           "$HOME/.oh-my-zsh/custom/plugins/zsh-syntax-highlighting"; do
    [[ -d "$d/.git" ]] || continue
    git -C "$d" pull --ff-only -q 2>/dev/null || true
  done
}

update-ai() {
  echo "🤖 Updating CLI AI tools..."
  if command -v claude &>/dev/null; then
    if _ai_brew_owned claude; then
      echo "  🤖 Claude Code: brew-managed — bup handles it"
    else
      echo "  🤖 Updating Claude Code..."
      claude update 2>/dev/null || true
    fi
  fi
  # The binary is `copilot` since the standalone CLI; older installs shipped
  # `copilot-cli`. Probing only the old name silently skipped it everywhere.
  if command -v copilot &>/dev/null || command -v copilot-cli &>/dev/null; then
    if _ai_brew_owned copilot || _ai_brew_owned copilot-cli; then
      echo "  🤖 Copilot CLI: brew-managed — bup handles it"
    else
      echo "  🤖 Updating Copilot CLI..."
      curl -fsSL https://gh.io/copilot-install | bash 2>/dev/null || true
    fi
  fi
  if command -v codex &>/dev/null; then
    if _ai_brew_owned codex; then
      echo "  🤖 Codex CLI: brew-managed — bup handles it"
    else
      echo "  🤖 Updating Codex CLI..."
      codex update 2>/dev/null || true
    fi
  fi
  # Grok: NEVER probe `agent` on PATH — that name is owned by cursor-agent
  # (it has flip-flopped between the two; it caused the cursor-worker
  # crash-loop). The Grok CLI home is authoritative.
  if [[ -x "$HOME/.grok/bin/agent" ]]; then
    echo "  🤖 Updating Grok CLI..."
    "$HOME/.grok/bin/agent" update 2>/dev/null || true
  fi
  # cursor-agent: through our updater, which restarts the worker, watches for
  # a crash loop and prunes old versions — not the raw `cursor-agent update`.
  # Probe the BINARY too: chezmoi deploys the update-cursor-agent script on
  # every machine, including ones (Pis, Macs) where cursor-agent itself is not
  # installed — without this, every sysup there printed a confusing error.
  if command -v cursor-agent &>/dev/null && command -v update-cursor-agent &>/dev/null; then
    if _ai_brew_owned cursor-agent; then
      echo "  🤖 cursor-agent: brew-managed — bup handles it"
    else
      echo "  🤖 Updating cursor-agent..."
      update-cursor-agent || true
    fi
  fi
  if command -v pi &>/dev/null && ! _ai_brew_owned pi; then
    echo "  🤖 Updating pi (pi.dev) + extensions..."
    pi update --all 2>/dev/null || true
  fi
  # omp (omp.sh): official one-liner, never the Homebrew tap. A brew copy
  # is uninstalled then replaced so sysup actually switches channels.
  if command -v omp &>/dev/null; then
    if _ai_brew_owned omp; then
      echo "  🤖 omp: Homebrew copy — migrating to https://omp.sh/install"
      brew uninstall --force omp 2>/dev/null || true
      curl -fsSL https://omp.sh/install | sh 2>/dev/null || true
    else
      echo "  🤖 Updating omp..."
      omp update 2>/dev/null || curl -fsSL https://omp.sh/install | sh 2>/dev/null || true
    fi
  fi
}

_update_herdr_if_present() {
  if command -v herdr &>/dev/null && command -v update-herdr &>/dev/null; then
    echo "📺 Updating herdr..."
    update-herdr || true
  fi
}

# Chezmoi update + package updates
cup() {
  cu "$@"
  sysup
  dcua "$HOME"
  echo "✅ Update complete!"
}

# ============================================================================
# Docker / Podman Compose
# ============================================================================
if command -v docker &>/dev/null; then
  alias dps='docker ps --format "table {{.Names}}\t{{.ID}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}"'
  alias dpsa='docker container ls -a --format "table {{.Names}}\t{{.ID}}\t{{.State}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}"'
  alias dcpl='docker compose pull'
  alias dcup='docker compose up -d'
  alias dcl='docker compose logs -f'
  alias dcd='docker compose down'
  alias dcr='docker compose restart'
  alias dcp='docker compose ps'
  alias dce='docker compose exec'
  alias dcb='docker compose build'
elif command -v podman &>/dev/null; then
  alias dps='podman ps --format "table {{.Names}}\t{{.ID}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}"'
  alias dpsa='podman container ls -a --format "table {{.Names}}\t{{.ID}}\t{{.State}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}"'
  alias dcpl='podman compose pull'
  alias dcup='podman compose up -d'
  alias dcl='podman compose logs -f'
  alias dcd='podman compose down'
  alias dcr='podman compose restart'
  alias dcp='podman compose ps'
  alias dce='podman compose exec'
  alias dcb='podman compose build'
fi

dcua() {
  local base="${1:-.}"
  local runtime=""

  if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
    runtime="docker"
  elif command -v podman &>/dev/null && podman info &>/dev/null 2>&1; then
    runtime="podman"
  else
    echo "No container runtime found."
    return 1
  fi

  local updated=0
  local compose_file

  for dir in "$base"/*/; do
    if [[ -f "$dir/docker-compose.yml" ]]; then
      compose_file="$dir/docker-compose.yml"
    elif [[ -f "$dir/compose.yml" ]]; then
      compose_file="$dir/compose.yml"
    else
      continue
    fi

    local name="$(basename "$dir")"
    echo "📥 $name"

    # Capture image digests before pull
    local before after
    before=$($runtime compose -f "$compose_file" images -q 2>/dev/null | sort)
    $runtime compose -f "$compose_file" pull --quiet 2>/dev/null
    after=$($runtime compose -f "$compose_file" images -q 2>/dev/null | sort)

    if [[ "$before" != "$after" ]]; then
      echo "  🔄 Updated, restarting..."
      $runtime compose -f "$compose_file" up -d --quiet-pull
      ((updated++)) || true
    else
      echo "  ✅ Up to date"
    fi
  done

  echo "🧹 Pruning dangling images..."
  $runtime image prune -f --filter "dangling=true" 2>/dev/null
  echo "✨ Done. $updated project(s) updated."
}

# ============================================================================
# Systemd (Linux only)
# ============================================================================
if [[ "$OSTYPE" == linux* ]]; then
  alias sc='sudo systemctl'
  alias scs='sudo systemctl status'
  alias scr='sudo systemctl restart'
  alias sce='sudo systemctl enable --now'
  alias jfl='journalctl -fu'
fi

# ============================================================================
# Network utilities
# ============================================================================
if [[ "$OSTYPE" == linux* ]]; then
  alias ports='sudo ss -tlnp'
else
  alias ports='lsof -iTCP -sTCP:LISTEN -n -P'
fi
alias myip='curl -s ifconfig.me'

# ============================================================================
# Tailscale
# ============================================================================
if command -v tailscale &>/dev/null; then
  alias ts='tailscale'
  alias tss='tailscale status'
  alias tsu='sudo tailscale up'
  alias tsd='sudo tailscale down'
  alias tssh='tailscale ssh'
  alias tsip='tailscale ip -4'
  alias tsping='tailscale ping'
  alias tsnet='tailscale status --json | jq -r ".Peer[] | \"\(.HostName)\t\(.TailscaleIPs[0])\t\(if .Online then \"connected\" else \"disconnected\" end)\"" | sort | column -t'
fi

# ============================================================================
# Jujutsu (jj)
# ============================================================================
alias j='jj'
alias js='jj st'
alias jl="jj log -r 'all()'"
alias jd='jj diff'
alias jn='jj new'
alias jui='jjui'
alias jundo='jj undo'
alias jp='jj git push'
alias jf='jj git fetch'

# ============================================================================
# herdr — every Unix machine (official installer, not Homebrew)
# ============================================================================
# No herdr-restart: the server holds your panes.
alias herdr-install='herdr-setup'
alias herdr-status='herdr-setup --status'
alias herdr-update='update-herdr'

# Self-hosted agent stacks (moshi / orca / cursor) — Linux only
# ============================================================================
# Hidden on macOS (especially mac-pro): chezmoi must not surface these names
# in the shell. Installation stays MANUAL on Linux. Details: ~/.local/bin/README.md.

if [[ "$(uname -s)" == "Linux" ]]; then
  alias herdr-logs='journalctl --user -u herdr-update.service -f'

  alias asvc='agentsvc'
  alias asvcs='agentsvc status'
  alias asvcu='agentsvc update'

  alias moshi-install='moshi-setup'
  alias moshi-status='moshi-setup --status'
  alias moshi-update='update-moshi'
  alias moshi-logs='journalctl --user -u moshi-hook.service -f'
  alias moshi-restart='systemctl --user restart moshi-hook.service'

  alias orca-install='orca-setup'
  alias orca-status='orca-setup --status'
  alias orca-update='update-orca'
  alias orca-logs='journalctl -u orca-serve.service -f'
  alias orca-restart='sudo systemctl restart orca-serve.service'

  alias cursor-install='cursor-setup'
  alias cursor-status='cursor-setup --status'
  alias cursor-update='update-cursor-agent'
  alias cursor-logs='journalctl --user -u cursor-worker.service -f'
  alias cursor-restart='systemctl --user restart cursor-worker.service'
fi
