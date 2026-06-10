# Mini-Me — Lark Plugin Design Notes

**Concept:** A Lark plugin that distills people's personalities into "mini-me" agents, which can then be used during chat — either to talk *to* that person's mini-me, or to have your own mini-me speak/act on your behalf.

---

## Project Structure

```
.
├── skill/          # distill_expert
│   ├── born
│   ├── grow        # (provide / crawl)
│   └── kill
├── mini-me/        # library of different mini-me's
├── src/
└── settings/
```

## Skill: `distill_expert`

Lifecycle commands for a mini-me:

| Command | Description |
|---------|-------------|
| `/born` | Create a new mini-me |
| `/grow` | Improve/train an existing mini-me |
| `/kill` | Delete a mini-me |

### `/grow` — two input modes

1. **Provide** — user supplies info directly, e.g. MBTI / personality traits (by user prompt)
2. **Crawl** — crawl chat history from Lark to learn the person's style

### Library

All distilled mini-me's are stored in a shared **library** for reuse.

---

## Plugin Interface

Context-setting commands when composing a message:

- `/to_whom` — select the target person (which mini-me to address / mimic)
- `/occasion` — select the tone/context:
  - `announcement`
  - `personal chat`
  - `formal sync`

## Bot Capabilities

- `/echo_me` — act as *your* mini-me:
  - send announcements
  - send calendar invitations
  - send emails
- `/chat_room` — mimic **the other person's** mini-me to chat (e.g. rehearse a conversation with them, or let their mini-me respond)

---

## Flow Summary

1. **Distill** — `/born` a mini-me, then `/grow` it via user-provided traits (MBTI) and/or crawled Lark chat history.
2. **Store** — mini-me's live in a library.
3. **Use** — in chat, pick `/to_whom` + `/occasion`, then either `/echo_me` (your mini-me acts for you) or `/chat_room` (chat with someone else's mini-me).

---

## Lark interface — implemented (`bot/`)

A small bot wires the skills into live Lark chat. All Lark I/O is `lark-cli`; the rewrite/
role-play brain is the model (`claude` CLI via Claude Code auth, or `ANTHROPIC_API_KEY`).

| File | Role |
|------|------|
| `bot/mini_me_bot.py` | message loop · routing · preview/confirm gate · sends via `lark-cli` |
| `bot/polish.py` | `polish(...)` + `complete(system,user)` — the shared model engine (echo_me/Usage 1 seam) |
| `bot/chatroom.py` | `/chat_room` role-play AS a mini-me, in-character, honoring `boundaries` |
| `bot/profiles.py` | reads `mini-me/<slug>/profile.json`, normalizes, applies occasion overrides |

**Run modes** (`python3 bot/mini_me_bot.py <mode>`):
- `repl` — local text window; demos polish **and** `/chat_room <name>` with no Lark wiring.
- `lark` — events for chats the bot is in (DM it, or `@mention` it in a group).
- `poll --watch <name>` — your user token watches a real 1:1 (bot not in the chat).

**`/chat_room <name>` in Lark** — start a session in any chat the bot sees; it replies
**in-character into that conversation**. `exit`/`stop` ends it. Reads the persona from the
shared library; never edits a profile; never sends as the real person (that's `/echo_me`).

> Note: the team's `distill_expert/scripts/minime.py` crashes on Python 3.9 (`str | None`
> without `from __future__ import annotations`). The bot reads profiles via its own
> `profiles.py`, so it's unaffected — but the `chat_room`/`distill_expert` *skills* need that
> one-line fix to run on 3.9.
