#!/usr/bin/env bash
set -euo pipefail
trap 'echo "HOOK CRASH: $0 line $LINENO" >&2; exit 2' ERR

# Stop hook: BLOCK if a sprint/PRD was finalized but /compound hasn't run.
#
# The learning loop is the most important part of the system — without it, the
# workflow never improves. When progress-signal.sh (PostToolUse) notices a
# progress.json under docs/tasks/ go fully "complete", it writes a one-shot
# signal marker. This Stop hook is gated on that signal and blocks (exit 2)
# until /compound writes its done marker.
#
# Gating (fast → slow):
#   1. check_stop_hook_active      — skip recursive Stop fires
#   2. check_completion_authorized — skip unless Claude authorized this turn
#                                    (.stop-hooks-ok marker) and it was a real
#                                    completion (not an AskUserQuestion pause)
#   3. .sprint-finalized-<session> — skip unless a PRD was finalized this session
#
# Done marker  : ~/.claude/state/.claude-compound-done-${session_id}
#                (== $CLAUDE_CODE_SESSION_ID; written by the /compound skill)
# Warned marker: ~/.claude/state/.claude-compound-warned-${session_id}
#                (block once per finalization; progress-signal.sh clears it on a
#                 fresh finalization so the next Stop gets a fresh chance)

# jq is required for JSON parsing. Exit silently if missing (other hooks warn).
if ! command -v jq &>/dev/null; then
  exit 0
fi

# Source shared stop-guard (fail-open: if missing, guards are no-ops).
source ~/.claude/hooks/lib/stop-guard.sh 2>/dev/null || true

# Read JSON input from stdin.
INPUT=$(cat)

# Guard 1: prevent infinite loop on recursive Stop fire.
check_stop_hook_active "$INPUT"

# Guard 2: only run when Claude authorized this turn as a genuine completion.
check_completion_authorized "$INPUT"

STATE_DIR="${HOME}/.claude/state"

SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null || echo "")
if [ -z "$SESSION_ID" ]; then
  exit 0
fi

# Guard 3: only act when a sprint/PRD was finalized this session (O(1) marker,
# written by progress-signal.sh — no filesystem walk here).
SIGNAL_FILE="${STATE_DIR}/.sprint-finalized-${SESSION_ID}"
if [ ! -f "$SIGNAL_FILE" ]; then
  exit 0
fi

# Tolerate a stale signal that points at a deleted file — no-op, never crash.
COMPLETED_PRD=$(cat "$SIGNAL_FILE" 2>/dev/null || echo "")
if [ -z "$COMPLETED_PRD" ] || [ ! -f "$COMPLETED_PRD" ]; then
  exit 0
fi

# /compound already ran this session → nothing to remind.
DONE_MARKER="${STATE_DIR}/.claude-compound-done-${SESSION_ID}"
if [ -f "$DONE_MARKER" ]; then
  exit 0
fi

# Already reminded once this finalization cycle → stay silent.
WARNED_MARKER="${STATE_DIR}/.claude-compound-warned-${SESSION_ID}"
if [ -f "$WARNED_MARKER" ]; then
  exit 0
fi

# Finalized without /compound — record that we warned, then BLOCK.
touch "$WARNED_MARKER" 2>/dev/null || true
{
  echo "BLOCKED: Completed task detected but /compound hasn't run."
  echo "The learning loop captures errors, model performance, and patterns that prevent future failures."
  echo "Run /compound to capture learnings, or dismiss this to skip (learnings will be lost)."
} >&2
exit 2
