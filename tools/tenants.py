from psycopg2 import sql

SCHEMA = {
    "name": "get_tenants",
    "description": "Returns all current tenants for a specific building, including their unit, contact info, and move-in date.",
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


def get_tenants(building: str, cursor) -> dict:
    cursor.execute(sql.SQL("""
        SELECT
            t.tenant_id,
            t.unit_id,
            u.unit_number,
            t.first_name,
            t.last_name,
            t.email,
            t.phone,
            t.move_in_date
        FROM {0}.tenants t
        JOIN {0}.units u ON u.unit_id = t.unit_id
        WHERE t.move_out_date IS NULL
        ORDER BY u.unit_number
    """).format(sql.Identifier(building)))

    rows = cursor.fetchall()
    return {
        "building": building,
        "tenants": [
            {
                "tenant_id": row[0],
                "unit_id": row[1],
                "unit_number": row[2],
                "first_name": row[3],
                "last_name": row[4],
                "email": row[5],
                "phone": row[6],
                "move_in_date": str(row[7])
            }
            for row in rows
        ]
    }
