# Nushell Configuration

Nushell is a modern shell that takes a structured, pipeline-oriented approach to the command line. This configuration sets up Nushell with the **Catppuccin Mocha** theme for a consistent, beautiful terminal experience.

## Overview

- **Version**: Nushell 0.109.1
- **Theme**: Catppuccin Mocha
- **Prompt**: Starship
- **Config Location**: `~/.config/nushell/` (source files)
- **Runtime Location**: `~/Library/Application Support/nushell/` (macOS default)

## File Structure

### Source Files (where you edit)
```
~/.config/nushell/
├── config.nu              # Main configuration file (963 lines)
├── env.nu                 # Environment variables and startup
├── catppuccin_mocha.nu    # Catppuccin Mocha theme
└── README.md              # This file
```

### Runtime Files (symlinked on macOS)
```
~/Library/Application Support/nushell/
├── config.nu -> ~/.config/nushell/config.nu    # Symlink
├── env.nu -> ~/.config/nushell/env.nu          # Symlink
├── history.txt                                 # Shell history
└── vendor/                                     # Auto-loaded plugins
```

> **Note for macOS users**: Nushell on macOS looks for config in `~/Library/Application Support/nushell/` by default. We use symlinks to point to our actual config files in `~/.config/nushell/` for consistency with other tools.

## Configuration Files

### `config.nu`
Main Nushell configuration file that:
- Sources the Catppuccin Mocha theme
- Configures color scheme for syntax highlighting
- Sets up shell behavior (vi mode, history, completions)
- Defines aliases for Git, Kubernetes, Docker, and system commands
- Configures keybindings and menus
- Sets up hooks (direnv integration)

### `env.nu`
Environment configuration that:
- Initializes Starship prompt with custom config (`starship-desktop.toml`)
- Initializes Zoxide for smart directory navigation
- Initializes Atuin for shell history sync
- Initializes Carapace for advanced completions
- Sets environment variables (BAT_THEME, FZF_DEFAULT_OPTS, LS_COLORS)
- Configures PATH and Ruby gems
- Sets up custom prompts (left/right with time and exit codes)

### `catppuccin_mocha.nu`
Complete Catppuccin Mocha color theme with:
- All 26 Catppuccin Mocha colors
- Syntax highlighting configuration
- File size and duration color gradients
- Explorer UI styling

## Integrated Tools

### Starship
Modern, fast prompt with custom configuration:
- **Config**: `~/.config/starship/starship-desktop.toml`
- **Format**: All modules in main prompt (different from ZSH)
- **Theme**: Catppuccin Mocha palette
- **Cache**: `~/.cache/starship/init.nu`

### Zoxide
Smart directory jumping:
- **Command**: `z` - Jump to frequently used directories
- **Cache**: `~/.zoxide.nu`

### Atuin
Shell history synchronization:
- **Features**: Sync history across machines, fuzzy search
- **Init**: `~/.local/share/atuin/init.nu`

### Carapace
Advanced shell completions:
- **Bridges**: zsh, fish, bash, inshellisense
- **Cache**: `~/.cache/carapace/init.nu`

### Direnv
Automatic environment switching:
- **Hook**: Pre-prompt hook in config.nu
- **Format**: Logs suppressed with `$env.DIRENV_LOG_FORMAT = ""`

## Catppuccin Mocha Theme

### Color Palette

The theme uses the full Catppuccin Mocha palette:

| Color      | Hex       | Usage                          |
|------------|-----------|--------------------------------|
| Base       | `#1e1e2e` | Background                     |
| Text       | `#cdd6f4` | Foreground/text                |
| Blue       | `#89b4fa` | Commands, keywords             |
| Green      | `#a6e3a1` | Strings, success               |
| Yellow     | `#f9e2af` | Files, warnings                |
| Red        | `#f38ba8` | Errors                         |
| Mauve      | `#cba6f7` | Keywords, operators            |
| Peach      | `#fab387` | Constants, numbers             |
| Flamingo   | `#f2cdcd` | Variables, parameters          |
| Teal       | `#94e2d5` | Closures, signatures           |

### Syntax Highlighting

The theme provides intelligent syntax highlighting for:
- **Commands**: Blue for recognized commands
- **Strings**: Green for string literals
- **Numbers**: Peach for integers and floats
- **Variables**: Flamingo (italic) for variables
- **Operators**: Sky blue for operators and pipes
- **Paths**: Yellow for file paths
- **Keywords**: Mauve for language keywords
- **Errors**: Red with red background

### Dynamic Colors

File sizes and durations use color gradients:

**File sizes:**
- < 1KB: Teal
- < 10KB: Green
- < 100KB: Yellow
- < 10MB: Peach
- < 100MB: Maroon
- < 1GB: Red
- ≥ 1GB: Mauve

**Durations:**
- < 1 day: Teal
- < 1 week: Green
- < 4 weeks: Yellow
- < 12 weeks: Peach
- < 24 weeks: Maroon
- < 52 weeks: Red
- ≥ 52 weeks: Mauve

### LS_COLORS with Vivid

File listings use vivid-generated LS_COLORS:
```nushell
$env.LS_COLORS = (vivid generate catppuccin-mocha)
```

This provides rich, context-aware colors for:
- Different file types (images, videos, archives, code)
- Permissions and ownership
- Symbolic links and broken links
- Executables and special files

## Environment Variables

The following environment variables are set with Catppuccin Mocha colors:

### BAT_THEME
```nushell
$env.BAT_THEME = "Catppuccin Mocha"
```

### FZF_DEFAULT_OPTS
Fuzzy finder with Catppuccin Mocha colors:
```nushell
$env.FZF_DEFAULT_OPTS = "--color=bg+:#313244,bg:#1e1e2e,spinner:#f5e0dc,hl:#f38ba8 --color=fg:#cdd6f4,header:#f38ba8,info:#cba6f7,pointer:#f5e0dc --color=marker:#b4befe,fg+:#cdd6f4,prompt:#cba6f7,hl+:#f38ba8 --color=selected-bg:#45475a --multi"
```

### LS_COLORS
Generated by vivid for Catppuccin Mocha:
```nushell
$env.LS_COLORS = (vivid generate catppuccin-mocha)
```

### Other Variables
- `$env.EDITOR = "nvim"`
- `$env.STARSHIP_CONFIG = "/Users/jeromesoyer/.config/starship/starship-desktop.toml"`
- `$env.NIX_CONF_DIR = "/Users/jeromesoyer/.config/nix"`
- `$env.CARAPACE_BRIDGES = 'zsh,fish,bash,inshellisense'`

## Aliases

### System
```nushell
alias l = ls --all
alias c = clear
alias ll = ls -l
alias lt = eza --tree --level=2 --long --icons --git
alias v = nvim
```

### Custom Functions
```nushell
def --env cx [arg] {  # Change directory and list
    cd $arg
    ls -l
}

def ff [] {  # Fuzzy find and focus Aerospace window
    aerospace list-windows --all | fzf --bind 'enter:execute(bash -c "aerospace focus --window-id {1}")+abort'
}
```

### Git
```nushell
alias gc = git commit -m
alias gca = git commit -a -m
alias gp = git push origin HEAD
alias gpu = git pull origin
alias gst = git status
alias glog = git log --graph --topo-order --pretty='%w(100,0,6)%C(yellow)%h%C(bold)%C(black)%d %C(cyan)%ar %C(green)%an%n%C(bold)%C(white)%s %N' --abbrev-commit
alias gdiff = git diff
alias gco = git checkout
alias gb = git branch
alias gba = git branch -a
alias gadd = git add
alias ga = git add -p
alias gcoall = git checkout -- .
alias gr = git remote
alias gre = git reset
```

### Kubernetes
```nushell
alias k = kubectl
alias ka = kubectl apply -f
alias kg = kubectl get
alias kd = kubectl describe
alias kdel = kubectl delete
alias kl = kubectl logs -f
alias kgpo = kubectl get pod
alias kgd = kubectl get deployments
alias kc = kubectx
alias kns = kubens
alias ke = kubectl exec -it
```

### Aerospace (Window Manager)
```nushell
alias as = aerospace
alias asr = atuin scripts run
```

### SSH
```nushell
alias sshpw = ssh -o PreferredAuthentications=password
```

### System Updates
```nushell
alias update-ai = # Updates Claude Code, Copilot CLI, Codex CLI
alias sysup = # Updates OS packages + Flatpak + update-ai
alias cup = # chezmoi update + system upgrade + container updates
```

## Configuration

### Vi Mode
```nushell
edit_mode: vi
```

Keybindings:
- Normal mode indicator: `〉`
- Insert mode indicator: `: `

### History
```nushell
max_size: 100_000
sync_on_enter: true
file_format: "plaintext"
```

### Completions
```nushell
case_sensitive: false
quick: true
partial: true
algorithm: "prefix"
use_ls_colors: true
```

### Shell Integration
All shell integration features enabled:
- `osc2`: Tab/window title
- `osc7`: Path communication
- `osc8`: Clickable links
- `osc133`: Prompt markers
- `osc633`: VSCode integration

## Starting Nushell

### Launch Nushell
```bash
nu
```

### Verify Configuration Paths
```bash
# Check where Nushell looks for config
nu -c '$nu.config-path'
# Should show: /Users/jeromesoyer/Library/Application Support/nushell/config.nu

nu -c '$nu.env-path'
# Should show: /Users/jeromesoyer/Library/Application Support/nushell/env.nu

# Verify symlinks are working
ls -la ~/Library/Application\ Support/nushell/*.nu
```

### Set as Default Shell (Optional)
```bash
# Add Nushell to allowed shells
echo /opt/homebrew/bin/nu | sudo tee -a /etc/shells

# Change default shell
chsh -s /opt/homebrew/bin/nu
```

### Test Configuration
```bash
nu -c 'echo "Hello from Nushell!"'

# Test that env.nu is loaded
nu -c '$env.BAT_THEME'
# Should show: Catppuccin Mocha
```

## Features

### Structured Data
Nushell treats everything as structured data:
```nushell
ls | where size > 1kb | sort-by modified | reverse
```

### Pipeline Operations
```nushell
# List processes using more than 100MB RAM
ps | where mem > 100mb | sort-by mem | reverse

# Parse JSON and extract data
open package.json | get dependencies | columns

# Work with CSV files
open data.csv | where status == "active" | select name email
```

### Custom Commands
```nushell
# Define custom commands
def greet [name: string] {
    $"Hello, ($name)!"
}

greet "World"
```

## Common Commands

### File Operations
```nushell
ls                          # List files (structured output)
ls | sort-by size           # Sort by size
ls | where type == file     # Filter files only
open file.json              # Open and parse JSON/CSV/TOML/YAML
save output.txt             # Save pipeline output
```

### String Operations
```nushell
"hello" | str uppercase        # HELLO
"  text  " | str trim       # text
"a,b,c" | split row ","     # [a, b, c]
```

### Data Manipulation
```nushell
[1 2 3] | math sum          # 6
[1 2 3] | math avg          # 2
{a: 1, b: 2} | get a        # 1
```

### System Info
```nushell
sys                         # System information
ps                          # Process list
date now                    # Current date/time
```

### Zoxide Commands
```nushell
z ~                         # Jump to home
z documents                 # Jump to frequently used 'documents' dir
z -                         # Jump to previous directory
zi                          # Interactive directory selection
```

## Maintenance

### Clear and Regenerate Caches
```bash
# Remove old caches
rm -rf ~/.cache/starship ~/.cache/carapace ~/.zoxide.nu

# Regenerate (happens automatically on next Nushell start)
# Or manually:
nu -c "
    mkdir ~/.cache/starship;
    starship init nu | save -f ~/.cache/starship/init.nu;
    zoxide init nushell | save -f ~/.zoxide.nu;
    mkdir ~/.cache/carapace;
    carapace _carapace nushell | save --force ~/.cache/carapace/init.nu
"
```

### Configuration Reload
```nushell
# Reload environment
source ~/.config/nushell/env.nu

# Reload config (note: some settings require restart)
source ~/.config/nushell/config.nu
```

## Tips & Tricks

### 1. Tab Completion
Nushell has intelligent tab completion:
- Press `Tab` to cycle through completions
- Works for commands, paths, and structured data fields
- Carapace provides completions for many external tools

### 2. Help System
```nushell
help commands               # List all commands
help ls                     # Help for specific command
help operators              # Operator reference
```

### 3. Error Messages
Nushell provides detailed, helpful error messages with suggestions.

### 4. Shell Integration
```nushell
# Run external commands with ^
^ls -la

# Capture external output
let output = (^git status | str trim)
```

### 5. History Search
- `Ctrl+R`: Search history with Atuin
- History syncs across machines with Atuin

### 6. Navigation
- Use `z` instead of `cd` for smart navigation
- `z documents` jumps to most frequently used directory matching "documents"

## Troubleshooting

### Configuration Not Loading Automatically

**Problem**: You have to manually `source` config files each time.

**Solution**: Nushell on macOS looks in `~/Library/Application Support/nushell/` by default. Create symlinks:

```bash
# Create symlinks to point to your actual config
mkdir -p ~/Library/Application\ Support/nushell
ln -sf ~/.config/nushell/env.nu ~/Library/Application\ Support/nushell/env.nu
ln -sf ~/.config/nushell/config.nu ~/Library/Application\ Support/nushell/config.nu

# Verify
ls -la ~/Library/Application\ Support/nushell/*.nu

# Test in new shell
nu -c '$env.BAT_THEME'
```

### Theme Not Loading
```nushell
# Verify theme file exists
ls ~/.config/nushell/catppuccin_mocha.nu

# Manually source theme
source ~/.config/nushell/catppuccin_mocha.nu
```

### Starship Not Showing
```nushell
# Check if Starship is installed
which starship

# Verify config path
echo $env.STARSHIP_CONFIG

# Manually regenerate
mkdir ~/.cache/starship
starship init nu | save -f ~/.cache/starship/init.nu
source ~/.cache/starship/init.nu
```

### Zoxide Not Working
```nushell
# Check if zoxide is installed
which zoxide

# Regenerate init file
zoxide init nushell | save -f ~/.zoxide.nu
source ~/.zoxide.nu
```

### Config Errors
```nushell
# Check config syntax
nu -c 'source ~/.config/nushell/config.nu'

# Check environment
nu -c 'source ~/.config/nushell/env.nu'
```

### "CONFIG ERROR" in Prompt
This was caused by Oh-My-Posh conflicting with Starship. Fixed by:
```bash
mv "/Users/jeromesoyer/Library/Application Support/nushell/vendor/autoload/oh-my-posh.nu" \
   "/Users/jeromesoyer/Library/Application Support/nushell/vendor/autoload/oh-my-posh.nu.disabled"
```

## Resources

- **Nushell Documentation**: https://www.nushell.sh/
- **Nushell Book**: https://www.nushell.sh/book/
- **Catppuccin for Nushell**: https://github.com/catppuccin/nushell
- **Catppuccin Palette**: https://github.com/catppuccin/catppuccin
- **Starship**: https://starship.rs/
- **Zoxide**: https://github.com/ajeetdsouza/zoxide
- **Atuin**: https://github.com/atuinsh/atuin
- **Carapace**: https://github.com/rsteube/carapace-bin
- **Vivid**: https://github.com/sharkdp/vivid

## Comparison with Other Shells

| Feature              | Nushell        | Zsh/Bash      |
|----------------------|----------------|---------------|
| Data Structure       | Native         | Text-based    |
| Type System          | Strong typing  | Strings       |
| Pipeline             | Structured     | Text streams  |
| JSON/CSV/YAML        | Native support | External tools|
| Error Messages       | Detailed       | Basic         |
| Tab Completion       | Context-aware  | Pattern-based |
| Configuration        | Nushell syntax | Shell script  |

## Theme Consistency

This Nushell configuration uses **Catppuccin Mocha** to match your other tools:

- ✅ **Nushell**: Catppuccin Mocha
- ✅ **Starship**: Catppuccin Mocha palette  
- ✅ **Ghostty**: Catppuccin Mocha
- ✅ **Bat**: Catppuccin Mocha
- ✅ **FZF**: Catppuccin Mocha
- ✅ **LS_COLORS**: Catppuccin Mocha (vivid)
- ✅ **ZSH**: Catppuccin Mocha (coordinated config)

---

**Updated**: 2026-03-28
**Theme**: Catppuccin Mocha
**Shell**: Nushell 0.109.1+
**Optimized**: Cache cleaned and regenerated

## Changelog

### 2026-03-28
- Added SSH, system update aliases (sshpw, update-ai, sysup, cup)

### 2025-01-25
- Fixed `$nu.home-path` → `$nu.home-dir` (renamed in Nushell 0.80+)
