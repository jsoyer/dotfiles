#!/usr/bin/env bash
set -euo pipefail
trap 'echo "HARNESS-HEALTH CRASH: line $LINENO exit $?" >&2' ERR

# harness-health.sh — Verify the Claude Code hook harness wiring.
#
# Modes:
#   Default  : full check including test suite run
#   --fast   : skip test suite (for use in session-start.sh)
#   --quiet  : suppress all output unless something fails
#
# Exit 0 if all checks pass, 1 if any fail.
#
# Usage:
#   ~/.claude/hooks/scripts/harness-health.sh            # full check
#   ~/.claude/hooks/scripts/harness-health.sh --fast     # skip tests
#   ~/.claude/hooks/scripts/harness-health.sh --fast --quiet  # silent unless failures

FAST=false
QUIET=false

for arg in "$@"; do
  case "$arg" in
    --fast)   FAST=true ;;
    --quiet)  QUIET=true ;;
  esac
done

CLAUDE_DIR="$HOME/.claude"
HOOKS_DIR="$CLAUDE_DIR/hooks"
SETTINGS="$CLAUDE_DIR/settings.json"

FAILURES=0
LINES=()

ok()   { LINES+=("  ✓ $*"); }
fail() { LINES+=("  ✗ $*"); FAILURES=$((FAILURES + 1)); }
warn() { LINES+=("  ~ $*"); }

# ─── 1. Hooks referenced in settings.json exist and are executable ───────────

LINES+=("")
LINES+=("── Hook wiring (settings.json) ──")

if command -v jq &>/dev/null && [ -f "$SETTINGS" ]; then
  # Extract all hook commands from settings.json
  mapfile -t HOOK_CMDS < <(
    jq -r '
      .hooks
      | to_entries[]
      | .value[]
      | .hooks[]?
      | .command
    ' "$SETTINGS" 2>/dev/null \
    | grep -v '^notify-send' \
    | grep -v '^$' \
    || true
  )

  for cmd in "${HOOK_CMDS[@]}"; do
    # Expand ~ and $HOME
    expanded="${cmd/\~/$HOME}"
    expanded="${expanded//\$HOME/$HOME}"
    # Strip any arguments (first token only)
    script="${expanded%% *}"
    if [ -f "$script" ]; then
      if [ -x "$script" ]; then
        ok "hook exists + executable: ${script##*/}"
      else
        fail "hook NOT executable: $script"
      fi
    else
      fail "hook NOT found: $script"
    fi
  done
else
  if ! command -v jq &>/dev/null; then
    warn "jq not available — skipping settings.json hook wiring check"
  else
    fail "settings.json not found: $SETTINGS"
  fi
fi

# ─── 2. Required directories exist ───────────────────────────────────────────

LINES+=("")
LINES+=("── Required directories ──")

REQUIRED_DIRS=(
  "$CLAUDE_DIR/docs/solutions"
  "$CLAUDE_DIR/state"
  "$HOOKS_DIR/lib"
  "$HOOKS_DIR/scripts"
)

# Operational dirs: create them if absent (they are transient, not indicative of a bug)
OPERATIONAL_DIRS=(
  "$HOOKS_DIR/.pending"
  "$HOOKS_DIR/.approvals"
)

for dir in "${REQUIRED_DIRS[@]}"; do
  if [ -d "$dir" ]; then
    ok "dir exists: ${dir##$CLAUDE_DIR/}"
  else
    fail "dir MISSING: $dir"
  fi
done

for dir in "${OPERATIONAL_DIRS[@]}"; do
  if [ ! -d "$dir" ]; then
    mkdir -p "$dir" 2>/dev/null || true
  fi
  if [ -d "$dir" ]; then
    ok "operational dir ready: ${dir##$CLAUDE_DIR/}"
  else
    fail "operational dir MISSING and could not create: $dir"
  fi
done

# ─── 3. No stale -unknown markers in state/ ──────────────────────────────────

LINES+=("")
LINES+=("── State directory health ──")

STALE_COUNT=0
if [ -d "$CLAUDE_DIR/state" ]; then
  while IFS= read -r f; do
    STALE_COUNT=$((STALE_COUNT + 1))
  done < <(find "$CLAUDE_DIR/state" -maxdepth 1 -name "*-unknown" 2>/dev/null || true)
fi

if [ "$STALE_COUNT" -eq 0 ]; then
  ok "no stale -unknown markers in state/"
else
  fail "$STALE_COUNT stale -unknown marker(s) in state/ (SESSION_ID bug regression)"
fi

# ─── 4. session-postmortems dir (gracefully absent is fine) ──────────────────

POSTMORTEM_DIR="$CLAUDE_DIR/evolution/session-postmortems"
if [ -d "$POSTMORTEM_DIR" ]; then
  COUNT=$(find "$POSTMORTEM_DIR" -maxdepth 1 -type f 2>/dev/null | wc -l)
  ok "session-postmortems dir exists ($COUNT file(s))"
else
  ok "session-postmortems dir absent (graceful — not required)"
fi

# ─── 5. lib/ shared libraries source cleanly ─────────────────────────────────

LINES+=("")
LINES+=("── Shared libraries ──")

for lib in stop-guard.sh approvals.sh; do
  lib_path="$HOOKS_DIR/lib/$lib"
  if [ -f "$lib_path" ]; then
    if bash -c "source '$lib_path'" 2>/dev/null; then
      ok "lib/$lib sources cleanly"
    else
      fail "lib/$lib has source errors"
    fi
  else
    fail "lib/$lib MISSING"
  fi
done

# ─── 6. Required scripts/ files present ──────────────────────────────────────

LINES+=("")
LINES+=("── hooks/scripts/ contents ──")

REQUIRED_SCRIPTS=(
  approve.sh
  harness-health.sh
  retry-with-backoff.sh
  validate-i18n-keys.sh
  validate-sprint-boundaries.sh
  verify-worktree-merge.sh
  worktree-preflight.sh
)

for script in "${REQUIRED_SCRIPTS[@]}"; do
  spath="$HOOKS_DIR/scripts/$script"
  if [ -f "$spath" ]; then
    ok "scripts/$script present"
  else
    fail "scripts/$script MISSING"
  fi
done

# ─── 7. Test suite (skipped in --fast mode) ──────────────────────────────────

if [ "$FAST" = "false" ]; then
  LINES+=("")
  LINES+=("── Test suite ──")

  RUN_ALL="$HOOKS_DIR/tests/run-all.sh"
  if [ -f "$RUN_ALL" ]; then
    TEST_OUT=$(bash "$RUN_ALL" 2>&1) || true
    # Check if all suites passed
    if echo "$TEST_OUT" | grep -q "ALL SUITES PASSED"; then
      # Extract assertion count — strip ANSI codes before summing.
      # Handles two output formats:
      #   "  Passed: 44"     (enforce-delegation style)
      #   "Results: ALL PASSED — 97 passed"   (block-dangerous style)
      CLEAN_OUT=$(echo "$TEST_OUT" | sed 's/\x1b\[[0-9;]*m//g')
      TOTAL=$(
        {
          echo "$CLEAN_OUT" | grep -E "^\s+Passed: [0-9]+" | grep -v "Suites" | awk '{sum += $NF} END {print sum+0}'
          echo "$CLEAN_OUT" | grep -E "[0-9]+ passed" | grep -v "Suites" | grep -oE "[0-9]+ passed" | awk '{sum += $1} END {print sum+0}'
        } | awk '{sum += $1} END {print sum+0}'
      )
      ok "test suite: all passed ($TOTAL assertions)"
    else
      FAILED_SUITES=$(echo "$TEST_OUT" | grep "SUITE FAILED" | wc -l)
      fail "test suite: $FAILED_SUITES suite(s) FAILED"
      # Append failing output
      LINES+=("$(echo "$TEST_OUT" | grep -E "FAILED|✗" | head -10 | sed 's/^/    /')")
    fi
  else
    fail "tests/run-all.sh NOT FOUND"
  fi
fi

# ─── Final report ─────────────────────────────────────────────────────────────

if [ "$QUIET" = "true" ] && [ "$FAILURES" -eq 0 ]; then
  exit 0
fi

echo ""
echo "┌─ Harness Health Check ──────────────────────────────────────────┐"
for line in "${LINES[@]}"; do
  printf "│ %s\n" "$line"
done
echo "└─────────────────────────────────────────────────────────────────┘"
echo ""

if [ "$FAILURES" -eq 0 ]; then
  echo "HARNESS HEALTH: OK"
  exit 0
else
  echo "HARNESS HEALTH: $FAILURES FAILURE(S)"
  exit 1
fi
