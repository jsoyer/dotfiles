#!/usr/bin/env bash
# PreToolUse hook: Protect config files from unintended modifications
# Reads JSON from stdin with tool_input.file_path
# Outputs JSON with "decision":"block" to prevent the edit

set -euo pipefail

if ! command -v jq &>/dev/null; then
  exit 0
fi

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

BASENAME=$(basename "$FILE_PATH")

# Protected config files
case "$BASENAME" in
  .eslintrc|.eslintrc.js|.eslintrc.json|.eslintrc.cjs|eslint.config.js|eslint.config.mjs|\
  .prettierrc|.prettierrc.js|.prettierrc.json|prettier.config.js|\
  tsconfig.json|tsconfig.*.json|\
  package-lock.json|yarn.lock|pnpm-lock.yaml|\
  .env|.env.local|.env.production)
    echo '{"decision":"block","reason":"Protected config file. Use explicit instructions to modify."}'
    ;;
esac
