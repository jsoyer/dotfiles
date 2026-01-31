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

# ============================================================================
# Smart Brew Install Wrapper
# ============================================================================
# Usage: bi install <package1> <package2>
# This function installs packages with Homebrew, then automatically updates
# the correct Brewfile based on the machine profile, and syncs to git.
bi() {
  # 1. Ensure we are on a Mac
  if [[ "$MACHINE_PROFILE" != "mac-pro" && "$MACHINE_PROFILE" != "mac-personal" ]]; then
    echo "Cette fonction est uniquement pour les machines macOS avec Homebrew."
    return 1
  fi

  # 2. Execute the real brew command
  echo "==> Exécution de 'brew $@'..."
  brew "$@"

  local brew_exit_code=$?
  if [[ ${brew_exit_code} -ne 0 ]]; then
    echo "Erreur lors de l'exécution de brew. Abandon de la mise à jour du Brewfile."
    return ${brew_exit_code}
  fi

  # 3. Determine the correct Brewfile to update
  local target_brewfile
  if [[ "$MACHINE_PROFILE" == "mac-pro" ]]; then
    target_brewfile="dot_private/Brewfile_pro"
    # For pro, we dump ALL packages, assuming it's a dedicated machine
    # We will split them later manually if needed between common and pro
    echo "==> Mise à jour de la liste PRO..."
    brew bundle dump --force --file="$(chezmoi source-path)/${target_brewfile}"
  else
    # For personal, we also dump all packages
    target_brewfile="dot_private/Brewfile_personal"
    echo "==> Mise à jour de la liste PERSONAL..."
    brew bundle dump --force --file="$(chezmoi source-path)/${target_brewfile}"
  fi

  # 4. Commit and Push changes
  echo "==> Synchronisation avec le dépôt Git..."
  (
    cd "$(chezmoi source-path)"
    git add .
    # Using 'style' as it's an automated formatting/update
    git commit -m "style(brew): update brewfiles via bi wrapper" || true
    git push
  )

  echo "✅ Brewfile mis à jour et poussé sur GitHub !"
}
