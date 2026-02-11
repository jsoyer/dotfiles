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
if [[ -x "/opt/homebrew/bin/brew" ]]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
elif [[ -x "/usr/local/bin/brew" ]]; then
  eval "$(/usr/local/bin/brew shellenv)"
fi

# ============================================================================
# User bins (highest priority)
# ============================================================================
path_prepend "${HOME}/.cargo/bin"
path_prepend "${HOME}/.local/bin"

# ============================================================================
# macOS-specific paths
# ============================================================================
if [[ "${IS_MACOS}" == "true" ]]; then
  path_prepend "${HOME}/.antigravity/antigravity/bin"
  path_prepend "${HOME}/.jenv/bin"
  path_prepend "${HOMEBREW_PREFIX:-/opt/homebrew}/opt/ruby/bin"
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
