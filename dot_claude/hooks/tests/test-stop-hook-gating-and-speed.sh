#!/usr/bin/env bash
set -uo pipefail

# Test suite: Stop hooks honor completion authorization + run fast.
#
# User requirement (2026-04-14):
#   - Compound/worktree-cleanup/etc. must only run when the agent answered with
#     a task-completion summary — never when the last turn was AskUserQuestion
#     or when Claude paused mid-work.
#   - Stop hooks must be fast when they short-circuit (no authorization).
#
# Gating contract (lib/stop-guard.sh::check_completion_authorized):
#   - If last assistant tool_use was AskUserQuestion → exit 0
#   - If no ~/.claude/state/.stop-hooks-ok-<session_id> marker → exit 0
#   - Otherwise: consume marker (one-shot) and allow hook to proceed
#
# This test covers every stop hook listed in settings.json.

HOOK_DIR="$HOME/.claude/hooks"
STATE_DIR="$HOME/.claude/state"
TEST_SESSION="gating-speed-$$"

# Per-hook speed budget when auth is missing (hook should early-return).
# 500ms is generous — each hook should be well under 100ms in practice,
# but bash startup + stop-guard.sh sourcing can eat 50-200ms on proot.
SPEED_BUDGET_MS=500

STOP_HOOKS=(
  "compound-reminder.sh"
  "verify-completion.sh"
  "cleanup-artifacts.sh"
  "cleanup-worktrees.sh"
  "end-of-turn-typecheck.sh"
  "consume-auth-marker.sh"
)

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
  rm -f \
    "$STATE_DIR/.stop-hooks-ok-$TEST_SESSION" \
    "$STATE_DIR/.sprint-finalized-$TEST_SESSION" \
    "$STATE_DIR/.claude-compound-warned-$TEST_SESSION" \
    "$STATE_DIR/.claude-verify-warned-$TEST_SESSION" \
    "$STATE_DIR/.claude-compound-done-$TEST_SESSION" \
    "$STATE_DIR/.claude-completion-evidence-$TEST_SESSION" 2>/dev/null || true
}
trap 'cleanup' EXIT

mkdir -p "$STATE_DIR" 2>/dev/null || true

# ── Hook runners ────────────────────────────────────────────────────────────

# run_hook HOOK_PATH JSON_PAYLOAD
# Returns: HOOK_EXIT, HOOK_ERR, HOOK_ELAPSED_MS
run_hook() {
  local hook="$1" json="$2"
  local tmpout tmperr exit_code=0 start_ns end_ns

  tmpout=$(mktemp)
  tmperr=$(mktemp)

  start_ns=$(date +%s%N)
  printf '%s' "$json" | bash "$hook" >"$tmpout" 2>"$tmperr" || exit_code=$?
  end_ns=$(date +%s%N)

  HOOK_OUT=$(cat "$tmpout")
  HOOK_ERR=$(cat "$tmperr")
  HOOK_EXIT=$exit_code
  HOOK_ELAPSED_MS=$(( (end_ns - start_ns) / 1000000 ))

  rm -f "$tmpout" "$tmperr"
}

ordinary_turn_json() {
  # Transcript ends with a plain assistant summary (no AskUserQuestion).
  # Last tool was Edit.
  printf '%s' '{
    "session_id": "'"$TEST_SESSION"'",
    "stop_hook_active": false,
    "transcript": [
      {"role": "user", "content": [{"type": "text", "text": "fix the bug"}]},
      {"role": "assistant", "content": [
        {"type": "tool_use", "name": "Edit"},
        {"type": "text", "text": "Bug fixed: added null-check."}
      ]}
    ]
  }'
}

ask_user_question_turn_json() {
  # Transcript ends with AskUserQuestion — Claude is still waiting on user.
  printf '%s' '{
    "session_id": "'"$TEST_SESSION"'",
    "stop_hook_active": false,
    "transcript": [
      {"role": "user", "content": [{"type": "text", "text": "please build X"}]},
      {"role": "assistant", "content": [
        {"type": "tool_use", "name": "AskUserQuestion"}
      ]}
    ]
  }'
}

stop_hook_active_json() {
  # Recursive Stop hook fire — must exit 0 immediately.
  printf '%s' '{
    "session_id": "'"$TEST_SESSION"'",
    "stop_hook_active": true,
    "transcript": []
  }'
}

# =============================================================================

printf "${BOLD}Running stop-hook gating + speed test suite${NC}\n"
printf "Hooks: %s\n" "${STOP_HOOKS[*]}"
printf "Speed budget (per hook): %dms\n" "$SPEED_BUDGET_MS"

# Sanity: every expected hook exists and is executable
for hook_name in "${STOP_HOOKS[@]}"; do
  if [ ! -x "$HOOK_DIR/$hook_name" ]; then
    printf "${RED}HOOK NOT EXECUTABLE: %s${NC}\n" "$HOOK_DIR/$hook_name"
    exit 1
  fi
done

if ! command -v jq &>/dev/null; then
  printf "${RED}jq is required${NC}\n"
  exit 1
fi

# ─── 1. No authorization marker → hooks fast-path ────────────────────────────
section "1. No authorization marker → every stop hook is a fast no-op"
cleanup
ORDINARY=$(ordinary_turn_json)

for hook_name in "${STOP_HOOKS[@]}"; do
  run_hook "$HOOK_DIR/$hook_name" "$ORDINARY"
  if [ "$HOOK_EXIT" -ne 0 ]; then
    fail "$hook_name exits 0 without auth" "exit=$HOOK_EXIT err='${HOOK_ERR:0:100}'"
    continue
  fi
  if [ "$HOOK_ELAPSED_MS" -gt "$SPEED_BUDGET_MS" ]; then
    fail "$hook_name fast-path <= ${SPEED_BUDGET_MS}ms" "actual=${HOOK_ELAPSED_MS}ms (exceeded budget)"
    continue
  fi
  pass "$hook_name exits 0 in ${HOOK_ELAPSED_MS}ms (no auth → skipped)"
done

# ─── 2. Last tool = AskUserQuestion → hooks skip even WITH auth marker ───────
section "2. AskUserQuestion last turn → hooks skip (pause, not completion)"
cleanup
touch "$STATE_DIR/.stop-hooks-ok-$TEST_SESSION"  # Auth marker planted
ASK_JSON=$(ask_user_question_turn_json)

for hook_name in "${STOP_HOOKS[@]}"; do
  # Re-plant marker (compound-reminder/verify-completion may consume it if auth reaches them)
  touch "$STATE_DIR/.stop-hooks-ok-$TEST_SESSION"
  run_hook "$HOOK_DIR/$hook_name" "$ASK_JSON"
  if [ "$HOOK_EXIT" -eq 0 ] && [ -z "$HOOK_ERR" ]; then
    pass "$hook_name silent when last turn was AskUserQuestion"
  else
    fail "$hook_name silent on AskUserQuestion" "exit=$HOOK_EXIT err='${HOOK_ERR:0:100}'"
  fi
done

# ─── 3. stop_hook_active=true → hooks short-circuit ──────────────────────────
section "3. stop_hook_active=true → recursive fire prevented"
cleanup
touch "$STATE_DIR/.stop-hooks-ok-$TEST_SESSION"
RECURSIVE=$(stop_hook_active_json)

for hook_name in "${STOP_HOOKS[@]}"; do
  touch "$STATE_DIR/.stop-hooks-ok-$TEST_SESSION"
  run_hook "$HOOK_DIR/$hook_name" "$RECURSIVE"
  if [ "$HOOK_EXIT" -eq 0 ] && [ -z "$HOOK_ERR" ]; then
    pass "$hook_name silent on stop_hook_active=true"
  else
    fail "$hook_name should silent-exit" "exit=$HOOK_EXIT err='${HOOK_ERR:0:100}'"
  fi
done

# ─── 4. Auth marker persists across the chain (all hooks can see it) ───────
section "4. Auth marker persists across the whole Stop chain (not one-shot per hook)"
cleanup
touch "$STATE_DIR/.stop-hooks-ok-$TEST_SESSION"
ORDINARY=$(ordinary_turn_json)

# Run every stop hook EXCEPT consume-auth-marker — the marker must persist.
CHAIN_HOOKS=(
  "end-of-turn-typecheck.sh"
  "cleanup-artifacts.sh"
  "cleanup-worktrees.sh"
  "verify-completion.sh"
  "compound-reminder.sh"
)
for hook_name in "${CHAIN_HOOKS[@]}"; do
  run_hook "$HOOK_DIR/$hook_name" "$ORDINARY"
done

if [ -f "$STATE_DIR/.stop-hooks-ok-$TEST_SESSION" ]; then
  pass "auth marker persists after every non-consume stop hook fires"
else
  fail "auth marker persistence" "marker vanished before consume-auth-marker could see it"
fi

# ─── 4b. consume-auth-marker (last in chain) removes the marker ─────────────
section "4b. consume-auth-marker.sh removes the marker after the chain"
run_hook "$HOOK_DIR/consume-auth-marker.sh" "$ORDINARY"
if [ ! -f "$STATE_DIR/.stop-hooks-ok-$TEST_SESSION" ]; then
  pass "consume-auth-marker removes the marker"
else
  fail "consume-auth-marker removal" "marker still present after consume hook ran"
fi

# Next turn with no re-authorize → every hook is a fast no-op again
cleanup  # ensure no lingering markers
run_hook "$HOOK_DIR/compound-reminder.sh" "$ORDINARY"
if [ "$HOOK_EXIT" -eq 0 ] && [ -z "$HOOK_ERR" ]; then
  pass "next turn without re-authorize → hooks silent again"
else
  fail "post-consume next turn" "exit=$HOOK_EXIT err='${HOOK_ERR:0:100}'"
fi

# ─── 5. compound-reminder specifically requires auth + sprint-finalized ──────
section "5. compound-reminder gates compound on authorization"
cleanup
ORDINARY=$(ordinary_turn_json)

# Scenario 5a: auth present, but no sprint-finalized marker → fast exit
touch "$STATE_DIR/.stop-hooks-ok-$TEST_SESSION"
run_hook "$HOOK_DIR/compound-reminder.sh" "$ORDINARY"
if [ "$HOOK_EXIT" -eq 0 ] && [ -z "$HOOK_ERR" ]; then
  pass "compound-reminder: auth + no sprint signal → silent"
else
  fail "compound-reminder silent without sprint signal" "exit=$HOOK_EXIT err='${HOOK_ERR:0:100}'"
fi

# Scenario 5b: auth present, sprint finalized, compound NOT done → BLOCK
cleanup
touch "$STATE_DIR/.stop-hooks-ok-$TEST_SESSION"
TMP_DIR=$(mktemp -d)
TASK_DIR="$TMP_DIR/docs/tasks/feature/2026-04-14-demo"
mkdir -p "$TASK_DIR"
cat > "$TASK_DIR/progress.json" << 'EOF'
{"prd": "demo", "sprints": [{"id": "S1", "status": "complete"}]}
EOF
echo "$TASK_DIR/progress.json" > "$STATE_DIR/.sprint-finalized-$TEST_SESSION"

run_hook "$HOOK_DIR/compound-reminder.sh" "$ORDINARY"
if [ "$HOOK_EXIT" -eq 2 ] && printf '%s' "$HOOK_ERR" | grep -q "/compound hasn't run"; then
  pass "compound-reminder: auth + sprint signal + no compound-done → BLOCKED"
else
  fail "compound-reminder blocks correctly" "exit=$HOOK_EXIT err='${HOOK_ERR:0:100}'"
fi

rm -rf "$TMP_DIR"

# ─── 6. Speed budget: hooks fast-path consistently ──────────────────────────
section "6. Speed budget: fast-path consistency over multiple invocations"
cleanup
ORDINARY=$(ordinary_turn_json)
TOTAL_RUNS=5

for hook_name in "${STOP_HOOKS[@]}"; do
  MAX_MS=0
  for i in $(seq 1 $TOTAL_RUNS); do
    run_hook "$HOOK_DIR/$hook_name" "$ORDINARY"
    [ "$HOOK_ELAPSED_MS" -gt "$MAX_MS" ] && MAX_MS="$HOOK_ELAPSED_MS"
  done
  if [ "$MAX_MS" -le "$SPEED_BUDGET_MS" ]; then
    pass "$hook_name worst-case fast-path: ${MAX_MS}ms over $TOTAL_RUNS runs"
  else
    fail "$hook_name speed budget" "worst=${MAX_MS}ms exceeded ${SPEED_BUDGET_MS}ms"
  fi
done

# ─── Summary ────────────────────────────────────────────────────────────────
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
