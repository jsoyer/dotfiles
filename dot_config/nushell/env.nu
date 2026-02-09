# Nushell Environment Config File
# version = "0.109.1"

# ============================================================================
# PATH Configuration (MUST BE FIRST)
# ============================================================================
$env.PATH = ($env.PATH | split row (char esep) | prepend '/opt/homebrew/bin' | prepend ($env.HOME | path join '.local' 'bin'))

# ============================================================================
# Starship Prompt Integration
# ============================================================================
$env.STARSHIP_CONFIG = "/Users/jeromesoyer/.config/starship/starship-nushell.toml"
mkdir ~/.cache/starship
starship init nu | save -f ~/.cache/starship/init.nu
source ~/.cache/starship/init.nu

# ============================================================================
# Zoxide Prompt Integration
# ============================================================================
zoxide init nushell | save -f ~/.zoxide.nu

# ============================================================================
# Carapace Prompt Integration
# ============================================================================
$env.CARAPACE_BRIDGES = 'zsh,fish,bash,inshellisense'
mkdir ~/.cache/carapace
carapace _carapace nushell | save --force ~/.cache/carapace/init.nu

# ============================================================================
# Environment Variables
# ============================================================================
$env.BAT_THEME = "Catppuccin Mocha"
$env.FZF_DEFAULT_OPTS = "--color=bg+:#313244,bg:#1e1e2e,spinner:#f5e0dc,hl:#f38ba8 --color=fg:#cdd6f4,header:#f38ba8,info:#cba6f7,pointer:#f5e0dc --color=marker:#b4befe,fg+:#cdd6f4,prompt:#cba6f7,hl+:#f38ba8 --color=selected-bg:#45475a --multi"

# ============================================================================
# LS_COLORS with vivid (Catppuccin Mocha)
# ============================================================================
$env.LS_COLORS = (vivid generate catppuccin-mocha)
