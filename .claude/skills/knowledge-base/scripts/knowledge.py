#!/usr/bin/env python3
"""Shared, realtime-ish knowledge + chat-history store for two agents on one repo.

The store is the git remote both teammates already clone. Each record is its OWN
file under knowledge/entries/ (timestamp-prefixed), so concurrent writes from two
people NEVER merge-conflict. Records are committed (path-scoped, so other in-progress
work is untouched) and pushed immediately; reads fetch the remote first, so each
agent sees the other's records within one session/recall.

Usage:
  knowledge.py record  --kind decision|fact|todo|note --summary S [--detail D] [--refs R]
  knowledge.py record-session --transcript /path/to/transcript.jsonl
  knowledge.py recall  [--limit N]            # prints recent records (local + remote)

All git operations are best-effort: if offline or push is rejected, the record is
still saved locally and will sync on the next push/recall.
"""
import argparse
import datetime as dt
import json
import os
import random
import string
import subprocess
import sys
from pathlib import Path

ENTRIES_REL = "knowledge/entries"


def run(args, **kw):
    """Run a command, returning (rc, stdout, stderr). Never raises."""
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=kw.get("timeout", 30))
        return p.returncode, p.stdout, p.stderr
    except Exception as e:  # noqa: BLE001
        return 1, "", str(e)


def repo_root():
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and Path(env, ".git").exists():
        return Path(env)
    rc, out, _ = run(["git", "rev-parse", "--show-toplevel"])
    if rc == 0 and out.strip():
        return Path(out.strip())
    return Path.cwd()


def branch(root):
    rc, out, _ = run(["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"])
    return out.strip() if rc == 0 and out.strip() and out.strip() != "HEAD" else "main"


def author(root):
    rc, out, _ = run(["git", "-C", str(root), "config", "user.name"])
    if rc == 0 and out.strip():
        return out.strip()
    return os.environ.get("USER", "unknown")


def slug(s, n=24):
    keep = "".join(c if c.isalnum() else "-" for c in (s or "").lower())
    return (keep.strip("-")[:n]) or "anon"


def now_compact():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


# ---------------------------------------------------------------- writing

def write_entry(root, entry):
    entries = root / ENTRIES_REL
    entries.mkdir(parents=True, exist_ok=True)
    rnd = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    fname = f"{now_compact()}__{slug(entry['author'])}__{rnd}.json"
    fpath = entries / fname
    fpath.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
    return fpath


def commit_push(root, fpath, summary):
    rel = str(fpath.relative_to(root))
    br = branch(root)
    # Path-scoped commit: touches ONLY this entry file, leaving any other staged or
    # unstaged work in the tree completely alone.
    run(["git", "-C", str(root), "add", "--", rel])
    rc, _, err = run(["git", "-C", str(root), "commit", "-m",
                      f"knowledge: {summary[:60]}", "--", rel])
    pushed = False
    note = ""
    if rc == 0:
        # Pull remote knowledge first (rebase keeps history linear), then push.
        run(["git", "-C", str(root), "fetch", "origin", br], timeout=45)
        prc, _, perr = run(["git", "-C", str(root), "push", "origin", f"HEAD:{br}"], timeout=60)
        pushed = prc == 0
        if not pushed:
            note = f"committed locally; push deferred ({perr.strip()[:120]})"
    else:
        note = f"commit skipped ({err.strip()[:120]})"
    return pushed, note


# ---------------------------------------------------------------- reading

def remote_entries(root, br):
    """List remote entry blobs without touching the working tree."""
    run(["git", "-C", str(root), "fetch", "origin", br], timeout=45)
    rc, out, _ = run(["git", "-C", str(root), "ls-tree", "-r", "--name-only",
                      f"origin/{br}", "--", ENTRIES_REL])
    names = {}
    if rc == 0:
        for line in out.splitlines():
            line = line.strip()
            if line.endswith(".json"):
                names[Path(line).name] = ("remote", line)
    return names


def local_entries(root):
    d = root / ENTRIES_REL
    out = {}
    if d.exists():
        for p in d.glob("*.json"):
            out[p.name] = ("local", str(p))
    return out


def load_entry(root, br, src, ref):
    try:
        if src == "local":
            return json.loads(Path(ref).read_text(encoding="utf-8"))
        rc, out, _ = run(["git", "-C", str(root), "show", f"origin/{br}:{ref}"])
        if rc == 0:
            return json.loads(out)
    except Exception:  # noqa: BLE001
        return None
    return None


def cmd_recall(root, limit):
    br = branch(root)
    merged = {}
    merged.update(remote_entries(root, br))
    merged.update(local_entries(root))  # local wins on identical names
    names = sorted(merged.keys())  # timestamp-prefixed => chronological
    recent = names[-limit:]
    if not recent:
        print("📒 Shared knowledge base is empty — nothing recorded yet.")
        return
    print(f"📒 Shared knowledge base — {len(recent)} most recent of {len(names)} record(s):\n")
    for name in recent:
        src, ref = merged[name]
        e = load_entry(root, br, src, ref)
        if not e:
            continue
        line = f"• [{e.get('time','?')}] ({e.get('author','?')}/{e.get('kind','note')}) {e.get('summary','').strip()}"
        print(line)
        if e.get("detail"):
            print(f"    {e['detail'].strip()[:400]}")
        if e.get("refs"):
            print(f"    refs: {e['refs']}")
    print("\n(Use the knowledge-base skill to /record new entries; this syncs to your teammate's agent.)")


# ---------------------------------------------------------------- session capture

def extract_user_turns(transcript_path, max_turns=12, max_chars=400):
    turns = []
    try:
        for raw in Path(transcript_path).read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except Exception:  # noqa: BLE001
                continue
            if obj.get("type") != "user":
                continue
            msg = obj.get("message", {})
            content = msg.get("content", "")
            text = ""
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
                text = " ".join(p for p in parts if p)
            text = text.strip()
            # skip tool-result / system-reminder noise
            if not text or text.startswith("<") or "tool_use_id" in raw:
                continue
            turns.append(text[:max_chars])
    except Exception:  # noqa: BLE001
        pass
    return turns[-max_turns:]


def cmd_record_session(root, transcript):
    turns = extract_user_turns(transcript)
    if not turns:
        return  # nothing worth recording
    sid = Path(transcript).stem[:16] if transcript else "session"
    summary = f"Session recap ({len(turns)} prompts): " + turns[-1][:80]
    detail = "\n".join(f"- {t}" for t in turns)
    entry = {
        "time": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "author": author(root),
        "kind": "chat-summary",
        "summary": summary,
        "detail": detail,
        "refs": f"transcript:{sid}",
        "host": os.uname().nodename if hasattr(os, "uname") else "",
    }
    fpath = write_entry(root, entry)
    pushed, note = commit_push(root, fpath, summary)
    print(f"[knowledge] recorded session recap ({'pushed' if pushed else note})")


def cmd_record(root, kind, summary, detail, refs):
    entry = {
        "time": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "author": author(root),
        "kind": kind,
        "summary": summary,
        "detail": detail or "",
        "refs": refs or "",
        "host": os.uname().nodename if hasattr(os, "uname") else "",
    }
    fpath = write_entry(root, entry)
    pushed, note = commit_push(root, fpath, summary)
    print(f"✅ Recorded to shared knowledge base: {entry['kind']} — {summary}")
    print("   " + (f"synced to teammate (pushed to origin/{branch(root)})" if pushed else f"saved locally — {note}"))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("record")
    r.add_argument("--kind", default="note")
    r.add_argument("--summary", required=True)
    r.add_argument("--detail", default="")
    r.add_argument("--refs", default="")

    rs = sub.add_parser("record-session")
    rs.add_argument("--transcript", required=True)

    rc = sub.add_parser("recall")
    rc.add_argument("--limit", type=int, default=15)

    a = ap.parse_args()
    root = repo_root()
    if a.cmd == "record":
        cmd_record(root, a.kind, a.summary, a.detail, a.refs)
    elif a.cmd == "record-session":
        cmd_record_session(root, a.transcript)
    elif a.cmd == "recall":
        cmd_recall(root, a.limit)


if __name__ == "__main__":
    main()
