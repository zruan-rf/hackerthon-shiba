---
name: mbti-communication
description: Smooth out communication hiccups between different MBTI / communication styles. Three modes - (1) DISTILL a person into a shareable "Comms Card" from their MBTI + a few prefs, (2) DECODE how to talk to someone given their card/type, (3) IMPROVE a draft message or email so it lands well with a specific recipient. Use when asked to "build my comms profile", "how should I message <person/type>", "rewrite this email for <recipient>", or "make this land better for an <MBTI type>". Core skill of the Lark communication plugin.
---

# MBTI Communication Coach

The product goal: people **distill themselves** into a small, shareable profile; teammates can
**look up how to reach them**; and anyone can **improve a message/email** before sending so it
lands across different personality + communication styles. This skill powers all three.

Treat MBTI as a *starting hypothesis about preferences*, never a verdict on ability or worth.
Personalization and observed behavior always override the type defaults. Avoid stereotyping and
clinical claims; speak in tendencies ("tends to", "usually prefers").

Read `references/dichotomies.md` for what each axis (E/I, S/N, T/F, J/P) implies for
communication, and `references/comms-card.md` for the Comms Card schema + an example.

---

## Mode 1 — DISTILL ("build my Comms Card")
Capture a person (usually the user) into a compact, shareable card. Ask only for what's missing:
- **MBTI type** (or run a 4-question lightweight check, one per axis, if they don't know it).
- **Name / role.**
- 3–6 quick prefs: directness (blunt ↔ diplomatic), detail level (headline ↔ deep-dive),
  pace (async ↔ real-time), evidence that convinces them (data / story / people-impact),
  preferred channel, response-time norms, and any **pet peeves** ("please don't…").

Output a **Comms Card** following `references/comms-card.md`: a friendly one-screen summary plus a
machine-readable JSON block (so it can be stored in Lark Base and reused). Keep it warm and human —
this is how a person introduces their wiring to teammates.

## Mode 2 — DECODE ("how do I communicate with <person>?")
Given a recipient's Comms Card (or just an MBTI type + whatever is known), produce a tight playbook:
1. **Read on them** — 2–3 sentences of likely preferences (tendencies, not rules).
2. **Do / Don't** — two short bullet lists tuned to this person + the situation.
3. **Structure** — opener → core → ask/close, with the right detail level, pace, and evidence type.
4. **Persuasion levers** — what moves them (logic/competence, vision, harmony, autonomy, efficiency,
   recognition), tied to T/F and N/S.
5. **Watch-outs** — what could backfire (surprising a J last-minute; over-detailing for an N;
   pushing an I to decide on the spot; cold efficiency with an F).

## Mode 3 — IMPROVE ("rewrite / tune this message for <recipient>")
The everyday workhorse. Inputs: the **draft** (message or email), the **recipient** (Comms Card or
type), optionally the **sender's** card and the **goal/tone/channel**.
Produce:
1. **Tuned rewrite** — ready to send, in the right channel + tone, restructured for the recipient.
2. **What changed & why** — 2–4 bullets mapping each edit to a preference ("led with the ask
   because J + time-pressed", "added the one data point an ISTJ will want", "warmed the opener for
   an F", "cut three paragraphs an N will skim").
3. *(If sender + recipient styles clash)* a one-line **bridge tip** for the relationship.
Preserve the sender's voice and all facts — improve *delivery*, don't fabricate content.

---

## Lark plugin integration (how this lives in the product)
- **Store cards** in a Lark Base table (one row per person: name, open_id, type, prefs, card JSON)
  via the `lark-base` skill. `references/comms-card.md` defines the columns.
- **Resolve people** by name → open_id with the `lark-contact` skill, then fetch their card.
- **Improve & send**: pull the draft from `lark-mail` (email) or `lark-im` (chat), run Mode 3,
  and offer to send/replace via the same skill.
- Keep this skill usable **standalone** too (no Lark needed) — Lark is the delivery surface.

## Output style
Friendly, concise, emoji-light-but-welcome. Adapt length to the ask: a quick "how do I phrase this"
gets a tight rewrite + 2 bullets, not all five sections. State any assumptions you make in one line.
