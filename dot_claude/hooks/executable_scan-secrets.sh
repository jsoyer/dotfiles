#!/usr/bin/env bash
set -euo pipefail

# PostToolUse(Edit|Write) hook: Scan edited files for accidental secret exposure.
#
# Detects common secret patterns and BLOCKS (exit 2) if found.
# NEVER logs the secret value — only the line number and pattern name.
#
# Exit codes:
#   0 — no secrets found (or skipped file)
#   2 — secret detected (block the tool use)

# Fail-open on any internal crash — never block due to a pattern bug
trap 'echo "scan-secrets: internal error at line $LINENO — skipping scan" >&2; exit 0' ERR

# ─── Input parsing ───────────────────────────────────────────────────────────

INPUT=$(cat)

if command -v jq &>/dev/null; then
  FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null || true)
else
  if [[ "$INPUT" =~ \"file_path\":\"(([^\"\\]|\\.)*)\" ]]; then
    FILE_PATH="${BASH_REMATCH[1]}"
    FILE_PATH="${FILE_PATH//\\\"/\"}"
    FILE_PATH="${FILE_PATH//\\\\/\\}"
  else
    exit 0
  fi
fi

[ -z "${FILE_PATH:-}" ] && exit 0

# Resolve relative paths
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
if [[ "$FILE_PATH" != /* ]]; then
  FILE_PATH="$PROJECT_DIR/$FILE_PATH"
fi

# Must be a regular file
[ -f "$FILE_PATH" ] || exit 0

# ─── Skip conditions ─────────────────────────────────────────────────────────

BASENAME=$(basename "$FILE_PATH")

# Skip .env.example (intended to show key names, not real values)
case "$BASENAME" in
  .env.example|.env.sample|.env.template) exit 0 ;;
esac

# Skip test files
case "$BASENAME" in
  *.test.*|*.spec.*) exit 0 ;;
esac
case "$FILE_PATH" in
  */tests/*|*/__tests__/*|*/test/*|*/spec/*) exit 0 ;;
esac

# Skip markdown (likely documentation showing fake examples)
case "$BASENAME" in
  *.md|*.mdx|*.rst|*.txt) exit 0 ;;
esac

# Skip generated/vendor paths
case "$FILE_PATH" in
  */node_modules/*|*/.git/*|*/dist/*|*/build/*|*/.next/*|*/vendor/*) exit 0 ;;
esac

# Skip files listed in .gitignore (best-effort — only if git is available)
if command -v git &>/dev/null; then
  if git -C "$(dirname "$FILE_PATH")" check-ignore -q "$FILE_PATH" 2>/dev/null; then
    exit 0
  fi
fi

# ─── Pattern definitions ──────────────────────────────────────────────────────
# Format: "PATTERN_NAME:regex"
# Patterns use ERE (grep -E). NEVER print the matched value — only name + line.

SECRET_PATTERNS=(
  # Anthropic / OpenAI style API key (sk- prefix, 20+ alphanumeric)
  "Anthropic/OpenAI API key:sk-[A-Za-z0-9]{20,}"
  # Anthropic-specific token
  "Anthropic key (sk-ant):sk-ant-[A-Za-z0-9_-]{20,}"
  # AWS access key ID
  "AWS access key ID:AKIA[0-9A-Z]{16}"
  # GitHub Personal Access Token
  "GitHub PAT:ghp_[A-Za-z0-9]{30,}"
  # Slack token
  "Slack token:xox[baprs]-[A-Za-z0-9-]{10,}"
  # PEM private key header
  "Private key:-----BEGIN (RSA |EC |OPENSSH |DSA |)PRIVATE KEY-----"
  # Generic api_key = "value" or api-key: 'value' (16+ char value)
  "Generic API key:api[_-]?key[[:space:]]*[:=][[:space:]]*[\"'][^\"']{16,}[\"']"
)

# ─── Scan the file ────────────────────────────────────────────────────────────

FOUND_ANY=false
FINDINGS=()

for entry in "${SECRET_PATTERNS[@]}"; do
  PATTERN_NAME="${entry%%:*}"
  REGEX="${entry#*:}"

  # Find matching line numbers (no value output — just line numbers)
  # Use -- to prevent patterns starting with - from being parsed as grep options
  MATCHING_LINES=$(grep -En -- "$REGEX" "$FILE_PATH" 2>/dev/null | cut -d: -f1 | tr '\n' ',' | sed 's/,$//' || true)

  if [ -n "$MATCHING_LINES" ]; then
    FOUND_ANY=true
    FINDINGS+=("  line(s) $MATCHING_LINES — pattern: $PATTERN_NAME")
  fi
done

# ─── Report and block ─────────────────────────────────────────────────────────

if [ "$FOUND_ANY" = "true" ]; then
  # Log to alert file (no secret values)
  ALERT_LOG="${HOME}/.claude/state/secret-alerts.log"
  mkdir -p "$(dirname "$ALERT_LOG")" 2>/dev/null || true
  {
    printf '[%s] FILE: %s\n' "$(date -Iseconds 2>/dev/null || date)" "$FILE_PATH"
    for finding in "${FINDINGS[@]}"; do
      printf '  %s\n' "$finding"
    done
    printf '\n'
  } >> "$ALERT_LOG" 2>/dev/null || true

  # Print warning to stderr (never print the secret value)
  {
    printf '🚨 SECRETS DETECTED in %s:\n' "$FILE_PATH"
    for finding in "${FINDINGS[@]}"; do
      printf '%s\n' "$finding"
    done
    printf 'Action: remove the secrets, rotate them, and re-edit the file.\n'
    printf 'Alert logged to: %s\n' "$ALERT_LOG"
  } >&2

  exit 2
fi

exit 0
