# Chris Two Demo — System Context for Claude Code

Research notes prepared for Great Expectations application interview

## What We Are Building

A local proof-of-concept that replicates the core query layer of Chris Two — the internal AI analyst built by Great Expectations (grtexp.co), a vertically integrated affordable housing company based in the Pacific Northwest. Chris Two lives in Microsoft Teams and Telegram, connects to hundreds of tables across their internal data platform (Maynard) and operational databases, and allows staff to ask natural language questions about their property portfolio and receive structured, data-driven answers in seconds.

This demo replicates that query layer locally using a multi-tenant Postgres database, Python orchestration, and the Anthropic API with tool calling.

The goal is not to replicate Chris Two in full. The goal is to demonstrate a deep enough understanding of the problem space to have a credible technical conversation with the Great Expectations engineering team.

---

## Architecture

The system has four layers:

### Layer 1 — Data Layer

A single Postgres database (`ge_demo`) running in a Docker container. Inside it, 8 schemas each represent one building in the portfolio. This mirrors how a real multi-tenant property management platform separates tenant data.

Each schema contains 6 tables: `units`, `tenants`, `leases`, `payments`, `work_orders`, `financials`.

Two schemas have intentional drift to simulate real acquisition history:
- `building_07.payments` uses `date_paid` and `is_late` instead of `payment_date` and `late_flag`
- `building_03.units` has an extra `subsidized BOOLEAN` column

Seed data is generated with the Python Faker library.

### Layer 2 — Schema Registry

A Python dictionary built dynamically by querying Postgres `information_schema` at startup. Maps each building schema to its actual table structure and real column names. Handles drift by exposing the actual column names per building rather than assuming a canonical schema. This is passed as context into each LLM call so Claude can generate correct SQL per building.

### Layer 3 — Tool Calling Orchestration

The Anthropic API with tool calling enabled. Five tools are defined as Python functions that execute SQL against the correct building schema:

- `get_occupancy` — occupancy breakdown per building
- `get_financials` — actual vs budget vs variance per line item
- `get_delinquency` — tenants with late or outstanding payments
- `get_lease_expirations` — leases expiring within a given window
- `get_work_orders` — open maintenance requests with age in days

The orchestration loop works as follows:
1. User submits a natural language question
2. Claude receives the question and schema registry context
3. Claude decides which tools to call and in what order
4. Python executes the corresponding SQL against the correct schema
5. Results are returned to Claude
6. Claude decides if additional tool calls are needed
7. Claude synthesizes all results into a structured report

### Layer 4 — Interface

Minimal terminal interface. User types a question, system returns a structured answer. Optionally a FastAPI endpoint for a more visual demo.

---

## Table Schemas

**units**
```
unit_id        SERIAL PRIMARY KEY
unit_number    VARCHAR(10)
beds           INT
baths          INT
rent_amount    DECIMAL
status         VARCHAR(20)    -- 'occupied', 'vacant', 'on_notice'
-- building_03 only: subsidized BOOLEAN
```

**tenants**
```
tenant_id      SERIAL PRIMARY KEY
unit_id        INT
first_name     VARCHAR(50)
last_name      VARCHAR(50)
email          VARCHAR(100)
phone          VARCHAR(20)
move_in_date   DATE
move_out_date  DATE
```

**leases**
```
lease_id       SERIAL PRIMARY KEY
unit_id        INT
tenant_id      INT
start_date     DATE
end_date       DATE
monthly_rent   DECIMAL
```

**payments**
```
payment_id     SERIAL PRIMARY KEY
tenant_id      INT
amount         DECIMAL
payment_date   DATE        -- building_07 uses date_paid
method         VARCHAR(20)
late_flag      BOOLEAN     -- building_07 uses is_late
```

**work_orders**
```
work_order_id  SERIAL PRIMARY KEY
unit_id        INT
description    TEXT
status         VARCHAR(20)
opened_date    DATE
closed_date    DATE
```

**financials**
```
financial_id   SERIAL PRIMARY KEY
line_item      VARCHAR(100)
actual         DECIMAL
budget         DECIMAL
variance       DECIMAL
period         VARCHAR(20)
```

---

## File Structure

```
chris-two-demo/
├── docker-compose.yml
├── seed/
│   ├── create_schemas.py       -- creates 8 building schemas and all tables
│   └── seed_data.py            -- populates tables with Faker data
├── registry/
│   └── schema_registry.py      -- dynamically builds schema map from information_schema
├── tools/
│   ├── occupancy.py
│   ├── financials.py
│   ├── delinquency.py
│   ├── lease_expirations.py
│   └── work_orders.py
├── orchestrator.py             -- Anthropic tool calling loop
└── main.py                     -- entry point
```

---

## Tech Stack

- Docker — Postgres container
- Postgres — database server, schema-per-tenant pattern
- Python — orchestration, SQL execution via psycopg2
- Anthropic API — Claude with tool calling
- Faker — seed data generation
- FastAPI (optional) — web interface for demo

---

## Demo Queries

These are the three queries the demo is built around:

**1. Owner update report**
```
"Give me an owner update for building 3"
```
Triggers get_occupancy, get_financials, get_delinquency, get_lease_expirations. Output mirrors the owner update format Ben Maritz demonstrated publicly — occupancy breakdown, vacancy analysis, financials with actual vs budget variance.

**2. Portfolio-wide delinquency**
```
"Which buildings had the highest late payment rate last month?"
```
Triggers get_delinquency across all 8 schemas. Tests fan-out and cross-schema aggregation.

**3. Upcoming lease expirations**
```
"Show me all units with leases expiring in the next 60 days across the portfolio"
```
Triggers get_lease_expirations across all schemas. Tests parallel querying and aggregation.

---

## Known Failure Points at Scale

These are intentional discussion points for the conversation with Great Expectations:

**Schema drift** — buildings acquired over time diverge in column names and structure. An LLM assuming a canonical schema silently returns incomplete results with no error. Production fix: formal schema registry with migration tooling and drift detection.

**Fan-out latency** — querying 20+ schemas sequentially is too slow. Production fix: parallelized query execution with partial result handling.

**Context window cost** — passing all schema definitions into every LLM call becomes expensive at scale. Production fix: embedding-based schema retrieval, only pass relevant tables per query.

**Hallucination on compliance data** — incorrect answers on AMI certifications or affordability restrictions are a legal liability, not just a bug. Production fix: output validation, human review workflows, confidence signaling.

---

## Current State

Docker container is running with `ge_demo` database created. Schema creation script (`create_schemas.py`) is in progress — all 8 schemas and 6 tables per schema, with drift applied to `building_07.payments` and `building_03.units`. Next step is to finish and run the schema creation script, then move to seed data.