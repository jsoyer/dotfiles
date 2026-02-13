# Nushell Environment Config File
# version = "0.109.1"

# ============================================================================
# PATH Configuration (MUST BE FIRST)
# ============================================================================
$env.PATH = ($env.PATH | split row (char esep) | prepend '/opt/homebrew/bin' | prepend '/opt/homebrew/opt/ruby/bin' | prepend ($env.HOME | path join '.local' 'bin'))

# ============================================================================
# Starship Prompt Integration
# ============================================================================
$env.STARSHIP_CONFIG = ($env.HOME | path join ".config" "starship" "starship-nushell.toml")
mkdir ~/.cache/starship
starship init nu | save -f ~/.cache/starship/init.nu

# ============================================================================
# Zoxide Integration (generate cache, sourced in config.nu)
# ============================================================================
mkdir ~/.cache/zoxide
zoxide init nushell --cmd cd | save -f ~/.cache/zoxide/init.nu

# ============================================================================
# Carapace Integration (generate cache, sourced in config.nu)
# ============================================================================
$env.CARAPACE_BRIDGES = 'zsh,fish,bash,inshellisense'
mkdir ~/.cache/carapace
carapace _carapace nushell | save --force ~/.cache/carapace/init.nu

# ============================================================================
# Machine Profile Detection
# ============================================================================
$env.MACHINE_PROFILE = if (sys host).hostname == "jsoyer-macOS" { "mac-pro" } else { "mac-personal" }

# ============================================================================
# Environment Variables
# ============================================================================
$env.BAT_THEME = "Catppuccin Mocha"
$env.FZF_DEFAULT_OPTS = "--color=bg+:#313244,bg:#1e1e2e,spinner:#f5e0dc,hl:#f38ba8 --color=fg:#cdd6f4,header:#f38ba8,info:#cba6f7,pointer:#f5e0dc --color=marker:#b4befe,fg+:#cdd6f4,prompt:#cba6f7,hl+:#f38ba8 --color=selected-bg:#45475a --multi"

# ============================================================================
# LS_COLORS with vivid (Catppuccin Mocha)
# ============================================================================
$env.LS_COLORS = (vivid generate catppuccin-mocha)
