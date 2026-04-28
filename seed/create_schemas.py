import psycopg2
from psycopg2 import sql

"""
Create schemas and tables for data shape.

8 schemas representing 8 buildings in the portfolio numbered 1-8,
intentional schema drift added to buildings_03 and building_07 to simulate production environment,
each table has one primary key, the tuples ID, and shares no foreign keys with other tables (this is a demo)

"""

def main():
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="ge_demo",
        user="postgres",
        password="password"
    )
    cursor = conn.cursor()

    cursor.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier("building_01")))
    cursor.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier("building_02")))
    cursor.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier("building_03")))
    cursor.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier("building_04")))
    cursor.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier("building_05")))
    cursor.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier("building_06")))
    cursor.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier("building_07")))
    cursor.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier("building_08")))

    buildings = [
        "building_01", "building_02", "building_03", "building_04",
        "building_05", "building_06", "building_07", "building_08"
    ]

    for building in buildings:
        if building == "building_03":
            cursor.execute(sql.SQL("""
                CREATE TABLE IF NOT EXISTS {}.units (
                    unit_id        SERIAL PRIMARY KEY,
                    unit_number    VARCHAR(10),
                    beds           INT,
                    baths          INT,
                    rent_amount    DECIMAL,
                    status         VARCHAR(20),
                    subsidized     BOOLEAN
                )
            """).format(sql.Identifier(building)))
        else:
            cursor.execute(sql.SQL("""
                CREATE TABLE IF NOT EXISTS {}.units (
                    unit_id        SERIAL PRIMARY KEY,
                    unit_number    VARCHAR(10),
                    beds           INT,
                    baths          INT,
                    rent_amount    DECIMAL,
                    status         VARCHAR(20)
                )
            """).format(sql.Identifier(building)))

        cursor.execute(sql.SQL("""
            CREATE TABLE IF NOT EXISTS {}.tenants (
                tenant_id      SERIAL PRIMARY KEY,
                unit_id        INT,
                first_name     VARCHAR(50),
                last_name      VARCHAR(50),
                email          VARCHAR(100),
                phone          VARCHAR(20),
                move_in_date   DATE,
                move_out_date  DATE
            )
        """).format(sql.Identifier(building)))

        cursor.execute(sql.SQL("""
            CREATE TABLE IF NOT EXISTS {}.leases (
                lease_id       SERIAL PRIMARY KEY,
                unit_id        INT,
                tenant_id      INT,
                start_date     DATE,
                end_date       DATE,
                monthly_rent   DECIMAL
            )
        """).format(sql.Identifier(building)))

        if building == "building_07":
            cursor.execute(sql.SQL("""
                CREATE TABLE IF NOT EXISTS {}.payments (
                    payment_id     SERIAL PRIMARY KEY,
                    tenant_id      INT,
                    amount         DECIMAL,
                    date_paid      DATE,
                    method         VARCHAR(20),
                    is_late        BOOLEAN
                )
            """).format(sql.Identifier(building)))
        else:
            cursor.execute(sql.SQL("""
                CREATE TABLE IF NOT EXISTS {}.payments (
                    payment_id     SERIAL PRIMARY KEY,
                    tenant_id      INT,
                    amount         DECIMAL,
                    payment_date   DATE,
                    method         VARCHAR(20),
                    late_flag      BOOLEAN
                )
            """).format(sql.Identifier(building)))

        cursor.execute(sql.SQL("""
            CREATE TABLE IF NOT EXISTS {}.work_orders (
                work_order_id  SERIAL PRIMARY KEY,
                unit_id        INT,
                description    TEXT,
                status         VARCHAR(20),
                opened_date    DATE,
                closed_date    DATE
            )
        """).format(sql.Identifier(building)))

        cursor.execute(sql.SQL("""
            CREATE TABLE IF NOT EXISTS {}.financials (
                financial_id   SERIAL PRIMARY KEY,
                line_item      VARCHAR(100),
                actual         DECIMAL,
                budget         DECIMAL,
                variance       DECIMAL,
                period         VARCHAR(20)
            )
        """).format(sql.Identifier(building)))

    conn.commit()
    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
