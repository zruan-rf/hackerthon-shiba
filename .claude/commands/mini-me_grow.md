---
description: Grow an existing mini-me — enrich it by providing more info or crawling Lark chat history.
argument-hint: <name>
---

Use the **distill_expert** skill in **GROW** mode (edit) to enrich an existing mini-me.

Target mini-me: **$ARGUMENTS**

If no name was given, run `scripts/minime.py list` and ask which one. Then `show <slug> --json` to
see what's there, and grow it via either input mode: **provide** (user gives more info/corrections)
or **crawl** (pull the user↔target DM history from Lark via `lark-contact` →
`lark-im +chat-messages-list --user-id <open_id>` and add the target's lines as voice samples).
Persist with `set` / `add-sample`, then report the new status and what changed.
