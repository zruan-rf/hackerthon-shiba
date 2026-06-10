#!/usr/bin/env python3
"""Mini-Me — Usage 1: polish my reply *inside the live conversation*.

You're chatting with someone. You type your reply with a leading marker:

    .. hey can u review my pr when u get a sec        (occasion inferred from the chat)
    ..formal pls send the q3 numbers asap             (explicit occasion)

Mini-Me, watching your own outgoing messages:
  1. RECALLS your raw draft (so the recipient doesn't keep seeing it),
  2. shows you a private before→after PREVIEW in your Mini-Me bot DM,
  3. on your approval (`y` / `send`), sends the polished version into the conversation AS YOU.

Recipient is automatic — it's whoever's chat you typed in. No /to_whom.
The rewrite itself is bot/polish.py (the distill_expert seam).

Why this shape: no Lark API can hook your compose box, so we can't polish text
*before* it's sent. We catch the just-sent draft, pull it back, and replace it
only after you OK the rewrite.

Modes (shared core):
    python bot/mini_me_bot.py repl     # local text window — demo the full UX, no wiring
    python bot/mini_me_bot.py lark     # real Lark: watch your messages, recall→preview→send
    --live   actually recall/send (otherwise dry-run prints the lark-cli calls)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time

import chatroom
import profiles
from polish import polish

LIVE = False
MARKER = ".."  # what you prepend to a draft you want polished
SENDER_SLUG = "lucia"  # which mini-me's voice to write AS (override with --as-me)

# Pending rewrite keyed BY USER (not chat) so the preview can be approved from a
# different chat (e.g. previewed in your bot DM, the draft was in a group).
# value: {draft, occasion, polished, raw_msg_id, recipient, target_chat_id}
PENDING: dict[str, dict] = {}


# --------------------------------------------------------------------------- #
# lark-cli helpers (all Lark I/O is the existing CLI)
# --------------------------------------------------------------------------- #
def lark(*args: str) -> dict:
    out = subprocess.run(["lark-cli", *args], capture_output=True, text=True)
    try:
        return json.loads(out.stdout or "{}")
    except json.JSONDecodeError:
        return {"_raw": out.stdout, "_err": out.stderr, "_code": out.returncode}


def _quote(a: str) -> str:
    return f'"{a}"' if (" " in a or not a) else a


def resolve_self_open_id() -> str:
    """Your own open_id via `contact +get-user` (omit user_id = self)."""
    res = lark("contact", "+get-user", "--as", "user")
    data = res.get("data") or res
    user = data.get("user") or data
    return user.get("open_id", "") if isinstance(user, dict) else ""


def _missing_scope(res: dict) -> list[str] | None:
    err = res.get("error") or {}
    if err.get("subtype") == "missing_scope":
        return err.get("missing_scopes") or [err.get("message", "missing scope")]
    return None


def _ok(res: dict) -> bool:
    return bool(res.get("ok")) or "data" in res or res.get("code", 1) == 0


def recall(message_id: str) -> str:
    args = ["im", "messages", "delete", "--params", json.dumps({"message_id": message_id}), "--as", "user", "--yes"]
    if not LIVE:
        return "   (dry-run recall) lark-cli " + " ".join(_quote(a) for a in args)
    res = lark(*args)
    ms = _missing_scope(res)
    if ms:
        return f"   ⚠️ couldn't recall your raw draft (missing scope: {', '.join(ms)}) — it stays in the chat"
    return "   (recalled your raw draft)"


def deliver(target: str, text: str) -> str:
    # target is a chat_id (oc_…) or "user:<open_id>" for a not-yet-resolved p2p
    base = ["im", "+messages-send", "--text", text]
    base += ["--user-id", target[5:]] if target.startswith("user:") else ["--chat-id", target]
    if not LIVE:
        return "🧪 dry-run — would send as YOU:\n   lark-cli " + " ".join(_quote(a) for a in base + ["--as", "user"])
    res = lark(*base, "--as", "user")
    ms = _missing_scope(res)
    if ms:  # fall back to bot so the loop still completes; tell user what to enable
        if _ok(lark(*base, "--as", "bot")):
            return f"✅ Sent — but AS THE BOT. To send as YOU, grant: {', '.join(ms)}"
        return f"⚠️ send failed (missing scope: {', '.join(ms)}) and bot fallback failed too"
    return "✅ Sent to the conversation as you." if _ok(res) else f"⚠️ send failed: {json.dumps(res)[:200]}"


# --------------------------------------------------------------------------- #
# Trigger parsing
# --------------------------------------------------------------------------- #
def _strip_mentions(text: str) -> str:
    """Drop leading @mentions (e.g. `@Lucia-www `) so `@bot .. draft` works in groups."""
    t = (text or "").strip()
    while t.startswith("@"):
        parts = t.split(None, 1)
        t = parts[1].lstrip() if len(parts) > 1 else ""
    return t


def parse_trigger(text: str) -> dict | None:
    """Parse a `..[as:<slug>] [occasion] <draft>` trigger (modifiers order-free), else None.
    Tolerates a leading @mention (group chats require mentioning the bot). Examples:
      `.. let's ship`            `..formal ping the team`            `..as:yunfei 明天同步`
      `..as:lucia humorous lunch?`"""
    t = _strip_mentions(text)
    if not t.startswith(MARKER):
        return None
    rest = t[len(MARKER):].lstrip()
    occasion, sender = None, None
    while rest:  # consume leading modifier tokens (as:<slug> / occasion) in any order
        first, _, tail = rest.partition(" ")
        low = first.lower()
        if sender is None and low.startswith("as:"):
            sender, rest = first[3:].strip(), tail.lstrip()
        elif occasion is None and profiles.normalize_occasion(first):
            occasion, rest = first, tail.lstrip()
        else:
            break
    return {"occasion": occasion, "sender": sender, "draft": rest}


def infer_occasion(chat_type: str) -> str:
    return "announcement" if chat_type == "group" else "personal_chat"


def chatroom_route(chat_id: str, text: str, chat_type: str) -> str | None:
    """If this message starts/continues/ends a chat_room session, return the in-character
    reply to post into THIS chat. Otherwise None (fall through to the polish flow)."""
    low = text.strip().lower()
    if low.startswith(("/chat_room", "/chatroom")):
        name = (text.split(maxsplit=1) + [""])[1].strip()
        occ = infer_occasion(chat_type)
        toks = name.split()
        if len(toks) > 1 and profiles.normalize_occasion(toks[-1]):  # "/chat_room alex formal"
            occ, name = profiles.normalize_occasion(toks[-1]), " ".join(toks[:-1])
        return chatroom.start(chat_id, name, occ)[1]
    if chatroom.active(chat_id):
        if low in ("exit", "stop", "end", "quit", "/exit"):
            chatroom.end(chat_id)
            return "🎭 left chat_room — back to normal."
        return chatroom.reply(chat_id, text)
    return None


# --------------------------------------------------------------------------- #
# Core: handle one inbound line for a conversation
#   `say` is how we reach the user privately (repl: print here; lark: DM the user)
# --------------------------------------------------------------------------- #
def handle(user_id: str, text: str, recipient: str, chat_type: str, chat_id: str,
           raw_msg_id: str | None = None) -> str:
    pending = PENDING.get(user_id)
    low = text.strip().lower()

    # --- approval of a pending preview (may arrive from a different chat) ---
    if pending:
        if low in ("y", "yes", "send", "✓", "ok"):
            out = []
            if pending.get("raw_msg_id"):
                out.append(recall(pending["raw_msg_id"]))
            out.append(deliver(pending["target_chat_id"], pending["polished"]))
            PENDING.pop(user_id, None)
            return "\n".join(out)
        if low in ("n", "no", "cancel"):
            PENDING.pop(user_id, None)
            return "❌ Kept your draft as-is (nothing sent)."
        if low.startswith("edit:"):
            note = text.split(":", 1)[1].strip()
            return _run(user_id, pending["polished"] + f"\n(adjust: {note})",
                        pending["occasion"], pending["raw_msg_id"],
                        pending["recipient"], pending["target_chat_id"],
                        sender_slug=pending.get("sender_slug"))

    # --- a new draft trigger ---
    trig = parse_trigger(text)
    if trig is None:
        return ""  # not for us — ignore (a normal message in the chat)
    if not trig["draft"]:
        return f"Add your draft after the marker, e.g. `{MARKER} let's ship today`."
    occasion = profiles.normalize_occasion(trig["occasion"]) if trig["occasion"] else infer_occasion(chat_type)
    return _run(user_id, trig["draft"], occasion, raw_msg_id, recipient, chat_id, sender_slug=trig.get("sender"))


def _run(user_id: str, draft: str, occasion: str, raw_msg_id: str | None,
         recipient: str, target_chat_id: str, sender_slug: str | None = None) -> str:
    chosen = sender_slug or SENDER_SLUG
    me = profiles.find_person(chosen) or (None if sender_slug else profiles.self_entry())
    if not me:
        avail = ", ".join(p.get("slug", "") for p in profiles.list_minimes()) or "(none)"
        return (f"⚠️ No mini-me “{chosen}” to write as. Available: {avail}. "
                f"Use `{MARKER}as:<slug> <draft>`, or create your own with /mini-me_born <you> --owner self.")
    recipient_entry = profiles.find_person(recipient) if recipient else None
    recipient_profile = profiles.load_profile(recipient_entry) if recipient_entry else {}
    polished, engine = polish(draft, profiles.load_profile(me), recipient_profile, occasion)
    PENDING[user_id] = {"draft": draft, "occasion": occasion, "polished": polished,
                        "raw_msg_id": raw_msg_id, "recipient": recipient,
                        "target_chat_id": target_chat_id, "sender_slug": me["slug"]}
    who = recipient_entry["name"] if recipient_entry else (recipient or "this chat")
    return (
        f"✨ Polish preview · as {me['name']} · to {who} · {occasion}  ({engine})\n"
        f"┌─ your draft ─────────────\n{_indent(draft)}\n"
        f"├─ polished ───────────────\n{_indent(polished)}\n"
        f"└──────────────────────────\n"
        f"Reply `y` to recall your draft and send this · `edit: <note>` · `n` to keep yours."
    )


def _indent(s: str) -> str:
    return "\n".join("│ " + ln for ln in s.splitlines())


# --------------------------------------------------------------------------- #
# Mode: repl — a local stand-in for the live conversation window
# --------------------------------------------------------------------------- #
REPL_HELP = (
    "🐕 Mini-Me — local text window\n"
    f"  /to <name> [group]      open a conversation (default: yunfei, p2p)\n"
    f"  {MARKER} <draft>              polish your reply (then: y | edit: <note> | n)\n"
    f"  {MARKER}formal <draft>        explicit occasion: casual|announcement|formal|humorous\n"
    f"  {MARKER}as:<slug> <draft>     write as a specific mini-me (e.g. as:yunfei); combine: ..as:lucia formal …\n"
    f"  /chat_room <name>       talk TO that mini-me (role-play); say 'exit' to leave\n"
)


def run_repl() -> None:
    print(REPL_HELP)
    key = "repl"
    recipient, chat_type = "yunfei", "p2p"
    chat_id = "oc_demo_yunfei"
    for line in sys.stdin:
        line = line.rstrip("\n")
        if not line.strip():
            continue
        cr = chatroom_route(chat_id, line, chat_type)  # chat_room takes priority when active
        if cr is not None:
            print(cr + "\n")
            continue
        if line.startswith("/to "):
            parts = line[4:].split()
            recipient = parts[0]
            chat_type = "group" if len(parts) > 1 and parts[1] == "group" else "p2p"
            chat_id = f"oc_demo_{recipient.lower()}"
            print(f"[opened {chat_type} conversation with {recipient}]\n")
            continue
        if line.strip() in ("/help", "help"):
            print(REPL_HELP)
            continue
        reply = handle(key, line, recipient, chat_type, chat_id, raw_msg_id="om_demo_raw")
        if reply:
            print(reply + "\n")
        else:
            print(f"[normal message to {recipient} — not a {MARKER} draft, ignored]\n")


# --------------------------------------------------------------------------- #
# Mode: lark — watch your own outgoing messages, recall→preview→send
# --------------------------------------------------------------------------- #
def run_lark(max_events: int | None) -> None:
    """Consume messages; act only on YOUR own `..`-prefixed drafts.

    NOTE: events arrive only for chats the app can see (DMs with the bot, or
    groups the bot is in). For 1:1s with a real person where the bot isn't a
    member, swap this for a user-token poll of `im +chat-messages-list`.
    Preview is DM'd to you privately; the recipient never sees it until you OK.
    """
    me = profiles.self_entry() or {}
    my_open_id = me.get("open_id") or resolve_self_open_id()
    if not my_open_id:
        print("[mini-me] could not resolve your open_id (run `lark-cli auth login`)", file=sys.stderr)
        return
    print(f"[mini-me] you = {my_open_id}", file=sys.stderr)
    cmd = ["lark-cli", "event", "consume", "im.message.receive_v1"]
    if max_events:
        cmd += ["--max-events", str(max_events)]
    print(f"[mini-me] watching for your `{MARKER}` drafts: {' '.join(cmd)}", file=sys.stderr)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    seen: set[str] = set()
    assert proc.stdout
    for raw in proc.stdout:
        raw = raw.strip()
        if not raw:
            continue
        try:
            evt = json.loads(raw)
        except json.JSONDecodeError:
            continue
        p = parse_event(evt)
        if not p or p["msg_id"] in seen:
            continue
        seen.add(p["msg_id"])
        mine = p["sender"] == my_open_id
        print(f"[recv] from={'me' if mine else p['sender']} chat={p['chat_id']} text={p['text']!r}", file=sys.stderr)

        # chat_room: in-character reply posts back INTO this conversation (as the bot)
        if mine:
            cr = chatroom_route(p["chat_id"], p["text"], p["chat_type"])
            if cr is not None:
                lark("im", "+messages-send", "--chat-id", p["chat_id"], "--text", cr, "--as", "bot")
                continue

        is_my_draft = mine and parse_trigger(p["text"])
        is_my_reply = mine and (my_open_id in PENDING)
        if not (is_my_draft or is_my_reply):
            if not mine:
                print("[skip] not your message — bot only polishes YOUR drafts", file=sys.stderr)
            elif not is_my_draft:
                print(f"[skip] no `{MARKER}` marker and nothing pending", file=sys.stderr)
            continue

        recipient = counterpart_name(p["chat_id"], p["chat_type"], my_open_id)
        reply = handle(my_open_id, p["text"], recipient, p["chat_type"], p["chat_id"], p["msg_id"])
        if reply:  # PRIVATE preview/status -> your own DM, never the conversation
            lark("im", "+messages-send", "--user-id", my_open_id, "--text", reply, "--as", "bot")


def counterpart_name(chat_id: str, chat_type: str, my_open_id: str) -> str:
    """For a p2p chat, resolve the other person's name (so we load their mini-me)."""
    if chat_type != "p2p":
        return chat_id  # group: profiles can key on chat_id
    res = lark("im", "chat.members", "get", "--params", json.dumps({"chat_id": chat_id}), "--as", "user")
    for m in (res.get("data") or {}).get("items", []) or []:
        if m.get("member_id") != my_open_id:
            return m.get("name") or m.get("member_id", chat_id)
    return chat_id


def parse_event(evt: dict) -> dict | None:
    """lark-cli emits a FLAT object (see `lark-cli event schema im.message.receive_v1`):
    top-level chat_id / chat_type / content / message_id / sender_id / message_type.
    For text messages `content` is already plain text. We tolerate an `event` wrapper
    and a legacy JSON-string content just in case."""
    e = evt.get("event") if isinstance(evt.get("event"), dict) else evt
    if (e.get("message_type") or "text") != "text":
        return None
    text = e.get("content", "")
    if isinstance(text, str) and text.startswith("{"):
        try:
            text = json.loads(text).get("text", text)
        except json.JSONDecodeError:
            pass
    chat_id = e.get("chat_id")
    if not (chat_id and text):
        return None
    return {
        "msg_id": e.get("message_id") or e.get("id") or e.get("event_id", ""),
        "chat_id": chat_id,
        "chat_type": e.get("chat_type", "p2p"),
        "sender": e.get("sender_id", ""),
        "text": text,
    }


# --------------------------------------------------------------------------- #
# Mode: poll — for REAL 1:1s where the bot is NOT a member.
#   Uses YOUR user token to watch your own `..` drafts in named teammate chats,
#   recall them, preview privately in your bot DM, and send polished as you on `y`.
#   Approvals are polled from your bot DM (a chat the bot IS in, so it's private).
# --------------------------------------------------------------------------- #
def bot_open_id() -> str:
    res = lark("api", "GET", "/open-apis/bot/v3/info")
    bot = res.get("bot") or (res.get("data") or {}).get("bot") or {}
    return bot.get("open_id", "")


def resolve_user_oid(name: str) -> str:
    res = lark("contact", "+search-user", "--query", name, "--as", "user")
    users = (res.get("data") or {}).get("users") or res.get("users") or []
    return users[0].get("open_id", "") if users else ""


def _msg_text(m: dict) -> str:
    """Pull plain text from a messages-list item across its possible shapes."""
    for k in ("text", "content"):
        v = m.get(k)
        if isinstance(v, str) and v:
            if v.startswith("{"):
                try:
                    return json.loads(v).get("text", "")
                except json.JSONDecodeError:
                    pass
            else:
                return v
    body = m.get("body") or {}
    c = body.get("content")
    if isinstance(c, str):
        if c.startswith("{"):
            try:
                return json.loads(c).get("text", "")
            except json.JSONDecodeError:
                return ""
        return c
    return ""


def list_messages(chat_id: str | None = None, user_oid: str | None = None, page_size: int = 20) -> list[dict]:
    """List recent messages in a chat (by chat_id) or a P2P (by the other party's open_id)."""
    args = ["im", "+chat-messages-list", "--as", "user", "--sort", "desc", "--page-size", str(page_size)]
    args += ["--chat-id", chat_id] if chat_id else ["--user-id", user_oid or ""]
    res = lark(*args)
    data = res.get("data") or res
    items = data.get("items") or data.get("messages") or []
    out = []
    for m in items:
        sender = m.get("sender_id") or ((m.get("sender") or {}).get("id")) or ""
        out.append({
            "id": m.get("message_id") or m.get("id") or "",
            "sender": sender,
            "text": _msg_text(m),
            "chat_id": m.get("chat_id") or (data.get("chat_id") if isinstance(data, dict) else "") or "",
        })
    return [m for m in out if m["id"] and m["text"]]


def run_poll(watch_names: list[str], interval: float, max_loops: int | None) -> None:
    me = profiles.self_entry() or {}
    my_oid = me.get("open_id") or resolve_self_open_id()
    if not my_oid:
        print("[mini-me] cannot resolve your open_id (run `lark-cli auth login`)", file=sys.stderr)
        return
    b_oid = bot_open_id()
    if not b_oid:
        print("[mini-me] cannot resolve the bot open_id", file=sys.stderr)
        return

    # Resolve each watched teammate -> their p2p chat_id (delivery + read target).
    targets: dict[str, dict] = {}  # key -> {name, oid, chat_id}
    for name in watch_names:
        oid = resolve_user_oid(name)
        if not oid:
            print(f"[mini-me] couldn't resolve teammate '{name}' — skipping", file=sys.stderr)
            continue
        first = list_messages(user_oid=oid, page_size=1)
        chat_id = first[0]["chat_id"] if first else ""
        targets[oid] = {"name": name, "oid": oid, "chat_id": chat_id}
        print(f"[mini-me] watching chat with {name} (chat={chat_id or 'unresolved'})", file=sys.stderr)
    if not targets:
        print("[mini-me] nothing to watch — pass --watch <teammate name>", file=sys.stderr)
        return

    # Seed `seen` with everything already present so we only act on NEW messages.
    seen: set[str] = set()
    for t in targets.values():
        for m in list_messages(chat_id=t["chat_id"] or None, user_oid=t["oid"]):
            seen.add(m["id"])
    for m in list_messages(user_oid=b_oid):  # control channel = your bot DM
        seen.add(m["id"])

    def to_me(text: str) -> None:  # private preview/status into your bot DM
        lark("im", "+messages-send", "--user-id", my_oid, "--text", text, "--as", "bot")

    print(f"[mini-me] poll every {interval}s · live={LIVE} · type `{MARKER} draft` in a watched chat", file=sys.stderr)
    loops = 0
    while max_loops is None or loops < max_loops:
        loops += 1
        # 1) new drafts in watched teammate chats
        for t in targets.values():
            for m in reversed(list_messages(chat_id=t["chat_id"] or None, user_oid=t["oid"])):  # oldest first
                if m["id"] in seen:
                    continue
                seen.add(m["id"])
                if m["sender"] != my_oid or not parse_trigger(m["text"]):
                    continue
                target = m["chat_id"] or t["chat_id"] or f"user:{t['oid']}"
                print(f"[draft] to {t['name']}: {m['text']!r}", file=sys.stderr)
                reply = handle(my_oid, m["text"], t["name"], "p2p", target, m["id"])
                if reply:
                    to_me(reply)
        # 2) your approvals (y / n / edit:) in the bot DM
        for m in reversed(list_messages(user_oid=b_oid)):
            if m["id"] in seen:
                continue
            seen.add(m["id"])
            if m["sender"] != my_oid or my_oid not in PENDING:
                continue
            reply = handle(my_oid, m["text"], "", "p2p", f"user:{b_oid}", None)
            if reply:
                to_me(reply)
        if max_loops is None or loops < max_loops:
            time.sleep(interval)


# --------------------------------------------------------------------------- #
def main() -> None:
    global LIVE, SENDER_SLUG
    ap = argparse.ArgumentParser(description="Mini-Me — polish your reply in the live conversation")
    ap.add_argument("mode", choices=["repl", "lark", "poll"],
                    help="repl=local demo · lark=events (chats the bot is in) · poll=real 1:1s via your user token")
    ap.add_argument("--live", action="store_true", help="actually recall/send (else dry-run)")
    ap.add_argument("--as-me", metavar="SLUG", default=None,
                    help="which mini-me's voice to write as (default: lucia, or the owner:self mini-me)")
    ap.add_argument("--max-events", type=int, default=None, help="lark mode: stop after N events")
    ap.add_argument("--watch", action="append", default=[], metavar="NAME",
                    help="poll mode: a teammate whose 1:1 to watch (repeatable)")
    ap.add_argument("--interval", type=float, default=4.0, help="poll mode: seconds between polls")
    ap.add_argument("--max-loops", type=int, default=None, help="poll mode: stop after N polls")
    args = ap.parse_args()
    LIVE = args.live
    if args.as_me:
        SENDER_SLUG = args.as_me
    if args.mode == "repl":
        run_repl()
    elif args.mode == "lark":
        run_lark(args.max_events)
    else:
        run_poll(args.watch, args.interval, args.max_loops)


if __name__ == "__main__":
    main()
