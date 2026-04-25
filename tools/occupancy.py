from psycopg2 import sql

# JSON schema — passed to Anthropic API so Claude knows this tool exists
SCHEMA = {
    "name": "get_occupancy",
    "description": "Returns occupancy breakdown for a specific building including total units, occupied, vacant, and on_notice counts.",
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

# Python function — executed by orchestrator when Claude calls this tool
def get_occupancy(building: str, cursor, translations: dict = None) -> dict:
    """
    Returns occupancy breakdown for a single building schema.

    Args:
        building: Postgres schema name e.g. 'building_01'
        cursor: active psycopg2 cursor

    Returns:
        dict with keys: building, total, occupied, vacant, on_notice
    """
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