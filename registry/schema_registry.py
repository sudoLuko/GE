import json

import psycopg2

# Maps actual (drifted) column names to canonical names.
# This is the single source of truth for all known drift.
COLUMN_ALIASES = {
    "payments": {
        "date_paid": "payment_date",
        "is_late": "late_flag"
    }
}


def build_translations(registry: dict) -> dict:
    """
    Returns a translations dict: canonical column name -> actual column name, per building per table.
    Only buildings with drift appear in the result. All others use canonical names directly.
    """
    translations = {}
    for building, tables in registry.items():
        for table, aliases in COLUMN_ALIASES.items():
            if table not in tables:
                continue
            actual_cols = set(tables[table])
            for actual, canonical in aliases.items():
                if actual in actual_cols:
                    translations.setdefault(building, {}).setdefault(table, {})[canonical] = actual
    return translations


def main():
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="ge_demo",
        user="postgres",
        password="password"
    )
    cursor = conn.cursor()

    expected_buildings = [
        "building_01", "building_02", "building_03", "building_04",
        "building_05", "building_06", "building_07", "building_08"
    ]

    expected_tables = [
        "units",
        "tenants",
        "leases",
        "payments",
        "work_orders",
        "financials"
    ]

    cursor.execute("""
        SELECT table_schema, table_name, column_name
        FROM information_schema.columns
        WHERE table_schema LIKE 'building_%'
        ORDER BY table_schema, table_name, ordinal_position
    """)

    registry = {}
    for schema_name, table_name, column_name in cursor.fetchall():
        if schema_name not in registry:
            registry[schema_name] = {}
        if table_name not in registry[schema_name]:
            registry[schema_name][table_name] = []
        registry[schema_name][table_name].append(column_name)

    errors = []

    for building in expected_buildings:
        if building not in registry:
            errors.append(f"Missing schema: {building}")
            continue

        for table_name in expected_tables:
            if table_name not in registry[building]:
                errors.append(f"{building} is missing table: {table_name}")

    if "building_03" in registry and "units" in registry["building_03"]:
        if "subsidized" not in registry["building_03"]["units"]:
            errors.append("building_03.units is missing drift column: subsidized")

    if "building_07" in registry and "payments" in registry["building_07"]:
        payment_columns = registry["building_07"]["payments"]
        if "date_paid" not in payment_columns:
            errors.append("building_07.payments is missing drift column: date_paid")
        if "is_late" not in payment_columns:
            errors.append("building_07.payments is missing drift column: is_late")
        if "payment_date" in payment_columns:
            errors.append("building_07.payments should not contain payment_date")
        if "late_flag" in payment_columns:
            errors.append("building_07.payments should not contain late_flag")

    for building in expected_buildings:
        if building == "building_07":
            continue

        if building in registry and "payments" in registry[building]:
            payment_columns = registry[building]["payments"]
            if "payment_date" not in payment_columns:
                errors.append(f"{building}.payments is missing column: payment_date")
            if "late_flag" not in payment_columns:
                errors.append(f"{building}.payments is missing column: late_flag")

    print("Schema registry:")
    print(json.dumps(registry, indent=2))
    print()

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
    else:
        print("Validation passed: all expected schemas, tables, and drifted columns are present.")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
