#!/usr/bin/env bash
# PostToolUse hook: Run quick quality checks after file edits
# Detects project type and runs appropriate linter/typecheck

set -euo pipefail

if ! command -v jq &>/dev/null; then
  exit 0
fi

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

PROJECT_DIR=$(dirname "$FILE_PATH")
# Walk up to find project root (max 10 levels)
for _ in $(seq 1 10); do
  if [ -f "$PROJECT_DIR/package.json" ] || [ -f "$PROJECT_DIR/Cargo.toml" ] || [ -f "$PROJECT_DIR/go.mod" ] || [ -f "$PROJECT_DIR/pyproject.toml" ]; then
    break
  fi
  PARENT=$(dirname "$PROJECT_DIR")
  if [ "$PARENT" = "$PROJECT_DIR" ]; then
    exit 0
  fi
  PROJECT_DIR="$PARENT"
done

cd "$PROJECT_DIR" 2>/dev/null || exit 0

# Run quick checks based on project type (non-blocking, async-friendly)
case "$FILE_PATH" in
  *.ts|*.tsx)
    if [ -f "tsconfig.json" ] && command -v npx &>/dev/null; then
      npx tsc --noEmit --pretty false 2>&1 | head -20 || true
    fi
    ;;
  *.rs)
    if [ -f "Cargo.toml" ] && command -v cargo &>/dev/null; then
      cargo check --message-format=short 2>&1 | head -20 || true
    fi
    ;;
esac
