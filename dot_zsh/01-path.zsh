#!/usr/bin/env zsh
# shellcheck shell=bash
# PATH configuration

# Build PATH in correct order (highest priority first)
typeset -U path  # Ensure uniqueness

# Add ~/bin for Raspberry Pi user scripts, if it exists
if [[ -d "$HOME/bin" ]] && [[ "$MACHINE_PROFILE" == "rpi" ]]; then
  path=("$HOME/bin" $path)
fi

# User bins (highest priority) — re-asserted after Homebrew below.
_user_bins=(
  "${HOME}/.opencode/bin"
  "${HOME}/.npm-global/bin"
  "${HOME}/.local/bin"
  "${HOME}/.cargo/bin"
)
path=("${_user_bins[@]}" "${path[@]}")

# mise shims — appended (lowest priority) on purpose: `mise activate` owns the
# PATH in interactive shells, the shims are only a fallback for non-interactive
# contexts (IDEs, cron, scripts) where the activation hook never runs.
_mise_shims="${XDG_DATA_HOME:-$HOME/.local/share}/mise/shims"
[[ -d "$_mise_shims" ]] && path=("${path[@]}" "$_mise_shims")
unset _mise_shims

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
# never makes it in (mtr, unbound, php-fpm live there), and bin/ keeps whatever
# position it had. On macOS, /etc/zprofile's path_helper (re-run by every nested
# login shell: tmux, new terminal tabs) moves /usr/bin ahead of it, so python3
# and bash resolved to Apple's 3.9 / 3.2. Re-prepend both explicitly; typeset -U
# keeps the first occurrence, so this moves them to the front.
for _brew_dir in /opt/homebrew /usr/local /home/linuxbrew/.linuxbrew "${HOME}/.linuxbrew"; do
  [[ -x "$_brew_dir/bin/brew" ]] || continue
  path=("$_brew_dir/bin" "$_brew_dir/sbin" "${path[@]}")
  break
done
unset _brew_dir
path=("${_user_bins[@]}" "${path[@]}")
unset _user_bins

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
