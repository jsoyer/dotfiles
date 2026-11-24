#!/usr/bin/env bash
set -uo pipefail

# Test suite for block-tree-revert.sh
# Covers: revert verbs soft-blocked ONLY on a dirty tree, clean-tree pass-through,
# safe `restore --staged` allow, branch-switch allow, non-revert git allow,
# non-git allow, and the approval-token bypass.

HOOK="$HOME/.claude/hooks/block-tree-revert.sh"
APPROVAL_DIR="$HOME/.claude/hooks/.approvals"
PENDING_DIR="$HOME/.claude/hooks/.pending"

PASS=0
FAIL=0
ERRORS=()
RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

if [ ! -x "$HOOK" ]; then
  printf "${RED}HOOK NOT EXECUTABLE: %s${NC}\n" "$HOOK"; exit 1
fi

# --- temp repos ---
TMPROOT=$(mktemp -d)
DIRTY="$TMPROOT/dirty"
CLEAN="$TMPROOT/clean"
mk_repo() {
  local d="$1"; mkdir -p "$d"; git -C "$d" init -q
  git -C "$d" config user.email t@t.t; git -C "$d" config user.name t
  printf 'v1\n' > "$d/file.txt"; git -C "$d" add file.txt; git -C "$d" commit -qm init
  git -C "$d" branch -q other 2>/dev/null || true
}
mk_repo "$DIRTY"; mk_repo "$CLEAN"
printf 'v2-uncommitted\n' > "$DIRTY/file.txt"   # make DIRTY actually dirty

cleanup_tokens() { rm -rf "$APPROVAL_DIR" "$PENDING_DIR" 2>/dev/null || true; }
teardown() { rm -rf "$TMPROOT" 2>/dev/null || true; cleanup_tokens; }
trap teardown EXIT

run_hook() {
  local cmd="$1" json tmpout exit_code=0
  json="{\"tool_name\":\"Bash\",\"session_id\":\"tree-revert-test\",\"cwd\":\"$TMPROOT\",\"tool_input\":{\"command\":\"$cmd\"}}"
  tmpout=$(mktemp)
  printf '%s' "$json" | bash "$HOOK" >"$tmpout" 2>/dev/null || exit_code=$?
  HOOK_OUT=$(cat "$tmpout"); HOOK_EXIT=$exit_code; rm -f "$tmpout"
}
assert_allow() {
  if [ "$HOOK_EXIT" -eq 0 ] && [ -z "$HOOK_OUT" ]; then pass "$1"
  else fail "$1" "expected allow, got exit=$HOOK_EXIT out='${HOOK_OUT:0:90}'"; fi
}
assert_soft_block() {
  if [ "$HOOK_EXIT" -eq 0 ] && printf '%s' "$HOOK_OUT" | grep -q "SOFT_BLOCK_APPROVAL_NEEDED"; then pass "$1"
  else fail "$1" "expected soft-block, got exit=$HOOK_EXIT out='${HOOK_OUT:0:90}'"; fi
}
pass() { PASS=$((PASS+1)); printf "  ${GREEN}✓${NC} %s\n" "$1"; }
fail() { FAIL=$((FAIL+1)); printf "  ${RED}✗${NC} %s ${RED}(%s)${NC}\n" "$1" "$2"; ERRORS+=("$1: $2"); }
section() { printf "\n${BOLD}${CYAN}▸ %s${NC}\n" "$1"; }

printf "${BOLD}Running block-tree-revert.sh test suite${NC}\n"

# --- 1. Revert verbs on a DIRTY tree → soft-block ---
section "Revert verbs blocked on dirty tree"
cleanup_tokens; run_hook "git -C $DIRTY checkout -- file.txt"; assert_soft_block "checkout -- <path> (dirty)"
cleanup_tokens; run_hook "git -C $DIRTY checkout .";           assert_soft_block "checkout . (dirty)"
cleanup_tokens; run_hook "git -C $DIRTY checkout -f other";    assert_soft_block "checkout --force (dirty)"
cleanup_tokens; run_hook "git -C $DIRTY restore file.txt";     assert_soft_block "restore <path> default worktree (dirty)"
cleanup_tokens; run_hook "git -C $DIRTY restore --worktree file.txt"; assert_soft_block "restore --worktree (dirty)"
cleanup_tokens; run_hook "git -C $DIRTY reset --hard HEAD";    assert_soft_block "reset --hard (dirty)"
cleanup_tokens; run_hook "git -C $DIRTY stash drop";           assert_soft_block "stash drop (dirty)"
cleanup_tokens; run_hook "git -C $DIRTY stash clear";          assert_soft_block "stash clear (dirty)"
cleanup_tokens; run_hook "git -C $DIRTY clean -fd";            assert_soft_block "clean -fd (dirty)"
cleanup_tokens; run_hook "git -C $DIRTY checkout origin/main -- file.txt"; assert_soft_block "checkout <ref> -- <path> (dirty)"

# --- 2. Same verbs on a CLEAN tree → allow (nothing to lose) ---
section "Revert verbs allowed on clean tree"
cleanup_tokens; run_hook "git -C $CLEAN checkout -- file.txt"; assert_allow "checkout -- <path> (clean)"
cleanup_tokens; run_hook "git -C $CLEAN reset --hard HEAD";    assert_allow "reset --hard (clean)"
cleanup_tokens; run_hook "git -C $CLEAN clean -fd";            assert_allow "clean -fd (clean)"

# --- 3. Safe operations → allow even on dirty tree ---
section "Safe ops allowed on dirty tree"
cleanup_tokens; run_hook "git -C $DIRTY restore --staged file.txt"; assert_allow "restore --staged only (unstage, safe)"
cleanup_tokens; run_hook "git -C $DIRTY checkout other";       assert_allow "branch switch (no --/path)"
cleanup_tokens; run_hook "git -C $DIRTY status";              assert_allow "git status"
cleanup_tokens; run_hook "git -C $DIRTY add file.txt";        assert_allow "git add"
cleanup_tokens; run_hook "git -C $DIRTY commit -m wip";       assert_allow "git commit"
cleanup_tokens; run_hook "git -C $DIRTY stash push -- file.txt"; assert_allow "stash push (non-destructive)"

# --- 4. Non-git commands → allow ---
section "Non-git commands"
cleanup_tokens; run_hook "ls -la";                            assert_allow "ls"
cleanup_tokens; run_hook "rm -f /tmp/x";                      assert_allow "rm (not our concern)"

# --- 5. Approval token bypasses the block ---
section "Approval-token bypass"
cleanup_tokens
CMD="git -C $DIRTY checkout -- file.txt"
run_hook "$CMD"; assert_soft_block "pre-approval still blocks"
HASH=$(printf '%s' "tree-revert-$(printf '%s' "$CMD" | sed 's/  */ /g; s/^ *//; s/ *$//')" | cksum | cut -d' ' -f1)
mkdir -p "$APPROVAL_DIR"; : > "$APPROVAL_DIR/$HASH"
run_hook "$CMD"; assert_allow "approved token allows"

# =============================================================================
printf "\n${BOLD}Results:${NC} ${GREEN}%d passed${NC}, ${RED}%d failed${NC}\n" "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then printf "\n${RED}Failures:${NC}\n"; for e in "${ERRORS[@]}"; do printf "  - %s\n" "$e"; done; exit 1; fi
exit 0
