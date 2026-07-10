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

  # Detect sub-agent origin from the hook payload (best-effort). The harness puts
  # "agent_type"/"agent_id" in the PreToolUse JSON for sub-agent tool calls and for
  # neither on a main-agent call (shell env cannot distinguish them — verified
  # 2026-07-10). $INPUT is in scope because this function is sourced into the hook.
  # RECORD-ONLY: this does not change the block decision; it lets approve.sh refuse
  # sub-agent self-approval (subagents must escalate, not self-approve).
  local agent_ctx=""
  if [ -n "${INPUT:-}" ]; then
    if command -v jq >/dev/null 2>&1; then
      agent_ctx=$(printf '%s' "$INPUT" | jq -r '.agent_type // empty' 2>/dev/null || printf '')
    fi
    if [ -z "$agent_ctx" ] && [[ "$INPUT" =~ \"agent_type\":\"([^\"]*)\" ]]; then
      agent_ctx="${BASH_REMATCH[1]}"
    fi
  fi

  # Write pending approval file (best-effort)
  mkdir -p "$pending_dir" 2>/dev/null || true
  {
    printf 'Reason: %s\n' "$reason"
    printf 'Command: %s\n' "$command"
    printf 'Time: %s\n' "$(date -Iseconds 2>/dev/null || date)"
    [ -n "$agent_ctx" ] && printf 'Subagent: %s\n' "$agent_ctx"
  } > "$pending_dir/$cmd_hash" 2>/dev/null || true

  # Log if hook-logger is available (sourced by calling hook)
  if command -v log_hook_event >/dev/null 2>&1; then
    log_hook_event "$hook_name" "soft-blocked" "$reason" 2>/dev/null || true
  fi

  # Emit JSON decision to stdout and exit
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"SOFT_BLOCK_APPROVAL_NEEDED: %s"}}\n' "$reason"
  exit 0
}
