#!/usr/bin/env zsh
# Environment variables configuration

# ============================================================================
# Platform & Profile-based Theming
# ============================================================================

# Default values
export STARSHIP_CONFIG="${HOME}/.config/starship/starship.toml"

# Cache OS and hostname — avoids forking uname/hostname on every shell start
_OS="${OSTYPE}"
_HOST="${HOST%%.*}"

# Determine OS and apply specific logic
case "${_OS}" in
  darwin*)
    # --- macOS ---
    export STARSHIP_ICON_COLOR="mauve"
    export STARSHIP_ICON=""
    if [[ "${_HOST}" == "jsoyer-macOS" ]]; then
      export MACHINE_PROFILE="mac-pro"
      # Mac Pro: install casks in $HOME/Applications
      export HOMEBREW_CASK_OPTS="--appdir=${HOME}/Applications"
    else
      export MACHINE_PROFILE="mac-personal"
    fi
    ;;

  linux*)
    # --- Linux ---
    export STARSHIP_CONFIG="${HOME}/.config/starship/starship-rpi.toml"

    if [[ -n "$TOOLBOX_PATH" ]] || [[ "$HOSTNAME" == *toolbx* ]]; then
      # Fedora Toolbox container
      export STARSHIP_ICON_COLOR="blue"
      export STARSHIP_ICON=""
      export MACHINE_PROFILE="toolbox"

    elif [[ -f /proc/device-tree/model ]] && grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
      # Raspberry Pi devices
      export STARSHIP_ICON_COLOR="red"
      case "${_HOST}" in
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
      export MACHINE_PROFILE="rpi"

    else
      # Other Linux devices (Fedora)
      export STARSHIP_ICON_COLOR="blue"
      export STARSHIP_ICON=""
      if [[ "${_HOST}" == "fedora" ]]; then
        export MACHINE_PROFILE="linux-standard"
      elif [[ "${_HOST}" == "fedora-atomic" ]]; then
        export MACHINE_PROFILE="linux-atomic"
      fi
    fi
    ;;

  cygwin*|msys*|mingw*)
    # --- Windows ---
    export STARSHIP_ICON_COLOR="cyan"
    export STARSHIP_ICON=""
    export MACHINE_PROFILE="windows"
    ;;
esac

unset _OS _HOST

# Convenience boolean flags (compatible with bash env)
[[ "$OSTYPE" == darwin* ]] && export IS_MACOS=true || export IS_MACOS=false
[[ "$MACHINE_PROFILE" == "rpi" ]] && export IS_RPI=true || export IS_RPI=false
[[ "$OSTYPE" == linux* ]] && export IS_LINUX=true || export IS_LINUX=false

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
if [[ "$MACHINE_PROFILE" == "rpi" ]]; then
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
# FZF Configuration
# ============================================================================
# FZF theme (Catppuccin Mocha)
export FZF_DEFAULT_OPTS=" \
--color=bg+:#313244,bg:#1e1e2e,spinner:#f5e0dc,hl:#f38ba8 \
--color=fg:#cdd6f4,header:#f38ba8,info:#cba6f7,pointer:#f5e0dc \
--color=marker:#f5e0dc,fg+:#cdd6f4,prompt:#cba6f7,hl+:#f38ba8"

# FZF default command — use $+commands to avoid forking
if (( $+commands[fd] )); then
  export FZF_DEFAULT_COMMAND='fd --type f --hidden --follow --exclude .git'
elif (( $+commands[fdfind] )); then
  export FZF_DEFAULT_COMMAND='fdfind --type f --hidden --follow --exclude .git'
fi

# ============================================================================
# Bat theme
# ============================================================================
export BAT_THEME="Catppuccin Mocha"

# ============================================================================
# GitHub token (for Claude Code MCP + tools)
# ============================================================================
# GITHUB_TOKEN: set in ~/.zsh/secrets.zsh (gitignored) or export on demand via: gh auth token
# Do NOT export here — forks a Go binary on every shell start (200-500ms on RPi)

# ============================================================================
# MCP API keys (Claude Code + OpenCode integrations)
# ============================================================================
# These environment variables are required by MCP servers configured in:
#   ~/.claude/settings.json
#   ~/.config/opencode/opencode.json
#
# To activate a server, uncomment its line and add your key.
# Keys should ideally be stored in ~/.zsh/secrets.zsh (gitignored).
#
# Server            Variable              Where to get it
# -------           --------              ---------------
# slack             SLACK_BOT_TOKEN       api.slack.com → Your apps → OAuth tokens
# slack             SLACK_TEAM_ID         Slack workspace ID (from URL or api.slack.com)
# brave-search      BRAVE_API_KEY         api.search.brave.com (free tier: 2000 req/month)
# linear            LINEAR_API_KEY        Linear → Settings → API → Personal API keys
# discord           DISCORD_TOKEN         discord.com/developers → Bot → Token
# obsidian          OBSIDIAN_API_KEY      Obsidian → Community plugins → Local REST API → Copy key
# notion            NOTION_API_KEY        notion.so/my-integrations → New integration → Secret
#
# export SLACK_BOT_TOKEN=""
# export SLACK_TEAM_ID=""
# export BRAVE_API_KEY=""
# export LINEAR_API_KEY=""
# export DISCORD_TOKEN=""
# export OBSIDIAN_API_KEY=""
# export NOTION_API_KEY=""
