#!/usr/bin/env bash
set -uo pipefail

# Test suite for modify_private_settings.json.tmpl — third-party hook grouping.
#
# Origin: moshi-hook reported the Claude integration "stale" after every
# chezmoi-autoupdate. The merge reused the baseline group whose matcher matched,
# so our hooks landed inside the group moshi considers its own (SessionStart,
# Stop, UserPromptSubmit — the matcher-less ones). moshi compares that group
# against its installer output and flags it as drifted.
#
# Covers:
#   1. A third-party matcher-less hook gets its OWN group, never ours
#   2. Our baseline hooks stay in their own group, untouched
#   3. No hook is lost in either direction
#   4. Two live groups sharing a matcher collapse into one foreign group
#   5. The live autocompact value still wins over the baseline
#   6. Unknown top-level keys still survive
#   7. env keys added by a tool (moshi-hook: CLAUDE_CODE_PLUGIN_DIRS) survive;
#      dropping it made moshi report the Claude hooks "out of date" every hour
#   8. baseline env values still win over live ones

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
YELLOW='\033[1;33m'
PASSED=0; FAILED=0

# Runs both from the repo (tests/../../..) and from ~/.claude/hooks/tests/ once
# deployed, where that relative walk lands on $HOME instead — ask chezmoi.
TMPL_REL="dot_claude/modify_private_settings.json.tmpl"
SOURCE_DIR="${CHEZMOI_SOURCE_DIR:-}"
[ -n "$SOURCE_DIR" ] || SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
[ -f "$SOURCE_DIR/$TMPL_REL" ] || SOURCE_DIR="$(chezmoi source-path 2>/dev/null || true)"
if [ -z "$SOURCE_DIR" ] || [ ! -f "$SOURCE_DIR/$TMPL_REL" ]; then
  printf "${YELLOW}  SKIP${NC} chezmoi source dir not found — cannot render %s\n" "$TMPL_REL"
  exit 0
fi

RENDERED=$(mktemp)
trap 'rm -f "$RENDERED"' EXIT
if ! chezmoi execute-template --source="$SOURCE_DIR" \
      < "$SOURCE_DIR/$TMPL_REL" > "$RENDERED" 2>/dev/null; then
  printf "${RED}  cannot render %s${NC}\n" "$TMPL_REL"
  exit 1
fi

check() {
  local name="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    printf "${GREEN}  PASS${NC} %s\n" "$name"; PASSED=$((PASSED+1))
  else
    printf "${RED}  FAIL${NC} %s\n       expected: %s\n       actual:   %s\n" "$name" "$expected" "$actual"
    FAILED=$((FAILED+1))
  fi
}

# Any env key the baseline defines — its value must not be overridden by live.
read -r BASELINE_ENV_KEY BASELINE_ENV_VALUE < <(python3 -c "
import json; e=json.load(open('$SOURCE_DIR/.chezmoitemplates/claude-settings.json')).get('env') or {}
k=next(k for k in e if k!='CLAUDE_AUTOCOMPACT_PCT_OVERRIDE'); print(k, e[k])")

# A live settings.json with a third-party hook sharing the matcher-less slot.
LIVE='{
  "env": {"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "62",
          "CLAUDE_CODE_PLUGIN_DIRS": "/home/u/.claude/moshi-plugin",
          "'"$BASELINE_ENV_KEY"'": "live-value"},
  "somethingNew": true,
  "hooks": {
    "Stop": [
      {"hooks": [{"type": "command", "command": "/opt/vendor/bin/vendor-hook run"}]},
      {"hooks": [{"type": "command", "command": "/opt/vendor/bin/other-hook run"}]}
    ]
  }
}'
OUT=$(printf '%s' "$LIVE" | bash "$RENDERED")

q() { printf '%s' "$OUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"; }

# 1 + 2: our hooks and the vendor's must never share a group
check "vendor hook is never in a group with ours" "True" \
  "$(q 'all(not (any("vendor" in h["command"] for h in g["hooks"]) and any(".claude/hooks/" in h["command"] for h in g["hooks"])) for g in d["hooks"]["Stop"])')"
check "our Stop hooks kept their own group" "True" \
  "$(q 'any(all(".claude/hooks/" in h["command"] for h in g["hooks"]) for g in d["hooks"]["Stop"])')"

# 3: nothing lost
check "vendor-hook survived" "True" "$(q 'any("vendor-hook" in h["command"] for g in d["hooks"]["Stop"] for h in g["hooks"])')"
check "other-hook survived" "True"  "$(q 'any("other-hook"  in h["command"] for g in d["hooks"]["Stop"] for h in g["hooks"])')"

# 4: both live groups share matcher None → one foreign group, not two
check "foreign groups collapsed into one" "1" \
  "$(q 'sum(1 for g in d["hooks"]["Stop"] if any("vendor" in h["command"] or "other-hook" in h["command"] for h in g["hooks"]))')"

# 5 + 6: pre-existing guarantees still hold
check "live autocompact value wins" "62" "$(q 'd["env"]["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"]')"
check "unknown top-level key survives" "True" "$(q 'd["somethingNew"]')"

# 7 + 8: tool-added env keys survive; baseline env keys keep the baseline value
check "tool-added env key survives" "/home/u/.claude/moshi-plugin" \
  "$(q 'd["env"].get("CLAUDE_CODE_PLUGIN_DIRS")')"
check "baseline env value wins over live" "$BASELINE_ENV_VALUE" \
  "$(q 'd["env"].get("'"$BASELINE_ENV_KEY"'")')"

printf "\n  passed: %d  failed: %d\n" "$PASSED" "$FAILED"
[ "$FAILED" -eq 0 ]
