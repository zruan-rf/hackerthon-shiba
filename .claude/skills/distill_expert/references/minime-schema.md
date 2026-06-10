# The Mini-Me profile

A **mini-me** is a distilled, reusable persona of a real person. It has two jobs:

1. **How to treat them** — so others know how to reach this person (the *Comms Card* part).
2. **How they talk** — so the mini-me can speak/act *as* them (the *Voice* part).

That second part is what makes a mini-me more than a Comms Card: it can be *talked to*
(`/chat_room`) or *speak on your behalf* (`/echo_me`).

Treat MBTI and any inferred trait as a **starting hypothesis about preferences**, never a verdict
on ability or worth. Explicit user input and observed chat samples always override type defaults.
Speak in tendencies ("tends to", "usually"), avoid clinical claims, and never invent biographical
facts the user didn't give.

Each mini-me is one folder in the library: `mini-me/<slug>/profile.json` (source of truth) plus a
generated `mini-me/<slug>/card.md` (human-readable, regenerated on every write — never hand-edit it).

---

## profile.json schema

```json
{
  "id": "aria-ruan",
  "name": "Aria Ruan",
  "slug": "aria-ruan",
  "role": "",
  "owner": "self",                        // self = my own mini-me | other = someone else's
  "open_id": "",                          // filled via lark-contact when known
  "status": "newborn",                    // newborn -> growing -> ready
  "created_at": "2026-06-10T21:00:00Z",
  "updated_at": "2026-06-10T21:00:00Z",

  "personality": {
    "mbti": "",                           // e.g. ENFP (or "" if unknown)
    "summary": "",                        // 1-2 sentence read on the person
    "traits": []                          // freeform tags: ["warm", "fast-moving", "visual"]
  },

  "comms": {                              // how to TREAT them (the Comms Card half)
    "directness": "balanced",             // direct | balanced | diplomatic
    "detail_level": "balanced",           // headline-first | balanced | deep-dive
    "pace": "flexible",                   // async-first | flexible | real-time
    "convinced_by": [],                   // logic, data, vision, people-impact, harmony,
                                          //   autonomy, efficiency, recognition, proven-examples
    "preferred_channels": [],             // im, email, doc, call, in-person, meeting
    "response_time": "",
    "pet_peeves": [],                     // the "please don't" list
    "best_move": "",                      // single most effective way to reach them
    "one_liner": ""                       // their self-summary blurb
  },

  "voice": {                              // how they TALK (the mimicry half)
    "tone": "",                           // e.g. "upbeat, playful, encouraging"
    "formality": 3,                       // 1 = very casual ... 5 = very formal
    "warmth": 3,                          // 1 = blunt ... 5 = very warm
    "verbosity": 3,                       // 1 = terse ... 5 = expansive
    "emoji_usage": "some",                // none | rare | some | heavy
    "humor": "",                          // dry | playful | none | self-deprecating ...
    "languages": ["en"],                  // they may code-switch, e.g. ["en", "zh"]
    "greetings": [],                       // how they open: ["hey!", "yo"]
    "sign_offs": [],                       // how they close: ["thanks!", "lmk"]
    "catchphrases": [],                    // recurring words/phrases
    "quirks": []                           // ["lowercase only", "double-texts", "lots of ellipses…"]
  },

  "samples": [                            // few-shot examples for mimicry; the more the better
    { "text": "", "context": "", "source": "self-described | pasted | lark-im", "added_at": "" }
  ],

  "topics": [],                           // what they tend to talk about / their expertise
  "boundaries": [                          // what the mini-me must NOT do when speaking as them
    "Never make real commitments, approvals, or promises on the person's behalf.",
    "Never invent facts, numbers, or events; flag anything you're unsure of.",
    "Never share anything the person would consider private or confidential."
  ],

  "provenance": {                         // where the distillation came from (for trust + grow)
    "sources": [],                        // ["self-description", "pasted-chat", "lark-im:oc_xxx"]
    "sample_count": 0,
    "last_grown_at": ""
  }
}
```

### Field guide
- **owner** — `self` (your own mini-me, used by `/echo_me`) or `other` (someone else's, used by
  `/chat_room` and for `/decode`-style "how do I reach them" lookups).
- **status** — `newborn` (just `/born`, mostly empty) → `growing` (some data) → `ready` (enough to
  mimic confidently: has voice + ≥3 samples *or* a solid self-description). The script computes a
  suggested status on each write; you may set it explicitly.
- **comms.\*** — defaults can be seeded from MBTI axes (see below) then overridden by what the
  person actually says. Same dials as the Comms Card so the two stay interoperable.
- **voice.\*** — the heart of the mini-me. Prefer evidence from `samples` over type guesses. If you
  only have a self-description, fill what's stated and leave the rest at neutral defaults.
- **samples** — short, representative lines in the person's real voice. 3-10 is plenty. These are
  the strongest signal for mimicry — one good sample beats a page of adjectives.
- **boundaries** — always present; a mini-me speaks in someone's *style*, never with their
  *authority*. Add person-specific don'ts here too.

### MBTI axis → defaults (seed only; samples override)
Use as gentle priors when the user gives a type but few prefs. Never treat as fact.
| Axis | Lean | Seed |
|---|---|---|
| **E / I** | E | `pace: real-time`, higher `warmth`, more `greetings` |
| | I | `pace: async-first`, `channels: [doc, im]` |
| **S / N** | S | `detail_level: deep-dive`, `convinced_by: [data, proven-examples]` |
| | N | `detail_level: headline-first`, `convinced_by: [vision]` |
| **T / F** | T | `directness: direct`, `convinced_by: [logic, efficiency]`, lower `warmth` |
| | F | `directness: diplomatic`, `convinced_by: [people-impact, harmony]`, higher `warmth` |
| **J / P** | J | `pet_peeves: [last-minute changes]`, `best_move: lead with the decision` |
| | P | `tone` more exploratory, comfortable with open-ended asks |

---

## card.md (generated)
A friendly one-screen view, regenerated from `profile.json` on every write. Example:

```
🧬  Aria Ruan  ·  ENFP  ·  owner: self  ·  status: ready
"Big-picture first, then let's riff — keep it warm and fast."

🗣️  Voice:   upbeat & playful · casual (2/5) · warm (5/5) · some emoji · code-switches en/zh
            opens with "hey!" · signs off "lmk!" · quirk: lots of ellipses…
✅ Reach me by:   im first, doc for anything long; convince me with vision + people-impact
⏱️ Response time:   fast on IM, same-day on email
🚫 Please don't:   bury the point under process, or spring a hard deadline last-minute
💬 Sounds like:   "ooh yes let's do it — but can we make it cuter? 😄"
🧪 Samples on file:   4   ·   last grown: 2026-06-10
```
