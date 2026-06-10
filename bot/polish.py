"""The polish function — rewrite a draft in a mini-me's distilled voice.

    polish(draft, sender_profile, recipient_profile, occasion) -> (text, engine)

The rewrite is driven by the mini-me PERSONA (tone/humor/quirks/samples/boundaries),
not hardcoded rules. Engine priority:

  1. ANTHROPIC_API_KEY set  -> Anthropic SDK (fastest, explicit key)
  2. `claude` CLI present   -> uses your Claude Code auth, no API key  (default here)
  3. neither                -> a minimal, non-canned cleanup (last resort)

(1) and (2) send the SAME persona prompt — mirroring the echo_me skill's rules — so output
matches each mini-me's style. The signature is the contract with the bot; keep it stable.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

from profiles import effective_voice


def _load_env() -> None:
    """Load bot/.env (KEY=VALUE lines) so ANTHROPIC_API_KEY can live out of the repo."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()
MODEL = os.environ.get("MINI_ME_MODEL", "claude-haiku-4-5-20251001")


def polish(draft: str, sender_profile: dict, recipient_profile: dict, occasion: str) -> tuple[str, str]:
    """Return (polished_text, engine_name)."""
    voice = effective_voice(sender_profile, occasion)
    prefs = dict((recipient_profile or {}).get("conversation_preferences", {}))
    prefs["_name"] = (recipient_profile or {}).get("identity", {}).get("name", "")
    system, user = _build_prompt(draft, sender_profile, voice, prefs, occasion)

    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _api_polish(system, user), f"llm:{MODEL}"
        except Exception as e:
            print(f"[polish] API call failed ({type(e).__name__}: {e}); trying claude CLI", file=sys.stderr)
    if shutil.which("claude"):
        try:
            return _claude_cli_polish(system, user), "claude-cli"
        except Exception as e:
            print(f"[polish] claude CLI failed ({type(e).__name__}: {e}); using basic fallback", file=sys.stderr)
    return _basic_polish(draft, voice, prefs), "basic"


def complete(system: str, user: str) -> tuple[str, str]:
    """Run one completion via the best available engine (API key → claude CLI).
    Shared by polish() and chat_room. Raises if no engine is reachable."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _api_polish(system, user), f"llm:{MODEL}"
        except Exception as e:  # noqa: BLE001
            print(f"[model] API failed ({type(e).__name__}: {e}); trying claude CLI", file=sys.stderr)
    if shutil.which("claude"):
        return _claude_cli_polish(system, user), "claude-cli"
    raise RuntimeError("no model engine (set ANTHROPIC_API_KEY or install the claude CLI)")


# --- the persona prompt (shared by both model engines) -----------------------
def _build_prompt(draft: str, sender_profile: dict, voice: dict, prefs: dict, occasion: str) -> tuple[str, str]:
    extra = sender_profile.get("_extra", {})
    samples = [s.get("text", "") for s in extra.get("samples", []) if s.get("text")][:5]
    sender = {
        "name": sender_profile.get("identity", {}).get("name", ""),
        "summary": extra.get("summary", ""),
        "tone": voice.get("tone", ""),
        "humor": voice.get("humor", ""),
        "formality_1to5": voice.get("formality"),
        "warmth_1to5": voice.get("warmth"),
        "verbosity_1to5": voice.get("verbosity"),
        "emoji_usage": voice.get("emoji_usage"),
        "language": voice.get("language"),
        "greetings": voice.get("openers", []),
        "sign_offs": voice.get("closers", []),
        "signature_phrases": voice.get("signature_phrases", []),
        "quirks": voice.get("quirks", []),
    }
    recipient = {"name": prefs.get("_name", ""), "likes": prefs.get("likes", []), "dislikes": prefs.get("dislikes", [])}
    boundaries = extra.get("boundaries", [])

    system = (
        "You rewrite the user's DRAFT into a single message written AS the sender, in the sender's "
        "distilled voice. Preserve the meaning and every concrete ask or detail. Do NOT invent facts, "
        "names, dates, numbers, or commitments — if the draft is vague, keep it vague. Match the "
        "sender's tone, formality, warmth, verbosity, humor, language, emoji habit, greetings and "
        "quirks. Adapt the register to the OCCASION and tailor HOW you pitch it to how the recipient "
        "likes to be reached — without changing the sender's voice. Respect the sender's boundaries. "
        "Return ONLY the rewritten message text — no quotes, no preamble, no options, no markdown."
    )
    user = (
        f"OCCASION: {occasion}\n\n"
        f"SENDER (write AS this person):\n{json.dumps(sender, ensure_ascii=False, indent=2)}\n\n"
        f"SENDER WRITING SAMPLES (mimic this style):\n"
        + ("\n".join(f"- {s}" for s in samples) if samples else "(none on file)")
        + (f"\n\nSENDER BOUNDARIES:\n" + "\n".join(f"- {b}" for b in boundaries) if boundaries else "")
        + f"\n\nRECIPIENT (tailor to them; blank = unknown):\n{json.dumps(recipient, ensure_ascii=False)}\n\n"
        f"DRAFT TO REWRITE:\n{draft}"
    )
    return system, user


# --- engine 1: Anthropic SDK -------------------------------------------------
def _api_polish(system: str, user: str) -> str:
    import anthropic  # type: ignore

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=MODEL, max_tokens=600, system=system,
        messages=[{"role": "user", "content": user}],
    )
    out = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
    if not out:
        raise RuntimeError("empty response")
    return out


# --- engine 2: claude CLI (uses Claude Code auth; no API key) ----------------
def _claude_cli_polish(system: str, user: str) -> str:
    prompt = f"{system}\n\n{user}"
    proc = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "text"],
        capture_output=True, text=True, timeout=120,
    )
    out = (proc.stdout or "").strip()
    if not out:
        raise RuntimeError((proc.stderr or "empty output").strip()[:200])
    return out


# --- engine 3: minimal fallback (no canned phrases, no invented wording) -----
def _basic_polish(draft: str, voice: dict, prefs: dict) -> str:
    """Last-resort touch-up when no model is reachable. Deliberately conservative:
    light formality cleanup + emoji policy only — never injects phrasing the user didn't write."""
    import re

    text = draft.strip()
    if voice.get("formality", 3) >= 4:
        repl = {r"\bu\b": "you", r"\bur\b": "your", r"\bpls\b": "please",
                r"\bplz\b": "please", r"\bthx\b": "thanks", r"\basap\b": "as soon as possible"}
        for pat, sub in repl.items():
            text = re.sub(pat, sub, text, flags=re.IGNORECASE)
        if text and text[0].islower():
            text = text[0].upper() + text[1:]
    dislikes = " ".join(prefs.get("dislikes", [])).lower()
    if voice.get("emoji_usage") == "none" or "emoji" in dislikes:
        text = _strip_emoji(text)
    return text.strip()


_EMOJI_RE = None


def _strip_emoji(s: str) -> str:
    global _EMOJI_RE
    if _EMOJI_RE is None:
        import re
        _EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]")
    return _EMOJI_RE.sub("", s).strip()
