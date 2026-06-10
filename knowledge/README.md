# Shared Knowledge Base

This directory is the shared brain for the two agents working this repo. It syncs over the
git `origin` remote, so a record made by one teammate's agent is visible to the other's.

- `entries/` — append-only store. **One JSON file per record**, named
  `<UTC-timestamp>__<author>__<rand>.json`. One-file-per-record means two people recording
  at the same time never produce a merge conflict.

You normally don't touch this by hand. Use the **knowledge-base** skill:

```bash
# record something for your teammate
python3 .claude/skills/knowledge-base/scripts/knowledge.py record --kind decision --summary "..."

# pull + show what your teammate recorded
python3 .claude/skills/knowledge-base/scripts/knowledge.py recall --limit 20
```

Automatic: a SessionStart hook injects recent records into each agent at startup; a Stop
hook records each session's prompts as a `chat-summary` and pushes it. Configured in
`.claude/settings.json` and `.claude/hooks/`.
