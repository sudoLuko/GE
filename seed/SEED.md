# Seed Data Instructions — chris-two-demo

## Overview

This document describes how to generate realistic seed data for the `ge_demo` Postgres database using the Python Faker library. The seed script populates all 8 building schemas with realistic property management data so the demo queries return meaningful results.

Install Faker before running:
```bash
pip install faker
```

---

## Connection

Connect to the database the same way as `create_schemas.py`:

```python
import psycopg2
from faker import Faker

fake = Faker()

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="ge_demo",
    user="postgres",
    password="password"
)
cursor = conn.cursor()
```

---

## Insertion Order

Foreign key dependencies require this exact order per building:

1. `units` — must exist before tenants or work orders
2. `tenants` — must exist before leases or payments
3. `leases` — references unit_id and tenant_id
4. `payments` — references tenant_id
5. `work_orders` — references unit_id
6. `financials` — no foreign keys, can go anywhere

---

## Data Volume Per Building

| Table | Row Count |
|---|---|
| units | 20-30 |
| tenants | 1 per occupied unit |
| leases | 1 per tenant |
| payments | 3-6 months of history per tenant |
| work_orders | 8-12 |
| financials | 6 months of line items |

---

## Table-by-Table Instructions

### units

Generate 25 units per building. Assign status randomly — weight it so roughly 85% are occupied, 10% vacant, 5% on_notice to reflect a realistic occupancy rate.

```python
statuses = ['occupied'] * 17 + ['vacant'] * 6 + ['on_notice'] * 2
```

Fields:
- `unit_number` — format as '101', '102' ... '125' or similar
- `beds` — random int between 0 and 3 (0 = studio)
- `baths` — random int between 1 and 2
- `rent_amount` — random decimal between 900.00 and 2200.00
- `status` — from weighted list above

Collect the returned `unit_id` values (use `cursor.fetchone()` after each insert with `RETURNING unit_id`) — you will need them for tenants and work orders.

---

### tenants

Insert one tenant per occupied or on_notice unit. Skip vacant units.

Fields:
- `unit_id` — from the units insertion above
- `first_name` — `fake.first_name()`
- `last_name` — `fake.last_name()`
- `email` — `fake.email()`
- `phone` — `fake.phone_number()`
- `move_in_date` — `fake.date_between(start_date='-3y', end_date='-6m')`
- `move_out_date` — NULL for active tenants

Collect the returned `tenant_id` values — you will need them for leases and payments.

---

### leases

Insert one active lease per tenant.

Fields:
- `unit_id` — matching unit
- `tenant_id` — matching tenant
- `start_date` — same as tenant move_in_date
- `end_date` — start_date plus 12 months
- `monthly_rent` — match the unit's rent_amount

---

### payments

Insert 4 months of payment history per tenant. Most payments should be on time, but introduce late payments for roughly 15% of tenants to make delinquency queries interesting.

Fields:
- `tenant_id` — matching tenant
- `amount` — match monthly_rent from lease, occasionally insert a partial payment
- `payment_date` / `date_paid` — see drift note below
- `method` — random choice from `['check', 'ach', 'card']`
- `late_flag` / `is_late` — see drift note below

**Drift handling:**
- For `building_07` use column names `date_paid` and `is_late`
- For all other buildings use `payment_date` and `late_flag`
- A payment is late if the payment date is more than 5 days after the 1st of the month

To generate a payment date, pick the 1st of each of the last 4 months then add a random offset of 0-10 days. If offset > 5 mark as late.

---

### work_orders

Insert 10 work orders per building. Mix of open, in_progress, and closed statuses.

Fields:
- `unit_id` — random unit from the building
- `description` — pick from a realistic list of property maintenance issues:
    - 'HVAC not cooling properly'
    - 'Leaking faucet in kitchen'
    - 'Broken window latch'
    - 'Mold reported in bathroom'
    - 'Garbage disposal not working'
    - 'Smoke detector battery replacement'
    - 'Door lock malfunction'
    - 'Water heater making noise'
    - 'Carpet replacement needed'
    - 'Exterior light not working'
- `status` — weight as 40% open, 30% in_progress, 30% closed
- `opened_date` — `fake.date_between(start_date='-6m', end_date='today')`
- `closed_date` — NULL if open or in_progress, otherwise opened_date plus 3-14 days

---

### financials

Insert 6 months of financial line items per building. Use the same set of line items for every building so cross-portfolio queries aggregate cleanly.

Line items to use:
- 'Gross Potential Rent'
- 'Vacancy Loss'
- 'Effective Gross Income'
- 'Operating Expenses'
- 'Net Operating Income'

For each line item and each of the last 6 months:
- `line_item` — name from list above
- `actual` — a realistic dollar amount based on the building's unit count and average rent
- `budget` — actual plus or minus a random variance of up to 8%
- `variance` — actual minus budget (can be negative)
- `period` — format as 'YYYY-MM' e.g. '2026-01'

---

## Commit and Close

After all buildings are seeded:

```python
conn.commit()
cursor.close()
conn.close()
```

---

## Notes

- Always insert in the order listed above — foreign key constraints will cause errors if tenants are inserted before units etc.
- Use `RETURNING unit_id` and `RETURNING tenant_id` in your INSERT statements to capture generated IDs without a separate SELECT
- The drift on `building_07` payments and `building_03` units is already handled in the schema — the seed script just needs to use the correct column names when inserting into those two schemas
- Run `create_schemas.py` before running this script