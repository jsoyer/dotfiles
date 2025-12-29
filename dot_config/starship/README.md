# Starship Prompt Configuration

Starship is a fast, customizable, and cross-shell prompt. This configuration uses the **Catppuccin Mocha** color palette for a beautiful, consistent prompt across all shells.

## Overview

- **Prompt**: Starship
- **Theme**: Catppuccin Mocha palette
- **Shells**: Zsh, Fish, Nushell, Bash
- **Location**: `~/.config/starship/starship.toml`

## File Structure

```
~/.config/starship/
├── starship.toml         # Main configuration
├── starship.toml.backup  # Backup of previous config
└── README.md            # This file
```

## Features

### 🚀 Fast Performance
- Written in Rust for speed
- Minimal latency (<10ms typically)
- Async module loading

### 🎨 Catppuccin Mocha Colors
- Consistent with your entire environment
- Soothing pastel colors
- Clear visual hierarchy

### 📊 Rich Information Display
- Git status and branch
- Programming language versions
- Command duration
- Execution time
- Directory path
- And much more...

## Color Palette

The prompt uses Catppuccin Mocha colors:

| Color      | Hex       | Usage                          |
|------------|-----------|--------------------------------|
| Blue       | `#89b4fa` | Directories, prompts           |
| Green      | `#a6e3a1` | Success, clean git status      |
| Yellow     | `#f9e2af` | Warnings, modified files       |
| Red        | `#f38ba8` | Errors, conflicts              |
| Mauve      | `#cba6f7` | Special indicators             |
| Peach      | `#fab387` | Important information          |
| Teal       | `#94e2d5` | Additional context             |
| Text       | `#cdd6f4` | Primary text                   |
| Subtext    | `#a6adc8` | Secondary text                 |

## Prompt Structure

Your prompt displays information in this order:

```
[username@hostname] [directory] [git_branch git_status] [language_versions]
[character] 
```

### Right Prompt
```
[cmd_duration] [time]
```

## Configured Modules

### Directory
- Shows current directory path
- Blue color (`#89b4fa`)
- Truncates long paths intelligently
- Shows read-only indicator

### Git Branch
- Current git branch name
- Mauve color (`#cba6f7`)
- Symbol: 

### Git Status
- Shows repository state
- Colors indicate status:
  - Green: Clean
  - Yellow: Modified/staged
  - Red: Conflicts/errors

Indicators:
- `✚` - Added files
- `✹` - Modified files
- `✖` - Deleted files
- `⚑` - Renamed files
- `≡` - Untracked files
- `⇡` - Ahead of remote
- `⇣` - Behind remote
- `⇕` - Diverged from remote
- `✔` - Stashed changes

### Character
The prompt character changes based on status:
- `❯` (green) - Success
- `❯` (red) - Error
- `❯` (yellow) - Vim normal mode (if using vi mode)

### Command Duration
- Shows execution time for slow commands
- Only appears for commands > 2 seconds
- Yellow color for visibility
- Format: `took 5s`

### Programming Languages

Automatically detects and shows versions for:

**Node.js**
- Symbol: 
- Shows when `package.json` present
- Green color

**Python**
- Symbol: 
- Shows when `.py` files or virtual env detected
- Yellow color
- Shows virtual environment name

**Rust**
- Symbol: 
- Shows when `Cargo.toml` present
- Red color

**Go**
- Symbol: 
- Shows when `go.mod` present
- Cyan color

**Ruby**
- Symbol: 
- Shows when `Gemfile` present
- Red color

**Java**
- Symbol: 
- Shows when `.java` files present
- Red color

## Shell Integration

### Zsh
Starship is loaded in `~/.zshrc`:
```zsh
eval "$(starship init zsh)"
```

### Fish
Starship is loaded in `~/.config/fish/config.fish`:
```fish
starship init fish | source
```

### Nushell
Starship is loaded in `~/.config/nushell/env.nu`:
```nushell
starship init nu | save -f ~/.cache/starship/init.nu
source ~/.cache/starship/init.nu
```

### Bash
Add to `~/.bashrc`:
```bash
eval "$(starship init bash)"
```

## Customization

### Change Directory Color
```toml
[directory]
style = "bold cyan"  # or any color
```

### Modify Git Branch Symbol
```toml
[git_branch]
symbol = "🌱 "
```

### Add More Languages
```toml
[php]
format = "via [🐘 $version](147 bold) "
```

### Change Prompt Character
```toml
[character]
success_symbol = "[➜](bold green)"
error_symbol = "[✗](bold red)"
```

### Adjust Command Duration Threshold
```toml
[cmd_duration]
min_time = 5000  # Show for commands > 5 seconds
```

### Add Battery Module
```toml
[battery]
full_symbol = "🔋 "
charging_symbol = "⚡️ "
discharging_symbol = "💀 "

[[battery.display]]
threshold = 30
style = "bold red"
```

### Add Time to Left Prompt
```toml
[time]
disabled = false
format = '🕙[\[ $time \]]($style) '
time_format = "%T"
```

## Example Configurations

### Minimal Prompt
```toml
format = """
[┌───────────────────>](bold green)
[│](bold green)$directory$git_branch$git_status
[└─>](bold green) """

[directory]
truncation_length = 3
```

### Nerd Font Heavy
```toml
[character]
success_symbol = "[](bold green) "
error_symbol = "[](bold red) "

[directory]
read_only = " "
```

### Two-Line Prompt
```toml
format = """
$username$hostname$directory$git_branch$git_status$nodejs$python$rust
$character"""
```

## Troubleshooting

### Prompt Not Showing

**Check if Starship is installed:**
```bash
which starship
starship --version
```

**Check initialization in shell:**
```bash
# Zsh
grep starship ~/.zshrc

# Fish
grep starship ~/.config/fish/config.fish

# Nushell
grep starship ~/.config/nushell/env.nu
```

### Icons Not Displaying

**Install a Nerd Font:**
```bash
# Install JetBrains Mono Nerd Font
brew tap homebrew/cask-fonts
brew install --cask font-jetbrains-mono-nerd-font
```

**Configure terminal to use the font:**
- WezTerm: Already using JetBrains Mono
- iTerm2: Preferences → Profiles → Text → Font
- Terminal.app: Preferences → Profiles → Font

### Colors Look Wrong

**Verify terminal supports 24-bit color:**
```bash
echo $COLORTERM  # Should show "truecolor" or "24bit"
```

**Check Starship palette:**
```toml
# Add to starship.toml
[palettes.catppuccin_mocha]
rosewater = "#f5e0dc"
flamingo = "#f2cdcd"
pink = "#f5c2e7"
# ... etc
```

### Prompt Too Slow

**Disable expensive modules:**
```toml
[git_status]
disabled = true  # Git status can be slow in large repos
```

**Reduce timeout:**
```toml
[cmd_duration]
min_time = 10000  # Only show for very slow commands
```

### Configuration Not Loading

**Check syntax:**
```bash
starship config
```

**Test configuration:**
```bash
starship print-config
```

**Clear cache:**
```bash
rm -rf ~/.cache/starship
```

## Advanced Features

### Custom Modules

Add custom information to your prompt:

```toml
[custom.giturl]
command = "git remote get-url origin"
when = "git rev-parse --git-dir"
format = "at [$output]($style) "
style = "bold blue"
```

### Conditional Formatting

Show modules only in specific contexts:

```toml
[nodejs]
detect_files = ["package.json", ".nvmrc"]
detect_folders = ["node_modules"]
```

### Environment Variables

```toml
[env_var.USER]
style = "bold yellow"
format = "[$env_value]($style) "
```

### Fill Character

```toml
[fill]
symbol = " "
```

### Line Break

```toml
[line_break]
disabled = false
```

## Preset Configurations

Starship includes presets you can use:

```bash
# View available presets
starship preset --help

# Apply a preset
starship preset nerd-font-symbols -o ~/.config/starship/starship.toml
```

Available presets:
- `nerd-font-symbols` - Use Nerd Font icons
- `bracketed-segments` - Bracket each segment
- `plain-text-symbols` - No special characters
- `no-runtime-versions` - Hide language versions
- `pure-preset` - Minimal pure-like prompt
- `pastel-powerline` - Powerline with pastel colors

## Performance Tips

### 1. Disable Unused Modules
```toml
[aws]
disabled = true

[gcloud]
disabled = true
```

### 2. Limit Git Operations
```toml
[git_status]
ahead = "⇡"
behind = "⇣"
diverged = "⇕"
disabled = false
```

### 3. Scan Timeout
```toml
scan_timeout = 30  # milliseconds
```

### 4. Async Modules
Most modules are already async - they load in parallel for speed.

## Migration from Other Prompts

### From Oh My Zsh Themes

Starship replaces OMZ themes. Remove theme setting from `.zshrc`:
```bash
# Remove or comment out:
# ZSH_THEME="..."
```

### From Powerlevel10k

Starship is similar but cross-shell:
- Faster startup
- Simpler configuration
- Works in Fish, Nushell, etc.

### From Pure

Starship can mimic Pure:
```bash
starship preset pure-preset -o ~/.config/starship/starship.toml
```

## Resources

- **Starship Documentation**: https://starship.rs/
- **Configuration Reference**: https://starship.rs/config/
- **Presets Gallery**: https://starship.rs/presets/
- **Catppuccin Preset**: https://starship.rs/presets/catppuccin-powerline

## Theme Consistency

This Starship configuration uses **Catppuccin Mocha** colors to match your environment:

- ✅ **Neovim**: Catppuccin Mocha
- ✅ **Bat**: Catppuccin Mocha
- ✅ **Starship**: Catppuccin Mocha palette
- ✅ **Zsh/FZF/Eza**: Catppuccin Mocha
- ✅ **Tmux**: Catppuccin Mocha
- ✅ **Ghostty**: Catppuccin Mocha
- ✅ **Zellij**: Catppuccin Mocha
- ✅ **Nushell**: Catppuccin Mocha
- ✅ **Fish**: Catppuccin Mocha
- ✅ **OBS Studio**: Catppuccin Mocha
- ✅ **WezTerm**: Catppuccin Mocha

## Quick Reference

### Common Customizations
```toml
# Minimal prompt
format = "$directory$character"

# Hide language versions
[nodejs]
disabled = true

# Two-line prompt
format = """
$all
$character"""

# Change colors
[directory]
style = "bold cyan"
```

### Useful Commands
```bash
starship config          # Edit config
starship print-config    # View full config
starship explain         # Explain current prompt
starship timings         # Show module timings
```

---

**Updated**: 2025-12-26  
**Theme**: Catppuccin Mocha  
**Starship**: Cross-shell prompt
