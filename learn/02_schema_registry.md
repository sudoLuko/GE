# Layer 2 — The Schema Registry

## What It Is

A Python dictionary built at startup by querying Postgres directly. It maps every building schema to its actual tables and real column names.

```python
{
  "building_01": {
    "units": ["unit_id", "unit_number", "beds", "baths", "rent_amount", "status"],
    "payments": ["payment_id", "tenant_id", "amount", "payment_date", "method", "late_flag"],
    ...
  },
  "building_07": {
    "units": ["unit_id", "unit_number", "beds", "baths", "rent_amount", "status"],
    "payments": ["payment_id", "tenant_id", "amount", "date_paid", "method", "is_late"],
    ...
  }
}
```

Notice building_07's payments columns differ. The registry captures that difference automatically — it doesn't assume anything.

---

## Why It Exists

Claude is a language model. It doesn't have a live connection to your database. It doesn't know what columns exist. If you just ask it "which tenants paid late last month?", it might write SQL referencing `payment_date` — which works for 7 buildings and silently fails for building_07.

The registry solves this by telling Claude the ground truth upfront:

> "Here is exactly what every building's tables look like. Use this when deciding what SQL to generate or what tools to call."

This is passed into every Claude API call as part of the system prompt.

---

## How It's Built

One query against Postgres's built-in `information_schema`:

```python
cursor.execute("""
    SELECT table_schema, table_name, column_name
    FROM information_schema.columns
    WHERE table_schema LIKE 'building_%'
    ORDER BY table_schema, table_name, ordinal_position
""")
```

`information_schema` is a special read-only schema in every Postgres database that describes the database itself — what schemas exist, what tables, what columns, in what order. You don't maintain it. Postgres keeps it up to date automatically.

The Python code loops over the results and builds the nested dictionary.

---

## How It's Used — Two Jobs

The registry does two things at startup:

**1. Informs Claude** — serialized to JSON and injected into the system prompt so Claude understands every building's actual structure before deciding which tools to call.

**2. Builds the translation map** — passed to `build_translations()` which produces a canonical→actual column mapping for any building with drift:

```python
registry = build_registry(cursor)
translations = build_translations(registry)
```

The translations dict looks like this:
```python
{
    "building_07": {
        "payments": {
            "payment_date": "date_paid",
            "late_flag": "is_late"
        }
    }
}
```

Buildings without drift don't appear in it at all. Tools use it like this:

```python
payment_translations = (translations or {}).get(building, {}).get("payments", {})
date_col = payment_translations.get("payment_date", "payment_date")
# building_07 → "date_paid", all others → "payment_date"
```

The fallback to the canonical name means tools that don't appear in the translations dict just work as normal.

---

## The Translation Layer — COLUMN_ALIASES

The known drift mappings are defined once in `registry/schema_registry.py`:

```python
COLUMN_ALIASES = {
    "payments": {
        "date_paid": "payment_date",   # actual → canonical
        "is_late": "late_flag"
    }
}
```

`build_translations()` reads the actual registry and uses `COLUMN_ALIASES` to figure out which buildings have drifted columns and in what direction. It inverts the mapping (actual→canonical becomes canonical→actual) so tools can look up "what's the real column name for `payment_date` in this building?"

This is the single source of truth for all drift in the system. Adding a new drifted building means updating `COLUMN_ALIASES` once — no tool files change.

---

## Why This Matters at Scale

In the demo, the registry is small enough to fit comfortably in Claude's context window. At scale (hundreds of buildings, dozens of tables each), the full registry would be enormous — and expensive to pass on every call.

The production solution is **embedding-based schema retrieval**: convert every table description into a vector embedding, store it in a vector database, and at query time retrieve only the schemas relevant to the question being asked.

For example, a question about lease expirations only needs the `leases` table definition — not the full schema for all 8 buildings. Retrieval cuts context window cost dramatically.

This is a concrete architectural improvement you can propose in the conversation with Great Expectations.
