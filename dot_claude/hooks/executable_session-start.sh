#!/usr/bin/env bash
set -euo pipefail
trap 'echo "HOOK CRASH: $0 line $LINENO" >&2; exit 0' ERR

# SessionStart hook: Auto-detect environment and load session state.
# Runs when a session begins or resumes.
# Non-blocking (exit 0) — advisory only.

source "${HOME}/.claude/hooks/lib/hook-logger.sh" 2>/dev/null || true

INPUT=$(cat)

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

WARNINGS=""

# 1. Detect proot-distro environment
IS_PROOT=false
if uname -r 2>/dev/null | grep -q "PRoot-Distro" && [ "$(uname -m)" = "aarch64" ]; then
  IS_PROOT=true
  WARNINGS="${WARNINGS}\n• PRoot-Distro ARM64 detected — expect 3x slower builds, no bwrap sandbox"

  # Per-session marker: only run the detailed proot checks once per 2-hour window
  SESSION_MARKER="${HOME}/.claude/state/.claude-proot-preflight-done"
  RUN_PROOT_CHECKS=true
  if [ -f "$SESSION_MARKER" ]; then
    MARKER_AGE=$(( $(date +%s) - $(stat -c %Y "$SESSION_MARKER" 2>/dev/null || echo 0) ))
    if [ "$MARKER_AGE" -lt 7200 ]; then
      RUN_PROOT_CHECKS=false
    fi
  fi

  if [ "$RUN_PROOT_CHECKS" = "true" ]; then
    touch "$SESSION_MARKER"

    # Node.js-specific checks
    if [ -f "$PROJECT_DIR/package.json" ]; then
      # Check for broken symlinks in node_modules
      if [ -d "$PROJECT_DIR/node_modules/.bin" ]; then
        BROKEN_COUNT=$(find "$PROJECT_DIR/node_modules/.bin" -type l ! -exec test -e {} \; -print 2>/dev/null | wc -l)
        if [ "$BROKEN_COUNT" -gt 0 ]; then
          WARNINGS="${WARNINGS}\n• BROKEN SYMLINKS: $BROKEN_COUNT broken symlinks in node_modules/.bin. Run: pnpm install"
        fi
      fi
      # Check for .npmrc with node-linker
      if [ -f "$PROJECT_DIR/.npmrc" ]; then
        if ! grep -q "node-linker" "$PROJECT_DIR/.npmrc" 2>/dev/null; then
          WARNINGS="${WARNINGS}\n• NPMRC: No node-linker setting. Consider adding node-linker=hoisted to .npmrc for proot compatibility."
        fi
      fi
    fi

    # Rust-specific checks
    if [ -f "$PROJECT_DIR/Cargo.toml" ]; then
      if [ ! -f "$HOME/.cargo/config.toml" ]; then
        WARNINGS="${WARNINGS}\n• RUST: No ~/.cargo/config.toml found. Build times may be slow without incremental compilation settings."
      fi
    fi

    # SST lock check
    if [ -f "$PROJECT_DIR/.sst/lock" ]; then
      WARNINGS="${WARNINGS}\n• SST LOCK: Stale lock file found at .sst/lock. Remove if no deploy is running."
    fi
  fi
fi

# 2. Check for session-learnings file
SESSION_LEARNINGS=""
for candidate in \
  "$PROJECT_DIR/docs/session-learnings.md" \
  "$PROJECT_DIR/session-learnings.md"; do
  if [ -f "$candidate" ]; then
    SESSION_LEARNINGS="$candidate"
    break
  fi
done

# 3. Check for pending work (progress.json with incomplete sprints)
PENDING_WORK=""
if [ -d "$PROJECT_DIR/docs/tasks" ]; then
  while IFS= read -r pjson; do
    if command -v jq &>/dev/null; then
      PENDING=$(jq -r '.sprints[]? | select(.status != "complete") | .id' "$pjson" 2>/dev/null | tr '\n' ', ' | sed 's/,$//')
      if [ -n "$PENDING" ]; then
        PRD=$(jq -r '.prd // "unknown"' "$pjson" 2>/dev/null)
        PENDING_WORK="${PENDING_WORK}\n  → ${PRD}: pending=[${PENDING}]"
      fi
    fi
  done < <(find "$PROJECT_DIR/docs/tasks" -name "progress.json" -type f 2>/dev/null)
fi

# 4. Check disk space
DISK_FREE_KB=$(df / 2>/dev/null | tail -1 | awk '{print $4}')
if [ -n "$DISK_FREE_KB" ] && [ "$DISK_FREE_KB" -lt 1048576 ]; then
  DISK_FREE_MB=$((DISK_FREE_KB / 1024))
  WARNINGS="${WARNINGS}\n• Low disk: ${DISK_FREE_MB}MB free"
fi

# 5. Autocompact policy check (per-window targets)
# Reads model.id from SessionStart input (if provided) and verifies that
# CLAUDE_AUTOCOMPACT_PCT_OVERRIDE matches the target for the detected window.
# Per-window targets (keep in sync with set-compact.sh and CLAUDE.md):
#   128K window -> 100K target (78%)
#   200K window -> 125K target (62%)
#   1M   window -> 150K target (15%)
# If mismatched, auto-corrects settings.json (takes effect next session) and warns now.
SETTINGS_FILE="$HOME/.claude/settings.json"
if command -v jq &>/dev/null && [ -f "$SETTINGS_FILE" ]; then
  CURRENT_PCT=$(jq -r '.env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE // "unset"' "$SETTINGS_FILE" 2>/dev/null || echo "unset")
  MODEL_ID=$(echo "$INPUT" | jq -r '.model.id // empty' 2>/dev/null || echo "")

  # Detect window size from model id suffix: [1m] = 1M, otherwise 200K default.
  # Pick the target per window — larger windows get a larger absolute budget, but
  # all stay well inside the quality zone.
  if echo "$MODEL_ID" | grep -q '\[1m\]'; then
    WINDOW=1000000
    WIN_LABEL="1M"
    TARGET_TOKENS=150000
  else
    WINDOW=200000
    WIN_LABEL="200K"
    TARGET_TOKENS=125000
  fi

  EXPECTED_PCT=$(( TARGET_TOKENS * 100 / WINDOW ))
  [ "$EXPECTED_PCT" -lt 5 ] && EXPECTED_PCT=5
  [ "$EXPECTED_PCT" -gt 95 ] && EXPECTED_PCT=95

  # Accept a +/-1 tolerance for the expected value (15-16 for 1M, 62-63 for 200K)
  LOW_BOUND=$((EXPECTED_PCT - 1))
  HIGH_BOUND=$((EXPECTED_PCT + 1))

  if [ "$CURRENT_PCT" = "unset" ]; then
    WARNINGS="${WARNINGS}\n• Autocompact: CLAUDE_AUTOCOMPACT_PCT_OVERRIDE unset — run: ~/.claude/set-compact.sh ${WIN_LABEL,,}"
  elif ! [[ "$CURRENT_PCT" =~ ^[0-9]+$ ]]; then
    WARNINGS="${WARNINGS}\n• Autocompact: CLAUDE_AUTOCOMPACT_PCT_OVERRIDE='${CURRENT_PCT}' is not numeric — run: ~/.claude/set-compact.sh ${WIN_LABEL,,}"
  elif [ "$CURRENT_PCT" -lt "$LOW_BOUND" ] || [ "$CURRENT_PCT" -gt "$HIGH_BOUND" ]; then
    # Auto-correct: write expected value to settings.json for next session
    TMP=$(mktemp)
    if jq --argjson pct "$EXPECTED_PCT" '.env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE = ($pct | tostring)' "$SETTINGS_FILE" > "$TMP" 2>/dev/null; then
      mv "$TMP" "$SETTINGS_FILE"
      WARNINGS="${WARNINGS}\n• Autocompact: env was ${CURRENT_PCT}% (target: ${EXPECTED_PCT}% for ${TARGET_TOKENS} on ${WIN_LABEL} window) — auto-corrected settings.json. Current session uses old value; next session is fixed."
    else
      rm -f "$TMP"
      WARNINGS="${WARNINGS}\n• Autocompact: env is ${CURRENT_PCT}%, expected ${EXPECTED_PCT}% for ${TARGET_TOKENS} on ${WIN_LABEL} — run: ~/.claude/set-compact.sh ${WIN_LABEL,,}"
    fi
  fi
fi

# Only output if there's something useful to report
HAS_OUTPUT=false
if [ -n "$SESSION_LEARNINGS" ] || [ -n "$PENDING_WORK" ] || [ -n "$WARNINGS" ]; then
  HAS_OUTPUT=true
fi

if [ "$HAS_OUTPUT" = "true" ]; then
  {
    echo ""
    echo "┌─ Session Start ─────────────────────────────────┐"
    if [ -n "$WARNINGS" ]; then
      echo -e "$WARNINGS"
    fi
    if [ -n "$SESSION_LEARNINGS" ]; then
      echo "  Session learnings: ${SESSION_LEARNINGS}"
    fi
    if [ -n "$PENDING_WORK" ]; then
      echo "  Pending work:"
      echo -e "$PENDING_WORK"
    fi
    echo "└─────────────────────────────────────────────────┘"
    echo ""
  } >&2
fi

log_hook_event "session-start" "initialized" "proot=${IS_PROOT}" 2>/dev/null || true

# 6. Harness health check (fast mode — skips test suite)
HARNESS_HEALTH="$HOME/.claude/hooks/scripts/harness-health.sh"
if [ -x "$HARNESS_HEALTH" ]; then
  if ! bash "$HARNESS_HEALTH" --fast --quiet 2>/dev/null; then
    HEALTH_OUT=$(bash "$HARNESS_HEALTH" --fast 2>/dev/null || true)
    WARNINGS="${WARNINGS}\n• HARNESS HEALTH FAILURE — run: ~/.claude/hooks/scripts/harness-health.sh --fast"
    # Print health details immediately so they appear in the session banner
    printf '%s\n' "$HEALTH_OUT" >&2
  fi
fi

exit 0
