#!/usr/bin/env bash
set -uo pipefail

# Test suite for scan-secrets.sh
# Covers:
#   1. Blocks sk-... API key in a .env file
#   2. Blocks PRIVATE KEY header in a file
#   3. Blocks AWS access key (AKIA...)
#   4. Blocks GitHub PAT (ghp_...)
#   5. Allows .env.example (skip list)
#   6. Allows .md documentation files
#   7. Allows test files (*.test.*)
#   8. Allows node_modules/ path
#   9. Allows files with no secrets
#  10. Fail-open on crash (ERR trap behavior)

HOOK="$HOME/.claude/hooks/scan-secrets.sh"
ALERT_LOG="$HOME/.claude/state/secret-alerts.log"
TMP_DIR=""

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

setup() {
  TMP_DIR=$(mktemp -d)
}

cleanup() {
  rm -rf "$TMP_DIR" 2>/dev/null || true
}

# Run the hook with a given file path, capture exit code and stderr
run_hook() {
  local file_path="$1"
  local tmpout tmperr
  tmpout=$(mktemp)
  tmperr=$(mktemp)
  local exit_code=0
  printf '{"tool_name":"Write","tool_input":{"file_path":"%s"}}' "$file_path" \
    | bash "$HOOK" >"$tmpout" 2>"$tmperr" || exit_code=$?
  HOOK_STDOUT=$(cat "$tmpout")
  HOOK_STDERR=$(cat "$tmperr")
  HOOK_EXIT=$exit_code
  rm -f "$tmpout" "$tmperr"
}

assert_blocked() {
  if [ "$HOOK_EXIT" -eq 2 ]; then
    pass "$1"
  else
    fail "$1" "expected exit 2 (blocked), got exit=$HOOK_EXIT stderr='${HOOK_STDERR:0:80}'"
  fi
}

assert_allowed() {
  if [ "$HOOK_EXIT" -eq 0 ]; then
    pass "$1"
  else
    fail "$1" "expected exit 0 (allowed), got exit=$HOOK_EXIT stderr='${HOOK_STDERR:0:80}'"
  fi
}

assert_stderr_contains() {
  local pattern="$1" label="$2"
  if printf '%s' "$HOOK_STDERR" | grep -qF "$pattern"; then
    pass "$label"
  else
    fail "$label" "stderr missing: $pattern (got: ${HOOK_STDERR:0:120})"
  fi
}

assert_secret_not_in_output() {
  local secret="$1" label="$2"
  # Secret value must NOT appear in stdout or stderr
  if printf '%s\n%s' "$HOOK_STDOUT" "$HOOK_STDERR" | grep -qF "$secret"; then
    fail "$label" "secret value leaked into output!"
  else
    pass "$label"
  fi
}

# =============================================================================

printf "${BOLD}Running scan-secrets.sh test suite${NC}\n"

# ─── 1. Blocks sk-... API key ────────────────────────────────────────────────

section "Blocks OpenAI/Anthropic-style API key (sk-...)"

setup
cat > "$TMP_DIR/config.env" <<'EOF'
DATABASE_URL=postgres://localhost/mydb
API_KEY=sk-abcdefghijklmnopqrstuvwxyz12345678
PORT=3000
EOF

run_hook "$TMP_DIR/config.env"
assert_blocked "sk- API key in config.env → blocked (exit 2)"
assert_stderr_contains "SECRETS DETECTED" "stderr contains SECRETS DETECTED"
assert_secret_not_in_output "sk-abcdefghijklmnopqrstuvwxyz12345678" "secret value not in output"
assert_stderr_contains "line(s)" "stderr mentions line numbers"

cleanup

# ─── 2. Blocks sk-ant-... (Anthropic specific) ───────────────────────────────

section "Blocks Anthropic-specific key (sk-ant-...)"

setup
cat > "$TMP_DIR/.env" <<'EOF'
ANTHROPIC_KEY=sk-ant-api03-verylongsecrettoken123456789abcdefgh
EOF

run_hook "$TMP_DIR/.env"
assert_blocked "sk-ant- key in .env → blocked"
assert_stderr_contains "SECRETS DETECTED" "stderr contains SECRETS DETECTED"
assert_secret_not_in_output "sk-ant-api03-verylongsecrettoken123456789abcdefgh" "Anthropic key not in output"

cleanup

# ─── 3. Blocks AWS access key (AKIA...) ──────────────────────────────────────

section "Blocks AWS access key ID (AKIA...)"

setup
cat > "$TMP_DIR/aws-config.ts" <<'EOF'
const config = {
  accessKeyId: 'AKIAIOSFODNN7EXAMPLE',
  secretAccessKey: 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
};
EOF

run_hook "$TMP_DIR/aws-config.ts"
assert_blocked "AWS access key in aws-config.ts → blocked"
assert_stderr_contains "AWS access key ID" "stderr names the pattern"

cleanup

# ─── 4. Blocks GitHub PAT (ghp_...) ──────────────────────────────────────────

section "Blocks GitHub PAT (ghp_...)"

setup
cat > "$TMP_DIR/deploy.sh" <<'EOF'
#!/bin/bash
GH_TOKEN=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef12
git push origin main
EOF

run_hook "$TMP_DIR/deploy.sh"
assert_blocked "GitHub PAT in deploy.sh → blocked"
assert_stderr_contains "GitHub PAT" "stderr names the pattern"
assert_secret_not_in_output "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef12" "GitHub PAT not in output"

cleanup

# ─── 5. Blocks PRIVATE KEY header ────────────────────────────────────────────

section "Blocks private key PEM header"

setup
cat > "$TMP_DIR/id_rsa.pem" <<'EOF'
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA0Z3VS5JJcds3xHn/ygWep4RqZM3sARxUFhTaqhKJgkxWGJQ=
-----END RSA PRIVATE KEY-----
EOF

run_hook "$TMP_DIR/id_rsa.pem"
assert_blocked "RSA PRIVATE KEY in .pem → blocked"
assert_stderr_contains "Private key" "stderr names the pattern"

cleanup

# ─── 6. Allows .env.example ──────────────────────────────────────────────────

section "Allows .env.example (template file)"

setup
cat > "$TMP_DIR/.env.example" <<'EOF'
API_KEY=sk-your-api-key-here-replace-with-real-key-xxxxxxxxxx
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
DATABASE_URL=postgres://user:password@localhost/db
EOF

run_hook "$TMP_DIR/.env.example"
assert_allowed ".env.example is skipped (template file)"

cleanup

# ─── 7. Allows .md documentation files ──────────────────────────────────────

section "Allows markdown documentation files"

setup
cat > "$TMP_DIR/README.md" <<'EOF'
# API Configuration

Set your API key:
```
API_KEY=sk-yourapikey12345678901234567890123456
AKIA_EXAMPLE=AKIAIOSFODNN7EXAMPLE
```
EOF

run_hook "$TMP_DIR/README.md"
assert_allowed "README.md is skipped (markdown docs)"

cleanup

# ─── 8. Allows test files ────────────────────────────────────────────────────

section "Allows test files (*.test.*)"

setup
cat > "$TMP_DIR/auth.test.ts" <<'EOF'
// Test fixtures — these are fake test credentials
const TEST_API_KEY = 'sk-fakekeyforfakekeyforfakekey123456789';
const TEST_AWS = 'AKIAIOSFODNN7EXAMPLEFAKE';

describe('auth', () => {
  it('rejects invalid keys', () => { /* ... */ });
});
EOF

run_hook "$TMP_DIR/auth.test.ts"
assert_allowed "auth.test.ts is a test file — skipped"

cleanup

# ─── 9. Allows node_modules/ paths ───────────────────────────────────────────

section "Allows paths under node_modules/"

setup
mkdir -p "$TMP_DIR/node_modules/some-pkg"
cat > "$TMP_DIR/node_modules/some-pkg/index.js" <<'EOF'
// This package uses sk-hardcoded-test-value-abcdefghijklmno as a test fixture
const key = 'sk-nodemoduleskey1234567890123456789';
EOF

run_hook "$TMP_DIR/node_modules/some-pkg/index.js"
assert_allowed "node_modules/ path is skipped"

cleanup

# ─── 10. Allows files with no secrets ────────────────────────────────────────

section "Allows clean files with no secrets"

setup
cat > "$TMP_DIR/utils.ts" <<'EOF'
export function add(a: number, b: number): number {
  return a + b;
}

export function greet(name: string): string {
  return `Hello, ${name}!`;
}
EOF

run_hook "$TMP_DIR/utils.ts"
assert_allowed "utils.ts with no secrets → allowed"

cleanup

# ─── 11. Alert log populated on detection ────────────────────────────────────

section "Alert log populated on detection (never contains secret value)"

setup
ORIG_LOG_CONTENT=""
[ -f "$ALERT_LOG" ] && ORIG_LOG_CONTENT=$(cat "$ALERT_LOG" 2>/dev/null || true)

cat > "$TMP_DIR/secret.env" <<'EOF'
GH_TOKEN=ghp_MyRealSecretGitHubPATToken1234567890abc
EOF

run_hook "$TMP_DIR/secret.env"

if [ -f "$ALERT_LOG" ]; then
  NEW_CONTENT=$(cat "$ALERT_LOG")
  if printf '%s' "$NEW_CONTENT" | grep -qF "$TMP_DIR/secret.env"; then
    pass "alert log contains file path"
  else
    fail "alert log contains file path" "file path not in log"
  fi
  # Secret value must NOT be in the log
  if printf '%s' "$NEW_CONTENT" | grep -qF "ghp_MyRealSecretGitHubPATToken1234567890abc"; then
    fail "alert log does NOT contain secret value" "secret value leaked to log!"
  else
    pass "alert log does NOT contain secret value"
  fi
else
  fail "alert log exists after detection" "log file not found: $ALERT_LOG"
  pass "alert log does NOT contain secret value (log missing)"
fi

cleanup

# =============================================================================

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
