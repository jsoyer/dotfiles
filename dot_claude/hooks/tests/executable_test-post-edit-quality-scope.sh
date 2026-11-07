#!/usr/bin/env bash
set -uo pipefail

# Regression test for post-edit-quality.sh: the Python formatter must touch
# only the edited file. `ruff check --fix "$FILE" && ruff format` (no path)
# reformatted the whole project dir, i.e. every .py file in a repo or in ~.

HOOK="$HOME/.claude/hooks/post-edit-quality.sh"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

if [ ! -x "$HOOK" ]; then
  printf "${RED}HOOK NOT EXECUTABLE: %s${NC}\n" "$HOOK"
  exit 1
fi
if ! command -v ruff &>/dev/null || ! command -v jq &>/dev/null; then
  echo "SKIP: ruff or jq not installed"
  exit 0
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# Same unformatted content in both files; only edited.py is "edited".
UNFORMATTED='x = (  1,2 )
'
printf '%s' "$UNFORMATTED" > "$TMP/edited.py"
printf '%s' "$UNFORMATTED" > "$TMP/bystander.py"

jq -n --arg f "$TMP/edited.py" '{tool_input: {file_path: $f}}' \
  | CLAUDE_PROJECT_DIR="$TMP" "$HOOK" >/dev/null 2>&1

if [ "$(cat "$TMP/bystander.py")" != "$(printf '%s' "$UNFORMATTED")" ]; then
  printf "${RED}FAIL${NC}: formatter rewrote a file that was not edited\n"
  exit 1
fi
printf "${GREEN}PASS${NC}: only the edited file is formatted\n"
exit 0
