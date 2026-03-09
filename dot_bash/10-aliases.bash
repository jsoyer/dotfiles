#!/usr/bin/env bash
# Aliases configuration

# ============================================================================
# Configuration shortcuts
# ============================================================================
alias bashconfig='nvim ~/.bashrc'

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
alias http='xh'
alias as='aerospace'
alias asr='atuin scripts run'

# Eza (modern ls replacement)
alias ls='eza --color=always --icons'
alias ll='eza -l --color=always --icons --git -a'
alias l='eza -l --icons --git -a'
alias lt='eza --tree --level=2 --long --icons --git'
alias ltree='eza --tree --level=2 --icons --git'
alias zl='eza -lagX --icons --color=always'

# ============================================================================
# System
# ============================================================================
alias cl='clear'
alias bcask='brew cask'

# Toolbox - enter with zsh instead of bash
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
alias iclouddrive='cd ~/Library/Mobile\ Documents/com~apple~CloudDocs/'

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
# Git (Additions)
# ============================================================================
alias gs='git status -s'
alias gsw='git switch'
alias gswc='git switch -c'
alias grs='git restore'
alias grbi='git rebase -i'
alias gcl='git clone'

# ============================================================================
# Docker / Podman
# ============================================================================
alias dco='docker compose'
alias dps='docker ps'
alias dpa='docker ps -a'
alias dl='docker ps -l -q'
alias dx='docker exec -it'

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
  local ssh_cmd=(command ssh)
  [[ "$TERM" == "xterm-kitty" ]] && ssh_cmd=(kitten ssh)

  local host=""
  for arg in "$@"; do
    [[ "$arg" == -* ]] && continue
    if [[ "$arg" == *@* ]]; then
      host="${arg##*@}"
    else
      host="$arg"
    fi
    break
  done
  host="${host%%.*}"

  if [[ -n "$TMUX" ]] && [[ -n "$host" ]]; then
    tmux rename-window "$host"
    "${ssh_cmd[@]}" "$@"
    tmux rename-window "bash"
  else
    "${ssh_cmd[@]}" "$@"
  fi
}

# ============================================================================
# Homebrew (via breww wrapper)
# ============================================================================
alias b='breww'
alias bi='breww install'
alias bu='breww update'
alias bup='breww upgrade'
alias bcu='breww cu -a' # Uses brew-cask-upgrade
alias bs='breww search'
alias bl='breww list'
alias bun='breww uninstall'
alias bci='breww cleanup'
alias binfo='breww info'
alias bd='breww doctor'

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

# Chezmoi apply/update with verbose mode
ca() {
  chezmoi apply -v "$@"
}

cu() {
  chezmoi update -v "$@"
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
alias ports='lsof -iTCP -sTCP:LISTEN -n -P'
alias myip='curl -s ifconfig.me && echo'
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

# Chezmoi update + package updates
cup() {
  cu "$@"

  local os
  case "${OSTYPE:-}" in
    darwin*)  os="darwin" ;;
    linux*)   os="linux" ;;
    msys*|cygwin*|mingw*) os="windows" ;;
    *) os="$(uname -s | tr '[:upper:]' '[:lower:]')" ;;
  esac

  case "$os" in
    darwin)
      eval "$(brew shellenv)"
      echo "Updating Homebrew..."
      brew update
      echo "Upgrading packages..."
      if [[ "$MACHINE_PROFILE" == "mac-pro" ]]; then
        brew upgrade
      else
        brew upgrade --greedy
      fi
      brew cleanup
      echo "Updating App Store apps..."
      if command -v mas &> /dev/null; then
        mas upgrade
      else
        echo "  mas-cli not installed (run: brew install mas)"
      fi
      ;;
    linux)
      if [[ "$(uname -m)" == *"rpi"* ]] || grep -qi rpi /proc/version 2>/dev/null; then
        echo "🐍 Updating apt packages..."
        sudo apt update && sudo apt dist-upgrade -y && sudo apt autoremove -y
      elif command -v dnf &>/dev/null; then
        if command -v rpm-ostree &>/dev/null; then
          echo "🐧 Updating Fedora Atomic..."
          sudo rpm-ostree upgrade
        else
          echo "🐧 Updating Fedora packages..."
          sudo dnf upgrade -y
        fi
      fi
      ;;
    windows)
      echo "🪣 Updating Scoop packages..."
      scoop update
      scoop update --all
      ;;
  esac

  # Docker/Podman maintenance
  if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
    CONTAINER_RUNTIME="docker"
    EMOJI="🐳"
  elif command -v podman &>/dev/null && podman info &>/dev/null 2>&1; then
    CONTAINER_RUNTIME="podman"
    EMOJI="🦭"
  fi

  if [ -n "$CONTAINER_RUNTIME" ]; then
    echo "$EMOJI Running container maintenance..."
    $CONTAINER_RUNTIME ps
    
    find "$HOME" -name "docker-compose.yml" -not -path "*/.*" 2>/dev/null | while read -r compose_file; do
      project_dir=$(dirname "$compose_file")
      project_name=$(basename "$project_dir")
      
      if $CONTAINER_RUNTIME compose -f "$compose_file" ps --services --filter "status=running" 2>/dev/null | grep -q .; then
        echo "  → Updating $project_name"
        pull_output=$($CONTAINER_RUNTIME compose -f "$compose_file" pull 2>&1)
        
        if echo "$pull_output" | grep -qE "(Pulling|Downloading|Extracting|Status: Downloaded)"; then
          echo "  🔄 New images found, restarting containers..."
          $CONTAINER_RUNTIME compose -f "$compose_file" up -d
        else
          echo "  ✅ No new images, containers up to date"
        fi
      fi
    done
    
    $CONTAINER_RUNTIME image prune -a -f
    echo "✨ Container maintenance complete!"
  fi

  echo "✅ Update complete!"
}

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
# Claude Code
# ============================================================================
alias cco='claude --model opus'
alias ccs='claude --model sonnet'
alias cch='claude --model haiku'

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
