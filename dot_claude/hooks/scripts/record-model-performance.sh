#!/usr/bin/env bash
set -euo pipefail

# record-model-performance.sh
#
# Atomically record a task-completion data point into
# ~/.claude/evolution/model-performance.json. Called by /compound, by
# compound-reminder.sh closing flow, or by sprint-executor/orchestrator
# when they know the (model, task_type, first_try_success) triple.
#
# Usage:
#   record-model-performance.sh <model> <task_type> <first_try_success>
#
# Args:
#   model                 — one of: sonnet | opus | haiku
#   task_type             — free-form label (e.g. "sprint_execution", "verification",
#                           "bug_fix", "implementation", "compound", "file_scanning")
#   first_try_success     — "true" or "false"
#
# Environment:
#   PERF_FILE             — override path (default: ~/.claude/evolution/model-performance.json)
#   RECORD_QUIET          — set to any value to suppress success echo
#
# Behavior:
#   - Creates the JSON file with skeleton if missing
#   - Increments `attempts`, adds 1 to `first_try_success` if success=true
#   - Atomically writes under flock to serialize concurrent recordings
#   - Updates `last_updated` to current ISO-8601 UTC timestamp
#   - Removes stale `_downgrade_candidates` / `_watch_list` entries for this
#     (model, task_type) pair — the evaluate script recomputes them fresh
#
# Exits 0 on success. Exits 1 on invalid args. Never crashes the caller.

MODEL="${1:-}"
TASK_TYPE="${2:-}"
SUCCESS="${3:-}"

if [ -z "$MODEL" ] || [ -z "$TASK_TYPE" ] || [ -z "$SUCCESS" ]; then
  echo "Usage: $0 <model> <task_type> <first_try_success>" >&2
  echo "  model: sonnet | opus | haiku" >&2
  echo "  task_type: free-form label" >&2
  echo "  first_try_success: true | false" >&2
  exit 1
fi

case "$MODEL" in
  sonnet|opus|haiku) ;;
  *)
    echo "ERROR: model must be sonnet | opus | haiku (got: $MODEL)" >&2
    exit 1
    ;;
esac

case "$SUCCESS" in
  true|false) ;;
  *)
    echo "ERROR: first_try_success must be true | false (got: $SUCCESS)" >&2
    exit 1
    ;;
esac

if ! command -v jq &>/dev/null; then
  echo "ERROR: jq is required" >&2
  exit 1
fi

PERF_FILE="${PERF_FILE:-$HOME/.claude/evolution/model-performance.json}"
LOCK_FILE="$HOME/.claude/evolution/.perf.lock"

mkdir -p "$(dirname "$PERF_FILE")"

if [ ! -f "$PERF_FILE" ]; then
  cat > "$PERF_FILE" << 'EOF'
{
  "models": {
    "sonnet": {"task_types": {}},
    "opus": {"task_types": {}},
    "haiku": {"task_types": {}}
  },
  "last_updated": ""
}
EOF
fi

# Atomic update under exclusive flock.
(
  flock -x 9

  TMP=$(mktemp)
  NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  SUCCESS_INC=0
  [ "$SUCCESS" = "true" ] && SUCCESS_INC=1

  jq --arg m "$MODEL" \
     --arg tt "$TASK_TYPE" \
     --argjson si "$SUCCESS_INC" \
     --arg now "$NOW" '
    .models //= {} |
    .models[$m] //= {"task_types": {}} |
    .models[$m].task_types //= {} |
    .models[$m].task_types[$tt] //= {"attempts": 0, "first_try_success": 0, "required_upgrade": 0} |
    .models[$m].task_types[$tt].attempts += 1 |
    .models[$m].task_types[$tt].first_try_success += $si |
    .last_updated = $now
  ' "$PERF_FILE" > "$TMP"

  if [ -s "$TMP" ]; then
    mv "$TMP" "$PERF_FILE"
  else
    rm -f "$TMP"
    echo "ERROR: jq produced empty output; not overwriting $PERF_FILE" >&2
    exit 1
  fi
) 9>"$LOCK_FILE"

if [ -z "${RECORD_QUIET:-}" ]; then
  echo "Recorded: model=$MODEL task_type=$TASK_TYPE first_try_success=$SUCCESS"
fi
exit 0
