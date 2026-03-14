# Nushell Environment Config File
# version = "0.111.0"

# ============================================================================
# PATH Configuration (MUST BE FIRST)
# ============================================================================
$env.PATH = ($env.PATH | split row (char esep) | prepend '/opt/homebrew/bin' | prepend '/opt/homebrew/opt/ruby/bin' | prepend ($env.HOME | path join '.local' 'bin') | prepend ($env.HOME | path join '.opencode' 'bin') | prepend '/usr/local/texlive/2025basic/bin/universal-darwin')

# ============================================================================
# Starship Prompt Integration
# ============================================================================
$env.STARSHIP_CONFIG = ($env.HOME | path join ".config" "starship" "starship-nushell.toml")
mkdir ~/.cache/starship
if (which starship | is-not-empty) {
    starship init nu | save -f ~/.cache/starship/init.nu
} else {
    "" | save --force ~/.cache/starship/init.nu
}

# ============================================================================
# Zoxide Integration (generate cache, sourced in config.nu)
# ============================================================================
mkdir ~/.cache/zoxide
if (which zoxide | is-not-empty) {
    zoxide init nushell --cmd cd | save -f ~/.cache/zoxide/init.nu
} else {
    "" | save --force ~/.cache/zoxide/init.nu
}

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
    # atuin 18.13.2 generates `job spawn -d` which doesn't exist in nu 0.111.0
    # Replace `-d <tag>` with `-t <tag>` (the correct flag name)
    atuin init nu | str replace --all 'job spawn -d' 'job spawn -t' | save --force ~/.cache/atuin/init.nu
} else {
    "" | save --force ~/.cache/atuin/init.nu
}

# ============================================================================
# Direnv - Environment switcher (PWD hook, no `direnv hook nushell` needed)
# ============================================================================
$env.config.hooks.env_change.PWD = $env.config.hooks.env_change.PWD? | default []
$env.config.hooks.env_change.PWD ++= [{||
    if (which direnv | is-empty) { return }
    let direnv_data = (direnv export json | from json | default {})
    if ($direnv_data | is-empty) { return }
    let has_path = ("PATH" in ($direnv_data | columns))
    $direnv_data | load-env
    if $has_path {
        # direnv exports PATH as colon-separated string; convert back to list
        $env.PATH = ($env.PATH | split row (char esep))
    }
}]

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
if (which vivid | is-not-empty) {
    $env.LS_COLORS = (vivid generate catppuccin-mocha)
}
