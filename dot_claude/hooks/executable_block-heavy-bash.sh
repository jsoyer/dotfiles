#!/usr/bin/env bash
set -euo pipefail
trap 'echo "HOOK CRASH: $0 line $LINENO" >&2; exit 0' ERR

# PreToolUse(Bash) hook: block build/test/lint commands in the main agent.
#
# These commands are "worker" operations — the main agent must delegate them
# to a sub-agent (sprint-executor for sprint work, general-purpose for one-shots)
# to keep context clean per the context-engineering article.
#
# Soft-block with approval mechanism: if delegation is genuinely not possible
# (e.g., quick sanity check, user explicitly asked for a build), approve via:
#   AskUserQuestion → ~/.claude/hooks/scripts/approve.sh → retry
#
# NEVER tell the user to run approve.sh manually — always wrap in AskUserQuestion.

INPUT=$(cat)

# === EXTRACT COMMAND ===
if [[ "$INPUT" =~ \"command\":\"(([^\"\\]|\\.)*)\" ]]; then
  COMMAND="${BASH_REMATCH[1]}"
  COMMAND="${COMMAND//\\\"/\"}"
  COMMAND="${COMMAND//\\\\/\\}"
else
  exit 0
fi

[ -z "$COMMAND" ] && exit 0

source ~/.claude/hooks/lib/hook-logger.sh 2>/dev/null || true
source ~/.claude/hooks/lib/approvals.sh 2>/dev/null || true

# === SUB-AGENT BYPASS ===
# Sub-agents (sprint-executor, code-reviewer, etc.) LEGITIMATELY run builds
# and tests. This hook only enforces against the main agent.
if [ -n "${CLAUDE_SUBAGENT:-}" ] || [ -n "${CLAUDE_AGENT_TYPE:-}" ] || [ -n "${SPRINT_EXECUTOR:-}" ]; then
  exit 0
fi

# Extract cwd for worktree heuristic
HOOK_CWD=""
if command -v jq &>/dev/null; then
  HOOK_CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || printf '')
fi
for p in "$HOOK_CWD" "${PWD:-}"; do
  case "$p" in
    */worktrees/*|*/.worktrees/*|*.worktree*) exit 0 ;;
  esac
done

# === GLOBAL EXEMPTIONS (command-level) ===

# Normalize whitespace once for cleaner matching
CMD_NORM=$(printf '%s' "$COMMAND" | sed 's/  */ /g; s/^ *//; s/ *$//')

# Help / version queries never count as heavy
case "$CMD_NORM" in
  *" --help"*|*" -h "*|*" --version"*|*" -v "*|*" -V "*) exit 0 ;;
  *--help|*-h|*--version|*-v|*-V) exit 0 ;;
esac

# Git commands are always allowed (block-dangerous.sh handles destructive git)
case "$CMD_NORM" in
  git|"git "*) exit 0 ;;
esac

# Dev servers are orchestration-level (article-sanctioned — needed for Playwright)
case "$CMD_NORM" in
  "pnpm dev"|"pnpm dev "*|"pnpm run dev"|"pnpm run dev "*) exit 0 ;;
  "npm run dev"|"npm run dev "*|"yarn dev"|"yarn dev "*) exit 0 ;;
  "next dev"|"next dev "*|"vite"|"vite "*|"nodemon"|"nodemon "*) exit 0 ;;
  "tsx watch "*|"node --watch "*) exit 0 ;;
esac

# === APPROVAL TOKEN MECHANISM (5-minute TTL) ===
APPROVAL_DIR="$HOME/.claude/hooks/.approvals"
PENDING_DIR="$HOME/.claude/hooks/.pending"
CMD_HASH=$(printf '%s' "heavy-bash-$CMD_NORM" | cksum 2>/dev/null | cut -d' ' -f1) || CMD_HASH="heavy-fallback"

if [ -f "$APPROVAL_DIR/$CMD_HASH" ]; then
  APPROVAL_TIME=$(stat -c %Y "$APPROVAL_DIR/$CMD_HASH" 2>/dev/null || echo 0)
  NOW=$(date +%s)
  if [ $((NOW - APPROVAL_TIME)) -lt 300 ]; then
    rm -f "$APPROVAL_DIR/$CMD_HASH" "$PENDING_DIR/$CMD_HASH" 2>/dev/null
    log_hook_event "block-heavy-bash" "approved-by-token" "$CMD_NORM" 2>/dev/null || true
    exit 0
  fi
  rm -f "$APPROVAL_DIR/$CMD_HASH"
fi

# === HEAVY COMMAND PATTERN MATCHING ===
MATCHED=""

match_pattern() {
  local regex="$1" label="$2"
  if [[ "$CMD_NORM" =~ $regex ]]; then
    MATCHED="$label"
    return 0
  fi
  return 1
}

match_pattern '^(pnpm|npm|yarn)[[:space:]]+(install|ci|audit|upgrade|update|outdated|add|remove)([[:space:]]|$)' "package manager install/audit" ||
match_pattern '^(pnpm|npm|yarn)[[:space:]]+(build|test|lint|typecheck|check|format|e2e)([[:space:]]|$)' "package manager build/test/lint" ||
match_pattern '^(pnpm|npm|yarn)[[:space:]]+run[[:space:]]+(build|test|lint|typecheck|check|format|ci|e2e)([[:space:]]|$)' "package manager run build/test/lint" ||
match_pattern '^cargo[[:space:]]+(build|test|check|clippy|install|run)([[:space:]]|$)' "cargo build/test/run" ||
match_pattern '^go[[:space:]]+(build|test|vet|install|run|generate)([[:space:]]|$)' "go build/test/run" ||
match_pattern '^(pytest|python[[:space:]]+-m[[:space:]]+pytest)([[:space:]]|$)' "pytest" ||
match_pattern '^(jest|vitest|mocha|ava)([[:space:]]|$)' "JS test runner" ||
match_pattern '^playwright[[:space:]]+test([[:space:]]|$)' "playwright test suite" ||
match_pattern '^tsc([[:space:]]|$)' "TypeScript compiler" ||
match_pattern '^(eslint|prettier|biome)[[:space:]]+' "JS linter/formatter" ||
match_pattern '^(ruff|black|isort)[[:space:]]+' "Python linter/formatter" ||
match_pattern '^(mypy|pyright)([[:space:]]|$)' "Python type checker" ||
match_pattern '^make[[:space:]]+(build|test|lint|ci|check|all)([[:space:]]|$)' "make build/test/lint" ||
match_pattern '^(mvn|gradle|sbt)[[:space:]]+' "JVM build tool" ||
match_pattern '^(bundle[[:space:]]+exec|rake)([[:space:]]|$)' "Ruby build tool" ||
true  # prevent errexit from firing when no pattern matches

if [ -z "$MATCHED" ]; then
  exit 0  # Not a heavy command — allow
fi

# === SOFT-BLOCK ===
REASON="Heavy command detected ($MATCHED). The main agent must delegate build/test/lint work to a sub-agent (general-purpose for one-shots, sprint-executor for sprint work) to keep context clean. Approve via AskUserQuestion + approve.sh only if delegation is genuinely not possible."

# Write hook-specific pending file with matched pattern context (preserved for approve.sh)
mkdir -p "$PENDING_DIR" 2>/dev/null || true
printf 'Reason: block-heavy-bash matched pattern "%s"\nCommand: %s\nTime: %s\n' \
  "$MATCHED" "$CMD_NORM" "$(date -Iseconds 2>/dev/null || date)" \
  > "$PENDING_DIR/$CMD_HASH" 2>/dev/null || true

log_hook_event "block-heavy-bash" "soft-blocked" "$MATCHED: $CMD_NORM" 2>/dev/null || true

# Emit soft-block JSON via shared lib (or inline fallback if lib unavailable)
if command -v emit_soft_block >/dev/null 2>&1; then
  # Pass empty pending_dir so emit_soft_block skips its own pending write (already done above)
  # We re-use emit_soft_block only for the JSON+exit step by writing to /dev/null hash
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"SOFT_BLOCK_APPROVAL_NEEDED: %s"}}\n' "$REASON"
  exit 0
else
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"SOFT_BLOCK_APPROVAL_NEEDED: %s"}}\n' "$REASON"
  exit 0
fi
