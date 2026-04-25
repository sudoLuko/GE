# Layer 1 — The Data Layer

## What It Is

A single Postgres database called `ge_demo` running in Docker. Inside it, 8 schemas each represent one building in the portfolio.

A **schema** in Postgres is like a namespace — a folder inside the database that contains its own set of tables. So instead of one giant `units` table with a `building_id` column, each building gets its own isolated `units` table:

```
ge_demo/
├── building_01/
│   ├── units
│   ├── tenants
│   ├── leases
│   ├── payments
│   ├── work_orders
│   └── financials
├── building_02/
│   └── (same 6 tables)
...
└── building_08/
    └── (same 6 tables)
```

This pattern is called **schema-per-tenant**. It mirrors how real property management platforms separate data when buildings are acquired from different sources over time.

---

## The Six Tables

**units** — the physical units in the building
```
unit_id, unit_number, beds, baths, rent_amount, status
status is one of: 'occupied', 'vacant', 'on_notice'
```

**tenants** — people currently or previously renting
```
tenant_id, unit_id, first_name, last_name, email, phone, move_in_date, move_out_date
```

**leases** — the legal agreements
```
lease_id, unit_id, tenant_id, start_date, end_date, monthly_rent
```

**payments** — monthly rent payments
```
payment_id, tenant_id, amount, payment_date, method, late_flag
```

**work_orders** — maintenance requests
```
work_order_id, unit_id, description, status, opened_date, closed_date
status is one of: 'open', 'in_progress', 'closed'
```

**financials** — monthly P&L summary per building
```
financial_id, line_item, actual, budget, variance, period
line_items: Gross Potential Rent, Vacancy Loss, Effective Gross Income, Operating Expenses, Net Operating Income
period format: 'YYYY-MM' (6 months of history per building)
```

---

## Schema Drift — The Critical Concept

Two buildings have intentionally different schemas to simulate real acquisition history.

**building_07.payments** uses different column names:
- `date_paid` instead of `payment_date`
- `is_late` instead of `late_flag`

**building_03.units** has an extra column:
- `subsidized BOOLEAN` — whether the unit is part of a subsidy program

This is realistic. When a company acquires a building, the data comes from whatever system the previous owner used. Forcing immediate migration is expensive and risky. So drift accumulates.

The danger: if your AI system assumes every building has `payment_date`, it silently fails on building_07 — no error, just missing data. This is why the schema registry exists.

---

## The Seed Data

`seed/create_schemas.py` — creates all 8 schemas and their tables (with drift applied)
`seed/seed_data.py` — populates every table with realistic fake data using the Faker library

Each building gets:
- 25 units (unit numbers 101–125)
- Tenants for all non-vacant units
- 12-month leases per tenant
- 4 months of payment history (15% of tenants are habitual late payers)
- 10 work orders
- 6 months of financial data

---

## Why Schema-Per-Tenant Over a Single Table?

The alternative — one `units` table with a `building_id` column — is simpler but breaks down when:

- Buildings have different columns (drift is impossible to represent cleanly)
- You want row-level security per building
- One building's data volume shouldn't affect query performance for others
- You want to drop or migrate a single building without touching others

Schema-per-tenant is the standard pattern for multi-tenant SaaS and property management platforms at scale.
