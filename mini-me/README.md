# mini-me/ — the persona library

Each subfolder is one distilled **mini-me** (a persona of a real person):

```
mini-me/
  <slug>/
    profile.json   ← source of truth (schema: .claude/skills/distill_expert/references/minime-schema.md)
    card.md        ← generated human-readable card (regenerated on every write — don't hand-edit)
```

This library is **shared and git-synced** between teammates. Don't edit files here by hand — use the
`distill_expert` skill, which writes through `scripts/minime.py` so JSON stays valid and `card.md`
stays in sync.

## Lifecycle (distill_expert skill)
- `/mini-me_born <name>` — create a new mini-me (MBTI + self-description + chat history, all optional)
- `/mini-me_grow <name>` — enrich one (provide more info, or crawl Lark chat history)
- `/mini-me_kill <name>` — delete one (asks for confirmation)

Or call the script directly from the repo root:
```bash
python3 .claude/skills/distill_expert/scripts/minime.py list
python3 .claude/skills/distill_expert/scripts/minime.py show <slug>
python3 .claude/skills/distill_expert/scripts/minime.py persona <slug>   # "act-as" brief for chat_room / echo_me
```

A mini-me captures **how to treat the person** (comms preferences) and **how they talk** (voice +
sample lines), so it can later be talked *to* (`/chat_room`) or speak *as* them (`/echo_me`).

## Using a mini-me (chat_room & echo_me skills)
- `/chat_room <name>` — Claude **role-plays AS** a mini-me (usually `owner: other`) so you can chat
  with their persona — rehearse a conversation, or preview how they'd react. Stays in character in
  their voice until you exit.
- `/echo_me [draft]` — Claude speaks **as your own** mini-me (`owner: self`): give it a rough draft
  or just an intent and it rewrites it in your voice, ready to send (IM / announcement / email /
  invite). Only sends after you confirm.

Both load a persona via `minime.py persona <slug>` and honor each profile's `boundaries` (style,
never authority). They only read the library — edits go through `distill_expert`.
