# Nushell Environment Config File
# version = "0.109.1"

# ============================================================================
# PATH Configuration (MUST BE FIRST)
# ============================================================================
$env.PATH = ($env.PATH | split row (char esep) | prepend '/opt/homebrew/bin' | prepend '/opt/homebrew/opt/ruby/bin' | prepend ($env.HOME | path join '.local' 'bin') | prepend '/usr/local/texlive/2025basic/bin/universal-darwin')

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
mkdir ~/.cache/carapace
if (which carapace | is-not-empty) {
    $env.CARAPACE_BRIDGES = 'zsh,fish,bash,inshellisense'
    carapace _carapace nushell | save --force ~/.cache/carapace/init.nu
} else {
    "" | save --force ~/.cache/carapace/init.nu
}

# ============================================================================
# Atuin - Magical shell history (generate cache, sourced in config.nu)
# ============================================================================
mkdir ~/.cache/atuin
if (which atuin | is-not-empty) {
    atuin init nu | save --force ~/.cache/atuin/init.nu
} else {
    "" | save --force ~/.cache/atuin/init.nu
}

# ============================================================================
# Direnv - Environment switcher (generate cache, sourced in config.nu)
# ============================================================================
mkdir ~/.cache/direnv
if (which direnv | is-not-empty) {
    direnv hook nushell | save --force ~/.cache/direnv/init.nu
} else {
    "" | save --force ~/.cache/direnv/init.nu
}

# ============================================================================
# Machine Profile Detection
# ============================================================================
$env.MACHINE_PROFILE = if (sys host).hostname == "jsoyer-macOS" { "mac-pro" } else { "mac-personal" }

# Mac Pro: install casks in $HOME/Applications
if $env.MACHINE_PROFILE == "mac-pro" {
    $env.HOMEBREW_CASK_OPTS = $"--appdir=($env.HOME)/Applications"
}

# ============================================================================
# Environment Variables
# ============================================================================
$env.BAT_THEME = "Catppuccin Mocha"
$env.FZF_DEFAULT_OPTS = "--color=bg+:#313244,bg:#1e1e2e,spinner:#f5e0dc,hl:#f38ba8 --color=fg:#cdd6f4,header:#f38ba8,info:#cba6f7,pointer:#f5e0dc --color=marker:#b4befe,fg+:#cdd6f4,prompt:#cba6f7,hl+:#f38ba8 --color=selected-bg:#45475a --multi"

# ============================================================================
# LS_COLORS with vivid (Catppuccin Mocha)
# ============================================================================
$env.LS_COLORS = (vivid generate catppuccin-mocha)
