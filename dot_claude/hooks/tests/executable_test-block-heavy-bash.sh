#!/usr/bin/env bash
set -uo pipefail

# Test suite for block-heavy-bash.sh
# Covers: heavy command blocking, dev server exemptions, git exemptions,
# help/version exemptions, sub-agent bypass, approval token.

HOOK="$HOME/.claude/hooks/block-heavy-bash.sh"
APPROVAL_DIR="$HOME/.claude/hooks/.approvals"
PENDING_DIR="$HOME/.claude/hooks/.pending"

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
  rm -rf "$APPROVAL_DIR" "$PENDING_DIR" 2>/dev/null || true
}

run_hook() {
  local cmd="$1"
  local json tmpout exit_code=0
  json="{\"tool_name\":\"Bash\",\"session_id\":\"heavy-test\",\"tool_input\":{\"command\":\"$cmd\"}}"
  tmpout=$(mktemp)
  printf '%s' "$json" | bash "$HOOK" >"$tmpout" 2>/dev/null || exit_code=$?
  HOOK_OUT=$(cat "$tmpout")
  HOOK_EXIT=$exit_code
  rm -f "$tmpout"
}

assert_allow() {
  if [ "$HOOK_EXIT" -eq 0 ] && [ -z "$HOOK_OUT" ]; then
    pass "$1"
  else
    fail "$1" "expected allow, got exit=$HOOK_EXIT out='${HOOK_OUT:0:80}'"
  fi
}

assert_soft_block() {
  if [ "$HOOK_EXIT" -eq 0 ] && printf '%s' "$HOOK_OUT" | grep -q "SOFT_BLOCK_APPROVAL_NEEDED"; then
    pass "$1"
  else
    fail "$1" "expected soft-block, got exit=$HOOK_EXIT out='${HOOK_OUT:0:80}'"
  fi
}

pass() { PASS=$((PASS+1)); printf "  ${GREEN}✓${NC} %s\n" "$1"; }
fail() { FAIL=$((FAIL+1)); printf "  ${RED}✗${NC} %s ${RED}(%s)${NC}\n" "$1" "$2"; ERRORS+=("$1: $2"); }
section() { printf "\n${BOLD}${CYAN}▸ %s${NC}\n" "$1"; }

# =============================================================================

printf "${BOLD}Running block-heavy-bash.sh test suite${NC}\n"

# --- 1. Package manager build/test/lint blocked ---
section "Package manager build/test/lint"
cleanup; run_hook "pnpm build";     assert_soft_block "pnpm build blocked"
cleanup; run_hook "pnpm test";      assert_soft_block "pnpm test blocked"
cleanup; run_hook "pnpm lint";      assert_soft_block "pnpm lint blocked"
cleanup; run_hook "pnpm typecheck"; assert_soft_block "pnpm typecheck blocked"
cleanup; run_hook "pnpm install";   assert_soft_block "pnpm install blocked"
cleanup; run_hook "pnpm add react"; assert_soft_block "pnpm add blocked"
cleanup; run_hook "npm test";       assert_soft_block "npm test blocked"
cleanup; run_hook "npm run build";  assert_soft_block "npm run build blocked"
cleanup; run_hook "npm run lint";   assert_soft_block "npm run lint blocked"
cleanup; run_hook "yarn build";     assert_soft_block "yarn build blocked"
cleanup; run_hook "yarn test";      assert_soft_block "yarn test blocked"

# --- 2. Rust/Go/Python/JVM ---
section "Rust / Go / Python / JVM tooling"
cleanup; run_hook "cargo build";      assert_soft_block "cargo build blocked"
cleanup; run_hook "cargo test";       assert_soft_block "cargo test blocked"
cleanup; run_hook "cargo clippy";     assert_soft_block "cargo clippy blocked"
cleanup; run_hook "go build ./...";   assert_soft_block "go build blocked"
cleanup; run_hook "go test ./...";    assert_soft_block "go test blocked"
cleanup; run_hook "go vet ./...";     assert_soft_block "go vet blocked"
cleanup; run_hook "pytest";           assert_soft_block "pytest blocked"
cleanup; run_hook "pytest tests/";    assert_soft_block "pytest tests/ blocked"
cleanup; run_hook "python -m pytest"; assert_soft_block "python -m pytest blocked"
cleanup; run_hook "jest";             assert_soft_block "jest blocked"
cleanup; run_hook "vitest";           assert_soft_block "vitest blocked"
cleanup; run_hook "playwright test";  assert_soft_block "playwright test blocked"
cleanup; run_hook "tsc";              assert_soft_block "tsc blocked"
cleanup; run_hook "eslint src";       assert_soft_block "eslint blocked"
cleanup; run_hook "prettier --write"; assert_soft_block "prettier blocked"
cleanup; run_hook "ruff check .";     assert_soft_block "ruff check blocked"
cleanup; run_hook "mypy";             assert_soft_block "mypy blocked"
cleanup; run_hook "make build";       assert_soft_block "make build blocked"
cleanup; run_hook "make test";        assert_soft_block "make test blocked"
cleanup; run_hook "gradle build";     assert_soft_block "gradle build blocked"

# --- 3. Dev servers allowed ---
section "Dev servers allowed (article-sanctioned)"
cleanup; run_hook "pnpm dev";          assert_allow "pnpm dev allowed"
cleanup; run_hook "pnpm dev --port 3000"; assert_allow "pnpm dev --port allowed"
cleanup; run_hook "npm run dev";       assert_allow "npm run dev allowed"
cleanup; run_hook "yarn dev";          assert_allow "yarn dev allowed"
cleanup; run_hook "next dev";          assert_allow "next dev allowed"
cleanup; run_hook "vite";              assert_allow "vite allowed"
cleanup; run_hook "nodemon";           assert_allow "nodemon allowed"

# --- 4. Git allowed ---
section "Git commands allowed"
cleanup; run_hook "git status";                  assert_allow "git status allowed"
cleanup; run_hook "git log --oneline";           assert_allow "git log allowed"
cleanup; run_hook "git diff HEAD";               assert_allow "git diff allowed"
cleanup; run_hook "git commit -m fix";           assert_allow "git commit allowed"
cleanup; run_hook "git push origin main";        assert_allow "git push allowed (block-dangerous handles destructive)"

# --- 5. Help / version queries allowed ---
section "Help and version queries allowed"
cleanup; run_hook "pnpm build --help";    assert_allow "pnpm build --help allowed"
cleanup; run_hook "cargo test --help";    assert_allow "cargo test --help allowed"
cleanup; run_hook "pytest --version";     assert_allow "pytest --version allowed"
cleanup; run_hook "tsc --version";        assert_allow "tsc --version allowed"

# --- 6. Ordinary commands allowed ---
section "Ordinary commands allowed"
cleanup; run_hook "echo hello";           assert_allow "echo allowed"
cleanup; run_hook "ls /tmp";              assert_allow "ls allowed"
cleanup; run_hook "mkdir /tmp/foo";       assert_allow "mkdir allowed"
cleanup; run_hook "pwd";                  assert_allow "pwd allowed"
cleanup; run_hook "which node";           assert_allow "which allowed"
cleanup; run_hook "cat /tmp/x.txt";       assert_allow "cat allowed (enforce-delegation counts, not this hook)"

# --- 7. Sub-agent bypass ---
section "Sub-agent env bypass"
cleanup
CLAUDE_SUBAGENT=1 run_hook "pnpm build"
assert_allow "CLAUDE_SUBAGENT bypasses pnpm build"

cleanup
SPRINT_EXECUTOR=1 run_hook "cargo test"
assert_allow "SPRINT_EXECUTOR bypasses cargo test"

cleanup
CLAUDE_AGENT_TYPE=sprint-executor run_hook "pnpm lint"
assert_allow "CLAUDE_AGENT_TYPE bypasses pnpm lint"

# --- 8. Approval token ---
section "Approval token unblocks"
cleanup
run_hook "pnpm build"
assert_soft_block "drove to soft-block"

mkdir -p "$APPROVAL_DIR"
HASH=$(printf '%s' "heavy-bash-pnpm build" | cksum | cut -d' ' -f1)
touch "$APPROVAL_DIR/$HASH"

run_hook "pnpm build"
assert_allow "approved pnpm build allowed"

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
