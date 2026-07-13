#!/usr/bin/env bash
set -euo pipefail
trap 'echo "HOOK CRASH: $0 line $LINENO" >&2; exit 0' ERR

# PostCompact hook: Auto-restore session state after context compaction.
# Outputs the last compact checkpoint so the agent knows where to resume.
# Non-blocking (exit 0) — advisory only.
#
# Reads the checkpoint from the per-session state file written by
# compact-save.sh (~/.claude/state/compact-checkpoint-<session>.md) instead of
# grepping docs/session-learnings.md. Durable resume state still comes from
# progress.json, recomputed live below.

source "${HOME}/.claude/hooks/lib/hook-logger.sh" 2>/dev/null || true

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
STATE_DIR="${HOME}/.claude/state"

# Derive session id from the hook JSON payload (canonical channel), with env
# fallback. Must match compact-save.sh so the same file is found.
INPUT=$(cat 2>/dev/null || true)
SESSION_ID=""
if command -v jq >/dev/null 2>&1; then
  SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null || true)
fi
[ -z "$SESSION_ID" ] && SESSION_ID="${CLAUDE_CODE_SESSION_ID:-${CLAUDE_SESSION_ID:-default}}"
SESSION_ID="${SESSION_ID//\//_}"
SESSION_ID="${SESSION_ID// /_}"

CHECKPOINT_FILE="${STATE_DIR}/compact-checkpoint-${SESSION_ID}.md"

if [ ! -f "$CHECKPOINT_FILE" ]; then
  exit 0
fi

LAST_CHECKPOINT=$(cat "$CHECKPOINT_FILE" 2>/dev/null)
if [ -z "$LAST_CHECKPOINT" ]; then
  exit 0
fi

# Resolve the learnings file to point the agent at for re-reading.
SESSION_LEARNINGS=""
for candidate in \
  "$PROJECT_DIR/docs/session-learnings.md" \
  "$PROJECT_DIR/session-learnings.md"; do
  if [ -f "$candidate" ]; then
    SESSION_LEARNINGS="$candidate"
    break
  fi
done

# Check for pending progress.json files
PENDING_WORK=""
if [ -d "$PROJECT_DIR/docs/tasks" ]; then
  while IFS= read -r pjson; do
    if command -v jq &>/dev/null; then
      PENDING=$(jq -r '.sprints[]? | select(.status != "complete") | .id' "$pjson" 2>/dev/null | tr '\n' ', ' | sed 's/,$//')
      if [ -n "$PENDING" ]; then
        PRD=$(jq -r '.prd // "unknown"' "$pjson" 2>/dev/null)
        PENDING_WORK="${PENDING_WORK}\n  - ${PRD}: pending=[${PENDING}]"
      fi
    fi
  done < <(find "$PROJECT_DIR/docs/tasks" -name "progress.json" -type f 2>/dev/null)
fi

# Output restore summary to stderr (visible to agent)
{
  echo ""
  echo "╔══════════════════════════════════════════════════╗"
  echo "║  PostCompact: Session state restored             ║"
  echo "╚══════════════════════════════════════════════════╝"
  echo "$LAST_CHECKPOINT"
  if [ -n "$PENDING_WORK" ]; then
    echo ""
    echo "Pending work:"
    echo -e "$PENDING_WORK"
  fi
  if [ -n "$SESSION_LEARNINGS" ]; then
    echo ""
    echo "→ Re-read: ${SESSION_LEARNINGS}"
  fi
  echo ""
} >&2

log_hook_event "compact-restore" "restored" "checkpoint loaded from ${CHECKPOINT_FILE}" 2>/dev/null || true

exit 0
