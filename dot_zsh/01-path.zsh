#!/usr/bin/env zsh
# shellcheck shell=bash
# PATH configuration

# Build PATH in correct order (highest priority first)
typeset -U path  # Ensure uniqueness

path=(
  # User bins (highest priority)
  "${HOME}/.local/bin"
  "${HOME}/.cargo/bin"

  # Preserve existing paths
  "${path[@]}"
)

# macOS-specific paths
if [[ "${IS_MACOS}" == "true" ]]; then
  path=(
    "${HOME}/.antigravity/antigravity/bin"
    "${HOME}/.jenv/bin"
    "${HOME}/.rbenv/shims"
    "${HOME}/.tmuxifier/bin"
    "${path[@]}"
    /usr/local/opt/rbenv/shims
    /opt/X11/bin
    /Library/TeX/texbin
    /usr/texbin
  )

  # Lazy load pyenv for faster startup (macOS only)
  if command -v pyenv >/dev/null 2>&1; then
    pyenv() {
      unfunction pyenv
      eval "$(command pyenv init -)"
      pyenv "$@"
    }
  fi

  # Lazy load jenv for faster startup (macOS only)
  if command -v jenv >/dev/null 2>&1; then
    jenv() {
      unfunction jenv
      eval "$(command jenv init -)"
      jenv "$@"
    }
  fi
fi
