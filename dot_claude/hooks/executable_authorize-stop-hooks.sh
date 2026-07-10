#!/usr/bin/env bash
# authorize-stop-hooks.sh — signal that Stop hooks should run this turn.
#
# Claude runs this (via Bash) when a task finishes successfully, before
# the final response. The Stop hooks check for the signal file and clear
# it after running (one-shot per invocation).
#
# Usage (from Claude's Bash tool):
#   bash ~/.claude/hooks/authorize-stop-hooks.sh
#
# The session ID is read from the CLAUDE_CODE_SESSION_ID env var injected by
# Claude Code (this equals the `.session_id` the Stop hooks read from their JSON
# payload). CLAUDE_SESSION_ID is kept as a legacy fallback. Do NOT use
# CLAUDE_CODE_BRIDGE_SESSION_ID — that is the web/bridge session id and does not
# match the marker the Stop hooks look for.

STATE_DIR="${HOME}/.claude/state"
mkdir -p "$STATE_DIR"

SESSION_ID="${CLAUDE_CODE_SESSION_ID:-${CLAUDE_SESSION_ID:-}}"

if [ -z "$SESSION_ID" ]; then
  # Non-fatal: warn to stderr but exit 0 so Claude's Bash tool doesn't surface
  # an error mid-task. The Stop hooks will simply skip without the env var.
  echo "authorize-stop-hooks: CLAUDE_CODE_SESSION_ID not set — Stop hooks will not be gated this turn" >&2
  exit 0
fi

SIGNAL_FILE="${STATE_DIR}/.stop-hooks-ok-${SESSION_ID}"
touch "$SIGNAL_FILE"
echo "Stop hooks authorized for session ${SESSION_ID}"
