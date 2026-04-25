import json
import anthropic
import psycopg2
from dotenv import load_dotenv

load_dotenv()

from registry.schema_registry import build_translations
from tools.occupancy import SCHEMA as OCCUPANCY_SCHEMA, get_occupancy
from tools.financials import SCHEMA as FINANCIALS_SCHEMA, get_financials
from tools.delinquency import SCHEMA as DELINQUENCY_SCHEMA, get_delinquency
from tools.lease_expirations import SCHEMA as LEASE_EXPIRATIONS_SCHEMA, get_lease_expirations
from tools.work_orders import SCHEMA as WORK_ORDERS_SCHEMA, get_work_orders

TOOLS = [
    OCCUPANCY_SCHEMA,
    FINANCIALS_SCHEMA,
    DELINQUENCY_SCHEMA,
    LEASE_EXPIRATIONS_SCHEMA,
    WORK_ORDERS_SCHEMA,
]

TOOL_FUNCTIONS = {
    "get_occupancy": get_occupancy,
    "get_financials": get_financials,
    "get_delinquency": get_delinquency,
    "get_lease_expirations": get_lease_expirations,
    "get_work_orders": get_work_orders,
}


def build_system_prompt(registry: dict) -> str:
    return f"""You are Chris Two, an AI analyst for a property management portfolio.
You have access to tools that query live data across 8 building schemas in a Postgres database.

Schema registry (actual column names per building — use this to understand drift):
{json.dumps(registry, indent=2)}

When answering questions:
- Call all relevant tools before synthesizing a response
- Be specific with numbers — don't round unless asked
- Flag any schema drift you encounter (e.g. building_07 payment columns differ)
"""


def build_registry(cursor) -> dict:
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
    return registry


def run_tool(name: str, inputs: dict, cursor, translations: dict) -> str:
    fn = TOOL_FUNCTIONS[name]
    result = fn(cursor=cursor, translations=translations, **inputs)
    return json.dumps(result)


def ask(question: str, cursor, registry: dict, translations: dict) -> str:
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": question}]

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=4096,
        system=build_system_prompt(registry),
        tools=TOOLS,
        messages=messages,
    )

    while response.stop_reason == "tool_use":
        tool_calls = [block for block in response.content if block.type == "tool_use"]

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for call in tool_calls:
            print(f"  -> calling {call.name}({call.input})")
            result = run_tool(call.name, call.input, cursor, translations)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": call.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=4096,
            system=build_system_prompt(registry),
            tools=TOOLS,
            messages=messages,
        )

    return next(block.text for block in response.content if block.type == "text")


def main():
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="ge_demo",
        user="postgres",
        password="password"
    )
    cursor = conn.cursor()
    registry = build_registry(cursor)
    translations = build_translations(registry)

    print("Chris Two — property portfolio analyst")
    print("Type 'exit' to quit\n")

    while True:
        question = input("Question: ").strip()
        if question.lower() == "exit":
            break
        if not question:
            continue

        print()
        answer = ask(question, cursor, registry, translations)
        print(f"\n{answer}\n")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
