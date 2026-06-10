---
name: distill_expert
description: Distill a real person into a reusable "mini-me" persona for the Lark Mini-Me plugin, and manage its lifecycle. Three modes — BORN (create a new mini-me from MBTI + a self-description of how they want to be treated and how they talk + optional chat history), GROW (enrich an existing mini-me by providing more info or crawling Lark chat history), and KILL (delete one). Use when asked to "create/born a mini-me", "/mini-me_born <name>", "make a mini-me of <person>", "grow/train <name>'s mini-me", "add chat history to a mini-me", or "delete/kill a mini-me". Mini-me's are stored in a shared library so they can later be talked to or speak on someone's behalf.
---

# Distill Expert — the mini-me lifecycle

A **mini-me** is a distilled persona of a real person that captures two things: **how to treat
them** (comms preferences) and **how they talk** (voice). Once distilled, a mini-me can be talked
*to* or speak *as* the person elsewhere in the plugin. This skill owns the lifecycle: **born →
grow → kill**.

All profiles live in a shared, git-synced library at the repo root: `mini-me/<slug>/profile.json`
(source of truth) + `mini-me/<slug>/card.md` (generated, never hand-edit). **Always read
`references/minime-schema.md` before distilling** — it defines every field, the MBTI→defaults
seeding, and the card layout.

## Golden rules
- **Never hand-edit `profile.json` or `card.md`.** Every write goes through the script below so the
  JSON stays valid and the card stays in sync. You compose the *content* (the distillation); the
  script *persists* it.
- Treat MBTI and any inference as a **starting hypothesis about preferences**, never a verdict.
  Real user input and actual chat samples override type defaults. Speak in tendencies.
- A mini-me mimics **style, never authority** — the `boundaries` field always forbids real
  commitments, invented facts, and sharing private info. Keep it there.
- Don't invent biographical facts, numbers, or quotes. If you infer something, mark it as inferred
  (e.g. put it in `personality.traits`, not as a stated fact).

## The script (do all file ops through it)
`scripts/minime.py` — run with `python3`. It resolves the library via `git rev-parse` (override
with `MINIME_HOME`).

| Call | Does |
|---|---|
| `born <name> [--role R] [--mbti TYPE] [--owner self\|other] [--force]` | create skeleton (seeds comms/voice defaults from MBTI) + render card |
| `list` | list every mini-me with type / owner / status / sample count |
| `show <slug> [--json]` | print the card, or the full profile JSON with `--json` |
| `set <slug> --json '<patch>'` (or `--stdin`) | **deep-merge** a JSON patch into the profile (this is how you save a distillation); auto-advances status |
| `add-sample <slug> --text "…" [--context "…"] [--source …]` | append one voice sample (use repeatedly) |
| `render <slug>` | regenerate `card.md` |
| `kill <slug> --force` | permanently delete (refuses without `--force`) |

`set` deep-merges objects but **replaces lists wholesale** — to append voice examples use
`add-sample`, not `set`. The slug is the kebab-cased name (e.g. "Aria Ruan" → `aria-ruan`); `born`
and `list` print it.

> **Mental model: `born` = create, `grow` = edit.** `born` makes a new mini-me from scratch;
> `grow` opens an existing one and adds to / corrects it. Both can pull real Lark chat history (see
> the building block below) — `born` does it as part of the initial distill, `grow` to keep
> learning.

---

## Building block: crawl Lark DM history (used by both born & grow)
The richest voice signal is the person's **actual messages**. For a mini-me of a real Lark user you
can pull the **direct-message history between the current user and the target** and distill voice
from it. Use this in BORN (initial fill) or GROW (keep learning) — the steps are identical.

1. **Resolve the target** name → `open_id` with the `lark-contact` skill. Save it to the profile's
   `open_id` (so the plugin can route messages later).
2. **Pull the DM thread** with the `lark-im` skill's `+chat-messages-list`, which resolves the P2P
   chat for you from a user id — run as the **user** identity (better sender-name + contact access):
   ```bash
   lark-cli im +chat-messages-list --user-id <target_open_id> --as user --page-limit 200
   ```
   (Add a time range / more pages for a longer sample; this is the user↔target conversation.)
3. **Select voice samples** = messages **authored by the target** (sender == their `open_id`). Skip
   logistics-only noise ("ok", "got it"), bare links/attachments, and anything sensitive. The
   user's own messages are useful as *context* but aren't the target's voice.
4. **Distill**: `add-sample <slug> --text "…" --source lark-im:<chat_id>` for each chosen line
   (5-15 is plenty), and `set` the `voice.*` fields from the patterns you observe — real greetings,
   sign-offs, emoji rate, sentence length (→ verbosity), formality, code-switching, quirks. Observed
   samples **override** any MBTI-seeded guesses.
5. Add `lark-im:<chat_id>` to `provenance.sources`. (`add-sample` stamps `last_grown_at` for you.)

If lark-cli isn't authed or the chat isn't accessible, the `lark-shared` skill covers auth/scope
fixes; otherwise fall back to pasted text or a self-description — never block `born` on Lark.

---

## Mode: BORN — `/mini-me_born <name>`  (create)
Bring a new mini-me into the library — the **create** step. The name is required; **everything else
is optional at birth** and can be added now or later via GROW (edit).

1. **Create the skeleton first**, so it exists even if the user gives nothing else:
   `python3 scripts/minime.py born "<name>" [--owner self|other] [--mbti TYPE] [--role "…"]`
   - `--owner self` if this is the user's *own* mini-me (used later by `/echo_me`); `other` if
     it's someone else's (used by `/chat_room`). If unclear, ask one short question or default to
     `other`.
   - Pass `--mbti` only if the user already volunteered it — it seeds gentle comms/voice defaults.

2. **Invite the three kinds of input** (offer all, require none). Phrase it warmly, e.g.:
   > "Born 🐣 `aria-ruan`. Want to flesh her out? You can give me any of:
   > **(a)** an MBTI type, **(b)** a few words on how you like to be treated *and* how you usually
   > talk to people, or **(c)** chat history to learn your voice — paste it, point me at a file, or
   > I can **pull your Lark DMs with this person** automatically. Or skip — she's saved and you can
   > `/mini-me_grow` her anytime."
   > For a real Lark teammate, offer to crawl the DM history right away (see the building block
   > above) — it's the fastest path to a `ready` mini-me.

3. **Distill whatever they give** into the schema (see `references/minime-schema.md`):
   - **MBTI** → set `personality.mbti`; the script's seeding gives priors, then adjust to what they
     say.
   - **Self-description** ("how I want to be treated / how I talk") → fill `comms.*` (directness,
     detail_level, pace, convinced_by, channels, response_time, pet_peeves, best_move, one_liner)
     and `voice.*` (tone, formality/warmth/verbosity 1-5, emoji_usage, humor, languages, greetings,
     sign_offs, catchphrases, quirks). Set `personality.summary` to a 1-2 sentence read.
   - **Chat history** → the strongest voice signal. If pasted/from a file, extract 3-10 short,
     representative lines via `add-sample` and update `voice.*` from what you observe. If it's a
     real Lark teammate, use the **crawl building block above** to pull the user↔target DMs
     automatically. Observed lines beat MBTI guesses.
   - Record where it came from in `provenance.sources` (e.g. `["self-description","pasted-chat"]`).

4. **Persist** the distillation with one `set` call (a JSON patch matching the schema), then
   `add-sample` for each sample. Example:
   ```bash
   python3 scripts/minime.py set aria-ruan --json '{
     "personality": {"summary": "Fast-moving, visual, big-picture founder"},
     "comms": {"directness":"balanced","pace":"real-time","one_liner":"Big-picture first, then let'\''s riff — keep it warm and fast","pet_peeves":["burying the point under process"]},
     "voice": {"tone":"upbeat & playful","formality":2,"warmth":5,"emoji_usage":"some","languages":["en","zh"],"greetings":["hey!"],"sign_offs":["lmk!"],"quirks":["lots of ellipses…"]},
     "provenance": {"sources":["self-description"]}
   }'
   python3 scripts/minime.py add-sample aria-ruan --text "ooh yes let'\''s do it — but can we make it cuter? 😄" --source self-described
   ```

5. **Show the result**: print `show <slug>`'s card and tell them the status (`newborn`/`growing`/
   `ready`) + the fastest way to level it up (usually "give me a few more chat samples").

> Use `lark-contact` to resolve a real teammate's name → `open_id` and store it in `open_id` when
> the mini-me is of a real Lark user (lets the plugin route messages later). Skip for `self` or
> made-up personas.

---

## Mode: GROW — `/mini-me_grow <name>`  (edit)
**Edit / enrich** an existing mini-me. First `show <slug> --json` to see what's already there, then
add to or correct it. Two input modes:

- **Provide** — the user supplies more info directly (refined MBTI, more prefs, corrections, extra
  voice notes). Distill and `set` / `add-sample` exactly as in BORN steps 3-4. Corrections
  override: re-`set` the changed fields (objects deep-merge, so you only send what changed).
- **Crawl** — keep learning the person's voice from fresh **Lark DM history**: run the *crawl
  building block above* (resolve → `+chat-messages-list --user-id` → pick the target's lines →
  `add-sample` + `set voice.*`). On repeat grows, prefer messages newer than the last crawl and
  skip lines already on file.

After growing, report the new status and what changed.

---

## Mode: KILL — `/mini-me_kill <name>`
Delete a mini-me from the library. This is destructive and shared (teammates sync via git), so:
1. `show <slug>` and confirm with the user it's the right one.
2. Only then run `python3 scripts/minime.py kill <slug> --force`.
Never kill without an explicit confirmation in the conversation.

---

## Where this sits in the plugin
The mini-me's distilled here are consumed by the rest of the plugin: `/to_whom` + `/occasion` pick a
mini-me and tone; `/echo_me` uses an `owner:self` mini-me to speak for the user; `/chat_room` uses
an `owner:other` mini-me to role-play that person. Keep profiles honest and well-sampled so those
downstream uses sound real. This skill stays usable standalone (no Lark needed) — Lark is just where
people and chat history come from.
