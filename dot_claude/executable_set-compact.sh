#!/usr/bin/env bash
# set-compact.sh — Switch CLAUDE_AUTOCOMPACT_PCT_OVERRIDE for a given context window size.
#
# Per-window compact targets (keeps context inside the quality zone described in the
# context-engineering article; larger windows can afford a larger absolute budget):
#   128K window -> compact at 100K tokens  (78%)
#   200K window -> compact at 125K tokens  (62%)
#   1M   window -> compact at 150K tokens  (15%)
#
# Usage:
#   ~/.claude/set-compact.sh 128k     # 128K window  -> 78%
#   ~/.claude/set-compact.sh 200k     # 200K window  -> 62%
#   ~/.claude/set-compact.sh 1m       # 1M window    -> 15%
#   ~/.claude/set-compact.sh custom 150000 500000  # 150K target on 500K window -> 30%
#   ~/.claude/set-compact.sh status   # Show current config without changing
#
# Run as: ! ~/.claude/set-compact.sh 1m

set -euo pipefail

SETTINGS="$HOME/.claude/settings.json"

# Per-window target table — edit here if policy changes.
# Keep in sync with: ~/.claude/hooks/session-start.sh, CLAUDE.md, rules/context-engineering.md
target_for_window() {
  case "$1" in
    128000)  echo 100000 ;;
    200000)  echo 125000 ;;
    1000000) echo 150000 ;;
    *)       echo 125000 ;;  # default for unknown windows
  esac
}

usage() {
  echo "Usage: $0 <window-size>"
  echo "  Presets: 200k | 1m | 128k"
  echo "  Custom:  custom <target_tokens> <window_tokens>"
  echo "  Query:   status"
  exit 1
}

if [ $# -lt 1 ]; then usage; fi

if ! command -v jq &>/dev/null; then
  echo "ERROR: jq is required but not installed." >&2
  exit 1
fi

ARG="${1,,}"  # lowercase

# status mode: print current config and exit
if [ "$ARG" = "status" ]; then
  CURRENT=$(jq -r '.env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE // "unset"' "$SETTINGS")
  echo "Current CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: ${CURRENT}"
  echo "Per-window targets: 128K->100K(78%)  200K->125K(62%)  1M->150K(15%)"
  case "$CURRENT" in
    15|16) echo "Matches: 1M window (150K trigger at ~15%)" ;;
    62|63) echo "Matches: 200K window (125K trigger at ~62-63%)" ;;
    78|79) echo "Matches: 128K window (100K trigger at ~78%)" ;;
    unset) echo "No override set - using Claude Code default (~95%)" ;;
    *)     echo "Custom value - verify against your window size" ;;
  esac
  exit 0
fi

case "$ARG" in
  200k) WINDOW=200000  ; TARGET_TOKENS=$(target_for_window 200000)  ;;
  1m)   WINDOW=1000000 ; TARGET_TOKENS=$(target_for_window 1000000) ;;
  128k) WINDOW=128000  ; TARGET_TOKENS=$(target_for_window 128000)  ;;
  custom)
    if [ $# -lt 3 ]; then
      echo "custom requires: $0 custom <target_tokens> <window_tokens>" >&2
      exit 1
    fi
    TARGET_TOKENS="$2"
    WINDOW="$3"
    ;;
  *)
    echo "Unknown window size: $1" >&2
    usage
    ;;
esac

# Compute percentage: floor(target/window * 100)
PCT=$(( TARGET_TOKENS * 100 / WINDOW ))

# Clamp between 5 and 95
if [ "$PCT" -lt 5 ]; then PCT=5; fi
if [ "$PCT" -gt 95 ]; then PCT=95; fi

echo "Window: ${WINDOW} tokens | Target: ${TARGET_TOKENS} tokens | Setting: ${PCT}%"

# Update settings.json in-place
TMP=$(mktemp)
jq --argjson pct "$PCT" '.env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE = ($pct | tostring)' "$SETTINGS" > "$TMP"
mv "$TMP" "$SETTINGS"

echo "Updated $SETTINGS: CLAUDE_AUTOCOMPACT_PCT_OVERRIDE = \"${PCT}\""
echo "Compact will trigger at ~${TARGET_TOKENS} tokens on a ${WINDOW}-token window."
echo "(Takes effect on next session start)"
