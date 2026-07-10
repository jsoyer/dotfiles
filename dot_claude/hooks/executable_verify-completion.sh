#!/usr/bin/env bash
set -euo pipefail
trap 'echo "HOOK CRASH: $0 line $LINENO" >&2; exit 2' ERR

# Stop hook: Enforce Anti-Premature Completion Protocol as a hard gate.
#
# When a sprint/PRD is finalized (progress.json under docs/tasks/ goes fully
# "complete"), progress-signal.sh (PostToolUse) writes a one-shot signal marker.
# This Stop hook is gated on that signal: it verifies proper completion evidence
# exists and BLOCKS otherwise — preventing the "Three Completion Lies" (tests
# pass ≠ works, build complete ≠ runs, items done ≠ verified).
#
# Gating (fast → slow):
#   1. check_stop_hook_active     — skip recursive Stop fires
#   2. check_completion_authorized — skip unless Claude authorized this turn
#                                    (.stop-hooks-ok marker) and it was a real
#                                    completion (not an AskUserQuestion pause)
#   3. .sprint-finalized-<session> — skip unless a PRD was finalized this session
#
# Signal marker : ~/.claude/state/.sprint-finalized-${session_id}
#                 (contains the absolute path of the finalized progress.json)
# Evidence marker: ~/.claude/state/.claude-completion-evidence-${session_id}
#                 (== $CLAUDE_CODE_SESSION_ID; written by orchestrator Step 8.5 /
#                  plan-build-test Phase 5.5 after full verification)
# Warned marker  : ~/.claude/state/.claude-verify-warned-${session_id}
#                 (block once per finalization; progress-signal.sh clears it on
#                  a fresh finalization so the next Stop gets a fresh chance)
#
# Exit codes:
#   0 — nothing to verify, or evidence present, or already warned this cycle
#   2 — finalized task without proper verification evidence

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

# The finalized progress.json path. Tolerate a stale signal that points at a
# deleted file — no-op, never crash.
COMPLETED_PRD=$(cat "$SIGNAL_FILE" 2>/dev/null || echo "")
if [ -z "$COMPLETED_PRD" ] || [ ! -f "$COMPLETED_PRD" ]; then
  exit 0
fi

# Already warned once this finalization cycle → stay silent. progress-signal.sh
# clears this marker when a fresh finalization lands.
WARNED_MARKER="${STATE_DIR}/.claude-verify-warned-${SESSION_ID}"
if [ -f "$WARNED_MARKER" ]; then
  exit 0
fi

# Completion evidence marker — must exist AND carry the required fields.
EVIDENCE_MARKER="${STATE_DIR}/.claude-completion-evidence-${SESSION_ID}"
if [ -f "$EVIDENCE_MARKER" ]; then
  VALID=true
  for field in "plan_reread" "dev_server_verified" "non_privileged_user_tested"; do
    if ! grep -q "$field" "$EVIDENCE_MARKER" 2>/dev/null; then
      VALID=false
      break
    fi
  done
  if [ "$VALID" = true ]; then
    exit 0  # Evidence exists and is valid.
  fi
fi

# No / insufficient evidence — record that we warned, then BLOCK.
touch "$WARNED_MARKER" 2>/dev/null || true
{
  echo "BLOCKED: Anti-Premature Completion Protocol — task declared complete without verification evidence."
  echo ""
  echo "Completed task: $COMPLETED_PRD"
  echo ""
  echo "Before claiming completion, you MUST:"
  echo "  1. Re-read the original plan/spec file (not from memory)"
  echo "  2. Enumerate ALL remaining unchecked items"
  echo "  3. Cite specific evidence for each acceptance criterion"
  echo "  4. Start the dev server and verify content (not just HTTP 200)"
  echo "  5. Test as a non-privileged user (not admin/superuser)"
  echo ""
  echo "After verification, write evidence to: $EVIDENCE_MARKER"
  echo "Required fields: plan_reread, dev_server_verified, non_privileged_user_tested"
  echo ""
  echo "Evidence format (write with bash):"
  echo "  cat > $EVIDENCE_MARKER << 'EOF'"
  echo "  plan_reread: true"
  echo "  acceptance_criteria_cited: true"
  echo "  dev_server_verified: true"
  echo "  non_privileged_user_tested: true"
  echo "  timestamp: \$(date -Iseconds)"
  echo "  EOF"
} >&2
exit 2
