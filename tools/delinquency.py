from psycopg2 import sql

SCHEMA = {
    "name": "get_delinquency",
    "description": "Returns tenants with late payments for a specific building. Shows tenant name, unit, payment amount, payment date, and how many days late. Handles schema drift across buildings automatically.",
    "input_schema": {
        "type": "object",
        "properties": {
            "building": {
                "type": "string",
                "description": "The schema name of the building e.g. building_01"
            },
            "months_back": {
                "type": "integer",
                "description": "How many months of payment history to look back. Defaults to 1."
            }
        },
        "required": ["building"]
    }
}


def get_delinquency(building: str, cursor, translations: dict = None, months_back: int = 1) -> dict:
    payment_translations = (translations or {}).get(building, {}).get("payments", {})   # filter to dictionary with date and late col
    date_col = payment_translations.get("payment_date", "payment_date")
    late_col = payment_translations.get("late_flag", "late_flag")

    cursor.execute(sql.SQL("""
        SELECT
            t.tenant_id,
            t.first_name,
            t.last_name,
            u.unit_number,
            p.amount,
            p.{date_col} AS payment_date,
            p.method
        FROM {building}.payments p
        JOIN {building}.tenants t ON t.tenant_id = p.tenant_id
        JOIN {building}.units u ON u.unit_id = t.unit_id
        WHERE p.{late_col} = true
          AND p.{date_col} >= (CURRENT_DATE - INTERVAL '1 month' * %s)
        ORDER BY p.{date_col} DESC
    """).format(
        building=sql.Identifier(building),
        date_col=sql.Identifier(date_col),
        late_col=sql.Identifier(late_col)
    ), (months_back,))

    rows = cursor.fetchall()
    return {
        "building": building,
        "months_back": months_back,
        "delinquent_payments": [
            {
                "tenant_id": row[0],
                "first_name": row[1],
                "last_name": row[2],
                "unit_number": row[3],
                "amount": float(row[4]),
                "payment_date": str(row[5]),
                "method": row[6]
            }
            for row in rows
        ]
    }
