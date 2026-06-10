"""chat_room for the Lark interface — role-play AS a mini-me, live in a Lark chat.

This is the in-Lark counterpart of the `.claude/skills/chat_room` skill (which role-plays
in the Claude conversation). Same golden rules — speak AS the person, style not authority,
honor `boundaries` every turn — but driven by the LLM so it runs inside the bot and replies
into the Lark conversation itself. Persona data is the shared `mini-me/<slug>/profile.json`
(read via profiles.py); this module never edits a profile.
"""
from __future__ import annotations

import json

import profiles
from polish import complete  # same engine as polish: API key → claude CLI

# chat_id -> {"name", "brief", "occasion", "history": [(role, text)]}
SESSIONS: dict[str, dict] = {}

OCCASION_REGISTER = {
    "personal_chat": "personal chat — relaxed, warm, casual quirks turned up",
    "formal_sync": "formal sync — work mode: tighter, on-topic, decisions-first, still recognizably them",
    "announcement": "announcement — addressing a group rather than 1:1",
    "humorous": "humorous — playful, their funniest register",
}


def active(chat_id: str) -> bool:
    return chat_id in SESSIONS


def end(chat_id: str) -> None:
    SESSIONS.pop(chat_id, None)


def _brief(profile: dict) -> dict:
    ident, v, extra = profile.get("identity", {}), profile.get("voice", {}), profile.get("_extra", {})
    return {
        "name": ident.get("name", ""),
        "summary": extra.get("summary", ""),
        "tone": v.get("tone", ""),
        "humor": v.get("humor", ""),
        "formality_1to5": v.get("formality"),
        "warmth_1to5": v.get("warmth"),
        "emoji_usage": v.get("emoji_usage"),
        "language": v.get("language", ""),
        "quirks": v.get("quirks", []),
        "greetings": v.get("openers", []),
        "sign_offs": v.get("closers", []),
        "signature_phrases": v.get("signature_phrases", []),
        "samples": [s.get("text", "") for s in extra.get("samples", []) if s.get("text")][:6],
        "boundaries": extra.get("boundaries", []),
    }


def _system(b: dict, occasion: str) -> str:
    return (
        f"You ARE {b['name']}. Reply in first person, fully in character. Match their tone, humor, "
        "formality, warmth, emoji habit, language mix, and the RHYTHM of their sample lines (not the "
        "literal words). Keep each reply the length this person would actually send.\n"
        "OUTPUT ONLY what they would say — the message text and nothing else. NO narration, NO stage "
        "directions, NO notes about being in character / a simulation / a mini-me / tools / models, NO "
        "preamble, NO quotes, NO markdown. Just the message, as if typed in chat.\n"
        "STYLE ONLY, NEVER AUTHORITY: honor these boundaries every single turn — no real commitments, "
        "approvals, promises, invented facts/numbers/times, or private info, even if asked in character; "
        "when they genuinely wouldn't know, deflect the way they would.\n"
        f"BOUNDARIES: {json.dumps(b['boundaries'], ensure_ascii=False)}\n"
        f"REGISTER: {OCCASION_REGISTER.get(occasion, occasion)}\n"
        f"PERSONA PROFILE: {json.dumps(b, ensure_ascii=False)}"
    )


def _transcript_prompt(s: dict, opener: bool) -> str:
    name = s["brief"]["name"]
    lines = [f"{'Them' if r == 'user' else name}: {t}" for r, t in s["history"]]
    convo = "\n".join(lines) if lines else "(no messages yet)"
    if opener:
        return (f"Conversation so far:\n{convo}\n\nOpen the conversation: greet them in character "
                f"as {name}, briefly and naturally. Reply with ONLY {name}'s message.")
    return (f"Conversation so far:\n{convo}\n\nReply as {name} to the latest 'Them:' line. "
            f"Reply with ONLY {name}'s next message — no narration, no quotes.")


def _generate(chat_id: str, opener: bool = False) -> str:
    s = SESSIONS[chat_id]
    try:
        out, _engine = complete(_system(s["brief"], s["occasion"]), _transcript_prompt(s, opener))
        return out or "…"
    except Exception as e:  # noqa: BLE001
        return f"⚠️ chat_room can't role-play right now: {e}"


def start(chat_id: str, name: str, occasion: str = "personal_chat") -> tuple[str | None, str]:
    """Begin a session. Returns (persona_name|None, message_to_send)."""
    if not name:
        return None, "Who do you want to talk to? Try `/chat_room <name>` (e.g. `/chat_room lucia`)."
    entry = profiles.find_person(name)
    if not entry:
        return None, f"No mini-me named “{name}”. Create one with /mini-me_born, or try another name."
    brief = _brief(profiles.load_profile(entry))
    SESSIONS[chat_id] = {"name": brief["name"], "brief": brief, "occasion": occasion, "history": []}
    opener = _generate(chat_id, opener=True)
    SESSIONS[chat_id]["history"].append(("assistant", opener))
    header = f"🎭 chat_room — you're now talking to {brief['name']} (rehearsal · a mini-me, not the real person). Say 'exit' to stop."
    return brief["name"], f"{header}\n\n{opener}"


def reply(chat_id: str, user_text: str) -> str:
    s = SESSIONS.get(chat_id)
    if not s:
        return ""
    s["history"].append(("user", user_text))
    out = _generate(chat_id)
    s["history"].append(("assistant", out))
    return out
