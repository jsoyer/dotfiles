#!/usr/bin/env zsh
# shellcheck shell=bash
# External tools and integrations

# ============================================================================
# FZF - Fuzzy finder
# ============================================================================
if [[ -f ~/.fzf.zsh ]]; then
  source ~/.fzf.zsh
elif [[ -f /usr/share/doc/fzf/examples/key-bindings.zsh ]]; then
  # Debian/Ubuntu location
  source /usr/share/doc/fzf/examples/key-bindings.zsh
  source /usr/share/doc/fzf/examples/completion.zsh
fi

# ============================================================================
# Zsh autosuggestions
# ============================================================================
_brew_prefix="${HOMEBREW_PREFIX:-/opt/homebrew}"
if [[ "${IS_MACOS}" == "true" ]]; then
  _zsh_autosuggest_path="${_brew_prefix}/share/zsh-autosuggestions/zsh-autosuggestions.zsh"
else
  # Linux: installed via oh-my-zsh custom plugins or apt
  _zsh_autosuggest_path="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh"
  [[ ! -f ${_zsh_autosuggest_path} ]] && _zsh_autosuggest_path="/usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh"
fi
if [[ -f ${_zsh_autosuggest_path} ]]; then
  source "${_zsh_autosuggest_path}"
fi
unset _zsh_autosuggest_path

# ============================================================================
# Zsh syntax highlighting
# ============================================================================
if [[ "${IS_MACOS}" == "true" ]]; then
  _zsh_syntax_path="${_brew_prefix}/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"
else
  # Linux: installed via oh-my-zsh custom plugins or apt
  _zsh_syntax_path="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"
  [[ ! -f ${_zsh_syntax_path} ]] && _zsh_syntax_path="/usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"
fi
if [[ -f ${_zsh_syntax_path} ]]; then
  source "${_zsh_syntax_path}"
fi
unset _zsh_syntax_path _brew_prefix

# ============================================================================
# Zoxide - Smarter cd command (cached init)
# ============================================================================
if command -v zoxide >/dev/null 2>&1; then
  _cache_eval zoxide 'zoxide init zsh'
fi

# ============================================================================
# Atuin - Magical shell history (cached init)
# ============================================================================
if command -v atuin >/dev/null 2>&1; then
  _cache_eval atuin 'atuin init zsh'
fi

# ============================================================================
# Direnv - Environment switcher (cached init)
# ============================================================================
if command -v direnv >/dev/null 2>&1; then
  _cache_eval direnv 'direnv hook zsh'
fi

# ============================================================================
# OrbStack - Docker/Kubernetes alternative (macOS only)
# ============================================================================
if [[ "${IS_MACOS}" == "true" ]] && [[ -f ~/.orbstack/shell/init.zsh ]]; then
  source ~/.orbstack/shell/init.zsh 2>/dev/null || :
fi

# ============================================================================
# Nix package manager (optional)
# ============================================================================
if [[ -f /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh ]]; then
  source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh
fi

# ============================================================================
# Thefuck - Command correction (lazy-loaded on first 'fuck' call)
# ============================================================================
if command -v thefuck >/dev/null 2>&1; then
  fuck() {
    unfunction fuck
    eval "$(thefuck --alias)"
    fuck "$@"
  }
fi
