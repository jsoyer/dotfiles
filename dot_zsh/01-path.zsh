#!/usr/bin/env zsh
# shellcheck shell=bash
# PATH configuration

# Build PATH in correct order (highest priority first)
# Note: Homebrew paths are already set by .zprofile via 'brew shellenv'
typeset -U path  # Ensure uniqueness

path=(
  # User bins (highest priority)
  "${HOME}/.antigravity/antigravity/bin"
  "${HOME}/.local/bin"
  "${HOME}/.jenv/bin"
  "${HOME}/.rbenv/shims"
  "${HOME}/.tmuxifier/bin"

  # Preserve existing paths from .zprofile (Homebrew, etc.)
  "${path[@]}"

  # Additional tool-specific paths
  /usr/local/opt/rbenv/shims

  # X11 and TeX
  /opt/X11/bin
  /Library/TeX/texbin
  /usr/texbin
)

# Lazy load pyenv for faster startup
pyenv() {
  unfunction pyenv
  if command -v pyenv >/dev/null 2>&1; then
    eval "$(command pyenv init -)"
  fi
  pyenv "$@"
}

# Lazy load jenv for faster startup
jenv() {
  unfunction jenv
  if command -v jenv >/dev/null 2>&1; then
    eval "$(command jenv init -)"
  fi
  jenv "$@"
}
