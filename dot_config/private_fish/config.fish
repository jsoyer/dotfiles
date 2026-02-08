# ============================================================================
# Fish Shell Configuration
# ============================================================================

# ============================================================================
# Fisher bootstrap – auto-install on first launch
# ============================================================================
if not functions -q fisher
    curl -sL https://raw.githubusercontent.com/jorgebucaran/fisher/main/functions/fisher.fish | source
    fisher update
end

# ============================================================================
# Homebrew Configuration
# ============================================================================
# Initialize Homebrew environment (equivalent to 'brew shellenv')
set -gx HOMEBREW_PREFIX "/opt/homebrew"
set -gx HOMEBREW_CELLAR "/opt/homebrew/Cellar"
set -gx HOMEBREW_REPOSITORY "/opt/homebrew"
fish_add_path -g /opt/homebrew/bin
fish_add_path -g /opt/homebrew/sbin
set -gx MANPATH "/opt/homebrew/share/man" $MANPATH
set -gx INFOPATH "/opt/homebrew/share/info" $INFOPATH

# PATH Configuration
# ============================================================================
# User bins (highest priority)
fish_add_path -g $HOME/.antigravity/antigravity/bin
fish_add_path -g $HOME/.local/bin
fish_add_path -g $HOME/.jenv/bin
fish_add_path -g $HOME/.rbenv/shims
fish_add_path -g $HOME/.tmuxifier/bin

# Additional tool-specific paths
fish_add_path -g /usr/local/opt/rbenv/shims

# X11 and TeX
fish_add_path -g /opt/X11/bin
fish_add_path -g /Library/TeX/texbin
fish_add_path -g /usr/texbin

# ============================================================================
# Environment Variables
# ============================================================================
set -gx LANG en_US.UTF-8
set -gx EDITOR nvim
set -gx DOCKER_CONFIG $HOME/.docker
set -gx HOMEBREW_CASK_OPTS "--appdir=/Applications"
set -gx KUBECONFIG $HOME/.kube/config

# ============================================================================
# Catppuccin Mocha Theme
# ============================================================================
fish_config theme choose "Catppuccin Mocha"

# Prompt is managed by Tide (installed via Fisher / fish_plugins)

# ============================================================================
# Environment Variables (Catppuccin Mocha)
# ============================================================================
set -gx BAT_THEME "Catppuccin Mocha"
set -gx FZF_DEFAULT_OPTS "\
--color=bg+:#313244,bg:#1e1e2e,spinner:#f5e0dc,hl:#f38ba8 \
--color=fg:#cdd6f4,header:#f38ba8,info:#cba6f7,pointer:#f5e0dc \
--color=marker:#f5e0dc,fg+:#cdd6f4,prompt:#cba6f7,hl+:#f38ba8"
set -gx FZF_DEFAULT_COMMAND 'fd --type f --hidden --follow --exclude .git'

# Eza colors (Catppuccin Mocha)
set -gx EZA_COLORS "uu=38;5;147:gu=38;5;147:ur=38;5;203:uw=38;5;204:ux=38;5;148:ue=38;5;148:gr=38;5;203:gw=38;5;204:gx=38;5;148:tr=38;5;203:tw=38;5;204:tx=38;5;148:da=38;5;110:sn=38;5;180:sb=38;5;180:xa=38;5;147"

# LS_COLORS with vivid (Catppuccin Mocha)
if command -v vivid &> /dev/null
    set -gx LS_COLORS (vivid generate catppuccin-mocha)
end

# ============================================================================
# Modern CLI Tools Integration
# ============================================================================

# Eza (modern ls)
if command -v eza &> /dev/null
    alias ls='eza --icons --group-directories-first'
    alias ll='eza -l --icons --group-directories-first'
    alias la='eza -la --icons --group-directories-first'
    alias lt='eza --tree --level=2 --icons'
end

# Bat (modern cat)
if command -v bat &> /dev/null
    alias cat='bat --style=auto'
end

# ============================================================================
# Development Environment Managers
# ============================================================================

# Pyenv - Python version management
if test -d $HOME/.pyenv
    set -gx PYENV_ROOT $HOME/.pyenv
    fish_add_path $PYENV_ROOT/bin
end
if command -v pyenv &> /dev/null
    pyenv init - | source
end

# Jenv - Java version management
if test -d $HOME/.jenv
    fish_add_path $HOME/.jenv/bin
end
if command -v jenv &> /dev/null
    jenv init - | source
end

# Rbenv - Ruby version management
if test -d $HOME/.rbenv
    fish_add_path $HOME/.rbenv/bin
end
if command -v rbenv &> /dev/null
    rbenv init - fish | source
end

# NVM - Node version management
if test -d $HOME/.nvm
    set -gx NVM_DIR $HOME/.nvm
end

# ============================================================================
# Shell Options
# ============================================================================

# Disable greeting
set -g fish_greeting

# Enable vi mode (optional - uncomment if you prefer vi keybindings)
# fish_vi_key_bindings

# ============================================================================
# Aliases
# ============================================================================

# Git shortcuts
alias g='git'
alias gs='git status'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gl='git pull'
alias gd='git diff'
alias gco='git checkout'
alias gb='git branch'

# Docker shortcuts
alias d='docker'
alias dc='docker compose'
alias dps='docker ps'
alias dimg='docker images'

# Kubernetes shortcuts
alias k='kubectl'
alias kgp='kubectl get pods'
alias kgs='kubectl get services'
alias kgd='kubectl get deployments'

# Navigation
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'

# Safety
alias rm='rm -i'
alias cp='cp -i'
alias mv='mv -i'
