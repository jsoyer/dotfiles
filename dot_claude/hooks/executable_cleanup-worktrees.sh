#!/usr/bin/env bash
# Stop hook: Prune stale worktrees and remove merged sprint branches
#
# Runs on every task end to guarantee worktree cleanup even if the orchestrator
# crashes mid-work, the user doesn't run the orchestrator, or worktrees accumulate
# between sessions.
#
# Safety invariants:
#   - NEVER deletes worktrees with unmerged changes — logs WARNING instead
#   - Uses `git branch -d` (lowercase) which refuses unmerged branches
#   - NEVER uses `git branch -D` (force delete)
#   - ALWAYS exits 0 — cleanup is best-effort, never blocks
#   - Skips if PROJECT_DIR is $HOME or /root
#   - Skips if not a git repository

# Cleanup hook crashes should never block — always exit 0
trap 'echo "HOOK WARNING: cleanup-worktrees.sh crashed at line $LINENO" >&2; exit 0' ERR

# Source shared logging utility
source ~/.claude/hooks/lib/hook-logger.sh 2>/dev/null || true

# Source shared stop-guard (fail-open: if missing, guard is a no-op)
source ~/.claude/hooks/lib/stop-guard.sh 2>/dev/null || true

# ─── CONFIGURATION ─────────────────────────────────────────────────────

HOOK_NAME="cleanup-worktrees"

# ─── READ STDIN INPUT ──────────────────────────────────────────────────

# Read JSON input from stdin (Stop hook protocol)
INPUT=""
if [ -t 0 ]; then
  # No stdin (running manually) — use pwd
  INPUT="{}"
else
  INPUT=$(cat 2>/dev/null || echo "{}")
fi

# Check stop_hook_active — prevent infinite loop
check_stop_hook_active "$INPUT"

# ─── RESOLVE PROJECT DIRECTORY ─────────────────────────────────────────

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Skip if working in home directory (not a real project)
if [ "$PROJECT_DIR" = "$HOME" ] || [ "$PROJECT_DIR" = "/root" ]; then
  log_hook_event "$HOOK_NAME" "skipped" "project dir is HOME — not a real project"
  exit 0
fi

# Skip if project directory doesn't exist
if [ ! -d "$PROJECT_DIR" ]; then
  log_hook_event "$HOOK_NAME" "skipped" "project dir does not exist: $PROJECT_DIR"
  exit 0
fi

# Skip if not a git repository
if ! git -C "$PROJECT_DIR" rev-parse --git-dir &>/dev/null 2>&1; then
  log_hook_event "$HOOK_NAME" "skipped" "not a git repo: $PROJECT_DIR"
  exit 0
fi

# ─── PRUNE STALE WORKTREE REFERENCES ───────────────────────────────────

# Remove worktree entries where the path no longer exists on disk
if git -C "$PROJECT_DIR" worktree prune 2>/dev/null; then
  log_hook_event "$HOOK_NAME" "pruned" "removed stale worktree references"
else
  log_hook_event "$HOOK_NAME" "prune-failed" "git worktree prune encountered an error (non-fatal)"
fi

# ─── LIST AND CLEAN MERGED WORKTREES ───────────────────────────────────

REMOVED_COUNT=0
WARNED_COUNT=0

# Parse worktree list (porcelain format):
#   worktree <path>
#   HEAD <sha>
#   branch refs/heads/<name>   (or "detached")
#   (blank line separates entries)
#
# We skip the first entry (main worktree) and process additional ones.

WORKTREE_LIST=$(git -C "$PROJECT_DIR" worktree list --porcelain 2>/dev/null || echo "")

if [ -z "$WORKTREE_LIST" ]; then
  log_hook_event "$HOOK_NAME" "completed" "no worktrees found"
  exit 0
fi

# ─── WORKTREE PROCESSOR (shared logic for loop body and final-entry case) ──

# process_worktree PATH BRANCH
# Checks if the worktree at PATH with BRANCH is merged and safe to remove.
# Updates REMOVED_COUNT and WARNED_COUNT globals.
process_worktree() {
  local wt_path="$1" wt_branch="$2"
  local main_head wt_dirty

  # Check if branch is merged into HEAD of main worktree
  main_head=$(git -C "$PROJECT_DIR" rev-parse HEAD 2>/dev/null || echo "")
  if [ -n "$main_head" ] && git -C "$PROJECT_DIR" merge-base --is-ancestor "$wt_branch" HEAD 2>/dev/null; then
    # Branch is merged — check worktree is clean before removing
    wt_dirty=$(git -C "$wt_path" status --porcelain 2>/dev/null || echo "")
    if [ -n "$wt_dirty" ]; then
      log_hook_event "$HOOK_NAME" "WARNING" "worktree $wt_path has uncommitted changes despite merged branch — skipping"
      echo "HOOK WARNING: cleanup-worktrees: worktree has dirty state: $wt_path ($wt_branch)" >&2
      WARNED_COUNT=$((WARNED_COUNT + 1))
    elif git -C "$PROJECT_DIR" worktree remove "$wt_path" 2>/dev/null; then
      log_hook_event "$HOOK_NAME" "removed-worktree" "$wt_path (branch: $wt_branch)"
      # Use -d (not -D) — will refuse if branch somehow has unmerged commits
      if git -C "$PROJECT_DIR" branch -d "$wt_branch" 2>/dev/null; then
        log_hook_event "$HOOK_NAME" "deleted-branch" "$wt_branch (merged)"
      else
        log_hook_event "$HOOK_NAME" "branch-delete-skipped" "$wt_branch — git branch -d refused (safety net)"
      fi
      REMOVED_COUNT=$((REMOVED_COUNT + 1))
    else
      log_hook_event "$HOOK_NAME" "remove-failed" "could not remove worktree $wt_path"
    fi
  else
    # Branch has unmerged commits — log warning, do NOT delete
    log_hook_event "$HOOK_NAME" "WARNING" "worktree $wt_path (branch: $wt_branch) has unmerged changes — skipping"
    echo "HOOK WARNING: cleanup-worktrees: unmerged worktree preserved: $wt_path ($wt_branch)" >&2
    WARNED_COUNT=$((WARNED_COUNT + 1))
  fi
}

# Track whether we are reading the first (main) worktree
IS_FIRST=true
CURRENT_PATH=""
CURRENT_BRANCH=""

while IFS= read -r line; do
  if [[ "$line" == worktree\ * ]]; then
    # Process previous worktree entry (if any and not main)
    if [ "$IS_FIRST" = "false" ] && [ -n "$CURRENT_PATH" ] && [ -n "$CURRENT_BRANCH" ]; then
      process_worktree "$CURRENT_PATH" "$CURRENT_BRANCH"
    fi

    # Start tracking new worktree entry
    CURRENT_PATH="${line#worktree }"
    CURRENT_BRANCH=""
    IS_FIRST="false"

    # The very first worktree entry is the main worktree — skip it
    # We detect it by checking if it matches the PROJECT_DIR
    if [ "$CURRENT_PATH" = "$PROJECT_DIR" ]; then
      IS_FIRST="true"
    fi

  elif [[ "$line" == branch\ * ]]; then
    # Extract branch name from "branch refs/heads/<name>"
    BRANCH_REF="${line#branch }"
    CURRENT_BRANCH="${BRANCH_REF#refs/heads/}"
  fi
done <<< "$WORKTREE_LIST"

# Process the last worktree entry (loop ends without a blank-line trigger)
if [ "$IS_FIRST" = "false" ] && [ -n "$CURRENT_PATH" ] && [ -n "$CURRENT_BRANCH" ]; then
  process_worktree "$CURRENT_PATH" "$CURRENT_BRANCH"
fi

# ─── SUMMARY ───────────────────────────────────────────────────────────

if [ "$REMOVED_COUNT" -gt 0 ] || [ "$WARNED_COUNT" -gt 0 ]; then
  log_hook_event "$HOOK_NAME" "completed" "removed $REMOVED_COUNT merged worktree(s), preserved $WARNED_COUNT unmerged (warnings logged)"
else
  log_hook_event "$HOOK_NAME" "completed" "no sprint worktrees found in $PROJECT_DIR"
fi

# Cleanup hook ALWAYS exits 0 — never blocks
exit 0
