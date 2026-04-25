from psycopg2 import sql

SCHEMA = {
    "name": "get_lease_expirations",
    "description": "Returns leases expiring within a given number of days for a specific building, including tenant name and unit number.",
    "input_schema": {
        "type": "object",
        "properties": {
            "building": {
                "type": "string",
                "description": "The schema name of the building e.g. building_01"
            },
            "days": {
                "type": "integer",
                "description": "Look-ahead window in days. Returns leases expiring within this many days from today. Defaults to 60."
            }
        },
        "required": ["building"]
    }
}


def get_lease_expirations(building: str, cursor, translations: dict = None, days: int = 60) -> dict:
    cursor.execute(sql.SQL("""
        SELECT
            l.lease_id,
            l.unit_id,
            u.unit_number,
            l.tenant_id,
            t.first_name,
            t.last_name,
            l.end_date,
            l.monthly_rent,
            (l.end_date - CURRENT_DATE) AS days_until_expiry
        FROM {0}.leases l
        JOIN {0}.units u ON u.unit_id = l.unit_id
        JOIN {0}.tenants t ON t.tenant_id = l.tenant_id
        WHERE l.end_date BETWEEN CURRENT_DATE AND (CURRENT_DATE + %s * INTERVAL '1 day')
        ORDER BY l.end_date ASC
    """).format(sql.Identifier(building)), (days,))

    rows = cursor.fetchall()
    return {
        "building": building,
        "days_window": days,
        "expirations": [
            {
                "lease_id": row[0],
                "unit_id": row[1],
                "unit_number": row[2],
                "tenant_id": row[3],
                "first_name": row[4],
                "last_name": row[5],
                "end_date": str(row[6]),
                "monthly_rent": float(row[7]),
                "days_until_expiry": row[8]
            }
            for row in rows
        ]
    }
