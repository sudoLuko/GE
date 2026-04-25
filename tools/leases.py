from psycopg2 import sql

SCHEMA = {
    "name": "get_leases",
    "description": "Returns leases for a specific building. By default returns only active leases (end date in the future). Pass active_only=false to include expired leases.",
    "input_schema": {
        "type": "object",
        "properties": {
            "building": {
                "type": "string",
                "description": "The schema name of the building e.g. building_01"
            },
            "active_only": {
                "type": "boolean",
                "description": "If true (default), returns only leases where end_date >= today."
            }
        },
        "required": ["building"]
    }
}


def get_leases(building: str, cursor, active_only: bool = True) -> dict:
    if active_only:
        cursor.execute(sql.SQL("""
            SELECT
                l.lease_id,
                l.unit_id,
                u.unit_number,
                l.tenant_id,
                l.start_date,
                l.end_date,
                l.monthly_rent
            FROM {0}.leases l
            JOIN {0}.units u ON u.unit_id = l.unit_id
            WHERE l.end_date >= CURRENT_DATE
            ORDER BY u.unit_number
        """).format(sql.Identifier(building)))
    else:
        cursor.execute(sql.SQL("""
            SELECT
                l.lease_id,
                l.unit_id,
                u.unit_number,
                l.tenant_id,
                l.start_date,
                l.end_date,
                l.monthly_rent
            FROM {0}.leases l
            JOIN {0}.units u ON u.unit_id = l.unit_id
            ORDER BY u.unit_number
        """).format(sql.Identifier(building)))

    rows = cursor.fetchall()
    return {
        "building": building,
        "active_only": active_only,
        "leases": [
            {
                "lease_id": row[0],
                "unit_id": row[1],
                "unit_number": row[2],
                "tenant_id": row[3],
                "start_date": str(row[4]),
                "end_date": str(row[5]),
                "monthly_rent": float(row[6])
            }
            for row in rows
        ]
    }
