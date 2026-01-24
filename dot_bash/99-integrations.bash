#!/usr/bin/env bash
# External tools and integrations

# ============================================================================
# FZF - Fuzzy finder
# ============================================================================
if [[ -f ~/.fzf.bash ]]; then
  source ~/.fzf.bash
elif [[ -f /usr/share/doc/fzf/examples/key-bindings.bash ]]; then
  # Debian/Ubuntu location
  source /usr/share/doc/fzf/examples/key-bindings.bash
  source /usr/share/doc/fzf/examples/completion.bash
fi

# ============================================================================
# Bash completion
# ============================================================================
if [[ "${IS_MACOS}" == "true" ]]; then
  # Homebrew bash-completion
  if [[ -r "$(brew --prefix 2>/dev/null)/etc/profile.d/bash_completion.sh" ]]; then
    source "$(brew --prefix)/etc/profile.d/bash_completion.sh"
  fi
else
  # Linux bash-completion
  if [[ -f /etc/bash_completion ]]; then
    source /etc/bash_completion
  elif [[ -f /usr/share/bash-completion/bash_completion ]]; then
    source /usr/share/bash-completion/bash_completion
  fi
fi

# ============================================================================
# Kubectl completion
# ============================================================================
if command -v kubectl >/dev/null 2>&1; then
  source <(kubectl completion bash)
  complete -o default -F __start_kubectl k
fi

# ============================================================================
# Helm completion
# ============================================================================
if command -v helm >/dev/null 2>&1; then
  source <(helm completion bash)
fi

# ============================================================================
# Docker completion
# ============================================================================
if command -v docker >/dev/null 2>&1; then
  if [[ -f /usr/share/bash-completion/completions/docker ]]; then
    source /usr/share/bash-completion/completions/docker
  fi
fi

# ============================================================================
# Zoxide - Smarter cd command
# ============================================================================
if command -v zoxide >/dev/null 2>&1; then
  eval "$(zoxide init bash)"
fi

# ============================================================================
# Atuin - Magical shell history (optional)
# ============================================================================
if command -v atuin >/dev/null 2>&1; then
  eval "$(atuin init bash)"
fi

# ============================================================================
# Direnv - Environment switcher (optional)
# ============================================================================
if command -v direnv >/dev/null 2>&1; then
  eval "$(direnv hook bash)"
fi

# ============================================================================
# OrbStack - Docker/Kubernetes alternative (macOS only)
# ============================================================================
if [[ "${IS_MACOS}" == "true" ]] && [[ -f ~/.orbstack/shell/init.bash ]]; then
  source ~/.orbstack/shell/init.bash 2>/dev/null || :
fi

# ============================================================================
# Nix package manager (optional)
# ============================================================================
if [[ -f /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh ]]; then
  source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh
fi

# ============================================================================
# Thefuck - Command correction (optional)
# ============================================================================
if command -v thefuck >/dev/null 2>&1; then
  eval "$(thefuck --alias)"
fi

# ============================================================================
# AWS completion
# ============================================================================
if command -v aws_completer >/dev/null 2>&1; then
  complete -C aws_completer aws
fi

# ============================================================================
# Git completion
# ============================================================================
if [[ -f /usr/share/bash-completion/completions/git ]]; then
  source /usr/share/bash-completion/completions/git
elif [[ "${IS_MACOS}" == "true" ]] && [[ -f "$(brew --prefix 2>/dev/null)/etc/bash_completion.d/git-completion.bash" ]]; then
  source "$(brew --prefix)/etc/bash_completion.d/git-completion.bash"
fi

# ============================================================================
# Terraform completion
# ============================================================================
if command -v terraform >/dev/null 2>&1; then
  complete -C terraform terraform
fi
