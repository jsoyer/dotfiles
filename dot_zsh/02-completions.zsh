#!/usr/bin/env zsh
# shellcheck shell=bash
# Completion system configuration

# Completion settings
setopt prompt_subst
zstyle ':completion:*' matcher-list 'm:{a-z}={A-Za-z}'

# Load and cache completions
autoload -Uz compinit

# Only check compinit cache once per day for faster startup
for dump in "${HOME}"/.zcompdump(N.mh+24); do
  compinit
done
compinit -C  # Skip security check for faster startup

autoload -Uz bashcompinit
bashcompinit

# Tool-specific completions
# Note: kubectl completion is already loaded by oh-my-zsh kubectl plugin

if command -v aws_completer >/dev/null 2>&1; then
  complete -C '/usr/local/bin/aws_completer' aws
fi
