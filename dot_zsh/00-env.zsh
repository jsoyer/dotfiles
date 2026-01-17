#!/usr/bin/env zsh
# shellcheck shell=bash
# Environment variables configuration

# ============================================================================
# Platform detection
# ============================================================================
export IS_MACOS=false
export IS_RPI=false
export IS_LINUX=false

case "$(uname -s)" in
  Darwin)
    export IS_MACOS=true
    export PLATFORM="macos"
    ;;
  Linux)
    export IS_LINUX=true
    if [[ -f /proc/device-tree/model ]] && grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
      export IS_RPI=true
      export PLATFORM="rpi"
      # Get RPi model for display
      export RPI_MODEL=$(cat /proc/device-tree/model 2>/dev/null | tr -d '\0')
    else
      export PLATFORM="linux"
    fi
    ;;
  *)
    export PLATFORM="unknown"
    ;;
esac

# ============================================================================
# Locale and language
# ============================================================================
export LANG=en_US.UTF-8

# ============================================================================
# History configuration
# ============================================================================
export HISTFILE="${HOME}/.zsh_history"
export HISTSIZE=50000
export SAVEHIST=50000
setopt EXTENDED_HISTORY          # Write timestamp to history
setopt HIST_EXPIRE_DUPS_FIRST    # Expire duplicates first
setopt HIST_IGNORE_DUPS          # Don't record duplicate entries
setopt HIST_IGNORE_SPACE         # Don't record commands starting with space
setopt HIST_VERIFY               # Show command before executing from history
setopt SHARE_HISTORY             # Share history between sessions

# ============================================================================
# Editor configuration
# ============================================================================
if [[ -n ${SSH_CONNECTION} ]]; then
  export EDITOR='nvim'
else
  export EDITOR='nvim'
fi

# ============================================================================
# Docker configuration
# ============================================================================
export DOCKER_CONFIG="${DOCKER_CONFIG:-${HOME}/.docker}"

# ============================================================================
# Homebrew (macOS only)
# ============================================================================
#export HOMEBREW_CASK_OPTS="--appdir=/Users/jsoyer/Applications"

# ============================================================================
# Kubernetes
# ============================================================================
export KUBECONFIG="${HOME}/.kube/config"

# ============================================================================
# Platform-specific theming
# ============================================================================
if [[ "${IS_RPI}" == "true" ]]; then
  # -------------------------------------------------------------------------
  # Raspberry Pi: Gruvbox Dark theme
  # -------------------------------------------------------------------------
  export STARSHIP_CONFIG="${HOME}/.config/starship/starship-rpi.toml"
  
  # FZF theme (Gruvbox Dark)
  export FZF_DEFAULT_OPTS=" \
--color=bg+:#3c3836,bg:#282828,spinner:#fb4934,hl:#83a598 \
--color=fg:#ebdbb2,header:#83a598,info:#d3869b,pointer:#fb4934 \
--color=marker:#fe8019,fg+:#ebdbb2,prompt:#d3869b,hl+:#83a598"
  
  # Vivid colors (Gruvbox Dark)
  if command -v vivid >/dev/null 2>&1; then
    export LS_COLORS="$(vivid generate gruvbox-dark)"
  fi
  
  # Bat theme (Gruvbox Dark)
  export BAT_THEME="gruvbox-dark"
  
  # Tmux alias to use RPi config
  alias tmux='tmux -f ~/.config/tmux/tmux-rpi.conf'

else
  # -------------------------------------------------------------------------
  # macOS / Other: Catppuccin Mocha theme
  # -------------------------------------------------------------------------
  export STARSHIP_CONFIG="${HOME}/.config/starship/starship.toml"
  
  # FZF theme (Catppuccin Mocha)
  export FZF_DEFAULT_OPTS=" \
--color=bg+:#313244,bg:#1e1e2e,spinner:#f5e0dc,hl:#f38ba8 \
--color=fg:#cdd6f4,header:#f38ba8,info:#cba6f7,pointer:#f5e0dc \
--color=marker:#f5e0dc,fg+:#cdd6f4,prompt:#cba6f7,hl+:#f38ba8"
  
  # Vivid colors (Catppuccin Mocha)
  if command -v vivid >/dev/null 2>&1; then
    export LS_COLORS="$(vivid generate catppuccin-mocha)"
  fi
  
  # Bat theme (Catppuccin Mocha)
  export BAT_THEME="Catppuccin Mocha"
fi

# ============================================================================
# FZF default command (platform-agnostic)
# ============================================================================
if command -v fd >/dev/null 2>&1; then
  export FZF_DEFAULT_COMMAND='fd --type f --hidden --follow --exclude .git'
elif command -v fdfind >/dev/null 2>&1; then
  # Debian/Ubuntu uses fdfind
  export FZF_DEFAULT_COMMAND='fdfind --type f --hidden --follow --exclude .git'
fi
