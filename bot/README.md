# Mini-Me — Lark bot (Usage 1: polish in your voice)

Polish your messages **in your own (or any) mini-me's voice**, right inside a Lark conversation —
and role-play *to* someone's mini-me to rehearse. The rewrite is driven by the distilled persona
in `../mini-me/<slug>/profile.json` (managed by the `distill_expert` skill), not hardcoded rules.

## Setup

```bash
# 1) log in as yourself (needed to send/recall AS you in real Lark)
lark-cli auth login

# 2) a voice engine — either is fine (no API key needed if the claude CLI is present)
#    - the `claude` CLI (uses your Claude Code auth), or
#    - export ANTHROPIC_API_KEY=...   (or put it in bot/.env)

# 3) mini-me's live in ../mini-me/  (create with the distill_expert skill: /mini-me_born …)
```

## Launch (pick a mode)

```bash
cd bot
python3 mini_me_bot.py repl                         # local text window — demo, no Lark wiring
python3 mini_me_bot.py lark  --live                 # chats the bot is in (DM it, or @mention in a group)
python3 mini_me_bot.py poll  --watch "Bob" --live   # a real 1:1 with a teammate (your user token)
```

| Option | Meaning |
|--------|---------|
| `--as-me <slug>` | default voice for the session (default `lucia`) |
| `--live` | actually recall/send; **omit for dry-run** (prints the `lark-cli` calls, sends nothing) |
| `--watch <name>` | poll mode: a teammate whose 1:1 to watch (repeatable) |
| `--interval <sec>` | poll mode: seconds between polls (default 4) |

Voice engine priority: `ANTHROPIC_API_KEY` → `claude` CLI → a minimal non-canned fallback.

---

## 1 · Polish — write a message *as* a mini-me

Type in the conversation, prefixed with the marker `..`. Modifiers are **order-free**:

| You type | Effect |
|----------|--------|
| `.. <draft>` | polish in the **default** voice; occasion inferred (p2p → personal, group → announcement) |
| `..<occasion> <draft>` | occasion ∈ `casual` · `announcement` · `formal` · `humorous` |
| `..as:<slug> <draft>` | **dynamic sender** — write as that mini-me (e.g. `..as:yunfei 明天同步`) |
| `..as:<slug> <occasion> <draft>` | combine, any order (`..formal as:lucia let's sync`) |
| `@Lucia-www ..[mods] <draft>` | same, inside a group (a bot only sees messages that @mention it) |

Then Mini-Me shows a **private preview** in your bot DM. Reply:

| Reply | Effect |
|-------|--------|
| `y` | recall your raw draft and send the polished version **as you** |
| `edit: <note>` | revise (keeps the same voice) |
| `n` | keep your original, send nothing |

Example — as Lucia → Yunfei, `..as:lucia can u review my PR when free` →
`Hey Yunfei! When you get a sec, could you take a look at my PR? No rush 🙂`

---

## 2 · Chat room — talk *to* a mini-me (rehearse / role-play)

| You type | Effect |
|----------|--------|
| `/chat_room <name>` | start a session; the bot replies **in that person's voice** |
| `/chat_room <name> <occasion>` | start with a register (e.g. `/chat_room yunfei formal`) |
| *(just type)* | converse; each reply stays in character |
| `exit` · `stop` · `end` · `quit` | leave, back to normal |

> **polish vs chat_room:** `..` speaks **as you** into the real conversation; `/chat_room`
> lets you **talk to someone else's** mini-me to rehearse — it never sends as the real person.

---

## Mini-me library

Current personas live in `../mini-me/<slug>/` (e.g. `lucia`, `yunfei`, `demo-friend`).
Manage them with the `distill_expert` skill: `/mini-me_born`, `/mini-me_grow`, `/mini-me_kill`.

## Notes & limits

- **Modes & visibility:** `lark` mode only sees chats the bot is a member of (DM it, or a group
  where you `@mention` it). For a true 1:1 with someone else, use `poll` mode.
- **Scopes (real Lark):** sending/recalling as you needs `im:message.send_as_user`; `poll` mode
  also needs `contact:user:search` + `im:message.p2p_msg:get_as_user`. These must be enabled on
  the app, then `lark-cli auth login --scope "…"`. Without them, sends fall back to "as the bot".
- **Files:** `mini_me_bot.py` (Lark I/O + UX), `polish.py` (persona-driven rewrite + engines),
  `profiles.py` (reads the mini-me library), `chatroom.py` (role-play sessions).
