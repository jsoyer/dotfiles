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
_brew_prefix="${HOMEBREW_PREFIX:-$(brew --prefix 2>/dev/null)}"
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
# Atuin - Magical shell history (cached init)
# ============================================================================
if (( $+commands[atuin] )); then
  _cache_eval atuin 'atuin init zsh'
fi

# ============================================================================
# Direnv - Environment switcher (cached init)
# ============================================================================
if (( $+commands[direnv] )); then
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
if (( $+commands[thefuck] )); then
  fuck() {
    unfunction fuck
    eval "$(thefuck --alias)"
    fuck "$@"
  }
fi

# ============================================================================
# chezmoi background auto-update (login hook — fires if last check > 1h)
# ============================================================================
_chezmoi_bg_update() {
  local stampdir="${HOME}/.cache/chezmoi-autoupdate"
  local stamp="${stampdir}/last-login-check"
  [[ -d "${stampdir}" ]] || mkdir -p "${stampdir}"
  local now
  now=$(date +%s)
  local last=0
  [[ -f "${stamp}" ]] && last=$(<"${stamp}")
  if (( now - last > 3600 )); then
    echo "${now}" > "${stamp}"
    (chezmoi-autoupdate &>/dev/null &)
  fi
}
(( $+commands[chezmoi] )) && _chezmoi_bg_update

# ============================================================================
# Completion overrides for aliased commands (must run after all plugins)
# ============================================================================
(( $+commands[eza] )) && (( $+functions[compdef] )) && compdef _eza ls

# ============================================================================
# ai-context auto-apply on cd (checks project-map.yaml)
# ============================================================================
if (( $+commands[aictx] )); then
  _aictx_auto_apply() {
    local project_map="${HOME}/.config/aictx/project-map.yaml"
    [[ -f "$project_map" ]] || return
    # Only apply if .claude/skills/ doesn't exist yet
    [[ -d ".claude/skills" ]] && return
    # Check if current dir is in project-map
    if grep -q "$(pwd)" "$project_map" 2>/dev/null; then
      aictx apply --auto --yes 2>/dev/null &!
    fi
  }
  autoload -Uz add-zsh-hook
  add-zsh-hook chpwd _aictx_auto_apply
fi

# ============================================================================
# Zoxide - Smarter cd command (cached init)
# Must be initialized LAST — after all other cd-hooking tools and integrations
# ============================================================================
export _ZO_DOCTOR=0
if (( $+commands[zoxide] )); then
  _cache_eval zoxide 'zoxide init --cmd cd zsh'
fi
