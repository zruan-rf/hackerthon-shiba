# The Comms Card

A Comms Card is how a person **distills themselves** into a small, shareable, reusable profile.
It has two parts: a friendly human-readable summary, and a JSON block for storage/reuse.

## Human-readable summary (what teammates see)
```
🪪  Sam Chen — VP Engineering   ·   INTJ
"Send me the headline + the ask up front. I love data, hate surprises."

✅ Reach me by:   async (Slack/doc) first, then a short call to decide
✅ Convince me with:   crisp logic, trade-offs, a number or two
✅ Detail level:   headline → details on demand (don't bury the point)
⏱️ Response time:   a few hours on Slack; same-day on email
🚫 Please don't:   spring last-minute changes, or open with small talk for 3 paragraphs
💡 Best move:   "Decision needed by Fri: option A vs B. Here's the 2-line why."
```

## JSON block (for Lark Base / reuse)
Store one row per person. Suggested Lark Base columns map 1:1 to these keys.
```json
{
  "name": "Sam Chen",
  "role": "VP Engineering",
  "open_id": "",                       // filled via lark-contact when stored in Lark
  "mbti": "INTJ",
  "directness": "direct",              // direct | balanced | diplomatic
  "detail_level": "headline-first",    // headline-first | balanced | deep-dive
  "pace": "async-first",               // async-first | flexible | real-time
  "convinced_by": ["logic", "data", "efficiency"],
  "preferred_channels": ["slack", "doc", "short-call"],
  "response_time": "Slack: hours; email: same-day",
  "pet_peeves": ["last-minute changes", "long preamble before the point"],
  "best_move": "Lead with the decision + a 2-line why; offer A vs B.",
  "one_liner": "Headline + ask up front. Loves data, hates surprises."
}
```

## Field guide
- **directness / detail_level / pace** — the three dials people differ on most; derive defaults
  from the MBTI axes (T→direct, S→detail, I→async) then adjust to what the person actually says.
- **convinced_by** — pick from: logic, data, vision, people-impact, harmony, autonomy, efficiency,
  recognition, proven-examples.
- **preferred_channels** — slack/IM, email, doc/async, call, in-person, meeting.
- **pet_peeves** — the "please don't" list; this prevents the most common hiccups.
- **best_move** — one tactical sentence: the single most effective way to communicate with them.
- **one_liner** — their self-summary; great as a status or profile blurb.

## Suggested Lark Base table
| Column | Type |
|---|---|
| Name | Text |
| Role | Text |
| Open ID | Text |
| MBTI | Single select |
| Directness | Single select |
| Detail level | Single select |
| Pace | Single select |
| Convinced by | Multi-select |
| Preferred channels | Multi-select |
| Response time | Text |
| Pet peeves | Text |
| Best move | Text |
| One-liner | Text |
| Card JSON | Text (the full JSON above) |
