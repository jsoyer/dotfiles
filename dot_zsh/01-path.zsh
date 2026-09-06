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
  "${HOME}/.npm-global/bin"
  "${HOME}/.local/bin"
  "${HOME}/.cargo/bin"

  # Preserve existing paths
  "${path[@]}"
)

# Homebrew (macOS: Apple Silicon or Intel) — cached to avoid forking brew on every shell start
if [[ -x "/opt/homebrew/bin/brew" ]]; then
  _cache_eval brew '/opt/homebrew/bin/brew shellenv'
elif [[ -x "/usr/local/bin/brew" ]]; then
  _cache_eval brew '/usr/local/bin/brew shellenv'
# Linuxbrew PATH (Homebrew on Linux) — cached to avoid forking brew on every shell start
elif [[ -d "/home/linuxbrew/.linuxbrew" ]]; then
  _cache_eval linuxbrew '/home/linuxbrew/.linuxbrew/bin/brew shellenv'
elif [[ -d "${HOME}/.linuxbrew" ]]; then
  _cache_eval linuxbrew "${HOME}/.linuxbrew/bin/brew shellenv"
fi

# brew shellenv drops the PATH export once its bin/ is already on PATH, so sbin/
# never makes it in (mtr, unbound, php-fpm live there). Add it explicitly.
for _brew_sbin in /opt/homebrew/sbin /usr/local/sbin /home/linuxbrew/.linuxbrew/sbin "${HOME}/.linuxbrew/sbin"; do
  [[ -d "$_brew_sbin" ]] && path=("$_brew_sbin" "${path[@]}")
done
unset _brew_sbin

# macOS-specific paths
if [[ "${IS_MACOS}" == "true" ]]; then
  path=(
    "${HOME}/.antigravity/antigravity/bin"
    "${HOME}/.jenv/bin"
    ${HOMEBREW_PREFIX:+${HOMEBREW_PREFIX}/opt/ruby/bin}
    "${HOME}/.rbenv/shims"
    "${HOME}/.tmuxifier/bin"
    "${path[@]}"
    /usr/local/opt/rbenv/shims
    /opt/X11/bin
    /Library/TeX/texbin
    /usr/texbin
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
