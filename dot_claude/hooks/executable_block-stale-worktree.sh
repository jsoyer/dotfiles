#!/usr/bin/env bash
# block-stale-worktree.sh — PreToolUse:Bash guard for the Noxys monorepo worktree
# discipline (see memory: noxys-wt-helper / shared-checkout-branch-collision /
# subagent-worktrees-anchor-stale-main).
#
# Two soft-blocks, scoped to the noxys-eu workspace only:
#   A) `git worktree add` that does NOT anchor on a fresh remote ref (origin/...).
#      Anchoring on HEAD / a local branch is the stale-base bug that left a sandbox
#      957 commits behind staging → merge conflicts → redone work.
#   B) `git checkout <branch>` / `git checkout -b <branch>` executed in the SHARED
#      checkout (~/Documents/Github/noxys-eu/noxys). The shared checkout must stay
#      parked on staging; per-task work goes in an isolated worktree via `noxys-wt`.
#      Allowed: checkout of staging/main (parking) and `git checkout -- <path>`.
#
# NOTE: the harness `isolation: worktree` sandboxes are NOT created via a Bash
# `git worktree add`, so this hook cannot intercept them. Phase 1 (keeping the
# shared checkout parked on fresh staging) is what keeps those inheriting a clean
# base. This hook covers MANUAL git worktree/checkout commands.
#
# Fail-open: any parse miss or error exits 0 (allow).

set -euo pipefail
trap 'exit 0' ERR   # fail-open: never block on hook crash

INPUT=$(cat)
if [[ "$INPUT" =~ \"command\":\"(([^\"\\]|\\.)*)\" ]]; then
  COMMAND="${BASH_REMATCH[1]}"
  COMMAND="${COMMAND//\\\"/\"}"
  COMMAND="${COMMAND//\\\\/\\}"
else
  exit 0
fi
[ -z "$COMMAND" ] && exit 0

# --- Scope: only the noxys-eu workspace ---
SCOPE="${COMMAND} ${CLAUDE_PROJECT_DIR:-} ${PWD:-}"
[[ "$SCOPE" == *noxys-eu* ]] || exit 0

source ~/.claude/hooks/lib/hook-logger.sh 2>/dev/null || true
source ~/.claude/hooks/lib/approvals.sh 2>/dev/null || true

APPROVAL_DIR="$HOME/.claude/hooks/.approvals"
PENDING_DIR="$HOME/.claude/hooks/.pending"
CMD_HASH=$(printf '%s' "$COMMAND" | cksum 2>/dev/null | cut -d' ' -f1) || CMD_HASH="fallback"

# Approval token (valid 5 min) — mirrors block-dangerous.sh
if [ -f "$APPROVAL_DIR/$CMD_HASH" ]; then
  APPROVAL_TIME=$(stat -c %Y "$APPROVAL_DIR/$CMD_HASH" 2>/dev/null || stat -f %m "$APPROVAL_DIR/$CMD_HASH" 2>/dev/null || echo 0)
  NOW=$(date +%s)
  if [ $((NOW - APPROVAL_TIME)) -lt 300 ]; then
    rm -f "$APPROVAL_DIR/$CMD_HASH" "$PENDING_DIR/$CMD_HASH" 2>/dev/null
    log_hook_event "block-stale-worktree" "approved-by-token" "$COMMAND" 2>/dev/null || true
    exit 0
  fi
  rm -f "$APPROVAL_DIR/$CMD_HASH"
fi

ask() {
  if command -v emit_soft_block >/dev/null 2>&1; then
    emit_soft_block "block-stale-worktree" "$1" "$COMMAND" "$PENDING_DIR" "$CMD_HASH"
  else
    mkdir -p "$PENDING_DIR" 2>/dev/null || true
    printf 'Reason: %s\nCommand: %s\nTime: %s\n' "$1" "$COMMAND" "$(date -Iseconds 2>/dev/null || date)" > "$PENDING_DIR/$CMD_HASH"
    log_hook_event "block-stale-worktree" "soft-blocked" "$1" 2>/dev/null || true
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"SOFT_BLOCK_APPROVAL_NEEDED: %s"}}\n' "$1"
    exit 0
  fi
}

# === Rule A: git worktree add must anchor on a fresh remote ref (origin/...) ===
if [[ "$COMMAND" =~ git[[:space:]].*worktree[[:space:]]+add[[:space:]] ]]; then
  if [[ ! "$COMMAND" =~ origin/ ]]; then
    ask "SOFT BLOCK: 'git worktree add' without an origin/ base anchors on HEAD/a local branch — the stale-base bug (a sandbox 957 commits behind staging). Anchor on a fresh remote ref, e.g.  git worktree add -b <branch> <path> origin/staging  (or just use: noxys-wt <slug>). Re-approve if intentional."
  fi
fi

# === Rule B: no branch checkout inside the SHARED checkout ===
# Match the shared repo root ~/…/noxys-eu/noxys but NOT sibling worktrees
# (noxys-eu/noxys-dt9-wt, noxys-eu/wt-*) nor .claude/worktrees subdir.
if [[ "$COMMAND" =~ noxys-eu/noxys([[:space:]]|\"|\'|\&|\;|$) ]]; then
  if [[ "$COMMAND" == *" -- "* ]]; then
    : # file/path restore (git checkout ... -- <path>) — allowed, not a branch switch
  elif [[ "$COMMAND" =~ git[[:space:]]+checkout[[:space:]]+-b[[:space:]] ]]; then
    ask "SOFT BLOCK: creating a branch in the SHARED checkout (noxys-eu/noxys) hijacks HEAD for concurrent agents (collision bug). Keep it parked on staging and isolate your task:  noxys-wt <slug>  → cd wt-<slug>. Re-approve if you really mean to branch here."
  elif [[ "$COMMAND" =~ git[[:space:]]+checkout[[:space:]]+([A-Za-z0-9._/-]+) ]]; then
    BR="${BASH_REMATCH[1]}"
    if [[ "$BR" != "staging" && "$BR" != "main" && "$BR" != "--" ]]; then
      ask "SOFT BLOCK: 'git checkout $BR' in the SHARED checkout (noxys-eu/noxys) switches HEAD and collides with concurrent agents. The shared checkout stays on staging; work in an isolated worktree:  noxys-wt <slug>. (checkout of staging/main, or 'git checkout -- <file>', is allowed.) Re-approve if intentional."
    fi
  fi
fi

exit 0
