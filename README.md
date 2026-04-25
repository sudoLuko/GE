# Chris Two Demo — AI Property Management Analyst

Local proof-of-concept replicating the query layer of Chris Two, the internal AI analyst built by Great Expectations (grtexp.co). Connects to a multi-tenant Postgres database and allows staff to ask natural language questions about their property portfolio.

## Purpose

Built as interview preparation for the Great Expectations engineering team. Demonstrates production-ready patterns for AI agents in financial and affordable housing compliance contexts.

## Architecture

```
User (terminal)
    ↓
orchestrator.py  ← Anthropic API with tool calling
    ↓                     ↓
Schema Registry    Tool Functions (Python → SQL)
(information_schema)    ↓
                    Postgres (8 schemas, schema-per-building)
```

## What's Here

### Core
- **`orchestrator.py`** - Tool calling loop: User query → Claude decides tools → Python executes SQL → Claude synthesizes answer
- **`registry/schema_registry.py`** - Dynamic schema registry built from `information_schema`, handles drift across acquired buildings
- **`tools/*.py`** - 8 tool functions: occupancy, financials, delinquency, lease expirations, work orders, etc.

### Data
- **`seed/create_schemas.py`** - Creates 8 building schemas with intentional drift (building_07, building_03)
- **`seed/seed_data.py`** - Populates with Faker-generated data
- **`seed/SEED.md`** - Data model documentation

### Research Notes
- **`learn/00_overview.md`** - Project overview
- **`learn/01_data_layer.md`** - Multi-tenant Postgres design
- **`learn/02_schema_registry.md`** - Handling schema drift
- **`learn/03_tools.md`** - Tool function design
- **`learn/04_tool_calling.md`** - Anthropic tool calling patterns
- **`learn/05_orchestrator.md`** - Orchestration loop
- **`learn/PROD_IMPROVEMENTS.md`** - Production readiness analysis (AI layer, security, compliance, cost optimization)
- **`learn/SYSTEM.md`** - Full system context and architecture

## Key Design Decisions

| Decision | Why |
|---|---|
| **Tool functions, not text-to-SQL** | SQL correctness in reviewed code, not LLM generation |
| **Schema registry from `information_schema`** | Registry can't go stale; drift handled centrally via `COLUMN_ALIASES` |
| **Read-only by default** | Write operations need human approval flows |
| **Affordable housing compliance** | AMI/LIHTC data = higher trust tier (Fair Housing Act exposure) |

## Stack

- **Database**: Postgres (multi-tenant, schema-per-building)
- **Orchestration**: Python + Anthropic API (tool calling)
- **Seed data**: Faker library
- **Schema registry**: Built from `information_schema` at startup

## Demo Queries

```
"Give me an owner update for building 3"
"Which buildings had the highest late payment rate last month?"
"Show me all units with leases expiring in the next 60 days"
```

## Production Gap (Documented in `learn/`)

The demo deliberately proves tool functions, schema drift handling, and read→write transition. `PROD_IMPROVEMENTS.md` covers what's needed for production:

- Prompt caching (biggest cost win)
- Async fan-out (parallel tool execution)
- RLS-backed RBAC
- Eval suite for regression testing
- Prompt injection hardening
- AMI/LIHTC compliance safeguards
