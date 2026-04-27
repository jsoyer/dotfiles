#!/usr/bin/env bash
set -uo pipefail

# Test suite for record-model-performance.sh and evaluate-model-performance.sh
# Covers: atomic updates, concurrent writes (flock), evaluation thresholds,
# JSON skeleton creation, invalid args.

RECORD="$HOME/.claude/hooks/scripts/record-model-performance.sh"
EVALUATE="$HOME/.claude/hooks/scripts/evaluate-model-performance.sh"

PASS=0
FAIL=0
ERRORS=()

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

if [ ! -x "$RECORD" ]; then
  printf "${RED}NOT EXECUTABLE: %s${NC}\n" "$RECORD"
  exit 1
fi
if [ ! -x "$EVALUATE" ]; then
  printf "${RED}NOT EXECUTABLE: %s${NC}\n" "$EVALUATE"
  exit 1
fi
if ! command -v jq &>/dev/null; then
  printf "${RED}jq required${NC}\n"
  exit 1
fi

pass() { PASS=$((PASS+1)); printf "  ${GREEN}✓${NC} %s\n" "$1"; }
fail() { FAIL=$((FAIL+1)); printf "  ${RED}✗${NC} %s ${RED}(%s)${NC}\n" "$1" "$2"; ERRORS+=("$1: $2"); }
section() { printf "\n${BOLD}${CYAN}▸ %s${NC}\n" "$1"; }

# Use a scratch file so we don't touch the real evolution/model-performance.json
SCRATCH=$(mktemp)
trap 'rm -f "$SCRATCH" "${HOME}/.claude/evolution/.perf.lock.test" 2>/dev/null' EXIT
export PERF_FILE="$SCRATCH"
export RECORD_QUIET=1

printf "${BOLD}Running record/evaluate model-performance test suite${NC}\n"

# 1. Skeleton creation when file missing
section "record creates skeleton on first write"
rm -f "$SCRATCH"
bash "$RECORD" sonnet test_task true >/dev/null 2>&1
if [ -f "$SCRATCH" ] && jq -e '.models.sonnet.task_types.test_task.attempts == 1' "$SCRATCH" >/dev/null 2>&1; then
  pass "skeleton created and first attempt recorded"
else
  fail "skeleton creation" "file=$(test -f "$SCRATCH" && echo exists || echo missing)"
fi

# 2. Success increment
section "first_try_success increments on true, stays same on false"
echo '{}' > "$SCRATCH"
bash "$RECORD" sonnet foo true >/dev/null
bash "$RECORD" sonnet foo true >/dev/null
bash "$RECORD" sonnet foo false >/dev/null
ATTEMPTS=$(jq '.models.sonnet.task_types.foo.attempts' "$SCRATCH")
FTS=$(jq '.models.sonnet.task_types.foo.first_try_success' "$SCRATCH")
if [ "$ATTEMPTS" = "3" ] && [ "$FTS" = "2" ]; then
  pass "attempts=3, first_try_success=2 after 3 recordings (2 true, 1 false)"
else
  fail "increment logic" "attempts=$ATTEMPTS first_try_success=$FTS (expected 3/2)"
fi

# 3. last_updated timestamp written
if jq -e '.last_updated | test("^[0-9]{4}-[0-9]{2}-[0-9]{2}T")' "$SCRATCH" >/dev/null 2>&1; then
  pass "last_updated is a valid ISO-8601 string"
else
  fail "last_updated format" "value=$(jq -r '.last_updated' "$SCRATCH")"
fi

# 4. Invalid args rejected
section "invalid arguments"
if bash "$RECORD" bogus_model test_task true >/dev/null 2>&1; then
  fail "invalid model accepted" "should have rejected bogus_model"
else
  pass "invalid model rejected"
fi

if bash "$RECORD" sonnet test_task maybe >/dev/null 2>&1; then
  fail "invalid success flag accepted" "should have rejected 'maybe'"
else
  pass "invalid first_try_success value rejected"
fi

if bash "$RECORD" sonnet >/dev/null 2>&1; then
  fail "missing args accepted" "should have rejected truncated call"
else
  pass "missing args rejected"
fi

# 5. Evaluate: empty / no proposals
section "evaluate on empty file"
echo '{"models":{"sonnet":{"task_types":{}},"opus":{"task_types":{}},"haiku":{"task_types":{}}}}' > "$SCRATCH"
OUT=$(bash "$EVALUATE" --format=json 2>&1)
if echo "$OUT" | jq -e '(.proposals | length == 0) and (.watch_list | length == 0)' >/dev/null 2>&1; then
  pass "empty file produces zero proposals"
else
  fail "empty-file evaluation" "output=$OUT"
fi

# 6. Evaluate: below threshold → watch list
section "below threshold → watch list"
for _ in 1 2 3 4 5 6 7; do bash "$RECORD" sonnet verification true >/dev/null; done
OUT=$(bash "$EVALUATE" --format=json 2>&1)
WATCH_COUNT=$(echo "$OUT" | jq '.watch_list | length')
PROPOSAL_COUNT=$(echo "$OUT" | jq '.proposals | length')
if [ "$WATCH_COUNT" -ge "1" ] && [ "$PROPOSAL_COUNT" = "0" ]; then
  pass "7 samples → on watch list, not yet a proposal"
else
  fail "watch-list gating" "watch=$WATCH_COUNT proposals=$PROPOSAL_COUNT"
fi

# 7. Evaluate: at threshold with 100% → downgrade proposal
section "threshold with 100% → downgrade"
for _ in 1 2 3; do bash "$RECORD" sonnet verification true >/dev/null; done  # bring to 10 @ 100%
OUT=$(bash "$EVALUATE" --format=json 2>&1)
DOWNGRADE=$(echo "$OUT" | jq -r '.proposals[] | select(.task_type == "verification") | .proposal')
if [ "$DOWNGRADE" = "downgrade" ]; then
  pass "10 samples at 100% → downgrade proposal"
else
  fail "downgrade trigger" "got: $DOWNGRADE"
fi

# 8. Evaluate: at threshold with <70% → upgrade proposal
section "threshold with low success rate → upgrade"
echo '{}' > "$SCRATCH"
for _ in 1 2 3 4; do bash "$RECORD" sonnet failure_prone true >/dev/null; done
for _ in 1 2 3 4 5 6; do bash "$RECORD" sonnet failure_prone false >/dev/null; done
# 10 samples, 4/10 = 40% → upgrade
OUT=$(bash "$EVALUATE" --format=json 2>&1)
UPGRADE=$(echo "$OUT" | jq -r '.proposals[] | select(.task_type == "failure_prone") | .proposal')
if [ "$UPGRADE" = "upgrade" ]; then
  pass "10 samples at 40% → upgrade proposal"
else
  fail "upgrade trigger" "got: $UPGRADE"
fi

# 9. Concurrent writes: flock serializes → no lost updates
section "parallel writes via flock"
echo '{}' > "$SCRATCH"
PARALLEL_N=8
PIDS=()
for i in $(seq 1 $PARALLEL_N); do
  ( bash "$RECORD" haiku parallel_test true >/dev/null 2>&1 ) &
  PIDS+=($!)
done
for pid in "${PIDS[@]}"; do
  wait "$pid" 2>/dev/null || true
done
FINAL=$(jq '.models.haiku.task_types.parallel_test.attempts' "$SCRATCH")
if [ "$FINAL" = "$PARALLEL_N" ]; then
  pass "flock: $PARALLEL_N parallel writes → attempts=$FINAL (no lost updates)"
else
  fail "flock serialization" "expected $PARALLEL_N, got $FINAL (lost updates)"
fi

# 10. evaluate exits 0 even with no data
section "evaluate is non-crashing on minimal input"
echo '{"models":{}}' > "$SCRATCH"
if bash "$EVALUATE" --format=json >/dev/null 2>&1; then
  pass "evaluate handles minimal .models gracefully"
else
  fail "evaluate crash" "minimal .models caused non-zero exit"
fi

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
