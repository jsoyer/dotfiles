#!/usr/bin/env bash
set -uo pipefail

# Test suite for enforce-delegation.sh
# Covers: counting, threshold, mixed tools, agent reset, exemptions,
# bash read-style detection, sub-agent bypass, approval token.

HOOK="$HOME/.claude/hooks/enforce-delegation.sh"
STATE_DIR="$HOME/.claude/hooks/state"
APPROVAL_DIR="$HOME/.claude/hooks/.approvals"
PENDING_DIR="$HOME/.claude/hooks/.pending"
TEST_SESSION="enforce-test-$$"

PASS=0
FAIL=0
ERRORS=()

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

if [ ! -x "$HOOK" ]; then
  printf "${RED}HOOK NOT EXECUTABLE: %s${NC}\n" "$HOOK"
  exit 1
fi

cleanup() {
  rm -f "$STATE_DIR/main-reads-$TEST_SESSION" 2>/dev/null || true
  rm -rf "$APPROVAL_DIR" "$PENDING_DIR" 2>/dev/null || true
}

# --- run_hook helpers ---
# Each helper feeds synthetic JSON matching the Claude Code PreToolUse hook
# input contract and captures stdout + exit code.

_run_with_json() {
  local json="$1"
  local tmpout exit_code=0
  tmpout=$(mktemp)
  printf '%s' "$json" | bash "$HOOK" >"$tmpout" 2>/dev/null || exit_code=$?
  HOOK_OUT=$(cat "$tmpout")
  HOOK_EXIT=$exit_code
  rm -f "$tmpout"
}

run_hook_read() {
  local path="$1"
  _run_with_json "{\"tool_name\":\"Read\",\"session_id\":\"$TEST_SESSION\",\"tool_input\":{\"file_path\":\"$path\"}}"
}

run_hook_grep() {
  local path="$1"
  _run_with_json "{\"tool_name\":\"Grep\",\"session_id\":\"$TEST_SESSION\",\"tool_input\":{\"path\":\"$path\",\"pattern\":\"foo\"}}"
}

run_hook_glob() {
  local pat="$1"
  _run_with_json "{\"tool_name\":\"Glob\",\"session_id\":\"$TEST_SESSION\",\"tool_input\":{\"pattern\":\"$pat\"}}"
}

run_hook_bash() {
  local cmd="$1"
  _run_with_json "{\"tool_name\":\"Bash\",\"session_id\":\"$TEST_SESSION\",\"tool_input\":{\"command\":\"$cmd\"}}"
}

run_hook_agent() {
  _run_with_json "{\"tool_name\":\"Task\",\"session_id\":\"$TEST_SESSION\",\"tool_input\":{\"description\":\"test delegation\"}}"
}

# --- Assertions ---

assert_allow() {
  if [ "$HOOK_EXIT" -eq 0 ] && [ -z "$HOOK_OUT" ]; then
    pass "$1"
  else
    fail "$1" "expected allow (exit 0, empty stdout), got exit=$HOOK_EXIT out='${HOOK_OUT:0:80}'"
  fi
}

assert_soft_block() {
  if [ "$HOOK_EXIT" -eq 0 ] && printf '%s' "$HOOK_OUT" | grep -q "SOFT_BLOCK_APPROVAL_NEEDED"; then
    pass "$1"
  else
    fail "$1" "expected SOFT_BLOCK_APPROVAL_NEEDED, got exit=$HOOK_EXIT out='${HOOK_OUT:0:80}'"
  fi
}

assert_counter() {
  local expected="$1" label="$2"
  local actual=0
  if [ -f "$STATE_DIR/main-reads-$TEST_SESSION" ]; then
    actual=$(cat "$STATE_DIR/main-reads-$TEST_SESSION")
  fi
  if [ "$actual" = "$expected" ]; then
    pass "$label"
  else
    fail "$label" "counter expected $expected, got $actual"
  fi
}

pass() { PASS=$((PASS+1)); printf "  ${GREEN}✓${NC} %s\n" "$1"; }
fail() { FAIL=$((FAIL+1)); printf "  ${RED}✗${NC} %s ${RED}(%s)${NC}\n" "$1" "$2"; ERRORS+=("$1: $2"); }
section() { printf "\n${BOLD}${CYAN}▸ %s${NC}\n" "$1"; }

# =============================================================================

printf "${BOLD}Running enforce-delegation.sh test suite${NC}\n"

# --- 1. Basic counting ---
section "Basic counting (Read)"
cleanup
run_hook_read "/tmp/fake1.txt"
assert_allow "1st read allowed"
assert_counter 1 "counter = 1 after 1st read"

run_hook_read "/tmp/fake2.txt"
assert_allow "2nd read allowed"
assert_counter 2 "counter = 2 after 2nd read"

run_hook_read "/tmp/fake3.txt"
assert_allow "3rd read allowed (under threshold)"
assert_counter 3 "counter = 3 after 3rd read"

run_hook_read "/tmp/fake4.txt"
assert_soft_block "4th read soft-blocked"

# --- 2. Mixed tool counting ---
section "Mixed tool types"
cleanup
run_hook_read "/tmp/a.txt"
run_hook_grep "/tmp/dir"
run_hook_glob "src/**/*.ts"
assert_counter 3 "Read + Grep + Glob all counted (=3)"

run_hook_read "/tmp/d.txt"
assert_soft_block "4th read across mixed tools soft-blocked"

# --- 3. Agent delegation resets counter ---
section "Agent/Task call resets counter"
cleanup
run_hook_read "/tmp/a.txt"
run_hook_read "/tmp/b.txt"
run_hook_read "/tmp/c.txt"
assert_counter 3 "counter = 3 before Agent call"

run_hook_agent
assert_allow "Agent call allowed"
assert_counter 0 "counter = 0 after Agent call"

run_hook_read "/tmp/d.txt"
assert_allow "post-reset 1st read allowed"
assert_counter 1 "counter restarts at 1 after Agent reset"

# --- 4. Exemptions ---
section "Exempt paths (do not count)"
cleanup
run_hook_read "/root/.claude/CLAUDE.md"
assert_allow "/root/.claude/ path exempt"
assert_counter 0 "exempt read does not increment counter"

run_hook_read "/root/.claude/projects/-root-projects/memory/MEMORY.md"
assert_counter 0 "MEMORY.md exempt"

run_hook_read "/root/projects/foo/docs/session-learnings.md"
assert_counter 0 "session-learnings exempt"

run_hook_read "/root/projects/foo/INVARIANTS.md"
assert_counter 0 "INVARIANTS.md exempt"

run_hook_read "/root/projects/foo/docs/tasks/feature/2026-04-09-spec.md"
assert_counter 0 "docs/tasks path exempt"

run_hook_read "/root/projects/foo/sprints/01-setup.md"
assert_counter 0 "sprints/*.md exempt"

run_hook_read "/root/projects/foo/CLAUDE.md"
assert_counter 0 "project CLAUDE.md exempt"

run_hook_read "/root/projects/foo/progress.json"
assert_counter 0 "progress.json exempt"

# Verify we can still block on non-exempt paths after many exempt reads
run_hook_read "/tmp/real1.txt"
run_hook_read "/tmp/real2.txt"
run_hook_read "/tmp/real3.txt"
assert_counter 3 "non-exempt reads still count after many exempt reads"
run_hook_read "/tmp/real4.txt"
assert_soft_block "threshold still fires after exempt reads"

# --- 5. Bash read-style commands ---
section "Bash read-style commands count"
cleanup
run_hook_bash "cat /tmp/a.txt"
assert_counter 1 "cat counted"
run_hook_bash "head -20 /tmp/b.txt"
assert_counter 2 "head counted"
run_hook_bash "rg foo /tmp"
assert_counter 3 "rg counted"
run_hook_bash "find /tmp -name *.txt"
assert_soft_block "find triggers soft-block on 4th read"

# --- 6. Bash non-read commands are ignored ---
section "Bash non-read commands do not count"
cleanup
run_hook_bash "echo hello"
assert_counter 0 "echo not counted"
run_hook_bash "mkdir /tmp/foo"
assert_counter 0 "mkdir not counted"
run_hook_bash "pwd"
assert_counter 0 "pwd not counted"
run_hook_bash "git status"
assert_counter 0 "git status not counted"

# --- 7. Sub-agent bypass (env var) ---
section "Sub-agent env bypass"
cleanup
CLAUDE_SUBAGENT=1 run_hook_read "/tmp/x.txt"
assert_allow "CLAUDE_SUBAGENT bypasses enforcement"
assert_counter 0 "counter NOT incremented under CLAUDE_SUBAGENT"

cleanup
SPRINT_EXECUTOR=1 run_hook_read "/tmp/y.txt"
assert_allow "SPRINT_EXECUTOR bypasses enforcement"
assert_counter 0 "counter NOT incremented under SPRINT_EXECUTOR"

cleanup
CLAUDE_AGENT_TYPE=sprint-executor run_hook_read "/tmp/z.txt"
assert_allow "CLAUDE_AGENT_TYPE bypasses enforcement"

# --- 8. Approval token works ---
section "Approval token unblocks + resets counter"
cleanup
# Drive to blocked state
run_hook_read "/tmp/a1.txt"
run_hook_read "/tmp/a2.txt"
run_hook_read "/tmp/a3.txt"
run_hook_read "/tmp/a4.txt"
assert_soft_block "drove to soft-block at 4 reads"

# Plant an approval token (what approve.sh would do)
mkdir -p "$APPROVAL_DIR"
HASH=$(printf '%s' "delegation-$TEST_SESSION" | cksum | cut -d' ' -f1)
touch "$APPROVAL_DIR/$HASH"

run_hook_read "/tmp/a5.txt"
assert_allow "approved read allowed"
assert_counter 0 "approval resets counter to 0"

# --- 9. Sanity: unknown tools pass through ---
section "Unknown tool_name passes through"
cleanup
_run_with_json "{\"tool_name\":\"Write\",\"session_id\":\"$TEST_SESSION\",\"tool_input\":{\"file_path\":\"/tmp/x.txt\"}}"
assert_allow "Write tool not matched — passes through"
assert_counter 0 "Write does not increment counter"

# --- 10. Parallel invocations: flock serializes counter writes ---
section "Parallel invocations: flock prevents lost updates"
cleanup

# Launch 5 parallel Read invocations that all try to increment the counter at the same time
PARALLEL_N=5
PIDS=()
for i in $(seq 1 $PARALLEL_N); do
  (
    printf '{"tool_name":"Read","session_id":"%s","tool_input":{"file_path":"/tmp/fake-parallel-%d.txt"}}' \
      "$TEST_SESSION" "$i" \
    | bash "$HOOK" >/dev/null 2>/dev/null || true
  ) &
  PIDS+=($!)
done

# Wait for all to finish
for pid in "${PIDS[@]}"; do
  wait "$pid" 2>/dev/null || true
done

# The counter should equal exactly PARALLEL_N (or be >= 4 which triggers soft-block)
# What we care about: no lost updates. Without flock, some increments can be lost.
# With flock, counter should be exactly PARALLEL_N.
ACTUAL_COUNTER=0
if [ -f "$STATE_DIR/main-reads-$TEST_SESSION" ]; then
  ACTUAL_COUNTER=$(cat "$STATE_DIR/main-reads-$TEST_SESSION" 2>/dev/null || echo 0)
fi

if [ "$ACTUAL_COUNTER" -eq "$PARALLEL_N" ]; then
  pass "flock: counter=$ACTUAL_COUNTER after $PARALLEL_N parallel increments (no lost updates)"
else
  fail "flock: counter=$ACTUAL_COUNTER after $PARALLEL_N parallel increments (expected $PARALLEL_N — lost updates!)"
fi

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
