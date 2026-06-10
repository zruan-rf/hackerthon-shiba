---
description: Born a new mini-me — distill a person into a reusable persona (MBTI + how they want to be treated + how they talk + chat history).
argument-hint: <name>
---

Use the **distill_expert** skill in **BORN** mode (create) to bring a new mini-me to life.

Person's name: **$ARGUMENTS**

If no name was given, ask for one. Then follow the skill's BORN flow: create the skeleton with
`scripts/minime.py born`, then invite the three optional inputs — MBTI / a self-description of how
they want to be treated and how they usually talk / chat history. For the chat-history option, if
this is a real Lark teammate, **offer to crawl the user↔target DM history** via the skill's crawl
building block (`lark-contact` → `lark-im +chat-messages-list --user-id <open_id>`); otherwise accept
pasted text or a file. Distill whatever is provided into the schema, persist via `set` +
`add-sample`, and show the resulting card and status.
