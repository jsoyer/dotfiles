# Zsh Configuration Documentation

> Modern, modular Zsh configuration with Oh-My-Zsh and Starship prompt

## 📁 Architecture

```
~/.zshrc                    # Main entry point
~/.zshenv                   # Environment variables (loaded first)
~/.zsh/                     # Modular configuration directory
  ├── 00-env.zsh           # Environment & theme configurations
  ├── 01-path.zsh          # PATH management with lazy loading
  ├── 02-completions.zsh   # Completion system setup
  ├── 10-aliases.zsh       # Command aliases & shortcuts
  ├── 20-functions.zsh     # Custom shell functions
  ├── 30-keybindings.zsh   # Keyboard shortcuts
  ├── 99-integrations.zsh  # External tool integrations
  └── secrets.zsh          # Private tokens (gitignored)
```

## 🎨 Theme: Catppuccin Mocha

All tools are configured with the **Catppuccin Mocha** color palette for a consistent visual experience:
- ✅ Starship prompt
- ✅ FZF fuzzy finder
- ✅ Eza file listings (via Vivid)
- ✅ Bat file viewer
- ✅ Neovim editor
- ✅ Vivid (LS_COLORS generator)

## 🔌 Oh-My-Zsh Plugins (48 active)

### Core Productivity (7)
- `colored-man-pages` - Colorful man pages
- `colorize` - Syntax highlighting for cat/less
- `copybuffer` - Copy command line with Ctrl+O
- `copyfile` - Copy file contents to clipboard
- `extract` - Universal archive extraction
- `encode64` - Base64 encoding/decoding
- `jsontools` - JSON manipulation (pp_json, is_json)

### Package Managers (1)
- `brew` - Homebrew completion and aliases

### Version Managers (3)
- `pyenv` - Python version management
- `jenv` - Java version management
- `rbenv` - Ruby version management

### Languages & Frameworks (4)
- `node` - Node.js aliases
- `npm` - NPM completion
- `yarn` - Yarn completion
- `poetry` - Python Poetry support

### Git (4)
- `git` - Core git aliases
- `github` - GitHub integration
- `git-extras` - Additional git commands
- `gitignore` - Gitignore templates

### Cloud & Infrastructure (5)
- `aws` - AWS CLI completion
- `docker` - Docker aliases and completion
- `kubectl` - Kubernetes completion
- `helm` - Helm completion
- `terraform` - Terraform completion

### System (4)
- `macos` - macOS-specific utilities
- `ssh-agent` - SSH agent management
- `sudo` - ESC ESC to add sudo
- `rsync` - Rsync completion

### Utilities (2)
- `web-search` - Search from terminal (google, ddg, github)
- `thefuck` - Correct previous command mistakes

## 🚀 Modern CLI Tools

Traditional tools are replaced with modern alternatives:

| Old Command | New Command | Tool | Description |
|-------------|-------------|------|-------------|
| `ls` | `ls`, `ll`, `l`, `lt` | eza | Modern ls with icons and git integration |
| `cat` | `cat` (aliased) | bat | Cat with syntax highlighting |
| `cd` | `z` | zoxide | Smart cd that learns your habits |
| `vim` | `vim` (aliased) | neovim | Modern vim |
| `http` | `http` (aliased) | xh | Fast HTTP client |
| `find` | `fd` | fd-find | Fast file finder |
| `grep` | `rg` | ripgrep | Fast grep alternative |
| N/A | `vivid` | vivid | LS_COLORS generator |

## 📝 File-by-File Documentation

### ~/.zshrc
**Purpose:** Main configuration entry point

**Key features:**
- Loads Oh-My-Zsh with 48 plugins
- Sources all modular configs from `~/.zsh/`
- Initializes Starship prompt (overrides Oh-My-Zsh theme)

**Load order:**
1. Oh-My-Zsh configuration
2. Plugin loading
3. Modular configs (00-99)
4. Starship initialization

### ~/.zshenv
**Purpose:** Environment setup for non-interactive shells

**Contains:**
- Basic environment variable definitions
- Ensures non-login shells have proper environment

### 00-env.zsh
**Purpose:** Core environment variables and profile-based theming.

**Key features:**
- **Profile-Aware Theming:** A `case` statement on `uname` and `hostname` detects the machine type (macOS Pro/Personal, Fedora, Raspberry Pi, Windows) and exports the correct `STARSHIP_ICON` and `STARSHIP_ICON_COLOR` for a unique prompt on each machine profile.
- **History:** 50,000 lines with deduplication.
- **Editor:** `nvim`.
- **FZF & Bat Theming:** Sets the theme for FZF and Bat.

### 01-path.zsh
**Purpose:** PATH management with performance optimization

**Key features:**
- Unique PATH entries (no duplicates)
- Prioritized ordering (user bins first)
- **Lazy loading for pyenv/jenv** (faster startup)

**PATH priority (highest to lowest):**
1. User bins (~/.local/bin, ~/.antigravity/bin)
2. Version managers (jenv, rbenv, tmuxifier)
3. Homebrew paths (from .zprofile)
4. System tools
5. X11 and TeX

**Lazy loading:**
```bash
# Functions are replaced on first call
pyenv()  # Loads pyenv only when used
jenv()   # Loads jenv only when used
```

### 02-completions.zsh
**Purpose:** Intelligent autocompletion configuration

**Features:**
- Case-insensitive matching (m → matches M)
- Daily cache refresh (faster startup after first run)
- AWS CLI completion
- Bash completion compatibility

**Performance:**
- Checks compinit cache only once per 24 hours
- Skips security check with `-C` flag

### 10-aliases.zsh
**Purpose:** Command shortcuts and modern tool aliases

**Categories:**

#### Modern Replacements
`ls`, `cat`, `vim`, `http` are aliased to modern alternatives (`eza`, `bat`, `nvim`, `xh`).

#### Navigation & System
Shortcuts for directory navigation (`..`, `...`) and system commands.

#### Git, Docker, Kubernetes
Extensive short aliases for common `git` (`gco`, `gp`, `gst`), `docker` (`dco`, `dps`), and `kubectl` (`k`, `kg`, `kl`) commands.

#### Homebrew, Chezmoi, Jujutsu
Quick aliases for package management (`bup`, `bcu`), dotfile management (`ca`, `cu`, `cedit`), and the `jj` version control system (`js`, `jl`, `jp`).


### 20-functions.zsh
**Purpose:** Custom shell functions for enhanced productivity

#### cx - Change directory and list
```bash
cx /path/to/dir  # cd + automatic eza listing
```

#### fcd - Fuzzy directory navigation
```bash
fcd  # Interactive FZF directory picker
```

#### f - Copy file path with FZF
```bash
f  # Select file with FZF, copy path to clipboard
```

#### fv - Open file in nvim with FZF
```bash
fv  # Select file with FZF, open in neovim
```


### 30-keybindings.zsh
**Purpose:** Custom keyboard shortcuts

#### Vi mode
```bash
jj  # Enter vi command mode from insert mode
```

#### Autosuggestions
```bash
Ctrl+w  # Execute current suggestion
Ctrl+e  # Accept suggestion
Ctrl+u  # Toggle suggestions on/off
Ctrl+L  # Jump forward one word
```

#### History
```bash
Ctrl+k  # Previous command
Ctrl+j  # Next command
```

### 99-integrations.zsh
**Purpose:** External tool integrations (loaded last)

**Integrated tools:**

#### Zplug
- Plugin manager for additional Zsh plugins

#### FZF
- Fuzzy finder for files, history, commands
- Catppuccin Mocha theme configured

#### Zsh Autosuggestions
- Fish-like command suggestions based on history
- Installed via Homebrew

#### Zsh Syntax Highlighting
- Real-time syntax highlighting in terminal
- Installed via Homebrew

#### Zoxide
- Smart cd replacement (learns your habits)
- Use `z project` instead of `cd ~/path/to/project`

#### Atuin
- Magical shell history with sync
- Better than Ctrl+R

#### Direnv
- Automatic environment switching per directory
- Loads .envrc files automatically

#### OrbStack
- Docker/Kubernetes alternative for macOS

#### Nix
- Nix package manager support

**Why loaded last:**
- These tools modify shell behavior
- Need to run after Oh-My-Zsh setup
- Prevents conflicts with plugins

### secrets.zsh
**Purpose:** Private tokens and API keys

**Security:**
- ✅ Gitignored (not tracked in version control)
- Contains sensitive credentials
- Sourced by main configuration

**Example contents:**
```bash
export HOMEBREW_GITHUB_API_TOKEN="ghp_..."
export OPENAI_API_KEY="sk-..."
```

⚠️ **Never commit this file to Git!**

## ⚡ Performance Optimizations

### 1. Lazy Loading
```bash
# pyenv and jenv are loaded only when called
# Saves ~200ms on startup
```

### 2. Completion Caching
```bash
# Compinit runs full check only once per day
# Subsequent starts use cached completions
```

### 3. Modular Loading
```bash
# Only source files that exist
for config_file ($HOME/.zsh/*.zsh(N)); do
  source $config_file
done
```

### 4. Unique PATH
```bash
typeset -U path  # Prevents duplicate entries
```

## 🎨 Color System (Catppuccin Mocha)

The entire shell uses a unified **Catppuccin Mocha** color scheme:

### Vivid Integration
```bash
# Vivid generates comprehensive LS_COLORS
export LS_COLORS="$(vivid generate catppuccin-mocha)"
```

**Benefits:**
- ✅ Consistent file type colors across all tools
- ✅ Beautiful, eye-friendly color palette
- ✅ Smart color assignment for extensions
- ✅ Automatically used by `eza`, `ls`, and other tools

### Changing Color Themes

To use a different Vivid theme, edit `~/.zsh/00-env.zsh`:

```bash
# Available themes: catppuccin-mocha, dracula, nord, gruvbox-dark, etc.
export LS_COLORS="$(vivid generate THEME_NAME)"
```

List all available themes:
```bash
vivid themes
```

## 🎯 Common Use Cases

### Quick Navigation
```bash
z project        # Jump to frequently used directory
fcd              # Fuzzy find and cd to directory
..               # Go up one level
...              # Go up two levels
```

### File Operations
```bash
ls               # List files with icons and colors (eza)
ll               # Long listing with git status
l                # Detailed list with all files
lt               # Tree view (2 levels)
cat file.txt     # View with syntax highlighting (bat)
extract file.zip # Universal archive extraction
fv               # Fuzzy find and edit file
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
ke pod-name      # kubectl exec -it
```

### Development
```bash
server           # Start HTTP server on port 4445
tunnel           # ngrok http 4445
gi python        # Generate Python .gitignore
pp_json file     # Pretty print JSON
```

## 🔧 Customization Guide

### Adding New Aliases
Edit `~/.zsh/10-aliases.zsh`:
```bash
alias myalias='command'
```

### Adding New Functions
Edit `~/.zsh/20-functions.zsh`:
```bash
myfunction() {
  # Your code here
}
```

### Adding Environment Variables
Edit `~/.zsh/00-env.zsh`:
```bash
export MY_VAR="value"
```

### Adding Oh-My-Zsh Plugins
Edit `~/.zshrc`:
```bash
plugins=(
  existing-plugins
  new-plugin
)
```

### Adding Custom Keybindings
Edit `~/.zsh/30-keybindings.zsh`:
```bash
bindkey '^x' custom-widget
```

## 🐛 Troubleshooting

### Slow startup?
```bash
# Profile startup time
time zsh -i -c exit

# Check which files are slow
zsh -xv 2>&1 | ts -i '%.s' > /tmp/zsh-profile.log
```

### Plugin not working?
```bash
# Verify plugin exists
ls ~/.oh-my-zsh/plugins/plugin-name

# Check if plugin is loaded
omz plugin list
```

### Completion not working?
```bash
# Rebuild completion cache
rm ~/.zcompdump*
compinit
```

### FZF not showing colors?
```bash
# Verify FZF_DEFAULT_OPTS is set
echo $FZF_DEFAULT_OPTS
```

### Colors not working in ls/eza?
```bash
# Verify LS_COLORS is set by Vivid
echo $LS_COLORS

# Test Vivid directly
vivid generate catppuccin-mocha

# Check if Vivid is installed
which vivid
```

## 📚 Additional Resources

- [Oh-My-Zsh Documentation](https://github.com/ohmyzsh/ohmyzsh/wiki)
- [Starship Documentation](https://starship.rs/)
- [Catppuccin Theme](https://github.com/catppuccin/catppuccin)
- [Vivid Documentation](https://github.com/sharkdp/vivid)
- [Eza Documentation](https://github.com/eza-community/eza)
- [Zsh Manual](https://zsh.sourceforge.io/Doc/)
- [FZF Examples](https://github.com/junegunn/fzf/wiki/examples)

## 🔄 Updating

### Update Oh-My-Zsh
```bash
omz update
```

### Update Starship
```bash
brew upgrade starship
```

### Update Homebrew packages
```bash
brew update && brew upgrade
```

### Reload configuration
```bash
source ~/.zshrc
```

## 📦 Required Tools

Install these tools for full functionality:

```bash
# Core tools
brew install eza bat fd ripgrep vivid fzf zoxide atuin direnv neovim

# Optional tools
brew install xh httpie
```

## 📄 License

This configuration is based on various open-source projects and personal customizations.

---

**Last updated:** 2025-12-30
**Maintained by:** Jerome Soyer
