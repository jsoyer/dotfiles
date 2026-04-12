# Environment: PRoot-Distro ARM64

Auto-detected via `uname -r` containing `PRoot-Distro`. Two layers: settings.json env vars, and `session-start.sh` (per-session warnings — proot checks merged in) + `hooks/scripts/worktree-preflight.sh` (per-sprint setup). Full rules, native module failures, language-specific workarounds, and error patterns: `~/.claude/docs/on-demand/proot-distro-environment.md`.

SessionStart hook auto-detects the environment and warns about known limitations.
