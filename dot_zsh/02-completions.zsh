#!/usr/bin/env zsh
# shellcheck shell=bash
# Completion system configuration

# Completion settings
setopt prompt_subst
zstyle ':completion:*' matcher-list 'm:{a-z}={A-Za-z}'

# Load and cache completions — skip if Oh-My-Zsh already called compinit
if [[ -z "$ZSH_COMPDUMP" ]]; then
  autoload -Uz compinit
  typeset -a _stale_dumps
  _stale_dumps=( "${HOME}"/.zcompdump(N.mh+24) )
  if (( ${#_stale_dumps} )); then
    compinit
  else
    compinit -C
  fi
  unset _stale_dumps
fi

# Fallback file/dir completion for modern CLI aliases (eza, bat, etc.)
# Homebrew/AUR ship their own _eza; this is a safety net for apt/dnf installs
(( $+functions[_eza] )) || compdef _files eza
(( $+functions[_bat] )) || compdef _files bat

# Load bashcompinit only when aws_completer is present (avoids 30ms overhead otherwise)
if (( $+commands[aws_completer] )); then
  autoload -Uz bashcompinit
  bashcompinit
  complete -C aws_completer aws
fi

# Carapace — multi-shell completion engine (cached init)
if (( $+commands[carapace] )); then
  _cache_eval carapace 'carapace _carapace zsh'
fi
