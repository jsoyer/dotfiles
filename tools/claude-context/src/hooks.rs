//! Shell hook generation for auto-apply on directory change.
//!
//! Usage: `eval "$(cctx hook zsh)"` in shell rc file.
//! Checks project-map.yaml for known projects before applying.

use anyhow::{bail, Result};

/// Generate shell hook code for the given shell.
pub fn generate(shell: &str) -> Result<String> {
    match shell {
        "zsh" => Ok(generate_zsh()),
        "bash" => Ok(generate_bash()),
        "fish" => Ok(generate_fish()),
        other => bail!(
            "Unsupported shell: '{}'. Supported: zsh, bash, fish",
            other
        ),
    }
}

fn generate_zsh() -> String {
    r#"# cctx auto-apply hook (zsh)
_cctx_chpwd() {
  local map="${HOME}/.config/claude-context/project-map.yaml"
  [[ -f "$map" ]] || return
  # Only apply if current dir is in project-map
  if command grep -q "$(pwd)" "$map" 2>/dev/null; then
    # Skip if already configured
    [[ -d ".claude/skills" ]] && return
    command cctx apply --auto --yes 2>/dev/null &!
  fi
}
autoload -Uz add-zsh-hook
add-zsh-hook chpwd _cctx_chpwd
"#
    .to_string()
}

fn generate_bash() -> String {
    r#"# cctx auto-apply hook (bash)
_cctx_prompt_command() {
  local cwd="$PWD"
  if [ "$cwd" != "$_CCTX_LAST_DIR" ]; then
    _CCTX_LAST_DIR="$cwd"
    local map="${HOME}/.config/claude-context/project-map.yaml"
    [ -f "$map" ] || return
    if command grep -q "$cwd" "$map" 2>/dev/null; then
      [ -d ".claude/skills" ] && return
      command cctx apply --auto --yes 2>/dev/null &
    fi
  fi
}
PROMPT_COMMAND="_cctx_prompt_command;${PROMPT_COMMAND}"
"#
    .to_string()
}

fn generate_fish() -> String {
    r#"# cctx auto-apply hook (fish)
function _cctx_on_cd --on-variable PWD
  set -l map "$HOME/.config/claude-context/project-map.yaml"
  test -f "$map"; or return
  if command grep -q (pwd) "$map" 2>/dev/null
    test -d ".claude/skills"; and return
    command cctx apply --auto --yes 2>/dev/null &
  end
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
        assert!(hook.contains("cctx apply"));
        assert!(hook.contains("project-map.yaml"));
    }

    #[test]
    fn generates_bash_hook() {
        let hook = generate("bash").unwrap();
        assert!(hook.contains("PROMPT_COMMAND"));
        assert!(hook.contains("cctx apply"));
    }

    #[test]
    fn generates_fish_hook() {
        let hook = generate("fish").unwrap();
        assert!(hook.contains("on-variable PWD"));
        assert!(hook.contains("cctx apply"));
    }

    #[test]
    fn rejects_unknown_shell() {
        assert!(generate("powershell").is_err());
    }
}
