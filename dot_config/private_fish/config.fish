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
# Initialize Homebrew environment (works on Intel /usr/local and Apple Silicon /opt/homebrew)
if command -q brew
    eval (brew shellenv)
end

# PATH Configuration
# ============================================================================
# User bins (highest priority)
fish_add_path -g $HOME/.antigravity/antigravity/bin
fish_add_path -g $HOME/.local/bin
fish_add_path -g $HOME/.jenv/bin
fish_add_path -g $HOME/.rbenv/shims
fish_add_path -g $HOME/.tmuxifier/bin

# Tool-specific paths (use $HOMEBREW_PREFIX set by brew shellenv above)
if set -q HOMEBREW_PREFIX
    fish_add_path -g $HOMEBREW_PREFIX/opt/ruby/bin
end

# X11 and TeX
fish_add_path -g /opt/X11/bin
fish_add_path -g /Library/TeX/texbin
fish_add_path -g /usr/texbin
fish_add_path -g /usr/local/texlive/2025basic/bin/universal-darwin

# ============================================================================
# Machine Profile Detection
# ============================================================================
if test (hostname) = "jsoyer-macOS"
    set -gx MACHINE_PROFILE "mac-pro"
else
    set -gx MACHINE_PROFILE "mac-personal"
end

# ============================================================================
# Environment Variables
# ============================================================================
set -gx LANG en_US.UTF-8
set -gx EDITOR nvim
set -gx DOCKER_CONFIG $HOME/.docker

# Homebrew Cask appdir based on machine profile
if test "$MACHINE_PROFILE" = "mac-pro"
    set -gx HOMEBREW_CASK_OPTS "--appdir=$HOME/Applications"
end

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

# Neovim with raised file descriptor limit
function nvim --wraps=nvim
    ulimit -n 4096
    command nvim $argv
end
alias vim='nvim'
alias v='nvim'
alias la='tree'
alias cat='bat'
alias http='xh'
alias as='aerospace'
alias asr='atuin scripts run'

# Eza (modern ls replacement)
alias ls='eza --color=always --icons'
alias ll='eza -l --color=always --icons --git -a'
alias l='eza -l --icons --git -a'
alias lt='eza --tree --level=2 --long --icons --git'
alias ltree='eza --tree --level=2 --icons --git'
alias zl='eza -lagX --icons --color=always'

# SSH wrapper for Kitty kitten ssh
function ssh --wraps=ssh
    if test "$TERM" = "xterm-kitty"
        kitten ssh $argv
    else
        command ssh $argv
    end
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
# System
# ============================================================================
alias cl='clear'
alias bcask='brew cask'
alias tbx='/usr/bin/toolbox run zsh'

# ============================================================================
# Navigation
# ============================================================================
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias .....='cd ../../../..'
alias ......='cd ../../../../..'

# ============================================================================
# Git
# ============================================================================
alias gc='git commit -m'
alias gca='git commit -a -m'
alias gp='git push origin HEAD'
alias gpu='git pull origin'
alias gst='git status'
alias glog="git log --graph --topo-order --pretty='%w(100,0,6)%C(yellow)%h%C(bold)%C(black)%d %C(cyan)%ar %C(green)%an%n%C(bold)%C(white)%s %N' --abbrev-commit"
alias gdiff='git diff'
alias gco='git checkout'
alias gb='git branch'
alias gba='git branch -a'
alias gadd='git add'
alias ga='git add -p'
alias gcoall='git checkout -- .'
alias gr='git remote'
alias gre='git reset'

# ============================================================================
# Git (Additions)
# ============================================================================
alias gs='git status -s'
alias gsw='git switch'
alias gswc='git switch -c'
alias grs='git restore'
alias grbi='git rebase -i'
alias gcl='git clone'

# ============================================================================
# Docker / Podman
# ============================================================================
alias dco='docker compose'
alias dps='docker ps'
alias dpa='docker ps -a'
alias dl='docker ps -l -q'
alias dx='docker exec -it'

# docker-compose -> docker compose (function for compatibility)
function docker-compose
    docker compose $argv
end

# Podman Compose
function podman-compose
    podman compose $argv
end

# ============================================================================
# Kubernetes
# ============================================================================
alias k='kubectl'
alias ka='kubectl apply -f'
alias kg='kubectl get'
alias kd='kubectl describe'
alias kdel='kubectl delete'
alias kl='kubectl logs -f'
alias kgpo='kubectl get pod'
alias kgd='kubectl get deployments'
alias kc='kubectx'
alias kns='kubens'
alias ke='kubectl exec -it'
alias kcns='kubectl config set-context --current --namespace'

# ============================================================================
# Security & Pentesting tools (not on mac-pro)
# ============================================================================
if test "$MACHINE_PROFILE" != "mac-pro"
    command -q gobuster; and alias gobust='gobuster dir --wordlist ~/security/wordlists/diccnoext.txt --wildcard --url'
    command -q dirsearch; and alias dirsearch='python dirsearch.py -w db/dicc.txt -b -u'
    test -x ~/hacking/tools/massdns/bin/massdns; and alias massdns='~/hacking/tools/massdns/bin/massdns -r ~/hacking/tools/massdns/lists/resolvers.txt -t A -o S bf-targets.txt -w livehosts.txt -s 4000'
    alias server='python -m http.server 4445'
    command -q ngrok; and alias tunnel='ngrok http 4445'
    command -q ffuf; and alias fuzz='ffuf -w ~/hacking/SecLists/content_discovery_all.txt -mc all -u'
    command -q nmap; and alias nm='nmap -sC -sV -oN nmap'
end

# ============================================================================
# Homebrew (via breww wrapper)
# ============================================================================
alias b='breww'
alias bi='breww install'
alias bu='breww update'
alias bup='breww upgrade'
alias bcu='breww cu -a'
alias bs='breww search'
alias bl='breww list'
alias bun='breww uninstall'
alias bci='breww cleanup'
alias binfo='breww info'
alias bd='breww doctor'

# ============================================================================
# Chezmoi
# ============================================================================
alias c='chezmoi'
alias cdiff='chezmoi diff'
alias cedit='chezmoi edit'
alias cadd='chezmoi add'
alias creadd='chezmoi re-add'
alias cs='chezmoi status'
alias ccd='chezmoi cd'

# Chezmoi apply/update with verbose mode
function ca
    chezmoi apply -v $argv
end

function cu
    chezmoi update -v $argv
end

# Chezmoi update + package updates
function cup
    chezmoi update -v $argv

    set os (uname -s | tr '[:upper:]' '[:lower:]')

    switch $os
        case darwin
            echo "🍺 Updating Homebrew packages..."
            if test "$MACHINE_PROFILE" = "mac-pro"
                brew upgrade
            else
                brew upgrade --greedy
            end
            brew cleanup
            brew update
            echo "📱 Updating App Store apps..."
            if command -q mas
                mas upgrade
            else
                echo "⚠️  mas-cli not installed (run: brew install mas)"
            end
        case linux
            set arch (uname -m)
            if string match -q "*rpi*" $arch
                echo "🐍 Updating apt packages..."
                sudo apt update
                sudo apt dist-upgrade -y
                sudo apt autoremove -y
            else if command -q dnf
                if command -q rpm-ostree
                    echo "🐧 Updating Fedora Atomic..."
                    sudo rpm-ostree upgrade
                else
                    echo "🐧 Updating Fedora packages..."
                    sudo dnf upgrade -y
                end
            end
        case windows
            echo "🪣 Updating Scoop packages..."
            scoop update
            scoop update --all
    end

    # Docker/Podman maintenance
    if command -q docker
        if docker info >/dev/null 2>&1
            set CONTAINER_RUNTIME "docker"
            set EMOJI "🐳"
        end
    else if command -q podman
        if podman info >/dev/null 2>&1
            set CONTAINER_RUNTIME "podman"
            set EMOJI "🦭"
        end
    end

    if set -q CONTAINER_RUNTIME
        echo "$EMOJI Running container maintenance..."
        $CONTAINER_RUNTIME ps
        
        for compose_file in (find $HOME -name "docker-compose.yml" -not -path "*/.*" 2>/dev/null)
            set project_dir (dirname $compose_file)
            set project_name (basename $project_dir)
            
            if $CONTAINER_RUNTIME compose -f $compose_file ps --services --filter "status=running" 2>/dev/null | grep -q .
                echo "  → Updating $project_name"
                set pull_output ($CONTAINER_RUNTIME compose -f $compose_file pull 2>&1)
                
                if echo "$pull_output" | grep -qE "(Pulling|Downloading|Extracting|Status: Downloaded)"
                    echo "  🔄 New images found, restarting containers..."
                    $CONTAINER_RUNTIME compose -f $compose_file up -d
                else
                    echo "  ✅ No new images, containers up to date"
                end
            end
        end
        
        $CONTAINER_RUNTIME image prune -a -f
        echo "✨ Container maintenance complete!"
    end

    echo "✅ Update complete!"
end

# ============================================================================
# Jujutsu (jj)
# ============================================================================
alias j='jj'
alias js='jj st'
alias jl="jj log -r 'all()'"
alias jd='jj diff'
alias jn='jj new'
alias jui='jjui'
alias jundo='jj undo'
alias jp='jj git push'
alias jf='jj git fetch'

# ============================================================================
# Tmux
# ============================================================================
alias t='tmux'
alias ta='tmux attach -t'
alias tl='tmux list-sessions'
alias tk='tmux kill-session -t'
alias tns='tmux new-session -s'

# ============================================================================
# lazygit / lazydocker
# ============================================================================
alias lg='lazygit'
alias ld='lazydocker'

# ============================================================================
# Disk / System
# ============================================================================
if command -q dust
    alias du='dust'
end
if command -q duf
    alias df='duf'
end
if command -q btop
    alias top='btop'
end
if command -q procs
    alias ps='procs'
end
alias ports='lsof -iTCP -sTCP:LISTEN -n -P'
function myip
    curl -s ifconfig.me; and echo
end
function path
    string join \n $PATH
end

# ============================================================================
# Markdown (glow)
# ============================================================================
if command -q glow
    alias md='glow'
end

# ============================================================================
# Search (ripgrep / fd)
# ============================================================================
alias rgf='rg --files-with-matches'
alias rgi='rg --ignore-case'
alias fdf='fd --type f'
alias fdd='fd --type d'

# ============================================================================
# Python (uv / poetry / venv)
# ============================================================================
# uv
alias uvi='uv init'
alias uva='uv add'
alias uvr='uv run'
alias uvs='uv sync'
alias uvp='uv pip'
alias uvpi='uv pip install'
alias uvvenv='uv venv'

# poetry
alias po='poetry'
alias poi='poetry install'
alias poa='poetry add'
alias por='poetry run'
alias pos='poetry shell'
alias pou='poetry update'
alias pol='poetry lock'

# venv shortcuts
function venv
    set -l dir (test (count $argv) -gt 0; and echo $argv[1]; or echo ".venv")
    uv venv $dir
end
function activate
    set -l dir (test (count $argv) -gt 0; and echo $argv[1]; or echo ".venv")
    if test -f "$dir/bin/activate.fish"
        source "$dir/bin/activate.fish"
    else
        echo "No virtualenv found at $dir/bin/activate.fish"
        return 1
    end
end

# ============================================================================
# Misc
# ============================================================================
function mkd
    mkdir -p $argv; and cd $argv[-1]
end

# ============================================================================
# Claude Code
# ============================================================================
alias cco='claude --model opus'
alias ccs='claude --model sonnet'
alias cch='claude --model haiku'

# ============================================================================
# fdupes (duplicate file finder)
# ============================================================================
alias dup='fdupes -r'
alias dupsize='fdupes -rS'
alias dupsum='fdupes -rm'
function dupdel
    set -l target (test (count $argv) -gt 0; and echo $argv; or echo ".")
    echo "WARNING: this will DELETE duplicate files (keeping one copy) in: $target"
    read -P "Continue? (y/N) " reply
    if string match -qi 'y' $reply
        fdupes -rdN $argv
    else
        echo "Aborted."
    end
end

# ============================================================================
# Custom functions (FZF-powered)
# ============================================================================
function cx --description 'cd and list'
    cd $argv; and l
end

function fcd --description 'FZF directory navigation'
    set -l dir (fd --type d --hidden --exclude .git | fzf)
    if test -n "$dir"
        cd $dir; and l
    end
end

function f --description 'Copy file path to clipboard via FZF'
    set -l file (fd --type f --hidden --exclude .git | fzf)
    if test -n "$file"
        if command -q pbcopy
            echo -n $file | pbcopy
        else if command -q wl-copy
            echo -n $file | wl-copy
        else if command -q xclip
            echo -n $file | xclip -selection clipboard
        end
        echo "Copied to clipboard: $file"
    end
end

if command -q aerospace
    function ff --description 'Aerospace window picker via FZF'
        aerospace list-windows --all | fzf --bind 'enter:execute(bash -c "aerospace focus --window-id {1}")+abort'
    end
end

function fv --description 'Open file in nvim via FZF'
    set -l file (fd --type f --hidden --exclude .git | fzf)
    if test -n "$file"
        nvim $file
    end
end

# ============================================================================
# Zoxide (smart cd)
# ============================================================================
if command -q zoxide
    zoxide init --cmd cd fish | source
end

# ============================================================================
# Atuin - Magical shell history
# ============================================================================
if command -q atuin
    atuin init fish | source
end

# ============================================================================
# Direnv - Environment switcher
# ============================================================================
if command -q direnv
    direnv hook fish | source
end

# ============================================================================
# Thefuck - Command correction (lazy-loaded)
# ============================================================================
if command -q thefuck
    function fuck
        functions -e fuck
        thefuck --alias | source
        fuck $argv
    end
end

# ============================================================================
# OrbStack - Docker/Kubernetes alternative (macOS only)
# ============================================================================
if test -f ~/.orbstack/shell/init.fish
    source ~/.orbstack/shell/init.fish 2>/dev/null
end
