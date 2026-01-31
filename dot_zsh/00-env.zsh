#!/usr/bin/env zsh
# Environment variables configuration

#!/usr/bin/env zsh

# Environment variables configuration



# ============================================================================

# Platform & Profile-based Theming

# ============================================================================



# Default values

export STARSHIP_CONFIG="${HOME}/.config/starship/starship.toml"



# Determine OS and apply specific logic

case "$(uname -s)" in

  Darwin)

    # --- macOS ---

    export STARSHIP_ICON_COLOR="mauve"

    if [[ "$(hostname)" == "jsoyer-macOS" ]]; then

      # Professional Mac

      export STARSHIP_ICON="💼"

    else

      # Personal Macs

      export STARSHIP_ICON="⌘"

    fi

    ;;



  Linux)

    # --- Linux ---

    export STARSHIP_CONFIG="${HOME}/.config/starship/starship-rpi.toml" # Use the linux/rpi theme



    if [[ -f /proc/device-tree/model ]] && grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then

      # Raspberry Pi devices

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

    else

      # Other Linux devices (Fedora)

      export STARSHIP_ICON_COLOR="blue"

      export STARSHIP_ICON=""

    fi

    ;;



  CYGWIN*|MINGW32*|MSYS*|MINGW*)

    # --- Windows ---

    export STARSHIP_ICON_COLOR="cyan"

    export STARSHIP_ICON=""

    ;;

esac





# ============================================================================

# Locale and language

# ============================================================================

export LANG=en_US.UTF-8

export LC_ALL=en_US.UTF-8



# ============================================================================

# History configuration

# ============================================================================

export HISTFILE="${HOME}/.zsh_history"

export HISTSIZE=50000

export SAVEHIST=50000

setopt EXTENDED_HISTORY

setopt HIST_EXPIRE_DUPS_FIRST

setopt HIST_IGNORE_DUPS

setopt HIST_IGNORE_SPACE

setopt HIST_VERIFY

setopt SHARE_HISTORY



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

# FZF Configuration

# ============================================================================

# FZF theme (Catppuccin Mocha)

export FZF_DEFAULT_OPTS=" \

--color=bg+:#313244,bg:#1e1e2e,spinner:#f5e0dc,hl:#f38ba8 \

--color=fg:#cdd6f4,header:#f38ba8,info:#cba6f7,pointer:#f5e0dc \

--color=marker:#f5e0dc,fg+:#cdd6f4,prompt:#cba6f7,hl+:#f38ba8"



# FZF default command (platform-agnostic)

if command -v fd >/dev/null 2>&1; then

  export FZF_DEFAULT_COMMAND='fd --type f --hidden --follow --exclude .git'

elif command -v fdfind >/dev/null 2>&1; then

  export FZF_DEFAULT_COMMAND='fdfind --type f --hidden --follow --exclude .git'

fi



# ============================================================================

# Bat theme

# ============================================================================

export BAT_THEME="Catppuccin Mocha"
