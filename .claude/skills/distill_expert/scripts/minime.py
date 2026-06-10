#!/usr/bin/env python3
"""minime.py — deterministic CRUD for the mini-me library.

The distill_expert skill uses this for every write so profiles stay well-formed and the
human-readable card.md never drifts from profile.json (the source of truth).

Library lives at <repo>/mini-me/<slug>/{profile.json, card.md}. Override with MINIME_HOME.

Commands:
  born <name> [--role R] [--mbti TYPE] [--owner self|other] [--force]
  list
  show <slug> [--json]
  set <slug> (--json '<patch>' | --stdin)        # deep-merge a JSON patch into the profile
  add-sample <slug> --text T [--context C] [--source S]
  persona <slug>                                  # print an "act-as" briefing for chat_room / echo_me
  render <slug>                                   # regenerate card.md from profile.json
  kill <slug> --force                             # delete; refuses without --force
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------- paths ----------

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def repo_root() -> Path:
    if os.environ.get("MINIME_HOME"):
        return Path(os.environ["MINIME_HOME"]).expanduser().resolve()
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL, text=True,
        ).strip()
        if out:
            return Path(out)
    except Exception:
        pass
    return Path(__file__).resolve().parents[4]


def library() -> Path:
    lib = repo_root() / "mini-me"
    lib.mkdir(parents=True, exist_ok=True)
    return lib


def slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return s or "mini-me"


def profile_path(slug: str) -> Path:
    return library() / slug / "profile.json"


def die(msg: str, code: int = 1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


# ---------- profile model ----------

def skeleton(name: str, slug: str, role: str, mbti: str, owner: str) -> dict:
    ts = now_iso()
    p = {
        "id": slug,
        "name": name,
        "slug": slug,
        "role": role or "",
        "owner": owner if owner in ("self", "other") else "other",
        "open_id": "",
        "status": "newborn",
        "created_at": ts,
        "updated_at": ts,
        "personality": {"mbti": (mbti or "").upper(), "summary": "", "traits": []},
        "comms": {
            "directness": "balanced", "detail_level": "balanced", "pace": "flexible",
            "convinced_by": [], "preferred_channels": [], "response_time": "",
            "pet_peeves": [], "best_move": "", "one_liner": "",
        },
        "voice": {
            "tone": "", "formality": 3, "warmth": 3, "verbosity": 3,
            "emoji_usage": "some", "humor": "", "languages": ["en"],
            "greetings": [], "sign_offs": [], "catchphrases": [], "quirks": [],
        },
        "samples": [],
        "topics": [],
        "boundaries": [
            "Never make real commitments, approvals, or promises on the person's behalf.",
            "Never invent facts, numbers, or events; flag anything you're unsure of.",
            "Never share anything the person would consider private or confidential.",
        ],
        "provenance": {"sources": [], "sample_count": 0, "last_grown_at": ""},
    }
    if p["personality"]["mbti"]:
        seed_from_mbti(p)
    return p


def seed_from_mbti(p: dict):
    """Gentle priors from a 4-letter type. Only fills still-empty/default fields."""
    t = p["personality"]["mbti"]
    if len(t) != 4:
        return
    e, sn, tf, jp = t[0], t[1], t[2], t[3]
    c, v = p["comms"], p["voice"]

    def add(lst_key, container, *vals):
        for x in vals:
            if x not in container[lst_key]:
                container[lst_key].append(x)

    if e == "E":
        if c["pace"] == "flexible":
            c["pace"] = "real-time"
        v["warmth"] = max(v["warmth"], 4)
    elif e == "I":
        if c["pace"] == "flexible":
            c["pace"] = "async-first"
        add("preferred_channels", c, "doc", "im")

    if sn == "S":
        if c["detail_level"] == "balanced":
            c["detail_level"] = "deep-dive"
        add("convinced_by", c, "data", "proven-examples")
    elif sn == "N":
        if c["detail_level"] == "balanced":
            c["detail_level"] = "headline-first"
        add("convinced_by", c, "vision")

    if tf == "T":
        if c["directness"] == "balanced":
            c["directness"] = "direct"
        add("convinced_by", c, "logic", "efficiency")
        v["warmth"] = min(v["warmth"], 3)
    elif tf == "F":
        if c["directness"] == "balanced":
            c["directness"] = "diplomatic"
        add("convinced_by", c, "people-impact", "harmony")
        v["warmth"] = max(v["warmth"], 4)

    if jp == "J":
        add("pet_peeves", c, "last-minute changes")
        if not c["best_move"]:
            c["best_move"] = "Lead with the decision + a short why."


_RANK = {"newborn": 0, "growing": 1, "ready": 2}


def suggest_status(p: dict) -> str:
    comms = p["comms"]
    voice = p["voice"]
    n_samples = len(p.get("samples", []))
    has_summary = bool(p["personality"]["summary"]) or bool(comms["one_liner"])
    has_voice = bool(voice["tone"]) or bool(voice["catchphrases"]) or bool(voice["quirks"])
    comms_filled = any([
        comms["convinced_by"], comms["pet_peeves"], comms["best_move"],
        comms["one_liner"], comms["response_time"],
    ])
    if n_samples >= 3 or (has_voice and has_summary):
        return "ready"
    if n_samples or has_voice or comms_filled or p["personality"]["mbti"] or p["topics"]:
        return "growing"
    return "newborn"


def deep_merge(base: dict, patch: dict):
    """Recursively merge patch into base. Lists are replaced wholesale (use add-sample to append)."""
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_merge(base[k], v)
        else:
            base[k] = v


def touch(p: dict, explicit_status: str | None = None):
    p["updated_at"] = now_iso()
    p["provenance"]["sample_count"] = len(p.get("samples", []))
    if explicit_status:
        p["status"] = explicit_status
    else:
        # auto-advance forward only; never silently downgrade a curated profile
        nxt = suggest_status(p)
        if _RANK[nxt] > _RANK.get(p.get("status", "newborn"), 0):
            p["status"] = nxt


def load(slug: str) -> dict:
    path = profile_path(slug)
    if not path.exists():
        die(f"no mini-me '{slug}' (looked in {path.parent}). Run: minime.py list")
    return json.loads(path.read_text(encoding="utf-8"))


def save(p: dict):
    path = profile_path(p["slug"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (path.parent / "card.md").write_text(render_card(p), encoding="utf-8")


# ---------- rendering ----------

def render_card(p: dict) -> str:
    per, c, v = p["personality"], p["comms"], p["voice"]
    head_bits = [p["name"]]
    if per["mbti"]:
        head_bits.append(per["mbti"])
    head_bits.append(f"owner: {p['owner']}")
    head_bits.append(f"status: {p['status']}")
    L = [f"🧬  {'  ·  '.join(head_bits)}"]
    if c["one_liner"]:
        L.append(f'"{c["one_liner"]}"')
    L.append("")

    vbits = []
    if v["tone"]:
        vbits.append(v["tone"])
    vbits.append(f"formality {v['formality']}/5 · warmth {v['warmth']}/5 · verbosity {v['verbosity']}/5")
    vbits.append(f"{v['emoji_usage']} emoji")
    if v["languages"] and v["languages"] != ["en"]:
        vbits.append("/".join(v["languages"]))
    L.append(f"🗣️  Voice:   {' · '.join(vbits)}")
    extra = []
    if v["greetings"]:
        extra.append("opens with " + ", ".join(f'"{g}"' for g in v["greetings"]))
    if v["sign_offs"]:
        extra.append("signs off " + ", ".join(f'"{s}"' for s in v["sign_offs"]))
    if v["quirks"]:
        extra.append("quirks: " + "; ".join(v["quirks"]))
    if extra:
        L.append("            " + " · ".join(extra))

    reach = []
    if c["preferred_channels"]:
        reach.append(", ".join(c["preferred_channels"]))
    if c["convinced_by"]:
        reach.append("convince with " + ", ".join(c["convinced_by"]))
    if reach:
        L.append(f"✅ Reach me by:   {' · '.join(reach)}")
    if c["response_time"]:
        L.append(f"⏱️ Response time:   {c['response_time']}")
    if c["pet_peeves"]:
        L.append(f"🚫 Please don't:   {', '.join(c['pet_peeves'])}")
    if p["samples"]:
        L.append(f'💬 Sounds like:   "{p["samples"][0]["text"]}"')
    meta = f"🧪 Samples on file:   {len(p['samples'])}"
    if p["provenance"]["last_grown_at"]:
        meta += f"   ·   last grown: {p['provenance']['last_grown_at'][:10]}"
    L.append(meta)
    return "\n".join(L) + "\n"


def render_persona(p: dict) -> str:
    """An 'act-as' briefing assembled from the profile — the shared input for chat_room & echo_me.

    Unlike card.md (a human-readable summary), this is written *at* the model that will embody the
    person: voice dials to match, sample lines to mimic, and the boundaries it must never cross.
    """
    per, c, v = p["personality"], p["comms"], p["voice"]
    L = [f"=== Persona brief: {p['name']} ({p['slug']}) ==="]
    head = f"Speak AS {p['name']} — embody this voice, do not describe it. owner: {p['owner']}"
    if per["mbti"]:
        head += f" · MBTI {per['mbti']}"
    L.append(head)
    if per["summary"]:
        L.append(f"Who they are: {per['summary']}")
    if per["traits"]:
        L.append("Traits: " + ", ".join(per["traits"]))
    if p["topics"]:
        L.append("Talks about: " + ", ".join(p["topics"]))

    L.append("")
    L.append("VOICE — match this:")
    if v["tone"]:
        L.append(f"  tone: {v['tone']}")
    dials = f"  formality {v['formality']}/5 · warmth {v['warmth']}/5 · verbosity {v['verbosity']}/5 · {v['emoji_usage']} emoji"
    if v["humor"]:
        dials += f" · humor: {v['humor']}"
    L.append(dials)
    if v["languages"]:
        line = "  languages: " + ", ".join(v["languages"])
        if len(v["languages"]) > 1:
            line += " (code-switches — keep their mix)"
        L.append(line)
    if v["greetings"]:
        L.append("  opens with: " + ", ".join(f'"{g}"' for g in v["greetings"]))
    if v["sign_offs"]:
        L.append("  signs off: " + ", ".join(f'"{s}"' for s in v["sign_offs"]))
    if v["catchphrases"]:
        L.append("  catchphrases: " + ", ".join(f'"{x}"' for x in v["catchphrases"]))
    if v["quirks"]:
        L.append("  quirks: " + "; ".join(v["quirks"]))

    if any([c["one_liner"], c["convinced_by"], c["best_move"], c["pet_peeves"]]):
        L.append("")
        L.append("HOW THEY OPERATE:")
        if c["one_liner"]:
            L.append(f'  their one-liner: "{c["one_liner"]}"')
        L.append(f"  directness: {c['directness']} · detail: {c['detail_level']} · pace: {c['pace']}")
        if c["convinced_by"]:
            L.append("  convinced by: " + ", ".join(c["convinced_by"]))
        if c["best_move"]:
            L.append(f"  best move: {c['best_move']}")
        if c["pet_peeves"]:
            L.append("  pet peeves (avoid): " + ", ".join(c["pet_peeves"]))

    if p["samples"]:
        L.append("")
        L.append("SAMPLES — mimic the rhythm & register, not the literal words:")
        for i, s in enumerate(p["samples"], 1):
            ctx = f"   ({s['context']})" if s.get("context") else ""
            L.append(f'  {i}. "{s["text"]}"{ctx}')

    L.append("")
    L.append("BOUNDARIES — never cross these, even if asked in-character:")
    for b in p["boundaries"]:
        L.append(f"  - {b}")

    status = p.get("status", "newborn")
    if status != "ready":
        L.append("")
        L.append(f"NOTE: this mini-me is '{status}', not fully distilled — stay conservative, "
                 "lean on the samples you do have, and flag anything you're guessing at.")
    return "\n".join(L) + "\n"


# ---------- commands ----------

def cmd_born(a):
    slug = slugify(a.name)
    path = profile_path(slug)
    if path.exists() and not a.force:
        die(f"'{slug}' already exists at {path}. Use --force to overwrite, or /mini-me_grow it.")
    p = skeleton(a.name, slug, a.role, a.mbti, a.owner)
    if a.mbti:
        p["provenance"]["sources"].append("mbti")
    save(p)
    print(f"born: {slug}  ->  {path}")
    print(render_card(p))


def cmd_list(a):
    lib = library()
    slugs = sorted(d.name for d in lib.iterdir() if d.is_dir() and (d / "profile.json").exists())
    if not slugs:
        print("(library empty — run /mini-me_born <name>)")
        return
    print(f"{len(slugs)} mini-me(s) in {lib}:\n")
    for slug in slugs:
        p = json.loads((lib / slug / "profile.json").read_text(encoding="utf-8"))
        mbti = p["personality"]["mbti"] or "—"
        line = f"  • {p['name']:<22} {mbti:<5} {p['owner']:<6} {p['status']:<8} samples:{len(p['samples'])}"
        if p["comms"]["one_liner"]:
            line += f'  "{p["comms"]["one_liner"]}"'
        print(line)


def cmd_show(a):
    p = load(a.slug)
    if a.json:
        print(json.dumps(p, ensure_ascii=False, indent=2))
    else:
        print(render_card(p))


def cmd_set(a):
    p = load(a.slug)
    raw = sys.stdin.read() if a.stdin else a.json
    if not raw:
        die("provide a patch via --json '<json>' or --stdin")
    try:
        patch = json.loads(raw)
    except json.JSONDecodeError as e:
        die(f"patch is not valid JSON: {e}")
    if not isinstance(patch, dict):
        die("patch must be a JSON object")
    explicit = patch.pop("status", None)
    src = patch.get("provenance", {}).get("sources")
    deep_merge(p, patch)
    if isinstance(src, list):
        p["provenance"]["sources"] = sorted(set(p["provenance"].get("sources", [])) | set(src))
    touch(p, explicit)
    save(p)
    print(f"updated: {a.slug} (status: {p['status']})")
    print(render_card(p))


def cmd_add_sample(a):
    p = load(a.slug)
    p["samples"].append({
        "text": a.text, "context": a.context or "",
        "source": a.source or "pasted", "added_at": now_iso(),
    })
    if a.source and a.source not in p["provenance"]["sources"]:
        p["provenance"]["sources"].append(a.source)
    p["provenance"]["last_grown_at"] = now_iso()
    touch(p)
    save(p)
    print(f"added sample to {a.slug} (now {len(p['samples'])}). status: {p['status']}")


def cmd_persona(a):
    p = load(a.slug)
    print(render_persona(p))


def cmd_render(a):
    p = load(a.slug)
    save(p)
    print(f"re-rendered card.md for {a.slug}")


def cmd_kill(a):
    p = load(a.slug)
    d = profile_path(a.slug).parent
    if not a.force:
        die(f"refusing to delete '{p['name']}' ({d}) without --force. "
            f"This permanently removes the mini-me.")
    shutil.rmtree(d)
    print(f"killed: {a.slug} (removed {d})")


def main():
    ap = argparse.ArgumentParser(prog="minime.py")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("born"); b.add_argument("name")
    b.add_argument("--role", default=""); b.add_argument("--mbti", default="")
    b.add_argument("--owner", default="other", choices=["self", "other"])
    b.add_argument("--force", action="store_true"); b.set_defaults(fn=cmd_born)

    sub.add_parser("list").set_defaults(fn=cmd_list)

    s = sub.add_parser("show"); s.add_argument("slug")
    s.add_argument("--json", action="store_true"); s.set_defaults(fn=cmd_show)

    st = sub.add_parser("set"); st.add_argument("slug")
    st.add_argument("--json", default=""); st.add_argument("--stdin", action="store_true")
    st.set_defaults(fn=cmd_set)

    sa = sub.add_parser("add-sample"); sa.add_argument("slug")
    sa.add_argument("--text", required=True); sa.add_argument("--context", default="")
    sa.add_argument("--source", default=""); sa.set_defaults(fn=cmd_add_sample)

    pe = sub.add_parser("persona"); pe.add_argument("slug"); pe.set_defaults(fn=cmd_persona)

    r = sub.add_parser("render"); r.add_argument("slug"); r.set_defaults(fn=cmd_render)

    k = sub.add_parser("kill"); k.add_argument("slug")
    k.add_argument("--force", action="store_true"); k.set_defaults(fn=cmd_kill)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
