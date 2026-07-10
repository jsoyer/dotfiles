#!/usr/bin/env bash
# noxys-tracker-audit.sh — periodic tracker-vs-staging reconciliation audit.
#
# WHY: the noxys monorepo's progress.json / checkbox trackers drift badly from
# shipped code — on 2026-07-10, 4 of 5 "pending" PRDs opened were actually already
# shipped (only the tracker was stale), causing wasted agent runs. This script
# generates a prioritised REVIEW QUEUE so stale trackers get reconciled instead of
# re-built. It FLAGS candidates for human/agent verification — it does NOT mutate
# any tracker (verification of "is this sprint's code really in staging" needs
# judgment; do that per-candidate with `git ls-tree/grep origin/staging`).
#
# Usage:  bash ~/.claude/scripts/noxys-tracker-audit.sh [output.md]
# Env:    NOXYS_MONOREPO (default ~/Documents/Github/noxys-eu/noxys)
# Cron:   scheduled weekly (see CronList). Exit 0 always (never break a cron run).
set -uo pipefail

REPO="${NOXYS_MONOREPO:-$HOME/Documents/Github/noxys-eu/noxys}"
STATE_DIR="$HOME/.claude/state"
mkdir -p "$STATE_DIR" 2>/dev/null || true
OUT="${1:-$STATE_DIR/noxys-tracker-audit-latest.md}"

cd "$REPO" 2>/dev/null || { echo "noxys-tracker-audit: repo not found at $REPO" >&2; exit 0; }
git fetch origin --quiet 2>/dev/null || true

PENDING_RE='"status": *"(pending|not_started|planned|backlog|scheduled|in_progress|in progress)"'
DONE_RE='"status": *"(complete|completed|done|merged)"'

{
  echo "# Noxys tracker audit — $(date -Iseconds 2>/dev/null || date)"
  echo
  echo "Prioritised review queue: progress.json trackers claiming unfinished work."
  echo "Signals (heuristic — VERIFY before acting):"
  echo "- **MIXED** = has BOTH done and pending sprints → the drift hot-spot (partly shipped, tracker lagging)."
  echo "- **staging-activity** = N recent origin/staging commits reference the task slug/id → likely already shipped."
  echo "- Action per row: \`git ls-tree -r origin/staging <task code paths>\` / \`git grep <symbol> origin/staging\`;"
  echo "  if the pending sprint's code is already on staging → reconcile the tracker (don't rebuild)."
  echo
  found=0
  while IFS= read -r pj; do
    [ -f "$pj" ] || continue
    dir=$(dirname "$pj")
    slug=$(basename "$dir")
    pend=$(grep -oiE "$PENDING_RE" "$pj" 2>/dev/null | wc -l | tr -d ' ')
    [ "${pend:-0}" -eq 0 ] && continue
    found=$((found + 1))
    done_=$(grep -oiE "$DONE_RE" "$pj" 2>/dev/null | wc -l | tr -d ' ')
    # task id (first "task"/"id"/"project" value) helps match commit messages
    tid=$(grep -oiE '"(task|id|project)": *"[A-Z0-9][A-Za-z0-9._-]*"' "$pj" 2>/dev/null | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
    # staging-activity signal: commits (last 150 days) referencing the slug or task id
    pat="$slug"; [ -n "${tid:-}" ] && pat="$slug|$tid"
    hits=$(git log origin/staging --oneline --since="150 days ago" 2>/dev/null | grep -icE "$pat" 2>/dev/null || echo 0)
    flags=""
    [ "${done_:-0}" -gt 0 ] && flags="MIXED(${done_} done/${pend} pending)"
    [ "${hits:-0}" -gt 0 ] && flags="${flags:+$flags · }staging-activity(${hits})"
    [ -z "$flags" ] && flags="no-signal (likely genuinely unbuilt)"
    printf -- "- \`%s\` — pending=%s done=%s%s — **%s**\n" \
      "${dir#./}" "$pend" "${done_:-0}" "${tid:+ [$tid]}" "$flags"
  done < <(find docs apps web surfaces packages -maxdepth 7 -name progress.json \
             -not -path '*/.claude/*' -not -path '*/node_modules/*' 2>/dev/null | sort)
  echo
  echo "_$found tracker(s) with unfinished-claimed work. Rows flagged MIXED or staging-activity are the most likely stale — verify + reconcile first._"
} > "$OUT" 2>/dev/null || true

echo "noxys-tracker-audit: wrote $OUT"
exit 0
