#!/usr/bin/env bash
set -euo pipefail
trap 'echo "HOOK CRASH: $0 line $LINENO" >&2; exit 0' ERR

# PreCompact hook: Auto-save session state before context compaction.
# Replaces the manual "Compact Recovery Protocol" with automated state capture.
# Non-blocking (exit 0) — compaction must never be prevented.
#
# The checkpoint is written to a dedicated per-session state file under
# ~/.claude/state/ (OVERWRITE, one block per session) instead of being appended
# to docs/session-learnings.md. This decouples recovery plumbing from the
# knowledge buffer: no churn, no pollution of the tracked learnings file, and no
# cross-session clobbering. compact-restore.sh reads from the same state file.

source "${HOME}/.claude/hooks/lib/hook-logger.sh" 2>/dev/null || true

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
STATE_DIR="${HOME}/.claude/state"
mkdir -p "$STATE_DIR" 2>/dev/null || true

# Derive session id from the hook JSON payload (canonical channel), with env
# fallback. Sanitize path/space chars like the other hooks do.
INPUT=$(cat 2>/dev/null || true)
SESSION_ID=""
if command -v jq >/dev/null 2>&1; then
  SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null || true)
fi
[ -z "$SESSION_ID" ] && SESSION_ID="${CLAUDE_CODE_SESSION_ID:-${CLAUDE_SESSION_ID:-default}}"
SESSION_ID="${SESSION_ID//\//_}"
SESSION_ID="${SESSION_ID// /_}"

CHECKPOINT_FILE="${STATE_DIR}/compact-checkpoint-${SESSION_ID}.md"

# Locate session-learnings only to reference it in the resume nudge.
SESSION_LEARNINGS=""
for candidate in \
  "$PROJECT_DIR/docs/session-learnings.md" \
  "$PROJECT_DIR/session-learnings.md"; do
  if [ -f "$candidate" ]; then
    SESSION_LEARNINGS="$candidate"
    break
  fi
done
[ -z "$SESSION_LEARNINGS" ] && SESSION_LEARNINGS="$PROJECT_DIR/docs/session-learnings.md"

# Find any active progress.json files
ACTIVE_SPRINTS=""
if [ -d "$PROJECT_DIR/docs/tasks" ]; then
  while IFS= read -r pjson; do
    if command -v jq &>/dev/null; then
      IN_PROGRESS=$(jq -r '.sprints[]? | select(.status == "in_progress") | .id' "$pjson" 2>/dev/null | tr '\n' ', ' | sed 's/,$//')
      if [ -n "$IN_PROGRESS" ]; then
        ACTIVE_SPRINTS="${ACTIVE_SPRINTS}${pjson}: ${IN_PROGRESS}\n"
      fi
    fi
  done < <(find "$PROJECT_DIR/docs/tasks" -name "progress.json" -type f 2>/dev/null)
fi

# Write (overwrite) the single checkpoint block for this session.
{
  echo "## Compact Checkpoint — ${TIMESTAMP}"
  echo ""
  echo "- **CWD:** ${PROJECT_DIR}"
  echo "- **Session:** ${SESSION_ID}"
  echo "- **Learnings:** ${SESSION_LEARNINGS}"
  if [ -n "$ACTIVE_SPRINTS" ]; then
    echo "- **Active sprints:**"
    echo -e "$ACTIVE_SPRINTS" | while IFS= read -r line; do
      [ -n "$line" ] && echo "  - $line"
    done
  fi
  echo "- **Action:** Re-read the learnings file after compaction. Resume from last completed phase."
} > "$CHECKPOINT_FILE" 2>/dev/null || true

# Prune stale checkpoints (>7 days) so the state dir does not accumulate.
find "$STATE_DIR" -name 'compact-checkpoint-*.md' -type f -mtime +7 -delete 2>/dev/null || true

log_hook_event "compact-save" "saved" "checkpoint at ${TIMESTAMP} -> ${CHECKPOINT_FILE}" 2>/dev/null || true

# Output advisory to stderr (visible to agent after compact)
echo "PreCompact: Session state saved to ${CHECKPOINT_FILE}" >&2

exit 0
