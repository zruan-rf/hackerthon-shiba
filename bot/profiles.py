"""Profile loader for Mini-Me.

Reads the shared library the distill_expert skill manages:
    <repo>/mini-me/<slug>/profile.json   (+ card.md)
No _index.json — the directory IS the index. We only READ + normalize to the
canonical shape polish() expects; distill_expert owns the write schema.
"""
from __future__ import annotations

import copy
import json
import os

MINI_ME_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mini-me")

OCCASIONS = ["personal_chat", "announcement", "formal_sync", "humorous"]
OCCASION_ALIASES = {
    "casual": "personal_chat", "chat": "personal_chat", "dm": "personal_chat",
    "announce": "announcement", "broadcast": "announcement",
    "formal": "formal_sync", "sync": "formal_sync", "serious": "formal_sync",
    "funny": "humorous", "joke": "humorous",
}


def _profile_path(slug: str) -> str:
    return os.path.join(MINI_ME_DIR, slug, "profile.json")


def list_minimes() -> list[dict]:
    """Every mini-me raw profile in the library (each dict carries its slug)."""
    out = []
    if not os.path.isdir(MINI_ME_DIR):
        return out
    for slug in sorted(os.listdir(MINI_ME_DIR)):
        path = _profile_path(slug)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
            raw.setdefault("slug", slug)
            out.append(raw)
        except (json.JSONDecodeError, OSError):
            continue
    return out


def _entry(raw: dict) -> dict:
    return {"name": raw.get("name", ""), "slug": raw.get("slug", ""),
            "open_id": raw.get("open_id", ""), "owner": raw.get("owner", "other")}


def find_person(name_or_slug: str) -> dict | None:
    """Resolve a slug / full name / first name (case-insensitive) to an entry."""
    key = (name_or_slug or "").strip().lower()
    if not key:
        return None
    minimes = list_minimes()
    for raw in minimes:  # exact slug / name / id
        if key in (raw.get("slug", "").lower(), raw.get("name", "").lower(), str(raw.get("id", "")).lower()):
            return _entry(raw)
    for raw in minimes:  # first-name match (e.g. "lucia" -> "Lucia Wen")
        if raw.get("name", "").lower().split()[:1] == [key]:
            return _entry(raw)
    return None


def self_entry() -> dict | None:
    """The user's own voice = the unique `owner: self` mini-me (None if 0 or many)."""
    selfs = [r for r in list_minimes() if r.get("owner") == "self"]
    return _entry(selfs[0]) if len(selfs) == 1 else None


def sender_entry(preferred_slug: str | None = None) -> dict | None:
    """Which mini-me to write AS: an explicit choice, else the unique self mini-me."""
    if preferred_slug:
        e = find_person(preferred_slug)
        if e:
            return e
    return self_entry()


def load_profile(entry_or_slug) -> dict:
    """Read a mini-me and normalize it to the canonical shape polish() expects."""
    slug = entry_or_slug["slug"] if isinstance(entry_or_slug, dict) else entry_or_slug
    with open(_profile_path(slug), encoding="utf-8") as f:
        raw = json.load(f)
    return _normalize(raw) if ("personality" in raw or "comms" in raw) else raw


_EMOJI_MAP = {"none": "none", "some": "light", "light": "light", "heavy": "heavy"}


def _normalize(raw: dict) -> dict:
    """distill_expert schema -> canonical {identity, voice, conversation_preferences,
    occasion_overrides}. Rich fields (tone/humor/quirks/samples/boundaries) are carried in
    `_extra` for the persona-driven rewrite; simpler fallbacks ignore what they don't use."""
    v = raw.get("voice", {})
    comms = raw.get("comms", {})
    base_formality = v.get("formality", 3)
    return {
        "identity": {"name": raw.get("name", ""), "slug": raw.get("slug", ""),
                     "open_id": raw.get("open_id", ""), "role": raw.get("role", "")},
        "voice": {
            "language": (v.get("languages") or ["en"])[0],
            "formality": base_formality,
            "warmth": v.get("warmth", 3),
            "verbosity": v.get("verbosity", 3),
            "emoji_usage": _EMOJI_MAP.get(v.get("emoji_usage", "light"), "light"),
            "tone": v.get("tone", ""),
            "humor": v.get("humor", ""),
            "quirks": v.get("quirks", []),
            "openers": v.get("greetings", []),
            "closers": v.get("sign_offs", []),
            "signature_phrases": v.get("catchphrases", []),
        },
        "conversation_preferences": {
            "address_as": "first_name",
            "likes": comms.get("convinced_by", []),
            "dislikes": comms.get("pet_peeves", []),
            "best_move": comms.get("best_move", ""),
        },
        "occasion_overrides": {
            "personal_chat": {},
            "announcement": {"formality": max(base_formality, 4), "emoji_usage": "none"},
            "formal_sync": {"formality": max(base_formality, 4)},
            "humorous": {"warmth": 5, "emoji_usage": "light"},
        },
        "_extra": {"summary": raw.get("personality", {}).get("summary", ""),
                   "samples": raw.get("samples", []), "boundaries": raw.get("boundaries", [])},
    }


def normalize_occasion(raw: str) -> str | None:
    if not raw:
        return None
    k = raw.strip().lower().replace(" ", "_")
    return k if k in OCCASIONS else OCCASION_ALIASES.get(k)


def effective_voice(sender_profile: dict, occasion: str) -> dict:
    """Apply the sender's occasion_overrides on top of their base voice."""
    voice = copy.deepcopy(sender_profile.get("voice", {}))
    voice.update(sender_profile.get("occasion_overrides", {}).get(occasion, {}))
    return voice
