#!/usr/bin/env zsh
# shellcheck shell=bash
# Custom functions

# Navigation with automatic listing
# Usage: cx /path/to/dir
cx() {
  cd "$@" && l
}

# FZF-powered directory navigation
# Usage: fcd (then select from fuzzy finder)
fcd() {
  local dir
  dir=$(find . -type d -not -path '*/.*' | fzf)
  if [[ -n ${dir} ]]; then
    cd "${dir}" && l
  fi
}

# Copy file path to clipboard using FZF
# Usage: f (then select from fuzzy finder)
f() {
  local file
  file=$(find . -type f -not -path '*/.*' | fzf)
  if [[ -n ${file} ]]; then
    echo "${file}" | pbcopy
    echo "Copied to clipboard: ${file}"
  fi
}

# Open file in nvim via FZF
# Usage: fv (then select from fuzzy finder)
fv() {
  local file
  file=$(find . -type f -not -path '*/.*' | fzf)
    if [[ -n ${file} ]]; then
      nvim "${file}"
    fi
  }
