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
