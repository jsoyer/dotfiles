#!/usr/bin/env bash
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

# SSH wrapper for tmux window naming
ssh() {
  # Extract hostname from ssh arguments
  local host=""
  for arg in "$@"; do
    # Skip flags
    [[ "$arg" == -* ]] && continue
    # First non-flag argument is the destination
    if [[ "$arg" == *@* ]]; then
      host="${arg##*@}"  # user@host -> host
    else
      host="$arg"
    fi
    break
  done

  # Remove domain if present (user@host.domain -> host)
  host="${host%%.*}"

  # Rename tmux window if in tmux
  if [[ -n "$TMUX" ]] && [[ -n "$host" ]]; then
    tmux rename-window "$host"
    command ssh "$@"
    # Restore window name after SSH exits
    tmux rename-window "bash"
  else
    command ssh "$@"
  fi
}
