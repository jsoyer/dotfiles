#!/usr/bin/env zsh
# shellcheck shell=bash
# Environment variables configuration

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
# Homebrew
# ============================================================================
export HOMEBREW_CASK_OPTS="--appdir=/Users/jsoyer/Applications"

# ============================================================================
# Kubernetes
# ============================================================================
export KUBECONFIG="${HOME}/.kube/config"

# ============================================================================
# FZF theme (Catppuccin Mocha)
# ============================================================================
export FZF_DEFAULT_OPTS=" \
--color=bg+:#313244,bg:#1e1e2e,spinner:#f5e0dc,hl:#f38ba8 \
--color=fg:#cdd6f4,header:#f38ba8,info:#cba6f7,pointer:#f5e0dc \
--color=marker:#f5e0dc,fg+:#cdd6f4,prompt:#cba6f7,hl+:#f38ba8"
export FZF_DEFAULT_COMMAND='fd --type f --hidden --follow --exclude .git'

# ============================================================================
# Eza colors (Catppuccin Mocha)
# ============================================================================
# Based on Catppuccin Mocha palette
export EZA_COLORS="uu=38;5;147:gu=38;5;147:ur=38;5;203:uw=38;5;204:ux=38;5;148:ue=38;5;148:gr=38;5;203:gw=38;5;204:gx=38;5;148:tr=38;5;203:tw=38;5;204:tx=38;5;148:da=38;5;110:sn=38;5;180:sb=38;5;180:xa=38;5;147"

# ============================================================================
# Bat theme (Catppuccin Mocha)
# ============================================================================
export BAT_THEME="Catppuccin Mocha"
