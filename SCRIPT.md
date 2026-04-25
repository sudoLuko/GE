# Loom Script — Great Expectations Internship

## Goal

Show Ben Maritz three things in two minutes:
1. You understand his problem from the outside
2. You're motivated enough to build something on your own time
3. You can contribute on day one

---

## Structure

### Opening — 20 seconds
Do NOT start with your name or "I'm applying for the internship." Ben knows who you are. Start with the action.

> "I saw your post about Chris Two and I wanted to show you what I built this weekend."

That one sentence signals this is different from every other follow up he's received.

---

### The Demo — 45 seconds
Two queries maximum. Let the system speak — don't over explain while it's running.

**Query 1 — Owner update report**
```
"Give me an owner update for building 3"
```
This directly mirrors the Crossroads Garden Apartments output Ben showed publicly in his Teams screenshot. He will recognize it immediately.

**Query 2 — Portfolio wide delinquency**
```
"Which buildings had the highest late payment rate last month?"
```
This shows fan-out across multiple schemas — the interesting architectural piece.

While the queries run, briefly narrate what is happening under the hood — Claude deciding which tools to call, the orchestrator firing SQL against the correct building schemas, results being fed back for synthesis.

---

### Engineering Design Decisions — 60 seconds
Frame every decision as "I chose X because Y, but in production at your scale I'd do Z."

**Decision 1 — Tool functions not text-to-SQL**
Claude doesn't generate raw SQL strings. It calls a fixed set of parameterized functions whose queries are written and version controlled by engineers. Text-to-SQL hallucinates joins, can't reason about schema drift, and opens a prompt injection surface. Tool functions move SQL correctness into code that can be tested and evolved.

**Decision 2 — Schema registry built from information_schema**
At startup the system queries Postgres's information_schema and builds a live dictionary of every table and column across all 8 building schemas. Postgres is the source of truth so the registry can never go stale on its own. This is also the surface where schema drift gets handled — each building reports its actual column names and the canonical translation layer maps them before anything reaches the LLM.

**Decision 3 — Intentional schema drift on two buildings**
building_07 uses date_paid and is_late instead of payment_date and late_flag. building_03 has an extra subsidized column on units. This simulates what happens when you acquire buildings managed by different companies over time. The canonical translation layer aliases every drifted column back to its canonical name at query time so the LLM never sees the drift at all.

---

### Meta Level Thinking — 30 seconds
This is where you show you're thinking about the system as a product not just a codebase. Ben came from McKinsey — he thinks in tradeoffs and unit economics. This section is for him.

**Prompt caching**
The schema registry gets inlined into the system prompt and re-sent on every API call right now. With Anthropic's prompt caching that is a one line change that cuts input token cost by roughly 90% on repeat queries.

**Model routing**
An owner update needs Opus level reasoning. "How many vacant units in building 5?" doesn't. A small router sending simple queries to Haiku and complex synthesis to Opus cuts cost significantly without a quality regression — provided you have an eval suite to catch regressions.

**The cost math**
A single owner update query runs roughly 12k input tokens and 1.5k output tokens. Without optimization on Opus that is around $0.15 per query. With prompt caching and model routing that drops to around $0.02. At 50 queries per manager per day across 100 managers that is the difference between $200k a year and $30k a year. Two engineering decisions, not new infrastructure.

---

### Close — 20 seconds
End with one genuine open question and a direct ask.

**The question** — pick one of these based on what feels most natural:
- "I couldn't figure out from the outside whether Chris Two reads directly from operational databases or from dbt models in Maynard — the right schema registry pattern depends on that answer and I'd love to understand how you've approached it."
- "I'd be curious whether you're thinking about the read to write transition yet — I have some thoughts on the approval flow and idempotency that I'd love to run by you."

**The ask** — direct, no hedging:
> "I'd love to get on a call this week to talk about the internship. Here's my calendar link."

Not "if you have time." Not "I know you're busy." Just the ask.

---

## The Two Layers You Are Signaling

**Engineering layer** — schema registry, canonical translation, tool calling orchestration, schema drift, fan-out latency. Shows you understand how the system works and could contribute technically on day one.

**Meta layer** — prompt caching, model routing, cost per query. Shows you're thinking about the system as a product. Ben came from McKinsey, he thinks in tradeoffs and unit economics constantly. When you drop the $200k vs $30k number he is going to lean forward.

Most junior candidates can talk about one layer. You are walking in with both.

---

## The Email That Wraps the Loom

Three sentences maximum.

> "Ben — I know you're busy so I recorded a 2 minute video instead of a long email. [Loom link]. Happy to connect whenever works for you — here's my calendar link."

Nothing else. The Loom is the content.

---

## Timing

| Section | Time |
|---|---|
| Opening | 20 seconds |
| Demo | 45 seconds |
| Engineering decisions | 60 seconds |
| Meta level thinking | 30 seconds |
| Close | 20 seconds |
| **Total** | **~2 minutes 55 seconds** |

---

## Key Messages

- "I built a local version of Chris Two this weekend to show you I understand the problem from the outside."
- "Schema drift across acquired buildings is the production problem you actually have. The registry pattern in this demo is the production ready answer to it."
- "From demo to production the two biggest wins are prompt caching and model routing — together they cut cost by an order of magnitude with two engineering decisions."
- "I'd love to work on this with your team."