#!/usr/bin/env zsh
# shellcheck shell=bash
# Zsh aliases - sources shared aliases + zsh-specific additions

SHELL_NAME="zsh"

# Source shared aliases (common to bash and zsh)
source "${HOME}/.shell_common/aliases.sh"

# ============================================================================
# Zsh-specific aliases
# ============================================================================
alias zshconfig='nvim ~/.zshrc'
alias ohmyzsh='nvim ~/.oh-my-zsh'
