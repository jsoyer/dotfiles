#!/usr/bin/env bash
# PostToolUse hook: Check for console.log/print statements in modified files
# Outputs a warning message if debug statements are found

set -euo pipefail

# Only run in git repos
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
  exit 0
fi

# Get modified files (staged + unstaged)
modified_files=$(git diff --name-only HEAD 2>/dev/null || git diff --name-only 2>/dev/null || true)

if [ -z "$modified_files" ]; then
  exit 0
fi

warnings=""

while IFS= read -r file; do
  [ -f "$file" ] || continue

  case "$file" in
    *.ts|*.tsx|*.js|*.jsx)
      matches=$(grep -n 'console\.\(log\|debug\|warn\|error\)' "$file" 2>/dev/null | head -5 || true)
      ;;
    *.py)
      matches=$(grep -n '^\s*print(' "$file" 2>/dev/null | head -5 || true)
      ;;
    *.rs)
      matches=$(grep -n '\(println!\|dbg!\|eprintln!\)' "$file" 2>/dev/null | head -5 || true)
      ;;
    *.go)
      matches=$(grep -n 'fmt\.Print' "$file" 2>/dev/null | head -5 || true)
      ;;
    *)
      continue
      ;;
  esac

  if [ -n "$matches" ]; then
    warnings="${warnings}${file}:\n${matches}\n\n"
  fi
done <<< "$modified_files"

if [ -n "$warnings" ]; then
  echo "WARNING: Debug statements found in modified files:"
  echo ""
  echo -e "$warnings"
  echo "Consider removing before commit."
fi
