#!/usr/bin/env bash
set -uo pipefail

# Test suite: Stop hooks must fire ONLY at sprint finalization, never on
# ordinary Q&A turns (AskUserQuestion / mid-task questions / empty turns).
#
# Covers:
#   1. Q&A turns — both Stop hooks exit 0 with no output
#   2. progress-signal.sh — writes marker only when progress.json has every
#      sprint in `complete` state and lives under a docs/tasks/ subtree
#   3. Marker-gated Stop hooks — they wake up only after a signal is written
#   4. verify-completion.sh — blocks without evidence, passes with evidence
#   5. compound-reminder.sh — blocks without /compound done marker, passes with it
#   6. Signal hook guards: unknown session_id, wrong tool name, non-progress.json
#   7. Warned markers get reset when a fresh finalization signal lands

HOOK_DIR="$HOME/.claude/hooks"
SIGNAL_HOOK="$HOOK_DIR/progress-signal.sh"
COMPOUND_HOOK="$HOOK_DIR/compound-reminder.sh"
VERIFY_HOOK="$HOOK_DIR/verify-completion.sh"
STATE_DIR="$HOME/.claude/state"

TEST_SESSION="gating-test-$$"
TMP_ROOT=$(mktemp -d)
TASK_DIR="$TMP_ROOT/docs/tasks/feature/2026-04-11-demo"
mkdir -p "$TASK_DIR"
PJSON="$TASK_DIR/progress.json"

PASS=0
FAIL=0
ERRORS=()

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

pass() { PASS=$((PASS+1)); printf "  ${GREEN}✓${NC} %s\n" "$1"; }
fail() { FAIL=$((FAIL+1)); printf "  ${RED}✗${NC} %s ${RED}(%s)${NC}\n" "$1" "$2"; ERRORS+=("$1: $2"); }
section() { printf "\n${BOLD}${CYAN}▸ %s${NC}\n" "$1"; }

cleanup() {
  rm -f "$STATE_DIR/.sprint-finalized-$TEST_SESSION" \
        "$STATE_DIR/.claude-compound-warned-$TEST_SESSION" \
        "$STATE_DIR/.claude-verify-warned-$TEST_SESSION" \
        "$STATE_DIR/.claude-compound-done-$TEST_SESSION" \
        "$STATE_DIR/.stop-hooks-ok-$TEST_SESSION" \
        "$STATE_DIR/.claude-completion-evidence-$TEST_SESSION" 2>/dev/null || true
}

finalize_cleanup() {
  cleanup
  rm -rf "$TMP_ROOT" 2>/dev/null || true
}
trap finalize_cleanup EXIT

# ── Hook runners ─────────────────────────────────────────────────────────────

# All three hooks read JSON from stdin. We feed a fake stop/post-tool-use
# payload and capture stdout + exit code.
run_signal_hook() {
  local file_path="$1" tool="${2:-Write}" session="${3:-$TEST_SESSION}"
  local json tmpout exit_code=0
  json=$(printf '{"tool_name":"%s","session_id":"%s","tool_input":{"file_path":"%s"}}' \
                 "$tool" "$session" "$file_path")
  tmpout=$(mktemp)
  printf '%s' "$json" | bash "$SIGNAL_HOOK" >"$tmpout" 2>/dev/null || exit_code=$?
  HOOK_OUT=$(cat "$tmpout")
  HOOK_EXIT=$exit_code
  rm -f "$tmpout"
}

run_stop_hook() {
  local hook="$1" session="${2:-$TEST_SESSION}"
  local json tmpout tmperr exit_code=0
  json=$(printf '{"session_id":"%s","stop_hook_active":false}' "$session")
  tmpout=$(mktemp)
  tmperr=$(mktemp)

  # Stop hooks now honor check_completion_authorized — they exit 0 unless Claude
  # planted the .stop-hooks-ok-<session> marker. Plant it for each test run so
  # we exercise the real gating logic, not the early-return path. Use
  # CLAUDE_UNSAFE_BYPASS_STOP_AUTH=1 in a test to opt out (verifies fast-path).
  mkdir -p "$STATE_DIR" 2>/dev/null || true
  if [ -z "${CLAUDE_UNSAFE_BYPASS_STOP_AUTH:-}" ]; then
    touch "$STATE_DIR/.stop-hooks-ok-${session}" 2>/dev/null || true
  fi

  printf '%s' "$json" | bash "$hook" >"$tmpout" 2>"$tmperr" || exit_code=$?
  HOOK_OUT=$(cat "$tmpout")
  HOOK_ERR=$(cat "$tmperr")
  HOOK_EXIT=$exit_code
  rm -f "$tmpout" "$tmperr"
}

# ── Fixture helpers ──────────────────────────────────────────────────────────

write_progress_json() {
  local status="$1"  # "all_complete" | "in_progress"
  case "$status" in
    all_complete)
      cat > "$PJSON" << 'EOF'
{
  "prd": "demo",
  "sprints": [
    {"id": "S1", "status": "complete"},
    {"id": "S2", "status": "complete"}
  ]
}
EOF
      ;;
    in_progress)
      cat > "$PJSON" << 'EOF'
{
  "prd": "demo",
  "sprints": [
    {"id": "S1", "status": "complete"},
    {"id": "S2", "status": "in_progress"}
  ]
}
EOF
      ;;
  esac
}

write_valid_evidence() {
  cat > "$STATE_DIR/.claude-completion-evidence-$TEST_SESSION" << 'EOF'
plan_reread: true
acceptance_criteria_cited: true
dev_server_verified: true
non_privileged_user_tested: true
EOF
}

# ─────────────────────────────────────────────────────────────────────────────

printf "${BOLD}Running stop-hooks-sprint-gating test suite${NC}\n"

# Sanity: hooks must be executable
for h in "$SIGNAL_HOOK" "$COMPOUND_HOOK" "$VERIFY_HOOK"; do
  if [ ! -x "$h" ]; then
    printf "${RED}HOOK NOT EXECUTABLE: %s${NC}\n" "$h"
    exit 1
  fi
done

# jq is required by all three hooks — fail loudly if missing rather than
# silently passing thanks to the hook's jq-missing early exit.
if ! command -v jq &>/dev/null; then
  printf "${RED}jq is required to run this suite${NC}\n"
  exit 1
fi

# ─── 1. Q&A turn: no signal, both Stop hooks must exit 0 silently ───────────
section "Q&A turn (no sprint finalized) — Stop hooks are fast no-ops"
cleanup

run_stop_hook "$COMPOUND_HOOK"
if [ "$HOOK_EXIT" -eq 0 ] && [ -z "$HOOK_ERR" ]; then
  pass "compound-reminder.sh: exit 0, no stderr when no signal marker"
else
  fail "compound-reminder.sh silent exit" "exit=$HOOK_EXIT err='${HOOK_ERR:0:120}'"
fi

run_stop_hook "$VERIFY_HOOK"
if [ "$HOOK_EXIT" -eq 0 ] && [ -z "$HOOK_ERR" ]; then
  pass "verify-completion.sh: exit 0, no stderr when no signal marker"
else
  fail "verify-completion.sh silent exit" "exit=$HOOK_EXIT err='${HOOK_ERR:0:120}'"
fi

# Bonus: the Q&A fast path should not have created any markers.
for f in ".sprint-finalized" ".claude-compound-warned" ".claude-verify-warned"; do
  if [ ! -f "$STATE_DIR/${f}-$TEST_SESSION" ]; then
    pass "no ${f}-<session> marker created during Q&A"
  else
    fail "${f} marker leaked" "unexpected file $STATE_DIR/${f}-$TEST_SESSION"
  fi
done

# ─── 2. Signal hook: only fires for progress.json in docs/tasks/, all done ───
section "progress-signal.sh: gating predicates"
cleanup

# 2a. Non-progress.json write — no signal
run_signal_hook "$TMP_ROOT/docs/tasks/feature/2026-04-11-demo/notes.md"
if [ ! -f "$STATE_DIR/.sprint-finalized-$TEST_SESSION" ]; then
  pass "non-progress.json write does not create signal"
else
  fail "non-progress.json write created signal" "marker present"
fi

# 2b. progress.json outside docs/tasks/ — no signal
OTHER_DIR="$TMP_ROOT/other/progress.json"
mkdir -p "$(dirname "$OTHER_DIR")"
cat > "$OTHER_DIR" << 'EOF'
{"sprints": [{"id": "X", "status": "complete"}]}
EOF
run_signal_hook "$OTHER_DIR"
if [ ! -f "$STATE_DIR/.sprint-finalized-$TEST_SESSION" ]; then
  pass "progress.json outside docs/tasks/ does not create signal"
else
  fail "out-of-scope progress.json created signal" "marker present"
fi

# 2c. progress.json with sprints still in progress — no signal
write_progress_json in_progress
run_signal_hook "$PJSON"
if [ ! -f "$STATE_DIR/.sprint-finalized-$TEST_SESSION" ]; then
  pass "in-progress PRD does not create signal"
else
  fail "in-progress PRD created signal" "marker present"
fi

# 2d. progress.json with every sprint complete — signal written
write_progress_json all_complete
run_signal_hook "$PJSON"
if [ -f "$STATE_DIR/.sprint-finalized-$TEST_SESSION" ]; then
  SIGNALED=$(cat "$STATE_DIR/.sprint-finalized-$TEST_SESSION")
  if [ "$SIGNALED" = "$PJSON" ]; then
    pass "all-complete PRD writes signal with absolute path"
  else
    fail "signal path mismatch" "expected $PJSON got $SIGNALED"
  fi
else
  fail "all-complete PRD did not create signal" "marker missing"
fi

# 2e. unknown session_id — no signal
rm -f "$STATE_DIR/.sprint-finalized-unknown" 2>/dev/null || true
run_signal_hook "$PJSON" "Write" "unknown"
if [ ! -f "$STATE_DIR/.sprint-finalized-unknown" ]; then
  pass "session_id=unknown is ignored (no -unknown marker leak)"
else
  fail "signal hook wrote -unknown marker" "stale marker regression"
  rm -f "$STATE_DIR/.sprint-finalized-unknown" 2>/dev/null || true
fi

# 2f. Wrong tool name — no signal
cleanup
run_signal_hook "$PJSON" "Read"
if [ ! -f "$STATE_DIR/.sprint-finalized-$TEST_SESSION" ]; then
  pass "Read tool_name ignored (only Write/Edit/MultiEdit trigger)"
else
  fail "Read tool triggered signal" "marker present"
fi

# ─── 3. Stop hooks wake up once a signal is written ─────────────────────────
section "verify-completion.sh: blocks without evidence, passes with evidence"
cleanup
write_progress_json all_complete
run_signal_hook "$PJSON"  # Plant signal

# 3a. No evidence → BLOCK
run_stop_hook "$VERIFY_HOOK"
if [ "$HOOK_EXIT" -eq 2 ] && printf '%s' "$HOOK_ERR" | grep -q "Anti-Premature Completion Protocol"; then
  pass "signal + no evidence → exit 2 with Anti-Premature message"
else
  fail "signal + no evidence expected block" "exit=$HOOK_EXIT err='${HOOK_ERR:0:120}'"
fi

# 3b. Second invocation — WARNED_MARKER short-circuits to silent exit
run_stop_hook "$VERIFY_HOOK"
if [ "$HOOK_EXIT" -eq 0 ] && [ -z "$HOOK_ERR" ]; then
  pass "warned marker prevents re-block in same turn"
else
  fail "second invocation should be silent" "exit=$HOOK_EXIT err='${HOOK_ERR:0:120}'"
fi

# 3c. Valid evidence → pass (after clearing the warn)
cleanup
write_progress_json all_complete
run_signal_hook "$PJSON"
write_valid_evidence
run_stop_hook "$VERIFY_HOOK"
if [ "$HOOK_EXIT" -eq 0 ] && [ -z "$HOOK_ERR" ]; then
  pass "signal + valid evidence → exit 0 (no block)"
else
  fail "valid evidence should unblock" "exit=$HOOK_EXIT err='${HOOK_ERR:0:120}'"
fi

# 3d. Evidence file missing required field → still blocks
cleanup
write_progress_json all_complete
run_signal_hook "$PJSON"
cat > "$STATE_DIR/.claude-completion-evidence-$TEST_SESSION" << 'EOF'
plan_reread: true
EOF
run_stop_hook "$VERIFY_HOOK"
if [ "$HOOK_EXIT" -eq 2 ]; then
  pass "partial evidence (missing required fields) → still blocks"
else
  fail "partial evidence should block" "exit=$HOOK_EXIT err='${HOOK_ERR:0:120}'"
fi

# ─── 4. compound-reminder.sh ────────────────────────────────────────────────
section "compound-reminder.sh: blocks without /compound done, passes with it"
cleanup
write_progress_json all_complete
run_signal_hook "$PJSON"

# 4a. No done marker → BLOCK
run_stop_hook "$COMPOUND_HOOK"
if [ "$HOOK_EXIT" -eq 2 ] && printf '%s' "$HOOK_ERR" | grep -q "/compound hasn't run"; then
  pass "signal + no compound-done marker → exit 2 with reminder"
else
  fail "compound-reminder should block" "exit=$HOOK_EXIT err='${HOOK_ERR:0:120}'"
fi

# 4b. Done marker present → pass
cleanup
write_progress_json all_complete
run_signal_hook "$PJSON"
: > "$STATE_DIR/.claude-compound-done-$TEST_SESSION"
run_stop_hook "$COMPOUND_HOOK"
if [ "$HOOK_EXIT" -eq 0 ] && [ -z "$HOOK_ERR" ]; then
  pass "signal + compound-done marker → exit 0"
else
  fail "compound-done should unblock" "exit=$HOOK_EXIT err='${HOOK_ERR:0:120}'"
fi

# ─── 5. Fresh finalization resets warned markers ─────────────────────────────
section "Re-finalization resets warned markers (second PRD in same session)"
cleanup
write_progress_json all_complete
run_signal_hook "$PJSON"

# First block — writes the warned marker
run_stop_hook "$VERIFY_HOOK"
if [ -f "$STATE_DIR/.claude-verify-warned-$TEST_SESSION" ]; then
  pass "first finalization writes verify-warned marker after block"
else
  fail "verify-warned marker missing" "expected after first block"
fi

# Simulate a second finalization — the signal hook should clear the warn
run_signal_hook "$PJSON"
if [ ! -f "$STATE_DIR/.claude-verify-warned-$TEST_SESSION" ]; then
  pass "new finalization clears verify-warned marker"
else
  fail "verify-warned marker should have been cleared" "stale"
fi

# And the next Stop blocks again (fresh chance)
run_stop_hook "$VERIFY_HOOK"
if [ "$HOOK_EXIT" -eq 2 ]; then
  pass "post-reset Stop blocks again (fresh warn cycle)"
else
  fail "post-reset Stop should block" "exit=$HOOK_EXIT err='${HOOK_ERR:0:120}'"
fi

# ─── 6. Stale signal pointing to deleted file is tolerated ───────────────────
section "Stale signal with missing progress.json is a no-op, not a crash"
cleanup
echo "/nonexistent/path/progress.json" > "$STATE_DIR/.sprint-finalized-$TEST_SESSION"
run_stop_hook "$COMPOUND_HOOK"
if [ "$HOOK_EXIT" -eq 0 ] && [ -z "$HOOK_ERR" ]; then
  pass "compound-reminder tolerates stale signal path"
else
  fail "stale signal crashed compound-reminder" "exit=$HOOK_EXIT err='${HOOK_ERR:0:120}'"
fi
run_stop_hook "$VERIFY_HOOK"
if [ "$HOOK_EXIT" -eq 0 ] && [ -z "$HOOK_ERR" ]; then
  pass "verify-completion tolerates stale signal path"
else
  fail "stale signal crashed verify-completion" "exit=$HOOK_EXIT err='${HOOK_ERR:0:120}'"
fi

# ─── Summary ─────────────────────────────────────────────────────────────────

cleanup
printf "\n${BOLD}Results${NC}\n"
printf "  Passed: ${GREEN}%d${NC}\n" "$PASS"
printf "  Failed: ${RED}%d${NC}\n" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
  printf "\n${RED}Failed tests:${NC}\n"
  for e in "${ERRORS[@]}"; do
    printf "  - %s\n" "$e"
  done
  exit 1
fi
exit 0
