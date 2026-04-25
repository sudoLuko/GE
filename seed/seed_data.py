import calendar
import random
from datetime import date, timedelta

import psycopg2
from faker import Faker
from psycopg2 import sql


def shift_months(date_value, months):
    month = date_value.month - 1 + months
    year = date_value.year + month // 12
    month = month % 12 + 1
    day = min(date_value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def main():
    fake = Faker()

    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="ge_demo",
        user="postgres",
        password="password"
    )
    cursor = conn.cursor()

    buildings = [
        "building_01", "building_02", "building_03", "building_04",
        "building_05", "building_06", "building_07", "building_08"
    ]

    payment_methods = ["check", "ach", "card"]
    work_order_descriptions = [
        "HVAC not cooling properly",
        "Leaking faucet in kitchen",
        "Broken window latch",
        "Mold reported in bathroom",
        "Garbage disposal not working",
        "Smoke detector battery replacement",
        "Door lock malfunction",
        "Water heater making noise",
        "Carpet replacement needed",
        "Exterior light not working"
    ]
    financial_line_items = [
        "Gross Potential Rent",
        "Vacancy Loss",
        "Effective Gross Income",
        "Operating Expenses",
        "Net Operating Income"
    ]

    for building in buildings:
        units = []
        tenants = []

        for unit_number in range(101, 126):
            beds = random.randint(0, 3)
            baths = random.randint(1, 2)
            rent_amount = round(random.uniform(900, 2200), 2)
            status = random.choices(
                ["occupied", "vacant", "on_notice"],
                weights=[85, 10, 5],
                k=1
            )[0]

            if building == "building_03":
                subsidized = random.choices([True, False], weights=[30, 70], k=1)[0]
                cursor.execute(sql.SQL("""
                    INSERT INTO {}.units (
                        unit_number,
                        beds,
                        baths,
                        rent_amount,
                        status,
                        subsidized
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING unit_id
                """).format(sql.Identifier(building)), (
                    str(unit_number),
                    beds,
                    baths,
                    rent_amount,
                    status,
                    subsidized
                ))
            else:
                cursor.execute(sql.SQL("""
                    INSERT INTO {}.units (
                        unit_number,
                        beds,
                        baths,
                        rent_amount,
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING unit_id
                """).format(sql.Identifier(building)), (
                    str(unit_number),
                    beds,
                    baths,
                    rent_amount,
                    status
                ))

            unit_id = cursor.fetchone()[0]
            units.append({
                "unit_id": unit_id,
                "unit_number": str(unit_number),
                "beds": beds,
                "baths": baths,
                "rent_amount": rent_amount,
                "status": status
            })

        for unit in units:
            if unit["status"] == "vacant":
                continue

            move_in_date = fake.date_between(start_date="-3y", end_date="-6m")

            cursor.execute(sql.SQL("""
                INSERT INTO {}.tenants (
                    unit_id,
                    first_name,
                    last_name,
                    email,
                    phone,
                    move_in_date,
                    move_out_date
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING tenant_id
            """).format(sql.Identifier(building)), (
                unit["unit_id"],
                fake.first_name(),
                fake.last_name(),
                fake.email(),
                fake.numerify("##########"),
                move_in_date,
                None
            ))

            tenant_id = cursor.fetchone()[0]
            tenants.append({
                "tenant_id": tenant_id,
                "unit_id": unit["unit_id"],
                "move_in_date": move_in_date,
                "monthly_rent": unit["rent_amount"]
            })

        for tenant in tenants:
            start_date = tenant["move_in_date"]
            end_date = shift_months(start_date, 12)

            cursor.execute(sql.SQL("""
                INSERT INTO {}.leases (
                    unit_id,
                    tenant_id,
                    start_date,
                    end_date,
                    monthly_rent
                )
                VALUES (%s, %s, %s, %s, %s)
            """).format(sql.Identifier(building)), (
                tenant["unit_id"],
                tenant["tenant_id"],
                start_date,
                end_date,
                tenant["monthly_rent"]
            ))

        for tenant in tenants:
            late_tenant = random.random() < 0.15

            for months_ago in range(4):
                payment_month = shift_months(date.today().replace(day=1), -months_ago)

                if late_tenant:
                    offset_days = random.randint(6, 10)
                else:
                    offset_days = random.randint(0, 5)

                payment_date = payment_month + timedelta(days=offset_days)
                is_late = offset_days > 5
                amount = tenant["monthly_rent"]

                if random.random() < 0.1:
                    amount = round(amount * random.uniform(0.5, 0.95), 2)

                if building == "building_07":
                    cursor.execute(sql.SQL("""
                        INSERT INTO {}.payments (
                            tenant_id,
                            amount,
                            date_paid,
                            method,
                            is_late
                        )
                        VALUES (%s, %s, %s, %s, %s)
                    """).format(sql.Identifier(building)), (
                        tenant["tenant_id"],
                        amount,
                        payment_date,
                        random.choice(payment_methods),
                        is_late
                    ))
                else:
                    cursor.execute(sql.SQL("""
                        INSERT INTO {}.payments (
                            tenant_id,
                            amount,
                            payment_date,
                            method,
                            late_flag
                        )
                        VALUES (%s, %s, %s, %s, %s)
                    """).format(sql.Identifier(building)), (
                        tenant["tenant_id"],
                        amount,
                        payment_date,
                        random.choice(payment_methods),
                        is_late
                    ))

        for _ in range(10):
            unit = random.choice(units)
            status = random.choices(
                ["open", "in_progress", "closed"],
                weights=[40, 30, 30],
                k=1
            )[0]
            opened_date = fake.date_between(start_date="-6m", end_date="today")
            closed_date = None

            if status == "closed":
                closed_date = min(
                    opened_date + timedelta(days=random.randint(3, 14)),
                    date.today()
                )

            cursor.execute(sql.SQL("""
                INSERT INTO {}.work_orders (
                    unit_id,
                    description,
                    status,
                    opened_date,
                    closed_date
                )
                VALUES (%s, %s, %s, %s, %s)
            """).format(sql.Identifier(building)), (
                unit["unit_id"],
                random.choice(work_order_descriptions),
                status,
                opened_date,
                closed_date
            ))

        unit_count = len(units)
        average_rent = sum(unit["rent_amount"] for unit in units) / unit_count
        vacant_units = len([unit for unit in units if unit["status"] != "occupied"])

        for months_ago in range(6):
            period_date = shift_months(date.today().replace(day=1), -months_ago)
            period = period_date.strftime("%Y-%m")

            gross_potential_rent = round(unit_count * average_rent * random.uniform(0.98, 1.02), 2)
            vacancy_loss = round(
                vacant_units * average_rent * random.uniform(0.85, 1.15),
                2
            )
            effective_gross_income = round(gross_potential_rent - vacancy_loss, 2)
            operating_expenses = round(
                effective_gross_income * random.uniform(0.35, 0.5),
                2
            )
            net_operating_income = round(
                effective_gross_income - operating_expenses,
                2
            )

            actuals = {
                "Gross Potential Rent": gross_potential_rent,
                "Vacancy Loss": vacancy_loss,
                "Effective Gross Income": effective_gross_income,
                "Operating Expenses": operating_expenses,
                "Net Operating Income": net_operating_income
            }

            for line_item in financial_line_items:
                actual = actuals[line_item]
                budget = round(actual * random.uniform(0.92, 1.08), 2)
                variance = round(actual - budget, 2)

                cursor.execute(sql.SQL("""
                    INSERT INTO {}.financials (
                        line_item,
                        actual,
                        budget,
                        variance,
                        period
                    )
                    VALUES (%s, %s, %s, %s, %s)
                """).format(sql.Identifier(building)), (
                    line_item,
                    actual,
                    budget,
                    variance,
                    period
                ))

    conn.commit()
    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
