#!/usr/bin/env zsh
# shellcheck shell=bash
# External tools and integrations

# ============================================================================
# Zplug - Plugin manager
# ============================================================================
export ZPLUG_HOME=/opt/homebrew/opt/zplug
if [[ -f ${ZPLUG_HOME}/init.zsh ]]; then
  source "${ZPLUG_HOME}/init.zsh"
fi

# ============================================================================
# FZF - Fuzzy finder
# ============================================================================
if [[ -f ~/.fzf.zsh ]]; then
  source ~/.fzf.zsh
fi

# ============================================================================
# Zsh autosuggestions
# ============================================================================
_zsh_autosuggest_path="$(brew --prefix)/share/zsh-autosuggestions/zsh-autosuggestions.zsh"
if [[ -f ${_zsh_autosuggest_path} ]]; then
  source "${_zsh_autosuggest_path}"
fi
unset _zsh_autosuggest_path

# ============================================================================
# Zsh syntax highlighting
# ============================================================================
_zsh_syntax_path="$(brew --prefix)/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"
if [[ -f ${_zsh_syntax_path} ]]; then
  source "${_zsh_syntax_path}"
fi
unset _zsh_syntax_path

# ============================================================================
# Zoxide - Smarter cd command
# ============================================================================
if command -v zoxide >/dev/null 2>&1; then
  eval "$(zoxide init zsh)"
fi

# ============================================================================
# Atuin - Magical shell history
# ============================================================================
if command -v atuin >/dev/null 2>&1; then
  eval "$(atuin init zsh)"
fi

# ============================================================================
# Direnv - Environment switcher
# ============================================================================
if command -v direnv >/dev/null 2>&1; then
  eval "$(direnv hook zsh)"
fi

# ============================================================================
# OrbStack - Docker/Kubernetes alternative
# ============================================================================
if [[ -f ~/.orbstack/shell/init.zsh ]]; then
  source ~/.orbstack/shell/init.zsh 2>/dev/null || :
fi

# ============================================================================
# Nix package manager
# ============================================================================
if [[ -f /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh ]]; then
  source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh
fi

# ============================================================================
# Thefuck - Command correction
# ============================================================================
if command -v thefuck >/dev/null 2>&1; then
  eval "$(thefuck --alias)"
fi
