#!/usr/bin/env bash
# stop-guard.sh — guards for Stop hooks
#
# Source this in any Stop hook AFTER reading stdin into INPUT.
# SAFETY: fail-open — if jq fails, guards are no-ops (they do not block the hook).
#
# Usage:
#   source ~/.claude/hooks/lib/stop-guard.sh 2>/dev/null || true
#   INPUT=$(cat)
#   check_stop_hook_active "$INPUT"
#   check_completion_authorized "$INPUT"

# Guard 1: exit 0 if the Stop hook is firing recursively (stop_hook_active=true)
check_stop_hook_active() {
  local input="${1:-}"
  local val
  val=$(printf '%s' "$input" | jq -r '.stop_hook_active // false' 2>/dev/null || echo "false")
  if [ "$val" = "true" ]; then
    exit 0
  fi
}

# Guard 2: exit 0 unless Claude explicitly authorized Stop hooks for this turn.
#
# Stop hooks are expensive (typecheck, git ops, cleanup). They should only run
# when Claude signals successful task completion — not on Monitor events,
# intermediate responses, or background turns.
#
# Authorization: Claude writes ~/.claude/state/.stop-hooks-ok-<session_id>
# via Bash before finishing a task. This guard checks for that file and
# deletes it after allowing the hooks to proceed (one-shot per signal).
#
# To authorize from Claude:
#   SESSION_ID=$(echo "$CLAUDE_SESSION_ID" | head -1)
#   touch ~/.claude/state/.stop-hooks-ok-${SESSION_ID}
#
# Or simply run the helper:
#   bash ~/.claude/hooks/authorize-stop-hooks.sh
check_completion_authorized() {
  local input="${1:-}"

  # Fast path #1: session_id check (cheap).
  local session_id
  session_id=$(printf '%s' "$input" | jq -r '.session_id // empty' 2>/dev/null || echo "")
  if [ -z "$session_id" ] || [ "$session_id" = "null" ]; then
    exit 0
  fi

  # Fast path #2: marker file check BEFORE parsing transcript.
  # If no authorization marker, skip hooks immediately — transcript parse is O(N)
  # in transcript length and must not run for unauthorized turns.
  local state_dir="${HOME}/.claude/state"
  local signal_file="${state_dir}/.stop-hooks-ok-${session_id}"
  if [ ! -f "$signal_file" ]; then
    exit 0
  fi

  # Auth marker present — now check if the turn was actually a completion.
  # If the last assistant tool_use was AskUserQuestion, the turn is a pause, not
  # a completion; skip hooks (but do NOT delete the marker — a later real
  # completion in the same session should still fire the hooks).
  local last_tool
  last_tool=$(printf '%s' "$input" | jq -r '
    (.transcript // []) | map(select(.role == "assistant")) | last
    | (.content // []) | map(select(.type == "tool_use")) | last
    | .name // ""
  ' 2>/dev/null || echo "")
  if [ "$last_tool" = "AskUserQuestion" ]; then
    exit 0
  fi

  # Auth + genuine completion → allow hook to proceed. Do NOT consume the
  # marker here — consume-auth-marker.sh (the last Stop hook) removes it
  # after the full chain has run, so every stop hook in the chain sees it.
}
