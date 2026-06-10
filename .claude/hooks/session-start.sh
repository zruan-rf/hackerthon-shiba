#!/usr/bin/env sh
# SessionStart hook: pull the teammate's latest records and inject them into context,
# so this agent starts already knowing what the other person's agent did.
# stdout from a SessionStart hook is added to the session context.
ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -z "$ROOT" ] && ROOT="$(pwd)"
SCRIPT="$ROOT/.claude/skills/knowledge-base/scripts/knowledge.py"
[ -f "$SCRIPT" ] || exit 0
echo "===== SHARED KNOWLEDGE (from your teammate's agent) ====="
python3 "$SCRIPT" recall --limit 15 2>/dev/null
echo "========================================================"
exit 0
