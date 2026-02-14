#!/usr/bin/env bash
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
    if [[ "$(hostname)" == "jsoyer-macOS" ]]; then
      export MACHINE_PROFILE="mac-pro"
      # Mac Pro: install casks in $HOME/Applications
      export HOMEBREW_CASK_OPTS="--appdir=${HOME}/Applications"
    else
      export MACHINE_PROFILE="mac-personal"
    fi
    ;;
  Linux)
    export IS_LINUX=true
    if [[ -f /proc/device-tree/model ]] && grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
      export IS_RPI=true
      export PLATFORM="rpi"
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
# Hostname-based icon for Starship prompt
# ============================================================================
if [[ "${IS_MACOS}" == "true" ]]; then
  export STARSHIP_ICON="⌘"
elif [[ "${IS_RPI}" == "true" ]] || [[ "${IS_LINUX}" == "true" ]]; then
  case "$(hostname)" in
    bbh-network*)
      export STARSHIP_ICON="🌐"
      ;;
    omv-*)
      export STARSHIP_ICON="🐟"
      ;;
    *)
      export STARSHIP_ICON="🍓"
      ;;
  esac
fi

# ============================================================================
# Locale and language
# ============================================================================
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# ============================================================================
# History configuration
# ============================================================================
export HISTFILE="${HOME}/.bash_history"
export HISTSIZE=50000
export HISTFILESIZE=50000
export HISTCONTROL=ignoreboth:erasedups
export HISTIGNORE="ls:cd:exit:clear:history"

# ============================================================================
# Editor configuration
# ============================================================================
export EDITOR='nvim'

# ============================================================================
# Docker configuration
# ============================================================================
export DOCKER_CONFIG="${DOCKER_CONFIG:-${HOME}/.docker}"

# ============================================================================
# Kubernetes
# ============================================================================
export KUBECONFIG="${HOME}/.kube/config"

# ============================================================================
# Platform-specific theming
# ============================================================================
if [[ "${IS_RPI}" == "true" ]] || [[ "${IS_LINUX}" == "true" && "${IS_MACOS}" == "false" ]]; then
  # Raspberry Pi / Linux: Snazzy theme
  export STARSHIP_CONFIG="${HOME}/.config/starship/starship-rpi.toml"

  # FZF theme (Snazzy)
  export FZF_DEFAULT_OPTS=" \
--color=bg+:#3a3d4d,bg:#282a36,spinner:#ff5c57,hl:#57c7ff \
--color=fg:#eff0eb,header:#57c7ff,info:#ff6ac1,pointer:#ff5c57 \
--color=marker:#f3f99d,fg+:#eff0eb,prompt:#ff6ac1,hl+:#57c7ff"

  # Vivid colors (Snazzy)
  if command -v vivid >/dev/null 2>&1; then
    export LS_COLORS="$(vivid generate snazzy)"
  fi

  # Bat theme
  export BAT_THEME="ansi"

  # Tmux alias to use RPi config
  alias tmux='tmux -f ~/.config/tmux/tmux-rpi.conf'

else
  # macOS: Catppuccin Mocha theme
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
  export FZF_DEFAULT_COMMAND='fdfind --type f --hidden --follow --exclude .git'
fi
