# How This System Works — Big Picture

## What You Built

A local replica of Chris Two — an AI analyst that lets property managers ask plain English questions about their portfolio and get back structured, data-driven answers in seconds.

The user types something like:

> "Give me an owner update for building 3"

And the system returns a full report: occupancy breakdown, financials vs budget, delinquent tenants, upcoming lease expirations.

No SQL. No dashboards. No waiting for a report to be run. Just a question and an answer.

---

## The Four Layers

```
[ User Question ]
       |
       v
[ Layer 4 — Interface ]         terminal input loop in orchestrator.py
       |
       v
[ Layer 3 — Orchestrator ]      sends question to Claude with tools attached;
                                runs the tool-calling loop
       |
       v
[ Layer 2 — Schema Registry ]   tells Claude exactly what columns each building has
       |
       v
[ Layer 1 — Data Layer ]        Postgres database, 8 building schemas, 6 tables each
```

Each layer has one job. They don't bleed into each other. That's what makes the system maintainable and extensible.

> **Note on numbering.** `SYSTEM.md` describes the architecture as four layers. The teaching docs below split Layer 3 (Orchestrator) into three separate units — tools, the tool-calling protocol, and the orchestrator glue — because each is large enough to deserve its own walkthrough. So `03_tools.md`, `04_tool_calling.md`, and `05_orchestrator.md` all live inside Layer 3 of the system architecture.

---

## Why This Is Hard at Scale

The demo uses 8 buildings. The real Chris Two connects to hundreds of tables across a full data platform. Three things break at scale that this demo deliberately exposes:

**Schema drift** — buildings acquired over time don't share the same column names. If you assume a canonical schema, you silently return wrong data with no error. This demo has two intentionally drifted schemas (building_07, building_03) to make this concrete.

**Fan-out latency** — querying 100+ schemas sequentially takes too long. You need parallel execution and partial result handling.

**Context window cost** — passing every schema definition into every Claude call gets expensive fast. Production fix is embedding-based schema retrieval: only pass the tables relevant to the question.

These aren't bugs in the demo. They're talking points — proof you understand the production problem space.

---

## Read These Next

- `01_data_layer.md` — Postgres, schemas, drift
- `02_schema_registry.md` — how Claude knows what columns exist
- `03_tools.md` — how Python functions become Claude tools
- `04_tool_calling.md` — how the Claude loop actually works
- `05_orchestrator.md` — how all four layers connect
