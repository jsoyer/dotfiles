//! Shell hook generation for auto-apply on directory change.
//!
//! Usage: `eval "$(aictx hook zsh)"` in shell rc file.
//! Checks project-map.yaml for known projects before applying.

use anyhow::{bail, Result};

/// Generate shell hook code for the given shell.
pub fn generate(shell: &str) -> Result<String> {
    match shell {
        "zsh" => Ok(generate_zsh()),
        "bash" => Ok(generate_bash()),
        "fish" => Ok(generate_fish()),
        other => bail!("Unsupported shell: '{}'. Supported: zsh, bash, fish", other),
    }
}

fn generate_zsh() -> String {
    r#"# aictx auto-apply hook (zsh)
_aictx_chpwd() {
    local map="$HOME/.config/aictx/project-map.yaml"
    [[ -f "$map" ]] || return
    grep -q "$(pwd)" "$map" || return
    local stamp_dir="$HOME/.cache/aictx"
    local stamp="$stamp_dir/$(echo -n "$(pwd)" | md5sum 2>/dev/null | cut -c1-8 || echo -n "$(pwd)" | shasum | cut -c1-8).stamp"
    if [[ -f "$stamp" ]]; then
        local age=$(( $(date +%s) - $(stat -c %Y "$stamp" 2>/dev/null || stat -f %m "$stamp" 2>/dev/null || echo 0) ))
        (( age < 300 )) && return
    fi
    mkdir -p "$stamp_dir"
    touch "$stamp"
    aictx apply --auto --yes 2>/dev/null &!
}
autoload -Uz add-zsh-hook
add-zsh-hook chpwd _aictx_chpwd
"#
    .to_string()
}

fn generate_bash() -> String {
    r#"# aictx auto-apply hook (bash)
_aictx_prompt_command() {
    local cwd="$PWD"
    if [ "$cwd" != "$_AICTX_LAST_DIR" ]; then
        _AICTX_LAST_DIR="$cwd"
        local map="${HOME}/.config/aictx/project-map.yaml"
        [ -f "$map" ] || return
        command grep -q "$cwd" "$map" 2>/dev/null || return
        local stamp_dir="${HOME}/.cache/aictx"
        local stamp="${stamp_dir}/$(echo -n "$cwd" | md5sum 2>/dev/null | cut -c1-8 || echo -n "$cwd" | shasum | cut -c1-8).stamp"
        if [ -f "$stamp" ]; then
            local mtime
            mtime=$(stat -c %Y "$stamp" 2>/dev/null || stat -f %m "$stamp" 2>/dev/null || echo 0)
            local age=$(( $(date +%s) - mtime ))
            [ "$age" -lt 300 ] && return
        fi
        mkdir -p "$stamp_dir"
        touch "$stamp"
        command aictx apply --auto --yes 2>/dev/null &
    fi
}
PROMPT_COMMAND="_aictx_prompt_command;${PROMPT_COMMAND}"
"#
    .to_string()
}

fn generate_fish() -> String {
    r#"# aictx auto-apply hook (fish)
function _aictx_on_cd --on-variable PWD
    set -l map "$HOME/.config/aictx/project-map.yaml"
    test -f "$map"; or return
    command grep -q (pwd) "$map" 2>/dev/null; or return
    set -l stamp_dir "$HOME/.cache/aictx"
    set -l pwd_hash (echo -n (pwd) | md5sum 2>/dev/null | cut -c1-8; or echo -n (pwd) | shasum | cut -c1-8)
    set -l stamp "$stamp_dir/$pwd_hash.stamp"
    if test -f "$stamp"
        set -l mtime (stat -c %Y "$stamp" 2>/dev/null; or stat -f %m "$stamp" 2>/dev/null; or echo 0)
        set -l age (math (date +%s) - $mtime)
        test $age -lt 300; and return
    end
    mkdir -p "$stamp_dir"
    touch "$stamp"
    command aictx apply --auto --yes 2>/dev/null &
end
"#
    .to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn generates_zsh_hook() {
        let hook = generate("zsh").unwrap();
        assert!(hook.contains("chpwd"));
        assert!(hook.contains("aictx apply"));
        assert!(hook.contains("project-map.yaml"));
        // debounce stamp logic present
        assert!(hook.contains(".cache/aictx"));
        assert!(hook.contains("age < 300"));
        // no old .claude/skills guard
        assert!(!hook.contains(".claude/skills"));
    }

    #[test]
    fn generates_bash_hook() {
        let hook = generate("bash").unwrap();
        assert!(hook.contains("PROMPT_COMMAND"));
        assert!(hook.contains("aictx apply"));
        // debounce stamp logic present
        assert!(hook.contains(".cache/aictx"));
        assert!(hook.contains("age"));
        // no old .claude/skills guard
        assert!(!hook.contains(".claude/skills"));
    }

    #[test]
    fn generates_fish_hook() {
        let hook = generate("fish").unwrap();
        assert!(hook.contains("on-variable PWD"));
        assert!(hook.contains("aictx apply"));
        // debounce stamp logic present
        assert!(hook.contains(".cache/aictx"));
        assert!(hook.contains("age"));
        // no old .claude/skills guard
        assert!(!hook.contains(".claude/skills"));
    }

    #[test]
    fn rejects_unknown_shell() {
        assert!(generate("powershell").is_err());
    }
}
