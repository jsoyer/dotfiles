#!/usr/bin/env bash
# Stop hook: Send desktop notification when Claude Code finishes
# Works on macOS (osascript) and Linux (notify-send)

set -euo pipefail

TITLE="Claude Code"
MESSAGE="Task completed"

case "$(uname -s)" in
  Darwin)
    osascript -e "display notification \"$MESSAGE\" with title \"$TITLE\"" 2>/dev/null || true
    ;;
  Linux)
    if command -v notify-send &>/dev/null; then
      notify-send "$TITLE" "$MESSAGE" 2>/dev/null || true
    fi
    ;;
esac
