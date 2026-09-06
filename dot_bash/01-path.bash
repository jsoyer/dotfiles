#!/usr/bin/env bash
# PATH configuration

# Helper function to add to PATH if directory exists
path_prepend() {
  [[ -d "$1" ]] && PATH="$1:${PATH//":$1:"/:}"
}

path_append() {
  [[ -d "$1" ]] && PATH="${PATH//":$1:"/:}:$1"
}

# ============================================================================
# Homebrew (must be first on macOS)
# ============================================================================
# Use _cache_eval to avoid forking brew on every startup (~200ms savings).
# _cache_eval is defined in 00-env.bash and caches output for 24h.
if [[ -x "/opt/homebrew/bin/brew" ]]; then
  _cache_eval brew '/opt/homebrew/bin/brew shellenv'
elif [[ -x "/usr/local/bin/brew" ]]; then
  _cache_eval brew '/usr/local/bin/brew shellenv'
elif [[ -d "/home/linuxbrew/.linuxbrew" ]]; then
  _cache_eval linuxbrew '/home/linuxbrew/.linuxbrew/bin/brew shellenv'
elif [[ -d "${HOME}/.linuxbrew" ]]; then
  _cache_eval linuxbrew "${HOME}/.linuxbrew/bin/brew shellenv"
fi

# brew shellenv drops the PATH export once its bin/ is already on PATH, so sbin/
# never makes it in (mtr, unbound, php-fpm live there). Add it explicitly.
for _brew_sbin in /opt/homebrew/sbin /usr/local/sbin /home/linuxbrew/.linuxbrew/sbin "${HOME}/.linuxbrew/sbin"; do
  [[ -d "$_brew_sbin" ]] && PATH="${_brew_sbin}:${PATH}"
done
unset _brew_sbin
export PATH

# ============================================================================
# User bins (highest priority)
# ============================================================================
path_prepend "${HOME}/.cargo/bin"
path_prepend "${HOME}/.local/bin"
path_prepend "${HOME}/.npm-global/bin"
path_prepend "${HOME}/.opencode/bin"

# ============================================================================
# macOS-specific paths
# ============================================================================
if [[ "${IS_MACOS}" == "true" ]]; then
  path_prepend "${HOME}/.antigravity/antigravity/bin"
  path_prepend "${HOME}/.jenv/bin"
  [[ -n "${HOMEBREW_PREFIX:-}" ]] && path_prepend "${HOMEBREW_PREFIX}/opt/ruby/bin"
  path_prepend "${HOME}/.rbenv/shims"
  path_prepend "${HOME}/.tmuxifier/bin"
  path_append "/usr/local/opt/rbenv/shims"
  path_append "/opt/X11/bin"
  path_append "/Library/TeX/texbin"
  path_append "/usr/texbin"

  # Lazy load pyenv for faster startup
  if command -v pyenv >/dev/null 2>&1; then
    pyenv() {
      unset -f pyenv
      eval "$(command pyenv init -)"
      pyenv "$@"
    }
  fi

  # Lazy load jenv for faster startup
  if command -v jenv >/dev/null 2>&1; then
    jenv() {
      unset -f jenv
      eval "$(command jenv init -)"
      jenv "$@"
    }
  fi
fi

# LM Studio CLI
path_append "${HOME}/.lmstudio/bin"

export PATH
