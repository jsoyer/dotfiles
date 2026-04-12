#!/usr/bin/env bash
set -euo pipefail
trap 'echo "HOOK CRASH: $0 line $LINENO" >&2; exit 2' ERR

# PostToolUse(Write|Edit) hook: Auto-format code after edits.
#
# Language-universal — auto-detects the file's language and runs the
# appropriate formatter/linter. Supports all major languages out of the box.
#
# To add a new language: update detect_formatter() in lib/detect-project.sh.
#
# Exit codes:
#   0 — formatted successfully (or skipped)
#   2 — formatter found unfixable errors

# Check for jq — exit silently if missing (auto-formatting is non-critical)
if ! command -v jq &>/dev/null; then
  exit 0
fi

# Read JSON input from stdin
INPUT=$(cat)

# Extract file_path from tool_input
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // empty')

# Skip if file_path is empty or null
if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Source shared detection library
source ~/.claude/hooks/lib/detect-project.sh

# Skip non-code files
if ! is_code_file "$FILE_PATH"; then
  exit 0
fi

# Skip generated/vendor directories
if is_generated_path "$FILE_PATH"; then
  exit 0
fi

# Resolve project directory
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Make file_path absolute if relative
if [[ "$FILE_PATH" != /* ]]; then
  FILE_PATH="$PROJECT_DIR/$FILE_PATH"
fi

# Check if file exists
if [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

# Detect formatter for this file
detect_formatter "$FILE_PATH" "$PROJECT_DIR"

if [ -z "$FORMATTER_CMD" ]; then
  exit 0
fi

# Run the formatter
# The FORMATTER_CMD may contain $FILE as a placeholder; if not, append the file path
if [[ "$FORMATTER_CMD" == *'$FILE'* ]]; then
  FILE="$FILE_PATH"
  export FILE
  OUTPUT=$(cd "$PROJECT_DIR" && eval "$FORMATTER_CMD" 2>&1) || {
    EXIT_CODE=$?
    echo "$OUTPUT" | head -n 10 >&2
    exit 2
  }
else
  OUTPUT=$(cd "$PROJECT_DIR" && eval "$FORMATTER_CMD" '"$FILE_PATH"' 2>&1) || {
    EXIT_CODE=$?
    echo "$OUTPUT" | head -n 10 >&2
    exit 2
  }
fi

# === console.log detection for JS/TS files ===
# PostToolUse: warn (don't block) — just print to stdout so Claude sees it.

EXT="${FILE_PATH##*.}"
case "$EXT" in
  ts|tsx|js|jsx)
    # Skip test files by filename pattern or directory
    BASENAME=$(basename "$FILE_PATH")
    IS_TEST_FILE=false
    case "$BASENAME" in
      *.test.*|*.spec.*) IS_TEST_FILE=true ;;
    esac
    case "$FILE_PATH" in
      */tests/*|*/__tests__/*|*/test/*|*/spec/*) IS_TEST_FILE=true ;;
    esac

    if [ "$IS_TEST_FILE" = "false" ] && [ -f "$FILE_PATH" ]; then
      # Count console.log( calls that are NOT eslint-disable-line no-console
      CONSOLE_COUNT=0
      while IFS= read -r line; do
        # Skip lines with eslint-disable no-console comment
        if echo "$line" | grep -q 'eslint-disable.*no-console'; then
          continue
        fi
        if echo "$line" | grep -qF 'console.log('; then
          CONSOLE_COUNT=$((CONSOLE_COUNT + 1))
        fi
      done < "$FILE_PATH"

      if [ "$CONSOLE_COUNT" -gt 0 ]; then
        printf '⚠ post-edit-quality: %d console.log call(s) detected in %s. Remove before committing (rule in CLAUDE.md Post-Implementation Checklist).\n' \
          "$CONSOLE_COUNT" "$FILE_PATH"
      fi
    fi
    ;;
esac

exit 0
