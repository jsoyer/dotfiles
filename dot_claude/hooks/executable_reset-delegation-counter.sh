#!/usr/bin/env bash
set -euo pipefail
trap 'exit 0' ERR

# UserPromptSubmit hook: reset main-agent read counter for a fresh turn.
# Each user message = new turn = 3 fresh "free" reads before enforce-delegation.sh kicks in.
#
# Also performs opportunistic cleanup of stale counter files from old sessions.

INPUT=$(cat)

SESSION_ID=""
if command -v jq &>/dev/null; then
  SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null || printf '')
fi
# Fallback regex if jq unavailable
if [ -z "$SESSION_ID" ] && [[ "$INPUT" =~ \"session_id\":\"([^\"]*)\" ]]; then
  SESSION_ID="${BASH_REMATCH[1]}"
fi
[ -z "$SESSION_ID" ] && SESSION_ID="default"
SESSION_ID="${SESSION_ID//\//_}"
SESSION_ID="${SESSION_ID// /_}"

STATE_DIR="$HOME/.claude/hooks/state"
mkdir -p "$STATE_DIR" 2>/dev/null || true

# Reset counter for this session
echo 0 > "$STATE_DIR/main-reads-$SESSION_ID" 2>/dev/null || true

# Clean up stale counter files (older than 1 day) to prevent disk bloat
find "$STATE_DIR" -maxdepth 1 -name "main-reads-*" -mtime +1 -delete 2>/dev/null || true

# Log the reset (non-fatal)
if [ -f "$HOME/.claude/hooks/lib/hook-logger.sh" ]; then
  source "$HOME/.claude/hooks/lib/hook-logger.sh" 2>/dev/null || true
  log_hook_event "reset-delegation-counter" "reset" "session=$SESSION_ID" 2>/dev/null || true
fi

exit 0
