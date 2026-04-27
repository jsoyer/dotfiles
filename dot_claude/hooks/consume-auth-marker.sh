#!/usr/bin/env bash
set -uo pipefail
trap 'echo "HOOK WARNING: consume-auth-marker.sh crashed at line $LINENO" >&2; exit 0' ERR

# Stop hook (runs LAST in the Stop chain): consume the one-shot auth marker.
#
# All Stop hooks in the chain check `~/.claude/state/.stop-hooks-ok-<session>`
# via `check_completion_authorized`. Previously the guard deleted the marker
# on first read, silently blocking every subsequent hook in the chain. This
# hook centralizes the consume step: it runs AFTER the other Stop hooks have
# had their chance to see the marker, then removes it so the next turn
# restarts with a fresh authorization requirement.
#
# Must be registered as the LAST entry in settings.json → hooks.Stop[0].hooks.
#
# Exits 0 always — cleanup must never block the stop flow.

if ! command -v jq &>/dev/null; then
  exit 0
fi

INPUT=$(cat 2>/dev/null || echo "{}")
SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null || echo "")
[ -z "$SESSION_ID" ] || [ "$SESSION_ID" = "null" ] && exit 0

SIGNAL_FILE="${HOME}/.claude/state/.stop-hooks-ok-${SESSION_ID}"
[ -f "$SIGNAL_FILE" ] && rm -f "$SIGNAL_FILE" 2>/dev/null || true

exit 0
