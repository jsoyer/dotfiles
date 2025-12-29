#!/usr/bin/env zsh
# shellcheck shell=bash
# Key bindings configuration

# ============================================================================
# Vi mode
# ============================================================================
# Type 'jj' to enter vi command mode
bindkey jj vi-cmd-mode

# ============================================================================
# Zsh autosuggestions keybindings
# ============================================================================
bindkey '^w' autosuggest-execute    # Ctrl+w: Execute suggestion
bindkey '^e' autosuggest-accept     # Ctrl+e: Accept suggestion
bindkey '^u' autosuggest-toggle     # Ctrl+u: Toggle suggestions
bindkey '^L' vi-forward-word        # Ctrl+L: Jump forward one word

# ============================================================================
# History navigation
# ============================================================================
bindkey '^k' up-line-or-search      # Ctrl+k: Previous command
bindkey '^j' down-line-or-search    # Ctrl+j: Next command
