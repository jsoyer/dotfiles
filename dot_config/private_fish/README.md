# Fish Shell Configuration

Fish (Friendly Interactive Shell) is a smart and user-friendly command line shell. This configuration sets up Fish with the **Catppuccin Mocha** theme for a beautiful, consistent terminal experience.

## Overview

- **Shell**: Fish Shell
- **Theme**: Catppuccin Mocha
- **Prompt**: Starship
- **Location**: `~/.config/fish/`
- **Package Manager**: Fisher (via fish_plugins)

## File Structure

```
~/.config/fish/
├── config.fish                    # Main configuration file
├── themes/
│   └── Catppuccin Mocha.theme     # Catppuccin Mocha color theme
├── conf.d/                        # Auto-loaded configuration snippets
├── functions/                     # Custom functions
├── completions/                   # Custom completions
├── fish_plugins                   # Fisher plugin list
├── fish_variables                 # Universal variables
└── README.md                      # This file
```

## Configuration Files

### `config.fish`
Main Fish configuration that includes:
- **Homebrew**: Environment setup and PATH configuration
- **Catppuccin Mocha theme**: Automatic activation on startup
- **Starship prompt**: Integration with custom config
- **Environment variables**: BAT_THEME, FZF_DEFAULT_OPTS, EZA_COLORS, LS_COLORS (vivid)
- **Modern CLI tools**: eza (ls replacement), bat (cat replacement)
- **Development managers**: pyenv (Python), jenv (Java), rbenv (Ruby), nvm (Node.js)
- **PATH management**: User bins, Antigravity, local bins, tool-specific paths
- **Useful aliases**: Git, Docker, Kubernetes, navigation, safety
- **Shell options**: Disabled greeting, optional vi mode

### `themes/Catppuccin Mocha.theme`
Official Catppuccin Mocha theme file with all Fish color definitions.

## Catppuccin Mocha Theme

### Color Palette

The theme provides a complete color scheme for Fish shell:

| Element              | Color     | Hex       |
|----------------------|-----------|-----------|
| Background           | Base      | `#1e1e2e` |
| Normal text          | Text      | `#cdd6f4` |
| Commands             | Blue      | `#89b4fa` |
| Parameters           | Flamingo  | `#f2cdcd` |
| Keywords             | Mauve     | `#cba6f7` |
| Strings              | Green     | `#a6e3a1` |
| Redirection          | Pink      | `#f5c2e7` |
| Operators            | Pink      | `#f5c2e7` |
| Comments             | Overlay1  | `#7f849c` |
| Errors               | Red       | `#f38ba8` |
| Autosuggestions      | Overlay0  | `#6c7086` |

### Fish Color Variables

The theme configures these Fish-specific colors:

```fish
fish_color_normal           # Normal text (cdd6f4)
fish_color_command          # Commands (89b4fa - blue)
fish_color_param            # Parameters (f2cdcd - flamingo)
fish_color_keyword          # Keywords (cba6f7 - mauve)
fish_color_quote            # Strings (a6e3a1 - green)
fish_color_redirection      # Redirections (f5c2e7 - pink)
fish_color_end              # Command terminators (fab387 - peach)
fish_color_comment          # Comments (7f849c - overlay1)
fish_color_error            # Errors (f38ba8 - red)
fish_color_autosuggestion   # Autosuggestions (6c7086 - overlay0)
fish_color_selection        # Selected text (bg: 313244)
fish_color_search_match     # Search matches (bg: 313244)
fish_color_cwd              # Current directory (f9e2af - yellow)
fish_color_user             # Username (94e2d5 - teal)
fish_color_host             # Hostname (89b4fa - blue)
```

### Changing Theme

To switch between themes:
```fish
# List available themes
fish_config theme show

# Preview a theme
fish_config theme choose "Catppuccin Mocha"

# Save permanently
fish_config theme save "Catppuccin Mocha"
```

## Starship Integration

Starship prompt is automatically initialized in `config.fish`:

```fish
if command -v starship &> /dev/null
    starship init fish | source
end
```

Your existing Starship configuration (`~/.config/starship/starship.toml`) with Catppuccin Mocha palette will be used.

## Environment Variables

### System Variables
```fish
set -gx LANG en_US.UTF-8
set -gx EDITOR nvim
set -gx DOCKER_CONFIG $HOME/.docker
set -gx KUBECONFIG $HOME/.kube/config
set -gx HOMEBREW_CASK_OPTS "--appdir=/Applications"
```

### Homebrew Environment
```fish
set -gx HOMEBREW_PREFIX "/opt/homebrew"
set -gx HOMEBREW_CELLAR "/opt/homebrew/Cellar"
set -gx HOMEBREW_REPOSITORY "/opt/homebrew"
```

### BAT_THEME
Syntax highlighting for `bat` (modern cat):
```fish
set -gx BAT_THEME "Catppuccin Mocha"
```

### FZF Configuration
Fuzzy finder with Catppuccin Mocha colors and fd integration:
```fish
set -gx FZF_DEFAULT_OPTS "\
--color=bg+:#313244,bg:#1e1e2e,spinner:#f5e0dc,hl:#f38ba8 \
--color=fg:#cdd6f4,header:#f38ba8,info:#cba6f7,pointer:#f5e0dc \
--color=marker:#f5e0dc,fg+:#cdd6f4,prompt:#cba6f7,hl+:#f38ba8"

set -gx FZF_DEFAULT_COMMAND 'fd --type f --hidden --follow --exclude .git'
```

### Eza Colors
```fish
set -gx EZA_COLORS "uu=38;5;147:gu=38;5;147:ur=38;5;203:uw=38;5;204:ux=38;5;148:ue=38;5;148:gr=38;5;203:gw=38;5;204:gx=38;5;148:tr=38;5;203:tw=38;5;204:tx=38;5;148:da=38;5;110:sn=38;5;180:sb=38;5;180:xa=38;5;147"
```

### LS_COLORS (Vivid)
```fish
if command -v vivid &> /dev/null
    set -gx LS_COLORS (vivid generate catppuccin-mocha)
end
```

## Modern CLI Tools

### Eza (Modern ls)
```fish
alias ls='eza --icons --group-directories-first'
alias ll='eza -l --icons --group-directories-first'
alias la='eza -la --icons --group-directories-first'
alias lt='eza --tree --level=2 --icons'
```

### Bat (Modern cat)
```fish
alias cat='bat --style=auto'
```

## Development Environments

### Python (Pyenv)
Manage multiple Python versions:
```fish
if test -d $HOME/.pyenv
    set -gx PYENV_ROOT $HOME/.pyenv
    fish_add_path $PYENV_ROOT/bin
end
if command -v pyenv &> /dev/null
    pyenv init - | source
end
```

**Usage:**
```fish
pyenv versions              # List installed versions
pyenv install 3.12.0        # Install Python 3.12.0
pyenv global 3.12.0         # Set global Python version
pyenv local 3.11.0          # Set local version for current directory
```

### Java (Jenv)
Manage multiple Java versions:
```fish
if test -d $HOME/.jenv
    fish_add_path $HOME/.jenv/bin
end
if command -v jenv &> /dev/null
    jenv init - | source
end
```

**Usage:**
```fish
jenv versions               # List Java versions
jenv add /path/to/jdk       # Add JDK to jenv
jenv global 17.0            # Set global Java version
jenv local 11.0             # Set local version
```

### Ruby (Rbenv)
Manage multiple Ruby versions:
```fish
if test -d $HOME/.rbenv
    fish_add_path $HOME/.rbenv/bin
end
if command -v rbenv &> /dev/null
    rbenv init - fish | source
end
```

**Usage:**
```fish
rbenv versions              # List Ruby versions
rbenv install 3.2.0         # Install Ruby 3.2.0
rbenv global 3.2.0          # Set global version
rbenv local 3.1.0           # Set local version
```

### Node.js (NVM)
Manage multiple Node.js versions:
```fish
if test -d $HOME/.nvm
    set -gx NVM_DIR $HOME/.nvm
end
```

**Usage:**
```fish
nvm install node            # Install latest Node.js
nvm install 20              # Install Node.js 20
nvm use 20                  # Use Node.js 20
nvm alias default 20        # Set default version
```

## Aliases

### Git
```fish
alias g='git'
alias gs='git status'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gl='git pull'
alias gd='git diff'
alias gco='git checkout'
alias gb='git branch'
```

### Docker
```fish
alias d='docker'
alias dc='docker compose'
alias dps='docker ps'
alias dimg='docker images'
```

### Kubernetes
```fish
alias k='kubectl'
alias kgp='kubectl get pods'
alias kgs='kubectl get services'
alias kgd='kubectl get deployments'
```

### Navigation
```fish
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
```

### Safety
```fish
alias rm='rm -i'
alias cp='cp -i'
alias mv='mv -i'
```

## Fish Features

### 1. Autosuggestions
Fish suggests commands as you type based on history:
- Press **→** (right arrow) to accept suggestion
- Press **Alt+→** to accept one word
- Styled with Catppuccin Mocha overlay0 color

### 2. Tab Completion
Intelligent tab completion with descriptions:
- Press **Tab** to see completions
- Press **Tab** again to cycle through options
- Completions show command descriptions

### 3. Syntax Highlighting
Real-time syntax highlighting as you type:
- Valid commands: Blue
- Invalid commands: Red
- Strings: Green
- Parameters: Flamingo

### 4. Web-based Configuration
```fish
fish_config
```
Opens a web interface to configure:
- Colors and themes
- Prompt
- Functions
- Variables
- Abbreviations

### 5. Abbreviations
```fish
# Add abbreviations (expand when you press Space)
abbr -a gst git status
abbr -a gco git checkout
abbr -a dcu docker compose up
```

## Common Commands

### Variables
```fish
# Set variable
set myvar "value"

# Export (global) variable
set -gx PATH $PATH /new/path

# Universal variable (persists across sessions)
set -U fish_greeting "Hello!"
```

### Functions
```fish
# Define function
function ll
    ls -lah $argv
end

# Save function permanently
funcsave ll

# Edit function
funced ll
```

### Conditionals
```fish
if test -f file.txt
    echo "File exists"
else
    echo "File not found"
end
```

### Loops
```fish
for file in *.txt
    echo $file
end
```

### Command Substitution
```fish
set current_dir (pwd)
set files (ls)
```

## Tips & Tricks

### 1. History Search
- Press **↑** to search history
- Type partial command then **↑** to search matching commands
- **Ctrl+R** for reverse search

### 2. Multi-line Editing
- Press **Alt+Enter** to add new line without executing

### 3. Directory History
```fish
prevd   # Go to previous directory
nextd   # Go to next directory
dirh    # Show directory history
```

### 4. Job Control
```fish
jobs        # List background jobs
bg %1       # Resume job 1 in background
fg %1       # Bring job 1 to foreground
```

### 5. Keybindings
```fish
# List all keybindings
bind

# Add custom keybinding
bind \cf 'commandline -f forward-word'
```

### 6. Vi Mode (Optional)
```fish
# Enable vi mode
fish_vi_key_bindings

# Switch back to default
fish_default_key_bindings
```

## PATH Management

Fish utilizes `fish_add_path` for clean PATH management. The configuration includes:

### User Binaries (Highest Priority)
```fish
fish_add_path -g $HOME/.antigravity/antigravity/bin
fish_add_path -g $HOME/.local/bin
fish_add_path -g $HOME/.jenv/bin
fish_add_path -g $HOME/.rbenv/shims
fish_add_path -g $HOME/.tmuxifier/bin
```

### Homebrew Paths
```fish
fish_add_path -g /opt/homebrew/bin
fish_add_path -g /opt/homebrew/sbin
```

### Additional Tools
```fish
fish_add_path -g /usr/local/opt/rbenv/shims
fish_add_path -g /opt/X11/bin
fish_add_path -g /Library/TeX/texbin
fish_add_path -g /usr/texbin
```

**Note**: `fish_add_path -g` adds paths globally, avoiding duplicates automatically.

## Starting Fish

### Launch Fish
```bash
fish
```

### Set as Default Shell
```bash
# Add Fish to allowed shells
echo /opt/homebrew/bin/fish | sudo tee -a /etc/shells

# Change default shell
chsh -s /opt/homebrew/bin/fish
```

### Test Configuration
```bash
fish -c 'echo "Hello from Fish with Catppuccin Mocha!"'
```

## Customization

### Add Custom Functions
Create a file in `~/.config/fish/functions/`:
```fish
# ~/.config/fish/functions/myfunction.fish
function myfunction
    echo "My custom function"
end
```

### Add Auto-loaded Config
Create files in `~/.config/fish/conf.d/`:
```fish
# ~/.config/fish/conf.d/custom.fish
set -gx MY_VAR "value"
```

### Override Prompt
If not using Starship, create custom prompt:
```fish
# ~/.config/fish/functions/fish_prompt.fish
function fish_prompt
    echo (set_color blue)(prompt_pwd)(set_color normal)' > '
end
```

## Troubleshooting

### Theme Not Active
```fish
# List available themes
fish_config theme show

# Activate theme
fish_config theme choose "Catppuccin Mocha"
```

### Starship Not Showing
```fish
# Check if Starship is installed
which starship

# Manually initialize in current session
starship init fish | source
```

### Config Errors
```fish
# Check config syntax
fish -n ~/.config/fish/config.fish

# Debug mode
fish -d 3
```

### Reset to Defaults
```fish
# Backup current config
mv ~/.config/fish ~/.config/fish.backup

# Fish will create new default config on next start
fish
```

## Comparison with Other Shells

| Feature              | Fish           | Zsh/Bash      |
|----------------------|----------------|---------------|
| Autosuggestions      | Built-in       | Plugin needed |
| Tab Completion       | Smart, built-in| Basic/plugin  |
| Syntax Highlighting  | Real-time      | Plugin needed |
| Configuration        | Simple         | Complex       |
| POSIX Compliance     | No             | Yes           |
| Scripting Syntax     | Clean, modern  | Traditional   |
| Web Config UI        | Yes            | No            |

## Resources

- **Fish Documentation**: https://fishshell.com/docs/current/
- **Fish Tutorial**: https://fishshell.com/docs/current/tutorial.html
- **Catppuccin for Fish**: https://github.com/catppuccin/fish
- **Fish Community**: https://github.com/fish-shell/fish-shell

## Theme Consistency

This Fish configuration uses **Catppuccin Mocha** to match your other tools:

- ✅ **Neovim**: Catppuccin Mocha
- ✅ **Bat**: Catppuccin Mocha
- ✅ **Starship**: Catppuccin Mocha palette
- ✅ **Zsh/FZF/Eza**: Catppuccin Mocha
- ✅ **Tmux**: Catppuccin Mocha
- ✅ **Ghostty**: Catppuccin Mocha
- ✅ **Zellij**: Catppuccin Mocha
- ✅ **Nushell**: Catppuccin Mocha
- ✅ **Fish**: Catppuccin Mocha

---

## Quick Reference

### Essential Commands
```fish
fish_config                 # Open web-based configuration
fish_update_completions     # Update completions
funced <function>           # Edit function
funcsave <function>         # Save function permanently
abbr -a <name> <expansion>  # Add abbreviation
set -U <var> <value>        # Set universal variable
```

### Development Environment Quick Setup
```fish
# Python
pyenv install 3.12.0 && pyenv global 3.12.0

# Java
jenv add /path/to/jdk && jenv global 17.0

# Ruby
rbenv install 3.2.0 && rbenv global 3.2.0

# Node.js
nvm install node && nvm alias default node
```

### Debugging
```fish
# Check config syntax
fish -n ~/.config/fish/config.fish

# Debug mode
fish -d 3

# Reload configuration
source ~/.config/fish/config.fish
```

---

**Updated**: 2025-12-26  
**Theme**: Catppuccin Mocha  
**Shell**: Fish Shell  
**Package Manager**: Fisher
