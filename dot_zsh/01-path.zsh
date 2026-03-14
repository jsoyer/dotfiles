#!/usr/bin/env zsh
# shellcheck shell=bash
# PATH configuration

# Build PATH in correct order (highest priority first)
typeset -U path  # Ensure uniqueness

# Add ~/bin for Raspberry Pi user scripts, if it exists
if [[ -d "$HOME/bin" ]] && [[ "$MACHINE_PROFILE" == "rpi" ]]; then
  path=("$HOME/bin" $path)
fi

path=(
  # User bins (highest priority)
  "${HOME}/.opencode/bin"
  "${HOME}/.local/bin"
  "${HOME}/.cargo/bin"

  # Preserve existing paths
  "${path[@]}"
)

# Linuxbrew PATH (Homebrew on Linux) — cached to avoid forking brew on every shell start
if [[ -d "/home/linuxbrew/.linuxbrew" ]]; then
  _cache_eval linuxbrew '/home/linuxbrew/.linuxbrew/bin/brew shellenv'
elif [[ -d "${HOME}/.linuxbrew" ]]; then
  _cache_eval linuxbrew "${HOME}/.linuxbrew/bin/brew shellenv"
fi

# macOS-specific paths
if [[ "${IS_MACOS}" == "true" ]]; then
  path=(
    "${HOME}/.antigravity/antigravity/bin"
    "${HOME}/.jenv/bin"
    "${HOMEBREW_PREFIX:-/opt/homebrew}/opt/ruby/bin"
    "${HOME}/.rbenv/shims"
    "${HOME}/.tmuxifier/bin"
    "${path[@]}"
    /usr/local/opt/rbenv/shims
    /opt/X11/bin
    /Library/TeX/texbin
    /usr/texbin
    /usr/local/texlive/2025basic/bin/universal-darwin
  )

  # Lazy load pyenv for faster startup (macOS only)
  if (( $+commands[pyenv] )); then
    pyenv() {
      unfunction pyenv
      eval "$(command pyenv init -)"
      pyenv "$@"
    }
  fi

  # Lazy load jenv for faster startup (macOS only)
  if (( $+commands[jenv] )); then
    jenv() {
      unfunction jenv
      eval "$(command jenv init -)"
      jenv "$@"
    }
  fi
fi
