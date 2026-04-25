from psycopg2 import sql

SCHEMA = {
    "name": "get_work_orders",
    "description": "Returns work orders for a specific building. Optionally filter by status: open, in_progress, or closed.",
    "input_schema": {
        "type": "object",
        "properties": {
            "building": {
                "type": "string",
                "description": "The schema name of the building e.g. building_01"
            },
            "status": {
                "type": "string",
                "enum": ["open", "in_progress", "closed"],
                "description": "Filter by work order status. Returns all statuses if omitted."
            }
        },
        "required": ["building"]
    }
}


def get_work_orders(building: str, cursor, translations: dict = None, status: str = None) -> dict:
    if status is not None:
        cursor.execute(sql.SQL("""
            SELECT
                w.work_order_id,
                w.unit_id,
                u.unit_number,
                w.description,
                w.status,
                w.opened_date,
                w.closed_date
            FROM {0}.work_orders w
            JOIN {0}.units u ON u.unit_id = w.unit_id
            WHERE w.status = %s
            ORDER BY w.opened_date DESC
        """).format(sql.Identifier(building)), (status,))
    else:
        cursor.execute(sql.SQL("""
            SELECT
                w.work_order_id,
                w.unit_id,
                u.unit_number,
                w.description,
                w.status,
                w.opened_date,
                w.closed_date
            FROM {0}.work_orders w
            JOIN {0}.units u ON u.unit_id = w.unit_id
            ORDER BY w.opened_date DESC
        """).format(sql.Identifier(building)))

    rows = cursor.fetchall()
    return {
        "building": building,
        "status_filter": status,
        "work_orders": [
            {
                "work_order_id": row[0],
                "unit_id": row[1],
                "unit_number": row[2],
                "description": row[3],
                "status": row[4],
                "opened_date": str(row[5]),
                "closed_date": str(row[6]) if row[6] else None
            }
            for row in rows
        ]
    }
