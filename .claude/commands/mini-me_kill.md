---
description: Kill a mini-me — permanently delete it from the shared library (asks for confirmation).
argument-hint: <name>
---

Use the **distill_expert** skill in **KILL** mode to delete a mini-me.

Target mini-me: **$ARGUMENTS**

If no name was given, run `scripts/minime.py list` and ask which one. Always `show <slug>` and get an
explicit confirmation in the conversation first — this is destructive and shared via git — then run
`scripts/minime.py kill <slug> --force`.
