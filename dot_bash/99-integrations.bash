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
  if [[ -f /usr/share/doc/fzf/examples/completion.bash ]]; then
    source /usr/share/doc/fzf/examples/completion.bash
  fi
fi

# ============================================================================
# Bash completion
# ============================================================================
if [[ "${IS_MACOS}" == "true" ]]; then
  # Homebrew bash-completion (use $HOMEBREW_PREFIX to avoid subprocess)
  if [[ -r "${HOMEBREW_PREFIX:-/opt/homebrew}/etc/profile.d/bash_completion.sh" ]]; then
    source "${HOMEBREW_PREFIX:-/opt/homebrew}/etc/profile.d/bash_completion.sh"
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
# Kubectl completion (cached)
# ============================================================================
if command -v kubectl >/dev/null 2>&1; then
  _cache_eval kubectl 'kubectl completion bash'
  complete -o default -F __start_kubectl k
fi

# ============================================================================
# Helm completion (cached)
# ============================================================================
if command -v helm >/dev/null 2>&1; then
  _cache_eval helm 'helm completion bash'
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
# Starship prompt (must be before atuin which sets up precmd_functions)
# ============================================================================
if command -v starship >/dev/null 2>&1; then
  _cache_eval starship 'starship init bash'
fi

# ============================================================================
# Atuin - Magical shell history (cached)
# ============================================================================
if command -v atuin >/dev/null 2>&1; then
  _cache_eval atuin 'atuin init bash'
fi

# ============================================================================
# Direnv - Environment switcher (cached)
# ============================================================================
if command -v direnv >/dev/null 2>&1; then
  _cache_eval direnv 'direnv hook bash'
fi

# ============================================================================
# Zoxide - Smarter cd command (cached)
# Must be initialized LAST among cd-hooking tools
# ============================================================================
if command -v zoxide >/dev/null 2>&1; then
  _cache_eval zoxide 'zoxide init --cmd cd bash'
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
# Thefuck - Command correction (lazy-loaded, ~200ms cold start)
# ============================================================================
if command -v thefuck >/dev/null 2>&1; then
  fuck() {
    unset -f fuck
    eval "$(thefuck --alias)"
    fuck "$@"
  }
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
elif [[ "${IS_MACOS}" == "true" ]] && [[ -f "${HOMEBREW_PREFIX:-/opt/homebrew}/etc/bash_completion.d/git-completion.bash" ]]; then
  source "${HOMEBREW_PREFIX:-/opt/homebrew}/etc/bash_completion.d/git-completion.bash"
fi

# ============================================================================
# Terraform completion
# ============================================================================
if command -v terraform >/dev/null 2>&1; then
  complete -C terraform terraform
fi

# ============================================================================
# chezmoi background auto-update (login hook — fires if last check > 1h)
# ============================================================================
_chezmoi_bg_update() {
  local stampdir="${HOME}/.cache/chezmoi-autoupdate"
  mkdir -p "${stampdir}"
  local stamp="${stampdir}/last-login-check"
  local now
  now=$(date +%s)
  local last=0
  [[ -f "${stamp}" ]] && last=$(<"${stamp}")
  if (( now - last > 3600 )); then
    echo "${now}" > "${stamp}"
    (chezmoi-autoupdate &>/dev/null &)
  fi
}
command -v chezmoi >/dev/null 2>&1 && _chezmoi_bg_update

# ============================================================================
# ai-context auto-apply on cd (checks project-map.yaml)
# ============================================================================
if command -v ai-context &>/dev/null; then
  _aictx_auto_apply() {
    local project_map="${HOME}/.config/ai-context/project-map.yaml"
    [[ -f "$project_map" ]] || return
    [[ -d ".claude/skills" ]] && return
    if grep -q "$(pwd)" "$project_map" 2>/dev/null; then
      ai-context apply --auto --yes &>/dev/null &
    fi
  }
  _aictx_orig_cd() { builtin cd "$@" && _aictx_auto_apply; }
  alias cd='_aictx_orig_cd'
fi
