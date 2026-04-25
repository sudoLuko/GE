# Tools (part of Layer 3)

## What a Tool Is

A tool is two things packaged together:

1. **A JSON schema** — tells Claude the tool exists, what it does, and what arguments it takes
2. **A Python function** — executes SQL against the database when Claude calls the tool

Claude never runs your Python directly. It reads the schema, decides to call the tool, and tells you what arguments to use. Your Python code does the actual execution and hands the result back.

---

## The JSON Schema

Every tool file defines a `SCHEMA` dict that gets sent to the Anthropic API:

```python
SCHEMA = {
    "name": "get_occupancy",
    "description": "Returns occupancy breakdown for a specific building...",
    "input_schema": {
        "type": "object",
        "properties": {
            "building": {
                "type": "string",
                "description": "The schema name of the building e.g. building_01"
            }
        },
        "required": ["building"]
    }
}
```

Three things Claude uses this for:
- **`name`** — what to call the tool when it wants to use it
- **`description`** — how to decide whether this tool is relevant to the question
- **`input_schema`** — what arguments to pass and in what format

The `required` array is how you make parameters optional — anything not listed there is optional. Claude will only pass it if it has a value for it.

---

## The Python Function

```python
def get_occupancy(building: str, cursor, translations: dict = None) -> dict:
    cursor.execute(sql.SQL("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'occupied') as occupied,
            COUNT(*) FILTER (WHERE status = 'vacant') as vacant,
            COUNT(*) FILTER (WHERE status = 'on_notice') as on_notice
        FROM {}.units
    """).format(sql.Identifier(building)))

    row = cursor.fetchone()
    return {
        "building": building,
        "total": row[0],
        "occupied": row[1],
        "vacant": row[2],
        "on_notice": row[3]
    }
```

A few things to note:

**`cursor` and `translations` are not in the schema** — Claude doesn't know about them and doesn't pass them. The orchestrator injects them when calling the function. Claude only passes the arguments listed in `input_schema`. `translations` carries the drift map (see below); tools that don't need it accept it as `translations=None` and ignore it.

**`sql.Identifier(building)`** — this safely interpolates the building name into the SQL query. Never use Python string formatting to build SQL — that's a SQL injection vulnerability. `sql.Identifier` escapes it correctly.

**`row[0]`, `row[1]`** — psycopg2 returns rows as plain tuples. The index corresponds to the order of columns in the SELECT statement, not the table definition.

---

## The Five Tools Wired into the Orchestrator

| Tool | What It Returns | Optional Params |
|---|---|---|
| `get_occupancy` | total / occupied / vacant / on_notice counts | — |
| `get_financials` | all 5 P&L line items with actual, budget, variance | `period` (YYYY-MM) |
| `get_delinquency` | tenants with late payments, with names and amounts | `months_back` |
| `get_lease_expirations` | leases expiring soon with tenant names and days remaining | `days` (default 60) |
| `get_work_orders` | maintenance requests with unit and age | `status` filter |

The `tools/` directory also contains `leases.py`, `payments.py`, and `tenants.py` — earlier scaffolding that exposes raw row reads. They are not imported by `orchestrator.py` because the demo's three target queries (owner update, portfolio delinquency, lease expirations) don't need them, and shipping fewer tools means cleaner tool selection by Claude. They're kept in the tree as reference and as an obvious place to extend.

---

## Handling Schema Drift in Tools

Tools always use **canonical column names** — `payment_date`, `late_flag`. They never hardcode building-specific column names or query `information_schema` themselves.

Instead, the orchestrator passes a `translations` dict built by the schema registry at startup. Every tool accepts it:

```python
def get_delinquency(building: str, cursor, translations: dict = None, months_back: int = 1) -> dict:
    payment_translations = (translations or {}).get(building, {}).get("payments", {})
    date_col = payment_translations.get("payment_date", "payment_date")
    late_col = payment_translations.get("late_flag", "late_flag")
```

For building_07, `translations["building_07"]["payments"]["payment_date"]` is `"date_paid"` — so `date_col` becomes `"date_paid"` and the SQL works correctly. For every other building, the key doesn't exist in translations, so the fallback `"payment_date"` is used.

Tools that don't have drifted columns (occupancy, financials, etc.) accept `translations=None` and ignore it. The orchestrator passes it uniformly to all tools so `run_tool` stays simple.

The drift knowledge lives in one place — `COLUMN_ALIASES` in `schema_registry.py`. Adding a new drifted building means updating that dict once. No tool files change.

---

## Why Separate Files Per Tool

Each tool is its own file (`occupancy.py`, `financials.py`, etc.) rather than one big `tools.py`. This makes it easy to:

- Add a new tool without touching existing ones
- Read and understand one tool in isolation
- Validate a tool's schema against the database independently

The orchestrator imports all of them and assembles them into a single list to pass to Claude.
