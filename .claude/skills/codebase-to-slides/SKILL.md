---
name: codebase-to-slides
description: Generate a fun, cute "slide deck" summarizing a codebase change and upload it to Google Drive as a Google Doc. Use when asked to "make slides/a deck for this commit/diff/change", "summarize the latest changes", or when triggered automatically by the post-commit hook. No local build step — the deck is composed as text and uploaded via the Google Drive MCP (which converts text/plain into a Google Doc).
allowed-tools: Bash, mcp__claude_ai_Google_Drive__create_file, mcp__claude_ai_Google_Drive__search_files
---

# Codebase → Cute Deck (Google Drive)

Turn a codebase change into a short, **humorous, vivid, vibrant, and cute** "slide deck" and drop
it in Google Drive as a Google Doc. Default target is the latest commit (`HEAD`); the caller may
pass a different ref or range.

> Why a Google Doc and not a .pptx? Google Drive's MCP only accepts `text/plain` (→ Google Doc)
> or `text/csv` (→ Sheet) for content uploads — it rejects wrapped base64 and can't take a
> populated .pptx. So we ship a text deck that auto-converts to a Doc. Cute comes from emojis,
> Unicode dividers, and playful copy.

## Steps

### 1. Gather the change
Resolve paths relative to the repo root (`git rev-parse --show-toplevel`).
```bash
git rev-parse --short HEAD
git log -1 --format='%h%n%an%n%ad%n%s%n%b' --date=short <ref>
git show --stat --format='' <ref>          # files changed + insertions/deletions
git diff --stat <ref>~1 <ref> 2>/dev/null || git show --stat <ref>   # handles the first commit
```
Then read a **bounded** diff for context (don't dump huge diffs):
```bash
git diff <ref>~1 <ref> 2>/dev/null | head -c 12000 \
  || git diff 4b825dc642cb6eb9a060e54bf8d69288fbee4904 <ref> | head -c 12000   # first commit
```

### 2. Compose the cute deck (FUN 🎉)
Tone: **humorous, vivid, vibrant, cute** — a celebration of the commit, while staying accurate.
Build a plain-text deck (it becomes a Google Doc). Each "slide" is a section with a big emoji
header, a Unicode divider, and witty one-line bullets. Sprinkle emojis generously.

Aim for a title block + 3–5 sections, e.g. **What happened** (the story, with flair),
**Changes by area** (grouped by file/module), **The cool bits** (clever/notable code),
**The receipts** (files / +adds / −dels, framed dramatically), **What's next / watch out**.

Template (adapt the words, keep it punchy):
```
🎉  COMMIT <shorthash> JUST DROPPED!  🚀
<commit subject>   ·   <author>   ·   <date>
hackerthon-shiba   ·   freshly baked 🍪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🧐  WHAT HAPPENED
   🌸  <one-line, witty>
   🌸  <one-line, witty>

🗂️  CHANGES BY AREA
   ✨  <path>: <what changed>
   ✨  <path>: <what changed>

✨  THE COOL BITS
   🌟  <notable decision / clever bit>

📊  THE RECEIPTS
   📦  <N> files changed
   ➕  +<adds>  /  ➖  −<dels>
   ☕  0 meetings required

🔮  WHAT'S NEXT / WATCH OUT
   🎈  <next step or risk>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
Keep bullets to one witty line each. Blank lines between sections give the Doc breathing room.

### 3. Find the Drive folder
Reuse the cached folder id; otherwise locate or create the folder **"hackerthon-shiba Auto Slides"**.
- If `.claude/skills/codebase-to-slides/.drive_folder_id` exists and is non-empty, read it (`cat`).
- Else `search_files` for `title = 'hackerthon-shiba Auto Slides' and mimeType = 'application/vnd.google-apps.folder'`.
  Note: `owners`/`owner` is **not** a supported query field here — don't add it.
- Else `create_file` with `mimeType: application/vnd.google-apps.folder` and that title.
- Cache the resulting id into `.claude/skills/codebase-to-slides/.drive_folder_id`.

### 4. Upload as a Google Doc
Call `create_file`:
- `title`: `Commit <shorthash> — <short subject> 🎉`
- `parentId`: the folder id from step 3
- `textContent`: the full deck text from step 2
- `contentMimeType`: `text/plain`   (this auto-converts to a Google Doc — do **not** set `disableConversionToGoogleType`)

### 5. Report
Print the new Doc's `viewUrl` (or id) and a one-line summary of what the deck covers.

## Notes
- Never create git commits from this skill (it runs inside a post-commit hook — committing would recurse).
- Emojis and Unicode dividers survive the text→Doc conversion; rich color/styling does not (text/plain).
- If the Google Drive MCP is unavailable, write the deck text to
  `.claude/skills/codebase-to-slides/logs/deck-<shorthash>.txt` and report its path instead.
