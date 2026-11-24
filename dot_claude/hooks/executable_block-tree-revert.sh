#!/usr/bin/env bash
set -euo pipefail
trap 'echo "HOOK CRASH: $0 line $LINENO" >&2; exit 0' ERR

# PreToolUse(Bash) hook: SOFT-BLOCK working-tree-revert commands when the target
# repo has uncommitted changes that the command would silently destroy.
#
# Motivation (error-registry #24, category MERGE, auto_preventable):
#   An agent isolating a clean commit ran a working-tree revert in a repo carrying
#   UNRELATED uncommitted changes → destroyed that work with NO git recovery path.
#   The revert verbs below discard working-tree / stash state irreversibly.
#
# Design:
#   - Applies to MAIN AND SUB-AGENTS (the incident was a sub-agent). No bypass.
#   - Only fires when the target repo is actually DIRTY (revert on a clean tree
#     loses nothing → allowed silently). This keeps false-positives near zero.
#   - Soft-block: approve via AskUserQuestion → ~/.claude/hooks/scripts/approve.sh
#     → retry. NEVER tell the user to run approve.sh manually.
#
# Covered verbs: git checkout -- <path> / git checkout . / git checkout -f,
#   git restore (worktree; --staged-only is allowed), git reset --hard,
#   git stash drop / clear / pop, git clean -f/-d.

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

CMD_NORM=$(printf '%s' "$COMMAND" | sed 's/  */ /g; s/^ *//; s/ *$//')

# Only inspect commands that actually invoke git.
case "$CMD_NORM" in
  git|"git "*|*"; git "*|*"&& git "*|*"| git "*) : ;;
  *) exit 0 ;;
esac

# === CLASSIFY: does this command contain a destructive revert verb? ===
MATCHED=""
match() { if [[ "$CMD_NORM" =~ $1 ]]; then MATCHED="$2"; return 0; fi; return 1; }

# git checkout with a path (-- separator), the "." pathspec, or -f/--force
match 'git( +-C +[^ ]+)? +checkout +.*--( |$)'      "git checkout -- <path> (discards worktree changes)" ||
match 'git( +-C +[^ ]+)? +checkout +\.( |$)'         "git checkout . (discards all worktree changes)" ||
match 'git( +-C +[^ ]+)? +checkout +(-f|--force)( |$)' "git checkout --force (discards worktree changes)" ||
# git restore that touches the worktree (‑‑staged-only is a safe unstage)
match 'git( +-C +[^ ]+)? +restore +.*(-W|--worktree)( |$)' "git restore --worktree (discards worktree changes)" ||
# git reset --hard
match 'git( +-C +[^ ]+)? +reset +.*--hard'           "git reset --hard (discards worktree + index)" ||
# git stash destructive subcommands
match 'git( +-C +[^ ]+)? +stash +(drop|clear|pop)( |$)' "git stash drop/clear/pop (drops stashed work)" ||
# git clean -f / -d (removes untracked files)
match 'git( +-C +[^ ]+)? +clean +.*-[a-zA-Z]*[fd]'   "git clean -f/-d (removes untracked files)" ||
true

# Regex literals must live in variables — bash mis-tokenizes spaces inside an
# inline `[[ =~ <literal> ]]` right-hand side.
RE_RESTORE='git( +-C +[^ ]+)? +restore'
RE_STAGED='(--staged|-S)( |$)'
RE_WORKTREE='(-W|--worktree)( |$)'

# Special case: bare `git restore <pathspec>` (no --staged) defaults to --worktree.
if [ -z "$MATCHED" ]; then
  if [[ "$CMD_NORM" =~ $RE_RESTORE ]] && ! [[ "$CMD_NORM" =~ $RE_STAGED ]]; then
    MATCHED="git restore <path> (defaults to --worktree, discards changes)"
  fi
fi

[ -z "$MATCHED" ] && exit 0

# `git restore --staged` WITHOUT worktree flag only unstages → safe, allow.
if [[ "$CMD_NORM" =~ $RE_RESTORE ]] \
   && [[ "$CMD_NORM" =~ $RE_STAGED ]] \
   && ! [[ "$CMD_NORM" =~ $RE_WORKTREE ]]; then
  exit 0
fi

# === RESOLVE TARGET REPO (honor `git -C <dir>`, else cwd) ===
TARGET_DIR=""
RE_DASHC='git +-C +([^ ]+)'
if [[ "$CMD_NORM" =~ $RE_DASHC ]]; then
  TARGET_DIR="${BASH_REMATCH[1]}"
fi
if [ -z "$TARGET_DIR" ]; then
  if command -v jq &>/dev/null; then
    TARGET_DIR=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || printf '')
  fi
  [ -z "$TARGET_DIR" ] && TARGET_DIR="${PWD:-.}"
fi

# === DIRTY-TREE GUARD: only block if there is something to lose ===
DIRTY=$(git -C "$TARGET_DIR" status --porcelain 2>/dev/null || printf '')
if [ -z "$DIRTY" ]; then
  exit 0  # clean tree — the revert destroys nothing, allow silently
fi
DIRTY_COUNT=$(printf '%s\n' "$DIRTY" | grep -c . || printf '0')

# === APPROVAL TOKEN MECHANISM (5-minute TTL) ===
APPROVAL_DIR="$HOME/.claude/hooks/.approvals"
PENDING_DIR="$HOME/.claude/hooks/.pending"
HASH_SRC=$(normalize_cmd_for_hash "$COMMAND" 2>/dev/null) || HASH_SRC=""; [ -n "$HASH_SRC" ] || HASH_SRC="$COMMAND"
CMD_HASH=$(printf '%s' "tree-revert-$HASH_SRC" | cksum 2>/dev/null | cut -d' ' -f1) || CMD_HASH="tree-revert-fallback"
if [ -f "$APPROVAL_DIR/$CMD_HASH" ]; then
  APPROVAL_TIME=$(stat -c %Y "$APPROVAL_DIR/$CMD_HASH" 2>/dev/null || stat -f %m "$APPROVAL_DIR/$CMD_HASH" 2>/dev/null || echo 0)
  NOW=$(date +%s)
  if [ $((NOW - APPROVAL_TIME)) -lt 300 ]; then
    rm -f "$APPROVAL_DIR/$CMD_HASH" "$PENDING_DIR/$CMD_HASH" 2>/dev/null
    log_hook_event "block-tree-revert" "approved-by-token" "$CMD_NORM" 2>/dev/null || true
    exit 0
  fi
  rm -f "$APPROVAL_DIR/$CMD_HASH"
fi

# === SOFT-BLOCK ===
REASON="Destructive revert ($MATCHED) in a repo with $DIRTY_COUNT uncommitted change(s) at '$TARGET_DIR'. This can PERMANENTLY destroy uncommitted work with no git recovery path (error-registry #24). Verify with 'git -C $TARGET_DIR status' that nothing UNRELATED will be lost; if you must isolate a commit, prefer 'git stash push -- <only-your-files>' or 'git add -p' over reverting. Approve via AskUserQuestion + approve.sh only after confirming the loss is intended."

mkdir -p "$PENDING_DIR" 2>/dev/null || true
printf 'Reason: block-tree-revert matched "%s"\nCommand: %s\nRepo: %s (%s dirty)\nTime: %s\n' \
  "$MATCHED" "$CMD_NORM" "$TARGET_DIR" "$DIRTY_COUNT" "$(date -Iseconds 2>/dev/null || date)" \
  > "$PENDING_DIR/$CMD_HASH" 2>/dev/null || true

log_hook_event "block-tree-revert" "soft-blocked" "$MATCHED: $CMD_NORM" 2>/dev/null || true

printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"SOFT_BLOCK_APPROVAL_NEEDED: %s"}}\n' "$REASON"
exit 0
