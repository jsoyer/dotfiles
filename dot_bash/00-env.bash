#!/usr/bin/env bash
# shellcheck shell=bash
# Environment variables configuration

# ============================================================================
# Cache helper — caches shell-init command output for 24h (like zsh _cache_eval)
# ============================================================================
_cache_eval() {
  local name="$1"
  shift
  local cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/shell"
  local cache_file="$cache_dir/${name}.bash"
  mkdir -p "$cache_dir"
  if [[ ! -f "$cache_file" ]] || [[ -n "$(find "$cache_file" -mtime +1 2>/dev/null)" ]]; then
    eval "$@" > "$cache_file" 2>/dev/null || { rm -f "$cache_file"; eval "$@"; return; }
  fi
  source "$cache_file" 2>/dev/null || eval "$@"
}

# ============================================================================
# Platform detection helpers
# ============================================================================

# Read distro ID from /etc/os-release (source of truth)
_detect_distro() {
  local id=""
  if [[ -f /etc/os-release ]]; then
    id=$(. /etc/os-release && echo "${ID:-}")
  fi
  echo "$id"
}

# True if running on Raspberry Pi hardware (works regardless of OS)
_is_rpi() {
  [[ -f /proc/device-tree/model ]] && grep -qi "raspberry pi" /proc/device-tree/model 2>/dev/null
}

# ============================================================================
# Platform detection
# ============================================================================
export IS_MACOS=false
export IS_RPI=false
export IS_LINUX=false
export IS_UBUNTU=false

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
    _DISTRO_ID="$(_detect_distro)"

    if [[ -n "${TOOLBOX_PATH:-}" ]] || [[ "${HOSTNAME:-}" == *toolbx* ]]; then
      export PLATFORM="toolbox"
      export MACHINE_PROFILE="toolbox"

    elif _is_rpi; then
      export IS_RPI=true
      export PLATFORM="rpi"
      export MACHINE_PROFILE="rpi"
      RPI_MODEL="$(tr -d '\0' < /proc/device-tree/model 2>/dev/null || true)"
      export RPI_MODEL

    elif [[ "${_DISTRO_ID}" == "ubuntu" ]]; then
      export IS_UBUNTU=true
      export PLATFORM="ubuntu"
      _HOST="${HOSTNAME%%.*}"
      if [[ "${_HOST}" == ubuntu-server* ]]; then
        export MACHINE_PROFILE="ubuntu-server"
      else
        export MACHINE_PROFILE="ubuntu-desktop"
      fi
      unset _HOST

    elif [[ "${_DISTRO_ID}" == "debian" ]]; then
      export PLATFORM="debian"
      export MACHINE_PROFILE="debian"

    else
      # Fedora — atomic by tool, then server/desktop by hostname
      _HOST="${HOSTNAME%%.*}"
      if command -v rpm-ostree &>/dev/null 2>&1; then
        export MACHINE_PROFILE="fedora-atomic"
      elif [[ "${_HOST}" == fedora-server* ]]; then
        export MACHINE_PROFILE="fedora-server"
      else
        export MACHINE_PROFILE="fedora-desktop"
      fi
      unset _HOST
    fi

    unset _DISTRO_ID
    ;;
  *)
    export PLATFORM="unknown"
    export MACHINE_PROFILE="unknown"
    ;;
esac

# ============================================================================
# Hostname-based icon for Starship prompt
# ============================================================================
if [[ "${IS_MACOS}" == "true" ]]; then
  export STARSHIP_ICON="⌘"
  export STARSHIP_ICON_COLOR="mauve"
elif [[ "${IS_RPI}" == "true" ]]; then
  export STARSHIP_ICON_COLOR="red"
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
elif [[ "${MACHINE_PROFILE}" == "ubuntu-desktop" ]]; then
  export STARSHIP_ICON=""
  export STARSHIP_ICON_COLOR="peach"
elif [[ "${MACHINE_PROFILE}" == "ubuntu-server" ]]; then
  export STARSHIP_ICON=""
  export STARSHIP_ICON_COLOR="yellow"
elif [[ "${IS_LINUX}" == "true" ]]; then
  export STARSHIP_ICON=""
  export STARSHIP_ICON_COLOR="blue"
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
if [[ "${MACHINE_PROFILE}" == "rpi" ]]; then
  export EDITOR='nano'
else
  export EDITOR='nvim'
fi

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
_use_snazzy=false
case "${MACHINE_PROFILE:-}" in
  rpi|fedora-server|fedora-atomic|toolbox|ubuntu-server|debian) _use_snazzy=true ;;
esac

if [[ "${_use_snazzy}" == "true" ]]; then
  # RPi / Linux servers: Snazzy theme
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
  # macOS / Ubuntu Desktop: Catppuccin Mocha theme
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

unset _use_snazzy

# ============================================================================
# FZF default command (platform-agnostic)
# ============================================================================
if command -v fd >/dev/null 2>&1; then
  export FZF_DEFAULT_COMMAND='fd --type f --hidden --follow --exclude .git'
elif command -v fdfind >/dev/null 2>&1; then
  export FZF_DEFAULT_COMMAND='fdfind --type f --hidden --follow --exclude .git'
fi
