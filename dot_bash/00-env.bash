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
  local meta_file="$cache_dir/${name}.meta"
  # Track binary path to invalidate cache when binary moves (e.g., brew -> pacman)
  local bin_name="${1%% *}"
  local cur_path
  cur_path="$(command -v "${bin_name}" 2>/dev/null)" || cur_path="${bin_name}"
  local prev_path=""
  [[ -f "$meta_file" ]] && prev_path="$(<"$meta_file")"
  mkdir -p "$cache_dir"
  if [[ ! -f "$cache_file" ]] || [[ "$cur_path" != "$prev_path" ]] || \
     [[ -n "$(find "$cache_file" -mtime +1 2>/dev/null)" ]]; then
    eval "$@" > "$cache_file" 2>/dev/null || { rm -f "$cache_file" "$meta_file"; eval "$@"; return; }
    echo "$cur_path" > "$meta_file"
  fi
  source "$cache_file" 2>/dev/null || eval "$@"
}

# ============================================================================
# Platform detection helpers
# ============================================================================

# Read distro ID from /etc/os-release (source of truth)
_detect_distro() {
  # Read ID= from os-release without forking a subshell
  local line id=""
  if [[ -f /etc/os-release ]]; then
    while IFS='=' read -r key val; do
      if [[ "$key" == "ID" ]]; then id="$val"; break; fi
    done < /etc/os-release
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
export IS_FEDORA=false
export IS_ARCH=false

case "$OSTYPE" in
  darwin*)
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
  linux*)
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

    elif [[ "${_DISTRO_ID}" == "omarchy" ]]; then
      export IS_ARCH=true
      export PLATFORM="omarchy"
      export MACHINE_PROFILE="omarchy"

    elif [[ "${_DISTRO_ID}" == "arch" ]]; then
      export IS_ARCH=true
      export PLATFORM="arch"
      _HOST="${HOSTNAME%%.*}"
      if [[ "${_HOST}" == arch-server* ]]; then
        export MACHINE_PROFILE="arch-server"
      else
        export MACHINE_PROFILE="arch-desktop"
      fi
      unset _HOST

    else
      # Fedora — atomic by tool, then server/desktop by hostname
      export IS_FEDORA=true
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
  export STARSHIP_ICON=$'\uf179'
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
  export STARSHIP_ICON=$'\uf31b'
  export STARSHIP_ICON_COLOR="peach"
elif [[ "${MACHINE_PROFILE}" == "ubuntu-server" ]]; then
  export STARSHIP_ICON=$'\uf31b'
  export STARSHIP_ICON_COLOR="yellow"
elif [[ "${MACHINE_PROFILE}" == "omarchy" ]]; then
  export STARSHIP_ICON=$'\uf303'
  export STARSHIP_ICON_COLOR="purple"
elif [[ "${MACHINE_PROFILE}" == arch-* ]]; then
  export STARSHIP_ICON=$'\uf303'
  export STARSHIP_ICON_COLOR="blue"
elif [[ "${MACHINE_PROFILE}" == "debian" ]]; then
  export STARSHIP_ICON=$'\uf306'
  export STARSHIP_ICON_COLOR="red"
elif [[ "${MACHINE_PROFILE}" == fedora-* ]]; then
  export STARSHIP_ICON=$'\uf30a'
  export STARSHIP_ICON_COLOR="blue"
elif [[ "${MACHINE_PROFILE}" == "toolbox" ]]; then
  export STARSHIP_ICON=$'\uf473'
  export STARSHIP_ICON_COLOR="blue"
elif [[ "${IS_LINUX}" == "true" ]]; then
  export STARSHIP_ICON=$'\uf17c'
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
  export STARSHIP_CONFIG="${HOME}/.config/starship/starship-ssh.toml"

  # FZF theme (Snazzy)
  export FZF_DEFAULT_OPTS=" \
--color=bg+:#3a3d4d,bg:#282a36,spinner:#ff5c57,hl:#57c7ff \
--color=fg:#eff0eb,header:#57c7ff,info:#ff6ac1,pointer:#ff5c57 \
--color=marker:#f3f99d,fg+:#eff0eb,prompt:#ff6ac1,hl+:#57c7ff"

  # Vivid colors (Snazzy) — cached to avoid forking on every startup
  if command -v vivid >/dev/null 2>&1; then
    _vivid_cache="${HOME}/.cache/vivid/ls-colors-snazzy.txt"
    if [[ ! -f "$_vivid_cache" ]] || [[ -n "$(find "$_vivid_cache" -mtime +7 2>/dev/null)" ]]; then
      mkdir -p "${HOME}/.cache/vivid"
      vivid generate snazzy > "$_vivid_cache" 2>/dev/null
    fi
    [[ -f "$_vivid_cache" ]] && export LS_COLORS="$(<"$_vivid_cache")"
  fi

  # Bat theme
  export BAT_THEME="ansi"

  # Tmux alias to use RPi config
  alias tmux='tmux -f ~/.config/tmux/tmux-rpi.conf'

else
  # macOS / Ubuntu Desktop: Catppuccin Mocha theme
  export STARSHIP_CONFIG="${HOME}/.config/starship/starship-desktop.toml"

  # FZF theme (Catppuccin Mocha)
  export FZF_DEFAULT_OPTS=" \
--color=bg+:#313244,bg:#1e1e2e,spinner:#f5e0dc,hl:#f38ba8 \
--color=fg:#cdd6f4,header:#f38ba8,info:#cba6f7,pointer:#f5e0dc \
--color=marker:#f5e0dc,fg+:#cdd6f4,prompt:#cba6f7,hl+:#f38ba8"

  # Vivid colors (Catppuccin Mocha) — cached
  if command -v vivid >/dev/null 2>&1; then
    _vivid_cache="${HOME}/.cache/vivid/ls-colors-catppuccin-mocha.txt"
    if [[ ! -f "$_vivid_cache" ]] || [[ -n "$(find "$_vivid_cache" -mtime +7 2>/dev/null)" ]]; then
      mkdir -p "${HOME}/.cache/vivid"
      vivid generate catppuccin-mocha > "$_vivid_cache" 2>/dev/null
    fi
    [[ -f "$_vivid_cache" ]] && export LS_COLORS="$(<"$_vivid_cache")"
  fi

  # Bat theme (Catppuccin Mocha)
  export BAT_THEME="Catppuccin Mocha"
fi

unset _use_snazzy

# SSH override: use compact Snazzy prompt when connected over SSH on desktops
if [[ -n "${SSH_TTY:-}" && "${STARSHIP_CONFIG}" == *"/starship-desktop.toml" ]]; then
  export STARSHIP_CONFIG="${HOME}/.config/starship/starship-ssh.toml"
fi

# ============================================================================
# FZF default command (platform-agnostic)
# ============================================================================
if command -v fd >/dev/null 2>&1; then
  export FZF_DEFAULT_COMMAND='fd --type f --hidden --follow --exclude .git'
elif command -v fdfind >/dev/null 2>&1; then
  export FZF_DEFAULT_COMMAND='fdfind --type f --hidden --follow --exclude .git'
fi
