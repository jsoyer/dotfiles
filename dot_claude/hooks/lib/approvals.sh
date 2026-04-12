#!/usr/bin/env bash
# approvals.sh — shared soft-block emission for PreToolUse hooks.
#
# SAFETY: fail-open contract — caller should wrap source with || true.
# If this file is missing, the calling hook falls back to its own inline logic.
#
# Usage:
#   source ~/.claude/hooks/lib/approvals.sh 2>/dev/null || true
#
# Then call:
#   emit_soft_block "$HOOK_NAME" "$REASON" "$COMMAND" "$PENDING_DIR" "$CMD_HASH"
#
# Args:
#   hook_name   — name for log_hook_event (e.g. "block-dangerous")
#   reason      — human-readable reason string (no newlines)
#   command     — the command being blocked
#   pending_dir — directory to write the pending approval file
#   cmd_hash    — filename key for the pending file (from cksum)
#
# Side effects:
#   - Creates pending file at $pending_dir/$cmd_hash
#   - Calls log_hook_event if available
#   - Prints JSON decision envelope to stdout
#   - Exits 0 (Claude Code hook contract: JSON on stdout, exit 0)

emit_soft_block() {
  local hook_name="$1" reason="$2" command="$3" pending_dir="$4" cmd_hash="$5"

  # Write pending approval file (best-effort)
  mkdir -p "$pending_dir" 2>/dev/null || true
  {
    printf 'Reason: %s\n' "$reason"
    printf 'Command: %s\n' "$command"
    printf 'Time: %s\n' "$(date -Iseconds 2>/dev/null || date)"
  } > "$pending_dir/$cmd_hash" 2>/dev/null || true

  # Log if hook-logger is available (sourced by calling hook)
  if command -v log_hook_event >/dev/null 2>&1; then
    log_hook_event "$hook_name" "soft-blocked" "$reason" 2>/dev/null || true
  fi

  # Emit JSON decision to stdout and exit
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"SOFT_BLOCK_APPROVAL_NEEDED: %s"}}\n' "$reason"
  exit 0
}
