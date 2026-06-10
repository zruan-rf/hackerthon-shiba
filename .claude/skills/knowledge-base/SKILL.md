---
name: knowledge-base
description: Shared realtime knowledge base + chat history for two teammates working this repo. Use to RECORD a decision/fact/todo/note so the OTHER person's agent can see it, or to RECALL what the teammate's agent has recorded. Records sync through the git remote (one file per record, conflict-free) and are auto-injected at session start. Use when asked to "remember/record/note this for my teammate", "what did the other person do", "sync our knowledge", or "save this to shared knowledge".
allowed-tools: Bash
---

# Shared Knowledge Base (two-agent sync)

Two people work this repo with separate Claude agents. This skill is the shared brain:
anything one agent records, the other's agent reads. Sync runs over the git remote both
already clone — each record is its own timestamp-named file under `knowledge/entries/`, so
two people writing at once never conflict. Records are committed (path-scoped, so your other
work is untouched) and pushed immediately.

Helper: `python3 .claude/skills/knowledge-base/scripts/knowledge.py`

## Record something for the teammate
```bash
python3 .claude/skills/knowledge-base/scripts/knowledge.py record \
  --kind decision \
  --summary "Chose Lark Base over Postgres for profile storage" \
  --detail "Realtime + already authed; revisit if we need SQL joins." \
  --refs ".claude/skills/mbti-communication/SKILL.md"
```
`--kind` is one of: `decision`, `fact`, `todo`, `note`. Keep `--summary` to one line
(this is what shows up in the teammate's context); put context in `--detail`.

## Recall what's been shared (pulls the teammate's latest first)
```bash
python3 .claude/skills/knowledge-base/scripts/knowledge.py recall --limit 20
```
This fetches the remote, then prints the most recent records from both people. Run it
any time mid-session to pull in what your teammate just did.

## Automatic behavior (no action needed)
- **Session start** (`.claude/hooks/session-start.sh`) pulls + injects the latest shared
  records into this agent's context, so you begin already knowing the teammate's state.
- **Session stop** (`.claude/hooks/stop.sh`) captures this session's prompts as a
  `chat-summary` record and pushes it, so the teammate can see what you worked on.

## Notes
- All git ops are best-effort: offline → record saved locally, syncs on next push/recall.
- For curated knowledge, prefer an explicit `record` with a clear summary over relying only
  on the auto chat-summary. Use `decision`/`fact` for things that should outlive the session.
- Both teammates must have the repo cloned with the same `origin` remote and push access.
