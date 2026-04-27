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
# The session ID is read from the CLAUDE_SESSION_ID env var injected by
# Claude Code, or falls back to a stable hash of the process tree.

STATE_DIR="${HOME}/.claude/state"
mkdir -p "$STATE_DIR"

SESSION_ID="${CLAUDE_SESSION_ID:-}"

if [ -z "$SESSION_ID" ]; then
  # Non-fatal: warn to stderr but exit 0 so Claude's Bash tool doesn't surface
  # an error mid-task. The Stop hooks will simply skip without the env var.
  echo "authorize-stop-hooks: CLAUDE_SESSION_ID not set — Stop hooks will not be gated this turn" >&2
  exit 0
fi

SIGNAL_FILE="${STATE_DIR}/.stop-hooks-ok-${SESSION_ID}"
touch "$SIGNAL_FILE"
echo "Stop hooks authorized for session ${SESSION_ID}"
