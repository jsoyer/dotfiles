#!/usr/bin/env bash
# stop-guard.sh — exit 0 if the Stop hook is firing recursively (stop_hook_active=true)
#
# Source this in any Stop hook AFTER reading stdin into INPUT.
# SAFETY: fail-open — if jq fails, the guard is a no-op (does not block the hook).
#
# Usage:
#   source ~/.claude/hooks/lib/stop-guard.sh 2>/dev/null || true
#   check_stop_hook_active "$INPUT"

check_stop_hook_active() {
  local input="${1:-}"
  local val
  val=$(printf '%s' "$input" | jq -r '.stop_hook_active // false' 2>/dev/null || echo "false")
  if [ "$val" = "true" ]; then
    exit 0
  fi
}
