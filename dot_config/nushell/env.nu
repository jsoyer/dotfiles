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
let _starship_cache = ($env.HOME | path join ".cache" "starship" "init.nu")
let _starship_ver_file = ($env.HOME | path join ".cache" "starship" "version")
if (which starship | is-not-empty) {
    let _current_ver = (starship --version | str trim)
    let _cached_ver = if ($_starship_ver_file | path exists) {
        open $_starship_ver_file | str trim
    } else {
        ""
    }
    if not ($_starship_cache | path exists) or $_cached_ver != $_current_ver {
        mkdir ($env.HOME | path join ".cache" "starship")
        starship init nu | save -f $_starship_cache
        $_current_ver | save -f $_starship_ver_file
    }
} else {
    if not ($_starship_cache | path exists) {
        mkdir ($env.HOME | path join ".cache" "starship")
        "" | save --force $_starship_cache
    }
}

# ============================================================================
# Zoxide Integration (generate cache, sourced in config.nu)
# ============================================================================
let _zoxide_cache = ($env.HOME | path join ".cache" "zoxide" "init.nu")
if not ($_zoxide_cache | path exists) {
    if (which zoxide | is-not-empty) {
        mkdir ($env.HOME | path join ".cache" "zoxide")
        zoxide init nushell --cmd cd | save -f $_zoxide_cache
    } else {
        mkdir ($env.HOME | path join ".cache" "zoxide")
        "" | save --force $_zoxide_cache
    }
}

# ============================================================================
# Carapace Integration (generate cache, sourced in config.nu)
# ============================================================================
let _carapace_cache = ($env.HOME | path join ".cache" "carapace" "init.nu")
if not ($_carapace_cache | path exists) {
    if (which carapace | is-not-empty) {
        $env.CARAPACE_BRIDGES = 'zsh,fish,bash,inshellisense'
        mkdir ($env.HOME | path join ".cache" "carapace")
        carapace _carapace nushell | save --force $_carapace_cache
    } else {
        mkdir ($env.HOME | path join ".cache" "carapace")
        "" | save --force $_carapace_cache
    }
}

# ============================================================================
# Atuin - Magical shell history (generate cache, sourced in config.nu)
# ============================================================================
let _atuin_cache = ($env.HOME | path join ".cache" "atuin" "init.nu")
if not ($_atuin_cache | path exists) {
    if (which atuin | is-not-empty) {
        mkdir ($env.HOME | path join ".cache" "atuin")
        # atuin 18.13.2 generates `job spawn -d` which doesn't exist in nu 0.111.0
        # Replace `-d <tag>` with `-t <tag>` (the correct flag name)
        atuin init nu | str replace --all 'job spawn -d' 'job spawn -t' | save --force $_atuin_cache
    } else {
        mkdir ($env.HOME | path join ".cache" "atuin")
        "" | save --force $_atuin_cache
    }
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
# LS_COLORS with vivid (Catppuccin Mocha) -- cached to avoid fork on every startup
# ============================================================================
let _vivid_cache = ($env.HOME | path join ".cache" "vivid" "ls-colors-catppuccin-mocha.txt")
if (which vivid | is-not-empty) {
    if not ($_vivid_cache | path exists) {
        mkdir ($env.HOME | path join ".cache" "vivid")
        vivid generate catppuccin-mocha | save -f $_vivid_cache
    }
    $env.LS_COLORS = (open $_vivid_cache | str trim)
}
