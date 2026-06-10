---
name: echo_me
description: Speak/write AS the user's own mini-me — take a rough draft, bullet points, or just an intent and rewrite it in the user's distilled voice, ready to send. Covers IM messages, announcements, emails, and calendar invites; can tailor to a recipient and an occasion. Use when asked to "/echo_me", "say this in my voice", "rewrite this as me", "echo me", "make this sound like me", "draft an announcement as me", "word this the way I would", or "send X on my behalf". Rewrites in style only, never invents commitments — defaults to an owner:self mini-me. Only actually sends after explicit confirmation.
---

# echo_me — speak *as* yourself, in your voice

Take whatever the user wants to say — a rough draft, a few bullets, or just an intent — and render it
in **their own** distilled voice, polished and ready to send. This is the "rewrite as me" demo: same
message, but it sounds like *them*. Optionally tailor it to who it's going to and the occasion, then
(only on confirmation) send it through the right Lark channel.

The user's voice comes from their `owner: self` **mini-me** in the shared library, created by the
**distill_expert** skill (`/mini-me_born <you> --owner self`). This skill only *reads* personas.

## Golden rules
- **Rewrite the wording, never the meaning.** Match voice; don't add commitments, dates, numbers,
  names, or claims the user didn't give. If a draft is vague, ask rather than invent. Honor the
  persona's `boundaries`.
- **It's the user's voice, first person.** Output is the message itself — not "here's a version
  where you…". Show the draft cleanly so it's copy/paste- or send-ready.
- **Sending is outward-facing.** Produce the draft first and show it. Only send via a Lark skill after
  the user explicitly approves *this* text and *this* target. Approval of one send doesn't authorize
  the next.
- **One voice, the user's own.** echo_me speaks as *you*. To role-play someone *else*, that's
  `/chat_room`.

## Flow

1. **Pick the speaker (whose voice).**
   - Default to the user's `owner: self` mini-me. Find candidates with
     `python3 .claude/skills/distill_expert/scripts/minime.py list`.
   - If exactly one `self` mini-me exists, use it. If several (or none clearly the user's), ask — or
     if the user named one, use that. No self mini-me yet? Offer to `/mini-me_born <you> --owner self`
     first (echo_me needs a voice to echo).

2. **Load the persona brief:**
   ```bash
   python3 .claude/skills/distill_expert/scripts/minime.py persona <slug>
   ```
   This is the voice you'll write in — dials, sample lines, boundaries. If status isn't `ready`, the
   echo will be rougher; say so and lean on the samples that exist.

3. **Get the raw input.** What do they want to say? Accept a rough draft, bullets, or a one-line
   intent ("tell the team standup moves to 10am"). If it's genuinely empty, ask for the gist.

4. **Apply the modifiers (optional).**
   - **occasion** — adjusts register while keeping the voice:
     - `personal chat` — casual, warm, quirks on.
     - `formal sync` / `announcement` — tighter and clearer, decisions/asks up front, but still
       recognizably them.
   - **to_whom** — if there's a recipient and they *also* have a mini-me (`owner: other`), peek at
     their card (`minime.py show <their-slug>`) and tailor *how you pitch it* to how they like to be
     reached (e.g. lead with the verdict for a direct thinker, vision-first for an N) — without
     changing the speaker's voice. This is the "your voice, their wavelength" move.

5. **Produce the echo.** Rewrite the input in the speaker's voice: their tone, length (`verbosity`),
   emoji rate, formality/warmth, language mix, greetings/sign-offs, catchphrases, quirks. Keep it the
   length and shape they'd actually send. Present it in a clear block, e.g.:
   ```
   📣 echo_me — as **Aria Ruan**, occasion: announcement → #team

   heyy team!! quick one — standup's moving to 10am starting tomorrow ⏰ same link, just an hour later. lmk if that clashes for anyone 🙌
   ```
   If useful for a demo, offer 1–2 alternates (e.g. shorter / warmer).

6. **Offer to send (confirm first).** Ask if they want it sent, and route by channel — only after an
   explicit yes on the exact text + destination:
   - IM message / group announcement → **lark-im** skill.
   - Email → **lark-mail** skill (compose/draft; default to a draft unless told to send).
   - Calendar invite → **lark-calendar** skill.
   Prefer creating a **draft** when the skill supports it, so the user gets a last look. If they just
   wanted the wording, stop after step 5 — don't push to send.

## Notes
- echo_me ≠ chat_room: this one is *you* talking (owner:self); chat_room is role-playing *someone
  else* (owner:other).
- To improve how your echo sounds, add more real samples with `/mini-me_grow <you>` — the more
  samples on file, the closer the echo.
