---
description: Chat with a mini-me — Claude role-plays AS that person's persona so you can rehearse or just talk.
argument-hint: <name> [occasion]
---

Use the **chat_room** skill to role-play AS a mini-me.

Target mini-me: **$ARGUMENTS**

If no name was given, run `python3 .claude/skills/distill_expert/scripts/minime.py list` and ask which
one (prefer an `owner: other` persona). Load it with `minime.py persona <slug>`, then stay fully in
character — first person, their voice, honoring the profile's boundaries — until the user says
exit/stop. Open with a one-line out-of-character header (who they're now talking to + how to exit),
then the in-character opener. Don't send anything outbound; this is a local rehearsal — use `/echo_me`
to draft a real message.
