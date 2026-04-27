#!/usr/bin/env bash
set -uo pipefail

# Test suite: cleanup-worktrees.sh
#
# User requirement (2026-04-14):
#   - All git worktrees must be merged to main
#   - If merged, they must be removed
#   - Only runs on final completion (authorization marker present)
#
# Safety invariants (from hook source):
#   - NEVER deletes worktrees with unmerged changes (logs warning)
#   - NEVER deletes dirty worktrees (uncommitted changes)
#   - NEVER deletes the main worktree
#   - Uses `git branch -d` (safe) not `git branch -D` (force)
#   - Exits 0 always (best-effort)

HOOK="$HOME/.claude/hooks/cleanup-worktrees.sh"
STATE_DIR="$HOME/.claude/state"
TEST_SESSION="cleanup-wt-$$"

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

if [ ! -x "$HOOK" ]; then
  printf "${RED}HOOK NOT EXECUTABLE: %s${NC}\n" "$HOOK"
  exit 1
fi

if ! command -v git &>/dev/null; then
  printf "${RED}git is required${NC}\n"
  exit 1
fi

# Scratch repo for each test
SCRATCH_ROOT=$(mktemp -d)
trap 'rm -rf "$SCRATCH_ROOT" "$STATE_DIR/.stop-hooks-ok-$TEST_SESSION" 2>/dev/null' EXIT

# Each test creates a fresh repo under $SCRATCH_ROOT and cd's into it.
make_repo() {
  local name="$1"
  local repo="$SCRATCH_ROOT/$name"
  mkdir -p "$repo"
  (
    cd "$repo"
    git init -q -b main 2>/dev/null || { git init -q && git branch -M main 2>/dev/null || true; }
    git config user.email "test@example.com"
    git config user.name "Test"
    echo "init" > README.md
    git add README.md
    git commit -q -m "initial"
  )
  echo "$repo"
}

run_hook() {
  local repo="$1"
  local json tmpout tmperr exit_code=0
  # Plant auth marker — the hook uses check_completion_authorized
  mkdir -p "$STATE_DIR" 2>/dev/null || true
  touch "$STATE_DIR/.stop-hooks-ok-$TEST_SESSION"
  json=$(printf '%s' "{\"session_id\":\"$TEST_SESSION\",\"stop_hook_active\":false,\"transcript\":[{\"role\":\"assistant\",\"content\":[{\"type\":\"tool_use\",\"name\":\"Edit\"}]}]}")
  tmpout=$(mktemp)
  tmperr=$(mktemp)
  CLAUDE_PROJECT_DIR="$repo" printf '%s' "$json" | env CLAUDE_PROJECT_DIR="$repo" bash "$HOOK" >"$tmpout" 2>"$tmperr" || exit_code=$?
  HOOK_OUT=$(cat "$tmpout")
  HOOK_ERR=$(cat "$tmperr")
  HOOK_EXIT=$exit_code
  rm -f "$tmpout" "$tmperr"
}

# =============================================================================

printf "${BOLD}Running cleanup-worktrees.sh test suite${NC}\n"

# ─── 1. Authorization gating: no marker → skip ──────────────────────────────
section "1. Skips when no authorization marker present"
REPO=$(make_repo "repo-unauth")
rm -f "$STATE_DIR/.stop-hooks-ok-$TEST_SESSION" 2>/dev/null
# Create a worktree to ensure the hook would have had work to do
(
  cd "$REPO"
  git checkout -q -b sprint/feature-x
  echo "feature" > feature.txt
  git add feature.txt
  git commit -q -m "add feature"
  git checkout -q main
  git worktree add -q ../wt-unauth sprint/feature-x 2>/dev/null || true
)

# Run without planting the auth marker — hook should be a no-op
json=$(printf '%s' "{\"session_id\":\"$TEST_SESSION\",\"stop_hook_active\":false,\"transcript\":[{\"role\":\"assistant\",\"content\":[{\"type\":\"tool_use\",\"name\":\"Edit\"}]}]}")
tmpout=$(mktemp); tmperr=$(mktemp); ec=0
printf '%s' "$json" | env CLAUDE_PROJECT_DIR="$REPO" bash "$HOOK" >"$tmpout" 2>"$tmperr" || ec=$?
rm -f "$tmpout" "$tmperr"

WT_COUNT=$(cd "$REPO" && git worktree list --porcelain 2>/dev/null | grep -c "^worktree " || echo 0)
if [ "$ec" -eq 0 ] && [ "$WT_COUNT" -ge 2 ]; then
  pass "no auth marker → hook exits 0 and worktree untouched"
else
  fail "no-auth no-op" "ec=$ec worktrees=$WT_COUNT (expected ec=0 and worktrees >= 2)"
fi

# ─── 2. No worktrees → fast exit ────────────────────────────────────────────
section "2. Fast exit when no worktrees exist"
REPO=$(make_repo "repo-empty")
run_hook "$REPO"
if [ "$HOOK_EXIT" -eq 0 ]; then
  pass "exits 0 when repo has no worktrees"
else
  fail "empty-repo fast exit" "exit=$HOOK_EXIT err='${HOOK_ERR:0:100}'"
fi

# ─── 3. Merged worktree → removed + branch deleted ──────────────────────────
section "3. Merged worktree: removed + branch deleted"
REPO=$(make_repo "repo-merged")
(
  cd "$REPO"
  git checkout -q -b sprint/feat-merged
  echo "content" > a.txt
  git add a.txt
  git commit -q -m "add a.txt"
  git checkout -q main
  # Worktree path is SIBLING to repo (standard pattern)
  git worktree add -q "$SCRATCH_ROOT/wt-merged" sprint/feat-merged
  # Merge the sprint branch into main
  git merge -q --no-ff sprint/feat-merged -m "merge sprint"
)

run_hook "$REPO"
WT_AFTER=$(cd "$REPO" && git worktree list --porcelain 2>/dev/null | grep -c "^worktree " || echo 0)
BRANCH_EXISTS=$(cd "$REPO" && git branch --list sprint/feat-merged | wc -l | tr -d ' ')

if [ "$HOOK_EXIT" -eq 0 ] && [ "$WT_AFTER" -eq 1 ] && [ "$BRANCH_EXISTS" -eq 0 ]; then
  pass "merged worktree removed (worktrees: 2→$WT_AFTER, branch deleted)"
else
  fail "merged worktree cleanup" "exit=$HOOK_EXIT worktrees_after=$WT_AFTER branch_exists=$BRANCH_EXISTS (expected 1, 0)"
fi

# ─── 4. Unmerged worktree → preserved (branch has unmerged commits) ─────────
section "4. Unmerged worktree: preserved with warning"
REPO=$(make_repo "repo-unmerged")
(
  cd "$REPO"
  git checkout -q -b sprint/feat-unmerged
  echo "unmerged" > b.txt
  git add b.txt
  git commit -q -m "add b.txt"
  git checkout -q main
  git worktree add -q "$SCRATCH_ROOT/wt-unmerged" sprint/feat-unmerged
  # DO NOT merge — branch stays unmerged
)

run_hook "$REPO"
WT_AFTER=$(cd "$REPO" && git worktree list --porcelain 2>/dev/null | grep -c "^worktree " || echo 0)
BRANCH_EXISTS=$(cd "$REPO" && git branch --list sprint/feat-unmerged | wc -l | tr -d ' ')

if [ "$HOOK_EXIT" -eq 0 ] && [ "$WT_AFTER" -eq 2 ] && [ "$BRANCH_EXISTS" -eq 1 ]; then
  pass "unmerged worktree preserved (worktrees=$WT_AFTER, branch intact)"
else
  fail "unmerged worktree preservation" "exit=$HOOK_EXIT worktrees_after=$WT_AFTER branch_exists=$BRANCH_EXISTS (expected 2, 1)"
fi

if printf '%s' "$HOOK_ERR" | grep -q "unmerged worktree preserved"; then
  pass "warning emitted for unmerged worktree"
else
  fail "warning for unmerged" "stderr missing unmerged warning: '${HOOK_ERR:0:150}'"
fi

# ─── 5. Dirty worktree (merged branch but uncommitted changes) → preserved ──
section "5. Dirty worktree with merged branch: preserved with warning"
REPO=$(make_repo "repo-dirty")
(
  cd "$REPO"
  git checkout -q -b sprint/feat-dirty
  echo "content" > c.txt
  git add c.txt
  git commit -q -m "add c.txt"
  git checkout -q main
  git worktree add -q "$SCRATCH_ROOT/wt-dirty" sprint/feat-dirty
  git merge -q --no-ff sprint/feat-dirty -m "merge sprint feat-dirty"
  # Introduce uncommitted change in the worktree
  echo "uncommitted" > "$SCRATCH_ROOT/wt-dirty/dirty.txt"
)

run_hook "$REPO"
WT_AFTER=$(cd "$REPO" && git worktree list --porcelain 2>/dev/null | grep -c "^worktree " || echo 0)

if [ "$HOOK_EXIT" -eq 0 ] && [ "$WT_AFTER" -eq 2 ]; then
  pass "dirty worktree preserved (worktrees=$WT_AFTER — not removed)"
else
  fail "dirty worktree preservation" "exit=$HOOK_EXIT worktrees_after=$WT_AFTER (expected 2)"
fi

if printf '%s' "$HOOK_ERR" | grep -q "dirty state"; then
  pass "warning emitted for dirty worktree"
else
  fail "warning for dirty" "stderr missing dirty warning: '${HOOK_ERR:0:150}'"
fi

# ─── 6. Main worktree never removed ─────────────────────────────────────────
section "6. Main worktree never touched"
REPO=$(make_repo "repo-main")
run_hook "$REPO"
if [ -d "$REPO/.git" ] && [ -f "$REPO/README.md" ]; then
  pass "main worktree files and .git intact"
else
  fail "main worktree integrity" "main repo damaged after hook run"
fi

# ─── 7. Mixed: one merged + one unmerged ────────────────────────────────────
section "7. Mixed worktrees: merged removed, unmerged preserved"
REPO=$(make_repo "repo-mixed")
(
  cd "$REPO"
  # Worktree A: will be merged
  git checkout -q -b sprint/a
  echo "A" > a.txt
  git add a.txt
  git commit -q -m "sprint A"
  git checkout -q main
  git worktree add -q "$SCRATCH_ROOT/wt-a" sprint/a
  git merge -q --no-ff sprint/a -m "merge A"
  # Worktree B: will NOT be merged
  git checkout -q -b sprint/b
  echo "B" > b.txt
  git add b.txt
  git commit -q -m "sprint B"
  git checkout -q main
  git worktree add -q "$SCRATCH_ROOT/wt-b" sprint/b
)

run_hook "$REPO"
BRANCH_A=$(cd "$REPO" && git branch --list sprint/a | wc -l | tr -d ' ')
BRANCH_B=$(cd "$REPO" && git branch --list sprint/b | wc -l | tr -d ' ')
if [ "$BRANCH_A" -eq 0 ] && [ "$BRANCH_B" -eq 1 ]; then
  pass "mixed: merged A removed, unmerged B preserved"
else
  fail "mixed cleanup" "branch_a=$BRANCH_A branch_b=$BRANCH_B (expected 0, 1)"
fi

# ─── 8. Non-git directory → graceful skip ───────────────────────────────────
section "8. Non-git directory: graceful skip"
NONGIT="$SCRATCH_ROOT/nongit"
mkdir -p "$NONGIT"
run_hook "$NONGIT"
if [ "$HOOK_EXIT" -eq 0 ]; then
  pass "non-git dir → exit 0"
else
  fail "non-git skip" "exit=$HOOK_EXIT err='${HOOK_ERR:0:100}'"
fi

# ─── 9. HOME/root blacklist ─────────────────────────────────────────────────
section "9. HOME/root dir: refuses to operate"
json=$(printf '%s' "{\"session_id\":\"$TEST_SESSION\",\"stop_hook_active\":false,\"transcript\":[{\"role\":\"assistant\",\"content\":[{\"type\":\"tool_use\",\"name\":\"Edit\"}]}]}")
tmpout=$(mktemp); tmperr=$(mktemp); ec=0
touch "$STATE_DIR/.stop-hooks-ok-$TEST_SESSION"
printf '%s' "$json" | env CLAUDE_PROJECT_DIR="$HOME" bash "$HOOK" >"$tmpout" 2>"$tmperr" || ec=$?
rm -f "$tmpout" "$tmperr"
if [ "$ec" -eq 0 ]; then
  pass "CLAUDE_PROJECT_DIR=\$HOME → refuses, exits 0"
else
  fail "HOME skip" "exit=$ec"
fi

# ─── Summary ────────────────────────────────────────────────────────────────

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
