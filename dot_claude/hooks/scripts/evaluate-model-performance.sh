#!/usr/bin/env bash
set -euo pipefail

# evaluate-model-performance.sh
#
# Reads ~/.claude/evolution/model-performance.json and reports (model, task_type)
# pairs that meet the upgrade/downgrade thresholds defined in CLAUDE.md:
#   - Samples >= THRESHOLD (default 10) AND success rate < 70% → propose upgrade
#   - Samples >= THRESHOLD (default 10) AND success rate > 90% → propose downgrade
#
# Usage:
#   evaluate-model-performance.sh [--format=human|json] [--threshold=N]
#
# Environment:
#   PERF_FILE — override path (default: ~/.claude/evolution/model-performance.json)
#
# Exit codes:
#   0 — ran successfully (zero proposals is still exit 0)
#   1 — could not read the performance file
#
# Called by /workflow-audit and /compound (Step 6 adaptation check).

FORMAT="human"
THRESHOLD=10

for arg in "$@"; do
  case "$arg" in
    --format=*) FORMAT="${arg#--format=}" ;;
    --threshold=*) THRESHOLD="${arg#--threshold=}" ;;
    -h|--help)
      sed -n '3,18p' "$0" | sed 's/^# //;s/^#//'
      exit 0
      ;;
    *)
      echo "Unknown arg: $arg" >&2
      exit 1
      ;;
  esac
done

PERF_FILE="${PERF_FILE:-$HOME/.claude/evolution/model-performance.json}"

if [ ! -f "$PERF_FILE" ]; then
  echo "ERROR: $PERF_FILE not found" >&2
  exit 1
fi

if ! command -v jq &>/dev/null; then
  echo "ERROR: jq is required" >&2
  exit 1
fi

# Build a flat array of {model, task_type, attempts, success_rate, proposal}
PROPOSALS=$(jq --argjson th "$THRESHOLD" '
  [ .models | to_entries[] | .key as $model | .value.task_types | to_entries[] |
    select(.value.attempts >= $th) |
    .value.first_try_success as $s | .value.attempts as $a |
    ($s / $a) as $rate |
    {
      model: $model,
      task_type: .key,
      attempts: $a,
      success_rate: ($rate * 100 | . * 10 | round / 10),
      proposal: (
        if $rate >= 0.9 then "downgrade"
        elif $rate < 0.7 then "upgrade"
        else "stable" end
      )
    }
  ]
' "$PERF_FILE")

# Also emit watch-list candidates (samples >= threshold/2, not yet at threshold)
WATCHLIST=$(jq --argjson th "$THRESHOLD" '
  [ .models | to_entries[] | .key as $model | .value.task_types | to_entries[] |
    select(.value.attempts >= ($th / 2 | floor) and .value.attempts < $th) |
    .value.first_try_success as $s | .value.attempts as $a |
    ($s / $a) as $rate |
    {
      model: $model,
      task_type: .key,
      attempts: $a,
      samples_needed: ($th - $a),
      success_rate: ($rate * 100 | . * 10 | round / 10),
      trend: (
        if $rate >= 0.9 then "toward_downgrade"
        elif $rate < 0.7 then "toward_upgrade"
        else "stable" end
      )
    }
  ]
' "$PERF_FILE")

if [ "$FORMAT" = "json" ]; then
  jq -n --argjson p "$PROPOSALS" --argjson w "$WATCHLIST" '{proposals: $p, watch_list: $w}'
  exit 0
fi

# Human format
echo "Model Performance Evaluation (threshold: $THRESHOLD samples)"
echo "============================================================"
echo ""

UPGRADE_COUNT=$(echo "$PROPOSALS" | jq '[.[] | select(.proposal == "upgrade")] | length')
DOWNGRADE_COUNT=$(echo "$PROPOSALS" | jq '[.[] | select(.proposal == "downgrade")] | length')
STABLE_COUNT=$(echo "$PROPOSALS" | jq '[.[] | select(.proposal == "stable")] | length')

if [ "$UPGRADE_COUNT" -gt 0 ]; then
  echo "↑ UPGRADE CANDIDATES (success rate < 70% at >= $THRESHOLD samples):"
  echo "$PROPOSALS" | jq -r '.[] | select(.proposal == "upgrade") | "  - \(.model) / \(.task_type): \(.success_rate)% over \(.attempts) attempts"'
  echo ""
fi

if [ "$DOWNGRADE_COUNT" -gt 0 ]; then
  echo "↓ DOWNGRADE CANDIDATES (success rate >= 90% at >= $THRESHOLD samples):"
  echo "$PROPOSALS" | jq -r '.[] | select(.proposal == "downgrade") | "  - \(.model) / \(.task_type): \(.success_rate)% over \(.attempts) attempts"'
  echo ""
fi

if [ "$STABLE_COUNT" -gt 0 ]; then
  echo "= STABLE (70% <= success rate < 90%):"
  echo "$PROPOSALS" | jq -r '.[] | select(.proposal == "stable") | "  - \(.model) / \(.task_type): \(.success_rate)% over \(.attempts) attempts"'
  echo ""
fi

WATCH_LEN=$(echo "$WATCHLIST" | jq 'length')
if [ "$WATCH_LEN" -gt 0 ]; then
  echo "◎ WATCH LIST (not yet at threshold):"
  echo "$WATCHLIST" | jq -r '.[] | "  - \(.model) / \(.task_type): \(.success_rate)% over \(.attempts) attempts (trend: \(.trend), need \(.samples_needed) more)"'
  echo ""
fi

TOTAL_TRACKED=$(jq '[.models | to_entries[] | .value.task_types | length] | add // 0' "$PERF_FILE")
LAST_UPDATED=$(jq -r '.last_updated // "never"' "$PERF_FILE")
echo "Total (model, task_type) pairs tracked: $TOTAL_TRACKED"
echo "Last updated: $LAST_UPDATED"
exit 0
