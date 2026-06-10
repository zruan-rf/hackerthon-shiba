#!/usr/bin/env sh
# Stop hook: when this agent finishes a turn, capture the session's chat history as a
# shared record and push it, so the teammate's agent can pick it up. Best-effort, never
# blocks. The hook receives JSON on stdin including "transcript_path".
ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -z "$ROOT" ] && ROOT="$(pwd)"
SCRIPT="$ROOT/.claude/skills/knowledge-base/scripts/knowledge.py"
[ -f "$SCRIPT" ] || exit 0

INPUT="$(cat)"
TRANSCRIPT="$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try:
    print(json.load(sys.stdin).get("transcript_path",""))
except Exception:
    print("")' 2>/dev/null)"

[ -z "$TRANSCRIPT" ] && exit 0
[ -f "$TRANSCRIPT" ] || exit 0

# Run detached so the agent never waits on git network I/O.
nohup python3 "$SCRIPT" record-session --transcript "$TRANSCRIPT" \
  >> "$ROOT/.claude/hooks/knowledge-sync.log" 2>&1 < /dev/null &
exit 0
