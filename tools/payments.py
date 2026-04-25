from psycopg2 import sql

SCHEMA = {
    "name": "get_payments",
    "description": "Returns recent payment records for a specific building including amount, date, method, and whether the payment was late. Note: column names vary slightly across buildings but output is normalized.",
    "input_schema": {
        "type": "object",
        "properties": {
            "building": {
                "type": "string",
                "description": "The schema name of the building e.g. building_01"
            },
            "late_only": {
                "type": "boolean",
                "description": "If true, returns only late payments. Defaults to false."
            }
        },
        "required": ["building"]
    }
}


def _get_date_and_late_columns(building: str, cursor) -> tuple[str, str]:
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = 'payments'
    """, (building,))
    columns = {row[0] for row in cursor.fetchall()}
    date_col = "date_paid" if "date_paid" in columns else "payment_date"
    late_col = "is_late" if "is_late" in columns else "late_flag"
    return date_col, late_col


def get_payments(building: str, cursor, late_only: bool = False) -> dict:
    date_col, late_col = _get_date_and_late_columns(building, cursor)

    query = sql.SQL("""
        SELECT
            p.payment_id,
            p.tenant_id,
            p.amount,
            p.{date_col} AS payment_date,
            p.method,
            p.{late_col} AS is_late
        FROM {building}.payments p
        {where}
        ORDER BY p.{date_col} DESC
    """).format(
        date_col=sql.Identifier(date_col),
        late_col=sql.Identifier(late_col),
        building=sql.Identifier(building),
        where=sql.SQL("WHERE p.{} = true".format(late_col)) if late_only else sql.SQL("")
    )

    cursor.execute(query)
    rows = cursor.fetchall()
    return {
        "building": building,
        "late_only": late_only,
        "payments": [
            {
                "payment_id": row[0],
                "tenant_id": row[1],
                "amount": float(row[2]),
                "payment_date": str(row[3]),
                "method": row[4],
                "is_late": row[5]
            }
            for row in rows
        ]
    }
