# 🐚 Bash Configuration

> Modern, modular Bash configuration mirroring the Zsh setup for consistency across shells

## 📁 Architecture

```
~/.bash_profile              # Login shell entry point (sources .bashrc)
~/.bashrc                    # Main configuration entry point
~/.bash/                     # Modular configuration directory
  ├── 00-env.bash           # Environment & theme configurations
  ├── 01-path.bash          # PATH management with lazy loading
  ├── 10-aliases.bash       # Command aliases & shortcuts
  ├── 20-functions.bash     # Custom shell functions
  └── 99-integrations.bash  # External tool integrations
```

> **Note for macOS users**: On macOS, terminals start login shells which read `.bash_profile`, not `.bashrc`. The `.bash_profile` simply sources `.bashrc` to unify behavior across platforms.

## 🎯 Why Bash?

While Zsh is the primary shell, Bash configuration is maintained for:

- 🖥️ **Minimal servers** - When only Bash is available
- 🐳 **Containers** - Docker/Kubernetes debugging
- 🔧 **Recovery mode** - System troubleshooting
- 🌐 **Universal compatibility** - Works everywhere

## 🎨 Theme: Catppuccin Mocha / Snazzy

Platform-specific theming with automatic detection:

| Platform | Theme | Colors |
|----------|-------|--------|
| 🍎 macOS | Catppuccin Mocha | Purple/Pink |
| 🐧 Linux | Snazzy | Cyan/Yellow |
| 🍓 Raspberry Pi | Snazzy | Cyan/Yellow |

## 🚀 Modern CLI Tools

Same modern tool aliases as Zsh:

| Traditional | Modern | Alias |
|-------------|--------|-------|
| `ls` | eza | `ls`, `ll`, `l`, `lt` |
| `cat` | bat | `cat` |
| `cd` | zoxide | `z` |
| `vim` | neovim | `vim` |
| `curl` | xh | `http` |

## 📝 File-by-File Documentation

### ~/.bash_profile

**Purpose:** Login shell entry point (macOS terminal sessions)

**Features:**
- Sources `~/.bashrc` for all configuration
- Required on macOS where terminals start login shells

```bash
# Source .bashrc for interactive shell configuration
if [[ -f "${HOME}/.bashrc" ]]; then
  source "${HOME}/.bashrc"
fi
```

---

### ~/.bashrc

**Purpose:** Main configuration entry point

**Features:**
- Interactive shell detection
- Shell options (histappend, autocd, globstar, etc.)
- Modular config loading from `~/.bash/`
- Starship prompt initialization

**Shell Options:**
```bash
shopt -s histappend       # Append to history
shopt -s checkwinsize     # Update terminal size
shopt -s cdspell          # Correct cd typos
shopt -s autocd           # cd without typing cd
shopt -s globstar         # ** recursive glob
shopt -s nocaseglob       # Case-insensitive glob
```

---

### 00-env.bash

**Purpose:** Core environment variables and platform detection

**Sections:**

#### 🌍 Platform Detection
```bash
IS_MACOS=true/false
IS_LINUX=true/false
IS_RPI=true/false
PLATFORM=macos/linux/rpi
```

#### 🏠 Hostname Icons (Starship)
```bash
macOS:       ⌘
bbh-network: 🌐
omv-*:       🐟
Other Linux: 🍓
```

#### 🌐 Locale
```bash
LANG=en_US.UTF-8
LC_ALL=en_US.UTF-8
```

#### 📜 History
```bash
HISTFILE=~/.bash_history
HISTSIZE=50000
HISTFILESIZE=50000
HISTCONTROL=ignoreboth:erasedups
HISTIGNORE="ls:cd:exit:clear:history"
```

#### 🎨 Theme Configuration

**macOS (Catppuccin Mocha):**
```bash
STARSHIP_CONFIG=~/.config/starship/starship.toml
FZF_DEFAULT_OPTS="--color=bg+:#313244,bg:#1e1e2e..."
BAT_THEME="Catppuccin Mocha"
LS_COLORS=$(vivid generate catppuccin-mocha)
```

**Linux/RPi (Snazzy):**
```bash
STARSHIP_CONFIG=~/.config/starship/starship-rpi.toml
FZF_DEFAULT_OPTS="--color=bg+:#3a3d4d,bg:#282a36..."
BAT_THEME="ansi"
LS_COLORS=$(vivid generate snazzy)
```

---

### 01-path.bash

**Purpose:** PATH management with performance optimization

**Helper Functions:**
```bash
path_prepend "/path"  # Add to beginning if exists
path_append "/path"   # Add to end if exists
```

**PATH Priority (highest first):**
1. `~/.local/bin`
2. `~/.cargo/bin`
3. `~/.antigravity/antigravity/bin` (macOS)
4. `~/.jenv/bin` (macOS)
5. `~/.rbenv/shims` (macOS)
6. `~/.tmuxifier/bin` (macOS)
7. System paths
8. `/opt/X11/bin`, `/Library/TeX/texbin` (macOS)
9. `~/.lmstudio/bin`

**⚡ Lazy Loading (macOS):**
```bash
# pyenv loads only when first called
pyenv() {
  unset -f pyenv
  eval "$(command pyenv init -)"
  pyenv "$@"
}

# jenv loads only when first called  
jenv() {
  unset -f jenv
  eval "$(command jenv init -)"
  jenv "$@"
}
```

---

### 10-aliases.bash

**Purpose:** Command shortcuts (identical to Zsh)

#### 🔧 Configuration
```bash
bashconfig    # Edit ~/.bashrc with nvim
```

#### 🚀 Modern Replacements
```bash
vim='nvim'
cat='bat'
http='xh'
la='tree'
```

#### 📂 Eza (ls replacement)
```bash
ls='eza --color=always --icons'
ll='eza -l --color=always --icons --git -a'
l='eza -l --icons --git -a'
lt='eza --tree --level=2 --long --icons --git'
ltree='eza --tree --level=2 --icons --git'
zl='eza -lagX --icons --color=always'
```

#### 📁 Navigation
```bash
..      # cd ..
...     # cd ../..
....    # cd ../../..
.....   # cd ../../../..
......  # cd ../../../../..
iclouddrive  # cd to iCloud Drive
```

#### 🔀 Git
```bash
gc='git commit -m'
gca='git commit -a -m'
gp='git push origin HEAD'
gpu='git pull origin'
gst='git status'
glog='git log --graph --pretty=...'
gdiff='git diff'
gco='git checkout'
gb='git branch'
gba='git branch -a'
gadd='git add'
ga='git add -p'
gcoall='git checkout -- .'
gr='git remote'
gre='git reset'
```

#### 🐳 Docker
```bash
dco='docker compose'
dps='docker ps'
dpa='docker ps -a'
dl='docker ps -l -q'
dx='docker exec -it'
```

#### ☸️ Kubernetes
```bash
k='kubectl'
ka='kubectl apply -f'
kg='kubectl get'
kd='kubectl describe'
kdel='kubectl delete'
kl='kubectl logs -f'
kgpo='kubectl get pod'
kgd='kubectl get deployments'
kc='kubectx'
kns='kubens'
ke='kubectl exec -it'
kcns='kubectl config set-context --current --namespace'
```

#### 🔐 Security & Pentesting
```bash
gobust='gobuster dir --wordlist ~/security/wordlists/diccnoext.txt --wildcard --url'
dirsearch='python dirsearch.py -w db/dicc.txt -b -u'
massdns='~/hacking/tools/massdns/bin/massdns -r ...'
server='python -m http.server 4445'
tunnel='ngrok http 4445'
fuzz='ffuf -w ~/hacking/SecLists/content_discovery_all.txt -mc all -u'
nm='nmap -sC -sV -oN nmap'
```

---

### 20-functions.bash

**Purpose:** Custom shell functions

#### 📂 cx - Change directory and list
```bash
cx /path/to/dir  # cd + automatic eza listing
```

#### 🔍 fcd - Fuzzy directory navigation
```bash
fcd  # Interactive FZF directory picker, then cd
```

#### 📋 f - Copy file path with FZF
```bash
f  # Select file with FZF, copy path to clipboard
```

#### ✏️ fv - Open file in nvim with FZF
```bash
fv  # Select file with FZF, open in neovim
```

#### 🔗 ssh - Tmux window naming wrapper
```bash
ssh user@host  # Automatically renames tmux window to hostname
               # Restores window name after disconnect
```

---

### 99-integrations.bash

**Purpose:** External tool integrations

#### 🔍 FZF
```bash
# Loads from ~/.fzf.bash or system location
# Provides Ctrl+R history, Ctrl+T file finder
```

#### 📝 Bash Completion
```bash
# macOS: Homebrew bash-completion
# Linux: /etc/bash_completion or /usr/share/bash-completion/
```

#### ☸️ Kubectl Completion
```bash
source <(kubectl completion bash)
complete -o default -F __start_kubectl k  # Alias completion
```

#### ⎈ Helm Completion
```bash
source <(helm completion bash)
```

#### 🐳 Docker Completion
```bash
# Loads from /usr/share/bash-completion/completions/docker
```

#### 🚀 Zoxide
```bash
eval "$(zoxide init bash)"  # Enables 'z' command
```

#### 📜 Atuin
```bash
eval "$(atuin init bash)"  # Magical shell history
```

#### 📂 Direnv
```bash
eval "$(direnv hook bash)"  # Auto-load .envrc files
```

#### 🐳 OrbStack (macOS)
```bash
source ~/.orbstack/shell/init.bash
```

#### ❄️ Nix
```bash
source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh
```

#### 🤬 TheFuck
```bash
eval "$(thefuck --alias)"  # Enables 'fuck' command
```

#### ☁️ AWS Completion
```bash
complete -C aws_completer aws
```

#### 🔀 Git Completion
```bash
# Loads from system or Homebrew location
```

#### 🏗️ Terraform Completion
```bash
complete -C terraform terraform
```

---

## 🔗 Zsh ↔ Bash Comparison

| Feature | Zsh | Bash |
|---------|-----|------|
| Framework | Oh-My-Zsh | None (manual) |
| Plugins | 48 OMZ plugins | bash-completion |
| Autosuggestions | zsh-autosuggestions | N/A (use atuin) |
| Syntax highlighting | zsh-syntax-highlighting | N/A |
| Prompt | Starship | Starship ✅ |
| PATH uniqueness | `typeset -U path` | Helper functions |
| Function removal | `unfunction` | `unset -f` |
| Completion | compinit | bash-completion |

## ⚡ Performance

### Startup Optimization

1. **Lazy Loading** - pyenv/jenv load on first use
2. **Conditional Sources** - Only load if tool exists
3. **No Heavy Framework** - Pure bash, no bloat

### Benchmarking

```bash
# Time bash startup
time bash -i -c exit

# Detailed profiling
bash -x ~/.bashrc 2>&1 | head -50
```

## 🎯 Common Use Cases

### Quick Navigation
```bash
z project        # Jump to frequently used directory
fcd              # Fuzzy find and cd to directory
..               # Go up one level
```

### File Operations
```bash
ls               # List with icons (eza)
ll               # Long listing with git status
lt               # Tree view
cat file.txt     # Syntax highlighted (bat)
fv               # Fuzzy find and edit
```

### Git Workflow
```bash
gst              # git status
ga               # git add -p (interactive)
gc "message"     # git commit -m
gp               # git push origin HEAD
glog             # Beautiful git log
```

### Docker/Kubernetes
```bash
dco up           # docker compose up
k get pods       # kubectl get pods
kl pod-name      # kubectl logs -f
```

## 🔧 Customization

### Adding Aliases
Edit `~/.bash/10-aliases.bash`:
```bash
alias myalias='command'
```

### Adding Functions
Edit `~/.bash/20-functions.bash`:
```bash
myfunction() {
  # Your code
}
```

### Adding Environment Variables
Edit `~/.bash/00-env.bash`:
```bash
export MY_VAR="value"
```

### Adding Tool Integrations
Edit `~/.bash/99-integrations.bash`:
```bash
if command -v newtool >/dev/null 2>&1; then
  eval "$(newtool init bash)"
fi
```

## 🐛 Troubleshooting

### Slow Startup?
```bash
# Profile startup
time bash -i -c exit

# Check what's loading
bash -x ~/.bashrc 2>&1 | head -100
```

### Completion Not Working?
```bash
# Check bash-completion is loaded
type _init_completion

# Reinstall on macOS
brew reinstall bash-completion@2
```

### Colors Not Working?
```bash
# Check LS_COLORS
echo $LS_COLORS

# Check vivid
vivid generate catppuccin-mocha
```

### Tool Not Found?
```bash
# Check PATH
echo $PATH | tr ':' '\n'

# Check if tool exists
which toolname
command -v toolname
```

## 📦 Required Tools

```bash
# Core (install via Homebrew or apt)
brew install eza bat fd ripgrep vivid fzf zoxide atuin direnv neovim starship

# Optional
brew install xh thefuck
```

## 📚 Resources

- [Bash Manual](https://www.gnu.org/software/bash/manual/)
- [Bash Completion](https://github.com/scop/bash-completion)
- [Starship](https://starship.rs/)
- [FZF](https://github.com/junegunn/fzf)
- [Zoxide](https://github.com/ajeetdsouza/zoxide)
- [Catppuccin](https://github.com/catppuccin/catppuccin)

---

**Last updated:** 2025-01-24  
**Maintained by:** Jerome Soyer (@jsoyer)
