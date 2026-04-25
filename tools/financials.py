from psycopg2 import sql

SCHEMA = {
    "name": "get_financials",
    "description": "Returns financial summary for a specific building and period, including Gross Potential Rent, Vacancy Loss, Effective Gross Income, Operating Expenses, and Net Operating Income with actual vs budget variance.",
    "input_schema": {
        "type": "object",
        "properties": {
            "building": {
                "type": "string",
                "description": "The schema name of the building e.g. building_01"
            },
            "period": {
                "type": "string",
                "description": "Period in YYYY-MM format e.g. 2026-03. Defaults to most recent if omitted."
            }
        },
        "required": ["building"]
    }
}


def get_financials(building: str, cursor, translations: dict = None, period: str = None) -> dict:
    if period is None:
        cursor.execute(sql.SQL("""
            SELECT MAX(period) FROM {}.financials
        """).format(sql.Identifier(building)))
        period = cursor.fetchone()[0]

    cursor.execute(sql.SQL("""
        SELECT line_item, actual, budget, variance
        FROM {}.financials
        WHERE period = %s
        ORDER BY financial_id
    """).format(sql.Identifier(building)), (period,))

    rows = cursor.fetchall()
    return {
        "building": building,
        "period": period,
        "line_items": [
            {
                "line_item": row[0],
                "actual": float(row[1]),
                "budget": float(row[2]),
                "variance": float(row[3])
            }
            for row in rows
        ]
    }
