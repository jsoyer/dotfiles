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
# Docker
# ============================================================================
alias dco='docker compose'
alias dps='docker ps'
alias dpa='docker ps -a'
alias dl='docker ps -l -q'
alias dx='docker exec -it'

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
# Security & Pentesting tools
# ============================================================================
alias gobust='gobuster dir --wordlist ~/security/wordlists/diccnoext.txt --wildcard --url'
alias dirsearch='python dirsearch.py -w db/dicc.txt -b -u'
alias massdns='~/hacking/tools/massdns/bin/massdns -r ~/hacking/tools/massdns/lists/resolvers.txt -t A -o S bf-targets.txt -w livehosts.txt -s 4000'
alias server='python -m http.server 4445'
alias tunnel='ngrok http 4445'
alias fuzz='ffuf -w ~/hacking/SecLists/content_discovery_all.txt -mc all -u'
alias nm='nmap -sC -sV -oN nmap'

# ============================================================================
# SSH wrapper for Kitty kitten ssh
# ============================================================================
ssh() {
  if [[ "$TERM" == "xterm-kitty" ]]; then
    kitten ssh "$@"
  else
    command ssh "$@"
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
# On RPi, use --no-diff to avoid deadlock bug in chezmoi's GitDiffSystem
ca() {
  if [[ "$MACHINE_PROFILE" == "rpi" ]]; then
    chezmoi apply -v --no-diff "$@"
  else
    chezmoi apply -v "$@"
  fi
}

cu() {
  if [[ "$MACHINE_PROFILE" == "rpi" ]]; then
    chezmoi update -v --no-diff "$@"
  else
    chezmoi update -v "$@"
  fi
}

# Chezmoi update + package updates
cup() {
  cu "$@"

  local script_dir="{{ .chezmoi.sourceDir }}/.chezmoiscripts/04-update"
  local os="{{ .chezmoi.os }}"

  case "$os" in
    darwin)
      eval "$(brew shellenv)"
      echo "🍺 Updating Homebrew packages..."
      brew upgrade
      brew cleanup
      brew update
      ;;
    linux)
      if [[ "$(uname -m)" == *"rpi"* ]] || grep -qi rpi /proc/version 2>/dev/null; then
        echo "🐍 Updating apt packages..."
        sudo apt update && sudo apt upgrade -y
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
