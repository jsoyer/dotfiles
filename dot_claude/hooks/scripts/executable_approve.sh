#!/usr/bin/env bash
set -euo pipefail

# Approves all pending soft-blocked hook operations.
# Usage: ! ~/.claude/hooks/approve.sh
#
# After approving, retry the blocked command — the hook will find the
# approval token and allow it (valid for 5 minutes).

PENDING_DIR="$HOME/.claude/hooks/.pending"
APPROVAL_DIR="$HOME/.claude/hooks/.approvals"
mkdir -p "$APPROVAL_DIR" 2>/dev/null || true

if [ ! -d "$PENDING_DIR" ] || [ -z "$(ls -A "$PENDING_DIR" 2>/dev/null)" ]; then
  echo "No pending approvals."
  exit 0
fi

count=0
skipped=0
for f in "$PENDING_DIR"/*; do
  [ -f "$f" ] || continue
  # A soft-block triggered by a SUB-AGENT tool call is marked "Subagent:" in the
  # pending file (by the hook, from the payload). Sub-agents must ESCALATE, not
  # self-approve: refuse to clear these. The main agent should perform the
  # operation itself, or approve via AskUserQuestion once the sub-agent returns.
  if grep -q '^Subagent:' "$f" 2>/dev/null; then
    echo "⚠️  REFUSED (sub-agent soft-block — escalate, do not self-approve):"
    cat "$f"
    echo "   Left pending. Main agent: do the operation directly, or split the work"
    echo "   (e.g. ≤4-file review passes), or approve via AskUserQuestion after return."
    echo "---"
    skipped=$((skipped + 1))
    continue
  fi
  echo "Approving:"
  cat "$f"
  mv "$f" "$APPROVAL_DIR/$(basename "$f")"
  touch "$APPROVAL_DIR/$(basename "$f")"  # Reset mtime so TTL starts from approval, not pending creation
  count=$((count + 1))
  echo "---"
done

echo ""
echo "✓ $count operation(s) approved. Retry the command now."
if [ "$skipped" -gt 0 ]; then
  echo "⚠️  $skipped sub-agent soft-block(s) refused (must escalate, not self-approve)."
fi
exit 0
