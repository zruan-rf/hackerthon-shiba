---
description: Echo me — rewrite/compose a message in your own distilled voice, ready to send.
argument-hint: [draft or intent] [--to <name>] [--occasion announcement|personal|formal]
---

Use the **echo_me** skill to speak as the user's own mini-me.

Input: **$ARGUMENTS**

Pick the user's `owner: self` mini-me (find with `python3 .claude/skills/distill_expert/scripts/minime.py
list`; if exactly one, use it, else ask — no self mini-me yet means offer `/mini-me_born <you> --owner
self`). Load it with `minime.py persona <slug>`. Take the draft/intent above (ask for the gist if
empty), apply any `--to` recipient and `--occasion` register, and rewrite it in their voice — same
meaning, no invented commitments. Show the polished message in a clear block, then offer to send via
lark-im / lark-mail / lark-calendar **only after explicit confirmation** of the exact text and target
(prefer a draft when possible).
