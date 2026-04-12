#!/usr/bin/env bash
set -uo pipefail

# Test suite for check-test-exists.sh
# Covers:
#   1. Soft-block on src/ file with no test infra (new behavior)
#   2. Pass silently on test/ file
#   3. Pass silently when test infra exists (original behavior)
#   4. Pass silently on config/doc files
#   5. Pass silently on files outside a detected project
#   6. Approval token unblocks the soft-block

HOOK="$HOME/.claude/hooks/check-test-exists.sh"
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

pass() { PASS=$((PASS+1)); printf "  ${GREEN}✓${NC} %s\n" "$1"; }
fail() { FAIL=$((FAIL+1)); printf "  ${RED}✗${NC} %s ${RED}(%s)${NC}\n" "$1" "$2"; ERRORS+=("$1: $2"); }
section() { printf "\n${BOLD}${CYAN}▸ %s${NC}\n" "$1"; }

cleanup() {
  rm -rf "$APPROVAL_DIR" "$PENDING_DIR" 2>/dev/null || true
  rm -rf "$TMP_PROJECT" 2>/dev/null || true
}

# Run hook with a given file_path and optional CLAUDE_PROJECT_DIR override
run_hook() {
  local file_path="$1"
  local project_dir="${2:-$TMP_PROJECT}"
  local tmpout exit_code=0
  tmpout=$(mktemp)
  printf '{"tool_name":"Write","tool_input":{"file_path":"%s"}}' "$file_path" \
    | CLAUDE_PROJECT_DIR="$project_dir" bash "$HOOK" >"$tmpout" 2>/dev/null || exit_code=$?
  HOOK_OUT=$(cat "$tmpout")
  HOOK_EXIT=$exit_code
  rm -f "$tmpout"
}

assert_allow() {
  # Allow: exit 0 and no output (or exit 0 with empty stdout)
  if [ "$HOOK_EXIT" -eq 0 ] && [ -z "$HOOK_OUT" ]; then
    pass "$1"
  else
    fail "$1" "expected allow (exit 0, empty stdout), got exit=$HOOK_EXIT out='${HOOK_OUT:0:120}'"
  fi
}

assert_soft_block() {
  if [ "$HOOK_EXIT" -eq 0 ] && printf '%s' "$HOOK_OUT" | grep -q "SOFT_BLOCK_APPROVAL_NEEDED"; then
    pass "$1"
  else
    fail "$1" "expected SOFT_BLOCK_APPROVAL_NEEDED, got exit=$HOOK_EXIT out='${HOOK_OUT:0:120}'"
  fi
}

assert_hard_block() {
  if [ "$HOOK_EXIT" -eq 2 ]; then
    pass "$1"
  else
    fail "$1" "expected hard block (exit 2), got exit=$HOOK_EXIT"
  fi
}

# =============================================================================

printf "${BOLD}Running check-test-exists.sh test suite${NC}\n"

# Set up a temp project directory
TMP_PROJECT=$(mktemp -d)

# ─── 1. Soft-block: production file in src/, no test infra ──────────────────

section "Soft-block: production file in src/ with no test infra"

cleanup
TMP_PROJECT=$(mktemp -d)

# Project with package.json but no test script
cat > "$TMP_PROJECT/package.json" <<'EOF'
{"name":"test-project","version":"1.0.0","scripts":{}}
EOF
mkdir -p "$TMP_PROJECT/src"
# Create the file so find_project_root can detect it
touch "$TMP_PROJECT/src/utils.ts"

run_hook "$TMP_PROJECT/src/utils.ts" "$TMP_PROJECT"
assert_soft_block "src/utils.ts with no test infra → soft-block"

# ─── 2. Test file is never blocked ──────────────────────────────────────────

section "Test files always pass through"

cleanup
TMP_PROJECT=$(mktemp -d)
cat > "$TMP_PROJECT/package.json" <<'EOF'
{"name":"test-project","version":"1.0.0","scripts":{}}
EOF
mkdir -p "$TMP_PROJECT/src/__tests__"
touch "$TMP_PROJECT/src/__tests__/utils.test.ts"

run_hook "$TMP_PROJECT/src/__tests__/utils.test.ts" "$TMP_PROJECT"
assert_allow "__tests__/utils.test.ts is a test file — passes through"

cleanup
TMP_PROJECT=$(mktemp -d)
cat > "$TMP_PROJECT/package.json" <<'EOF'
{"name":"test-project","version":"1.0.0","scripts":{}}
EOF
mkdir -p "$TMP_PROJECT/tests"
touch "$TMP_PROJECT/tests/foo.spec.ts"

run_hook "$TMP_PROJECT/tests/foo.spec.ts" "$TMP_PROJECT"
assert_allow "tests/foo.spec.ts is a test file — passes through"

# ─── 3. Pass when test infra IS configured ──────────────────────────────────

section "Pass silently when test infra exists"

cleanup
TMP_PROJECT=$(mktemp -d)
# Use Python with pytest.ini — no dep-install check needed, cleanly detected
touch "$TMP_PROJECT/pytest.ini"
touch "$TMP_PROJECT/pyproject.toml"
mkdir -p "$TMP_PROJECT/src"
touch "$TMP_PROJECT/src/utils.py"

run_hook "$TMP_PROJECT/src/utils.py" "$TMP_PROJECT"
# When test infra IS detected, we should NOT soft-block about "no test infra"
# (We may get a hard-block for missing test FILE, or pass — either is fine)
if [ "$HOOK_EXIT" -eq 0 ] && printf '%s' "$HOOK_OUT" | grep -qF "No test infrastructure detected"; then
  fail "src/utils.py with pytest.ini should NOT soft-block about no test infra" \
       "got no-test-infra soft-block when infra exists"
else
  pass "src/utils.py with pytest.ini: no 'no test infra' soft-block"
fi

# ─── 4. Config files always pass ────────────────────────────────────────────

section "Config and doc files always pass through"

cleanup
TMP_PROJECT=$(mktemp -d)
cat > "$TMP_PROJECT/package.json" <<'EOF'
{"name":"test-project","version":"1.0.0","scripts":{}}
EOF

run_hook "$TMP_PROJECT/package.json" "$TMP_PROJECT"
assert_allow "package.json is a config file — passes through"

run_hook "$TMP_PROJECT/README.md" "$TMP_PROJECT"
assert_allow "README.md passes through (not a code file)"

run_hook "$TMP_PROJECT/docker-compose.yml" "$TMP_PROJECT"
assert_allow "docker-compose.yml passes through (config)"

# ─── 5. File outside a detected project: pass silently ──────────────────────

section "File outside any project root: pass silently"

cleanup

# /tmp/standalone.ts — no package.json, Cargo.toml, etc. walking up
run_hook "/tmp/standalone.ts" "/tmp"
assert_allow "/tmp/standalone.ts (no project root) — passes through"

# ─── 6. Approval token unblocks the soft-block ──────────────────────────────

section "Approval token unblocks no-test-infra soft-block"

cleanup
TMP_PROJECT=$(mktemp -d)
cat > "$TMP_PROJECT/package.json" <<'EOF'
{"name":"test-project","version":"1.0.0","scripts":{}}
EOF
mkdir -p "$TMP_PROJECT/src"
touch "$TMP_PROJECT/src/utils.ts"

# First invocation: soft-block
run_hook "$TMP_PROJECT/src/utils.ts" "$TMP_PROJECT"
assert_soft_block "initial: soft-block emitted"

# Plant an approval token (same hash the hook would generate)
mkdir -p "$APPROVAL_DIR"
CMD_HASH=$(printf '%s' "no-test-infra-$TMP_PROJECT/src/utils.ts" | cksum | cut -d' ' -f1)
touch "$APPROVAL_DIR/$CMD_HASH"

# Second invocation: should be allowed
run_hook "$TMP_PROJECT/src/utils.ts" "$TMP_PROJECT"
assert_allow "with approval token: allowed through"

# ─── 7. lib/ dir treated as production dir ───────────────────────────────────

section "lib/ directory treated as production dir"

cleanup
TMP_PROJECT=$(mktemp -d)
cat > "$TMP_PROJECT/package.json" <<'EOF'
{"name":"test-project","version":"1.0.0","scripts":{}}
EOF
mkdir -p "$TMP_PROJECT/lib"
touch "$TMP_PROJECT/lib/helper.ts"

run_hook "$TMP_PROJECT/lib/helper.ts" "$TMP_PROJECT"
assert_soft_block "lib/helper.ts with no test infra → soft-block"

# ─── 8. File in app/ treated as production dir ───────────────────────────────

section "app/ directory treated as production dir"

cleanup
TMP_PROJECT=$(mktemp -d)
cat > "$TMP_PROJECT/package.json" <<'EOF'
{"name":"test-project","version":"1.0.0","scripts":{}}
EOF
mkdir -p "$TMP_PROJECT/app/routes"
# Use a non-entry-point name (index.ts is an entry point, skipped if ≤20 lines)
touch "$TMP_PROJECT/app/routes/users.ts"

run_hook "$TMP_PROJECT/app/routes/users.ts" "$TMP_PROJECT"
assert_soft_block "app/routes/users.ts with no test infra → soft-block"

# =============================================================================

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
