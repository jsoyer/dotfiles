#!/usr/bin/env zsh
# shellcheck shell=bash
# Custom functions

# Cross-platform clipboard helper
_clip() {
  if command -v pbcopy &>/dev/null; then
    pbcopy
  elif command -v wl-copy &>/dev/null; then
    wl-copy
  elif command -v xclip &>/dev/null; then
    xclip -selection clipboard
  else
    echo "(clipboard not available)" >&2
    cat >/dev/null
  fi
}

# Navigation with automatic listing
cx() {
  cd "$@" && l
}

# FZF-powered directory navigation
fcd() {
  local dir
  dir=$(fd --type d --hidden --exclude .git | fzf)
  if [[ -n "${dir}" ]]; then
    cd "${dir}" && l
  fi
}

# Copy file path to clipboard using FZF
f() {
  local file
  file=$(fd --type f --hidden --exclude .git | fzf)
  if [[ -n "${file}" ]]; then
    echo -n "${file}" | _clip
    echo "Copied to clipboard: ${file}"
  fi
}

# Open file in nvim via FZF
fv() {
  local file
  file=$(fd --type f --hidden --exclude .git | fzf)
  if [[ -n "${file}" ]]; then
    nvim "${file}"
  fi
}

# Aerospace window picker via FZF (macOS only)
if command -v aerospace &>/dev/null; then
  ff() {
    aerospace list-windows --all | fzf --bind 'enter:execute(bash -c "aerospace focus --window-id {1}")+abort'
  }
fi
