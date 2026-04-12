#!/usr/bin/env bash
set -euo pipefail
trap 'echo "HOOK CRASH: $0 line $LINENO" >&2; exit 0' ERR

# PreToolUse hook: Enforce sub-agent delegation for the main agent.
#
# Matches (via settings.json): Read | Grep | Glob | Bash | Task | Agent
#
# Behavior:
#   - Counts Read/Grep/Glob calls per session in ~/.claude/hooks/state/main-reads-<session>
#   - Counts Bash read-style commands (cat/head/tail/grep/rg/find/ls/wc/awk/sed/jq/...)
#   - Resets counter on Agent/Task tool call (main agent delegated — good signal)
#   - Soft-blocks at count >= 4 with SOFT_BLOCK_APPROVAL_NEEDED
#   - Exempts maintenance paths (~/.claude/, MEMORY.md, session-learnings, INVARIANTS.md, etc.)
#   - Bypasses when sub-agent markers (env var or worktree cwd) are detected
#
# Threshold rationale: 3 free reads, 4th triggers. Matches the "main agent is
# an orchestrator, not a worker" principle from the context-engineering article.
# Three quick lookups are fine; the 4th is the sign the main agent is doing
# work it should delegate.
#
# Exit codes: always 0 (JSON decision goes to stdout per Claude Code hook contract).

INPUT=$(cat)

# === EXTRACT FIELDS ===
extract_field() {
  local path="$1"
  if command -v jq &>/dev/null; then
    printf '%s' "$INPUT" | jq -r "$path // empty" 2>/dev/null || printf ''
  else
    printf ''
  fi
}

TOOL_NAME=$(extract_field '.tool_name')

# Fallback regex for tool_name if jq unavailable or returns empty
if [ -z "$TOOL_NAME" ] && [[ "$INPUT" =~ \"tool_name\":\"([^\"]*)\" ]]; then
  TOOL_NAME="${BASH_REMATCH[1]}"
fi

# If we still can't determine tool_name, fail open (allow)
[ -z "$TOOL_NAME" ] && exit 0

SESSION_ID=$(extract_field '.session_id')
[ -z "$SESSION_ID" ] && SESSION_ID="default"
# Sanitize session id for filename
SESSION_ID="${SESSION_ID//\//_}"
SESSION_ID="${SESSION_ID// /_}"

HOOK_CWD=$(extract_field '.cwd')

# === SUB-AGENT BYPASS ===
# Explicit env var markers (set by sub-agents that source shared config)
if [ -n "${CLAUDE_SUBAGENT:-}" ] || [ -n "${CLAUDE_AGENT_TYPE:-}" ] || [ -n "${SPRINT_EXECUTOR:-}" ]; then
  exit 0
fi
# Worktree heuristic bypass (sub-agents usually run in worktrees)
for p in "$HOOK_CWD" "${PWD:-}"; do
  case "$p" in
    */worktrees/*|*/.worktrees/*|*.worktree*) exit 0 ;;
  esac
done

# === SHARED STATE ===
STATE_DIR="$HOME/.claude/hooks/state"
mkdir -p "$STATE_DIR" 2>/dev/null || true
COUNTER_FILE="$STATE_DIR/main-reads-$SESSION_ID"
LOCK_FILE="$STATE_DIR/counter.lock"
APPROVAL_DIR="$HOME/.claude/hooks/.approvals"
PENDING_DIR="$HOME/.claude/hooks/.pending"

source ~/.claude/hooks/lib/hook-logger.sh 2>/dev/null || true
source ~/.claude/hooks/lib/approvals.sh 2>/dev/null || true

# Opportunistic cleanup of stale counter files (older than 1 day)
find "$STATE_DIR" -maxdepth 1 -name "main-reads-*" -mtime +1 -delete 2>/dev/null || true

read_counter() {
  if [ -f "$COUNTER_FILE" ]; then
    cat "$COUNTER_FILE" 2>/dev/null || echo 0
  else
    echo 0
  fi
}

write_counter() {
  echo "$1" > "$COUNTER_FILE" 2>/dev/null || true
}

# Atomically increment the counter and return the new value.
# Uses flock so parallel hook invocations serialize their read/write.
# Outputs the new counter value to stdout.
atomic_increment_counter() {
  local new_val
  (
    # Acquire exclusive lock on fd 9 (the lock file)
    flock -x 9
    local cur
    cur=$(read_counter)
    new_val=$((cur + 1))
    write_counter "$new_val"
    echo "$new_val"
  ) 9>"$LOCK_FILE"
}

# Atomically reset the counter to 0.
atomic_reset_counter() {
  (
    flock -x 9
    write_counter 0
  ) 9>"$LOCK_FILE"
}

# === RESET ON DELEGATION ===
# When the main agent spawns a sub-agent via Task/Agent tool, that's the
# signal we wanted — reset the counter so the main agent has fresh headroom
# to process the sub-agent's return summary.
case "$TOOL_NAME" in
  Task|Agent|task|agent)
    atomic_reset_counter
    log_hook_event "enforce-delegation" "reset-on-delegation" "tool=$TOOL_NAME" 2>/dev/null || true
    exit 0
    ;;
esac

# === DETERMINE IF THIS CALL COUNTS AS A READ ===
SHOULD_COUNT=0
READ_TARGET=""

case "$TOOL_NAME" in
  Read)
    SHOULD_COUNT=1
    READ_TARGET=$(extract_field '.tool_input.file_path')
    ;;
  Grep)
    SHOULD_COUNT=1
    READ_TARGET=$(extract_field '.tool_input.path')
    [ -z "$READ_TARGET" ] && READ_TARGET=$(extract_field '.tool_input.pattern')
    ;;
  Glob)
    SHOULD_COUNT=1
    READ_TARGET=$(extract_field '.tool_input.pattern')
    ;;
  Bash)
    COMMAND=$(extract_field '.tool_input.command')
    # Fallback regex for command
    if [ -z "$COMMAND" ] && [[ "$INPUT" =~ \"command\":\"(([^\"\\]|\\.)*)\" ]]; then
      COMMAND="${BASH_REMATCH[1]}"
    fi
    # Extract the first token as the command name, stripped of any leading path
    FIRST_WORD="${COMMAND%% *}"
    FIRST_WORD="${FIRST_WORD##*/}"
    case "$FIRST_WORD" in
      cat|head|tail|less|more|grep|rg|find|ls|wc|awk|sed|jq|yq|fd|tree|file|stat|xxd|hexdump|strings|diff|column|od)
        SHOULD_COUNT=1
        READ_TARGET="$COMMAND"
        ;;
      *)
        # Not a read-style bash command — allow without counting
        exit 0
        ;;
    esac
    ;;
  *)
    # Unknown tool on this matcher — allow without counting
    exit 0
    ;;
esac

[ "$SHOULD_COUNT" = "0" ] && exit 0

# === EXEMPTIONS ===
# These paths represent "maintenance of own config / own state" or task-tracking
# files. Reading them doesn't pollute context in the way reading source code does.
is_exempt_path() {
  local p="$1"
  [ -z "$p" ] && return 1
  case "$p" in
    */.claude/*|/root/.claude/*) return 0 ;;
    *MEMORY.md|*/memory/*.md) return 0 ;;
    *session-learnings*|*session_learnings*) return 0 ;;
    *INVARIANTS.md|*/progress.json) return 0 ;;
    */.artifacts/*) return 0 ;;
    */docs/tasks/*) return 0 ;;
    */sprints/*.md) return 0 ;;
    */CLAUDE.md|*/AGENTS.md) return 0 ;;
  esac
  return 1
}

if is_exempt_path "$READ_TARGET"; then
  log_hook_event "enforce-delegation" "exempt" "$TOOL_NAME:$READ_TARGET" 2>/dev/null || true
  exit 0
fi

# === INCREMENT COUNTER (atomic, flock-serialized) ===
CURRENT=$(atomic_increment_counter)

THRESHOLD=4

if [ "$CURRENT" -lt "$THRESHOLD" ]; then
  log_hook_event "enforce-delegation" "count-$CURRENT" "$TOOL_NAME:$READ_TARGET" 2>/dev/null || true
  exit 0
fi

# === CHECK APPROVAL TOKEN (5-minute TTL) ===
CMD_HASH=$(printf '%s' "delegation-$SESSION_ID" | cksum 2>/dev/null | cut -d' ' -f1) || CMD_HASH="delegation-fallback"

if [ -f "$APPROVAL_DIR/$CMD_HASH" ]; then
  APPROVAL_TIME=$(stat -c %Y "$APPROVAL_DIR/$CMD_HASH" 2>/dev/null || echo 0)
  NOW=$(date +%s)
  if [ $((NOW - APPROVAL_TIME)) -lt 300 ]; then
    rm -f "$APPROVAL_DIR/$CMD_HASH" "$PENDING_DIR/$CMD_HASH" 2>/dev/null
    atomic_reset_counter  # Reset counter after approval — fresh slate
    log_hook_event "enforce-delegation" "approved-by-token" "count=$CURRENT" 2>/dev/null || true
    exit 0
  fi
  rm -f "$APPROVAL_DIR/$CMD_HASH"
fi

# === SOFT-BLOCK ===
REASON="Main agent has done $CURRENT direct reads this turn (threshold=$THRESHOLD). The main agent is an orchestrator, not a worker — delegate to an Explore sub-agent (Agent tool, subagent_type=Explore, model=haiku) to keep context clean. Approve via AskUserQuestion + approve.sh only if delegation is genuinely not possible."

# Write hook-specific pending file with read-count context (preserved for approve.sh)
mkdir -p "$PENDING_DIR" 2>/dev/null || true
printf 'Reason: enforce-delegation threshold reached (%s reads)\nTool: %s\nTarget: %s\nSession: %s\nTime: %s\n' \
  "$CURRENT" "$TOOL_NAME" "$READ_TARGET" "$SESSION_ID" "$(date -Iseconds 2>/dev/null || date)" \
  > "$PENDING_DIR/$CMD_HASH" 2>/dev/null || true

log_hook_event "enforce-delegation" "soft-blocked" "count=$CURRENT tool=$TOOL_NAME" 2>/dev/null || true

# Emit soft-block JSON (shared format via printf; lib sourced above for consistency)
printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"SOFT_BLOCK_APPROVAL_NEEDED: %s"}}\n' "$REASON"
exit 0
