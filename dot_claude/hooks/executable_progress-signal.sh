#!/usr/bin/env bash
set -euo pipefail
trap 'echo "HOOK CRASH: $0 line $LINENO" >&2; exit 0' ERR

# PostToolUse(Write|Edit|MultiEdit) hook: Emit the "sprint finalized" signal.
#
# Purpose
# -------
# The Stop hooks `compound-reminder.sh` and `verify-completion.sh` must only
# run at the end of a sprint (or the end of a PRD). They previously ran on
# EVERY Stop — including every AskUserQuestion — and scanned `docs/tasks`
# with `find` each time, which was both expensive and semantically wrong
# (the hooks were firing while the user was just answering a question).
#
# This hook inverts the control: instead of the Stop hooks polling the file
# system, the PostToolUse hook notices when a `progress.json` is written with
# every sprint in `complete` state, and writes a signal marker that the Stop
# hooks consume as a fast O(1) gate.
#
# Fast path: no write to a `progress.json` → exit 0 with almost no work.
# Slow path: write to a `progress.json` that has all sprints complete →
#   write `${HOME}/.claude/state/.sprint-finalized-${SESSION_ID}` containing
#   the absolute path of the finalized file, and reset the "already warned"
#   markers so that the Stop hooks get a fresh chance to fire once.
#
# Why this is not in a Stop hook
# ------------------------------
# Claude Code fires `Stop` on every turn boundary, including when the agent
# calls AskUserQuestion and hands control back to the user. The Stop hooks
# cannot distinguish "end of Q&A" from "end of sprint" without side-channel
# state. PostToolUse fires ONLY on actual tool calls, so a Q&A turn with no
# Edit/Write of `progress.json` never produces a signal.
#
# Exit codes
#   0 — always (this hook is advisory, never blocks)

# jq is required to parse the tool input JSON. Exit silently if missing —
# other hooks already warn about jq, no need to duplicate the noise.
if ! command -v jq &>/dev/null; then
  exit 0
fi

INPUT=$(cat)

TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || echo "")
case "$TOOL_NAME" in
  Write|Edit|MultiEdit) ;;
  *) exit 0 ;;
esac

FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null || echo "")
[ -z "$FILE_PATH" ] && exit 0

# Only interested in files named `progress.json`. This is a literal basename
# match so it cannot accidentally match things like `prd-progress.json.bak`.
case "$FILE_PATH" in
  */progress.json) ;;
  progress.json)   ;;
  *) exit 0 ;;
esac

# Resolve relative path against the project directory, same convention as
# scan-secrets.sh and post-edit-quality.sh.
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
if [[ "$FILE_PATH" != /* ]]; then
  FILE_PATH="$PROJECT_DIR/$FILE_PATH"
fi

# The file must exist and be a regular file (MultiEdit can fire before the
# file is fully written in edge cases — fail-open).
[ -f "$FILE_PATH" ] || exit 0

# Must live under a `docs/tasks/` subtree so unrelated progress.json files
# (e.g. build artifacts in random projects) do not trigger the signal.
case "$FILE_PATH" in
  */docs/tasks/*) ;;
  *) exit 0 ;;
esac

# Check whether the file describes a fully-complete PRD. Two conditions:
#   1. It has at least one sprint (TOTAL > 0)
#   2. No sprint is in a non-complete state (INCOMPLETE == 0)
INCOMPLETE=$(jq '[.sprints[]? | select(.status != "complete")] | length' "$FILE_PATH" 2>/dev/null || echo "1")
TOTAL=$(jq '.sprints | length' "$FILE_PATH" 2>/dev/null || echo "0")

if [ "$TOTAL" -le 0 ] || [ "$INCOMPLETE" -ne 0 ]; then
  exit 0
fi

# Resolve the session id. If it is missing or literally "unknown", skip the
# write — otherwise we pollute state/ with `-unknown` markers that the
# harness-health check flags as a regression.
SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null || echo "")
if [ -z "$SESSION_ID" ] || [ "$SESSION_ID" = "unknown" ]; then
  exit 0
fi

STATE_DIR="${HOME}/.claude/state"
mkdir -p "$STATE_DIR" 2>/dev/null || true

SIGNAL_FILE="${STATE_DIR}/.sprint-finalized-${SESSION_ID}"
# Record the absolute path of the finalized progress.json so the Stop hooks
# can re-parse it without another `find` walk.
printf '%s\n' "$FILE_PATH" > "$SIGNAL_FILE"

# A fresh completion deserves a fresh chance for the Stop hooks to warn.
# Clear the "already warned" markers left over from a prior completion in
# the same session (e.g. a second PRD run back-to-back).
rm -f "${STATE_DIR}/.claude-compound-warned-${SESSION_ID}" 2>/dev/null || true
rm -f "${STATE_DIR}/.claude-verify-warned-${SESSION_ID}"   2>/dev/null || true

exit 0
