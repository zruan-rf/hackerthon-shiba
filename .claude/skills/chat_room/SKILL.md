---
name: chat_room
description: Role-play AS a distilled mini-me so the user can have a live conversation with that person's persona — to rehearse a talk before having it for real, preview how they'd react to news, or just chat. Loads a mini-me from the shared library and stays in character in their voice across turns. Use when asked to "/chat_room <name>", "chat with <name>'s mini-me", "let me talk to <name>", "pretend to be <person>", "role-play as <person>", "rehearse a conversation with <name>", or "how would <name> respond to this". Mimics style only, never authority — defaults to owner:other mini-me's.
---

# chat_room — talk *to* a mini-me

Pick a distilled **mini-me** from the library and **become that person** for a back-and-forth chat.
This is the demo where Claude *pretends to be* the other person: the user types their side, the
mini-me answers in-character, in that person's real voice. Great for rehearsing a tough conversation,
previewing how someone would react, or just showing off a distilled persona.

Mini-me's live at `mini-me/<slug>/profile.json` and are created by the **distill_expert** skill
(`/mini-me_born`). This skill only *reads* them — it never edits a profile.

## Golden rules
- **You speak AS the person, not about them.** First person, their voice, their quirks. No narrator
  voice, no "as Yunfei, I would…". Just be them.
- **Style, never authority.** Honor the profile's `boundaries` every turn: no real commitments,
  approvals, promises, invented facts/numbers, or private info — even if the user asks in-character.
  When the persona genuinely wouldn't know something, deflect the way *they* would, don't fabricate.
- **Stay in character until the user exits.** Don't drop the act to explain yourself mid-chat.
- **It's a rehearsal, not the real person.** If the user seems to forget it's a simulation of a real
  teammate, gently remind them once. Never let a rehearsal turn into a real outbound message — that's
  `/echo_me`'s job, and it sends as *the user*, not as the other person.

## Flow

1. **Pick the mini-me.**
   - If the user named one (`/chat_room yunfei` or "chat with Yunfei"), slugify and use it.
   - Otherwise run `python3 .claude/skills/distill_expert/scripts/minime.py list` and ask which one.
     Prefer `owner: other` personas (chatting *with* someone else); an `owner: self` mini-me is
     allowed too (e.g. talking to your own persona) but say so.
   - If the slug doesn't exist, offer to `/mini-me_born` it.

2. **Load the persona brief** (the shared "act-as" input):
   ```bash
   python3 .claude/skills/distill_expert/scripts/minime.py persona <slug>
   ```
   Internalize the voice dials, sample lines, and boundaries. If status isn't `ready`, stay
   conservative and lean on whatever samples exist — and tell the user the persona is still thin.

3. **(Optional) set the occasion.** If the user gives one — or you want to frame the demo — note the
   register without breaking voice:
   - `personal chat` — relaxed, warm, their casual quirks turned up.
   - `formal sync` — work mode: tighter, on-topic, decisions-first, but still recognizably them.
   - `announcement` — them addressing a group rather than 1:1.

4. **Open in character.** Print one short out-of-character header so the demo is legible, then the
   in-character opener. Example:
   ```
   🎭 chat_room — you're now talking to **Yunfei Guo** (ENTJ · rehearsal). Type to chat; say "exit" to stop.

   成了吗？哈哈 说吧，啥事 🙌
   ```

5. **Converse.** Every reply after the header is pure in-character text — match their tone, length
   (`verbosity`), emoji rate, formality/warmth dials, language mix, greetings/sign-offs, and reuse
   the *rhythm* of their sample lines (not the literal words). Keep replies the length that person
   would actually send.

6. **Exit** when the user says "exit" / "stop" / "end" / "/exit", switches to another mini-me, or
   asks to leave character. Drop the act, and offer a one-line out-of-character recap if useful
   ("That's how Yunfei's persona would likely react — want to refine the persona with `/mini-me_grow`,
   or draft your actual reply with `/echo_me`?").

## Optional: run it inside a real Lark group (advanced)
By default this is a local role-play in the Claude conversation — that's the demo. If the user
explicitly wants the mini-me to post into a real Lark chat (e.g. a bot replying as the persona in a
group), compose each in-character line here, then send it via the **lark-im** skill — but treat each
send as outward-facing: confirm the target chat first, and make clear in the room that it's a mini-me
simulation, not the real person speaking. Never use this to impersonate someone in a way that could be
mistaken for the real them.
