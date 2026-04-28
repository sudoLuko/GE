"""
Improved Orchestrator with all tool functions and updated system prompt.

Added a simple router-then-worker setup. Haiku looks at the incoming query
and tags it as simple, standard, or complex. From there the right model
takes over with Haiku for simple lookups, Sonnet for cross-building comparisons,
Opus for full narrative summaries. Keeps Opus reserved for queries that
actually need it.

Handwritten to make sure I understand the system and the methods inside it.

"""
import json
import anthropic
import psycopg2
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown

from registry.schema_registry import build_translations
from tools.delinquency import SCHEMA as DELINQUENCY_SCHEMA, get_delinquency
from tools.financials import SCHEMA as FINANCIAL_SCHEMA, get_financials
from tools.lease_expirations import SCHEMA as EXPIRATIONS_SCHEMA, get_lease_expirations
from tools.leases import SCHEMA as LEASE_SCHEMA, get_leases
from tools.occupancy import SCHEMA as OCCUPANCY_SCHEMA, get_occupancy
from tools.payments import SCHEMA as PAYMENT_SCHEMA, get_payments
from tools.tenants import SCHEMA as TENANT_SCHEMA, get_tenants
from tools.work_orders import SCHEMA as WORKORDER_SCHEMA, get_work_orders

load_dotenv()
console = Console()

SCHEMAS = [
          DELINQUENCY_SCHEMA, FINANCIAL_SCHEMA, 
          EXPIRATIONS_SCHEMA,LEASE_SCHEMA, 
          OCCUPANCY_SCHEMA, PAYMENT_SCHEMA, 
          TENANT_SCHEMA, WORKORDER_SCHEMA
]

# dispatch table for use with the run_tool function
TOOLS = {
        "get_delinquency": get_delinquency, 
         "get_financials": get_financials, 
         "get_lease_expirations": get_lease_expirations, 
         "get_leases": get_leases, 
         "get_occupancy": get_occupancy, 
         "get_payments": get_payments, 
         "get_tenants": get_tenants, 
         "get_work_orders": get_work_orders
}

MODEL_BY_CATEGORY = {                                                                                                           
      "simple": "claude-haiku-4-5",                                                                                      
      "standard": "claude-sonnet-4-6",                      
      "complex": "claude-opus-4-7",                                                                                               
  }   

def build_system_prompt(registry: dict) -> str:
    return f"""You are Chris Two. A helpful AI assistant built by Great Expectations that is involved in the
property procurement and management business. You have access to several tools that you will
use to help you understand the shape of the databases in production. You must use these
tools when appropriate. You also have access to the schema registry which is built at startup from the Postgres database
instance. It contains the actual column names per building and you may use it to understand what is present in the database: {json.dumps(registry, indent=2)}

Example queries are as follows:
'Give me an owner update for building x',
'Give me a report across all our buildings financials'
'What is the delinquency rate of building y'

You will call the corresponding tools you find that best fit each query and synthesize a response that constitutes
a summary that a property manager at Arboreal Management or Great Expectations would expect. These summaries will drive
real business value for all organizations under the Great Expectations umbrella and you will take care in crafting them,
understanding that real operators will use them to make strategic decisions.

The shape of your response should follow this pattern:
-> User queries for information about property
-> You respond back with tool messages
-> User's orchestrator will feed you real data from the production databases
-> You synthesize executive briefing
"""

def router_system_prompt() -> str:
    return """You are a router at the front of a reasoning system that takes in business-critical questions,
queries tools for information from production databases, and returns summaries to property managers.

Your job is to classify the incoming question into exactly one of three categories: simple, standard, or complex.
Respond with one word only — the category label. No explanation, no punctuation, no quotes.

Categories and their linguistic signals:

simple — one building, one metric, one tool call. The answer is a single number or fact.
Examples:
- "What is the occupancy rate of building 2?"
- "How many tenants are in building 6?"

standard — comparison or aggregation across multiple buildings. The answer is a list, table, or ranking — not a written analysis.
Signals: "which", "compare", "rank", "top N", "average across".
Examples:
- "Which buildings have the highest cash flow?"
- "Compare delinquency between buildings 1 and 2."
- "What's the average occupancy across the portfolio?"

complex — multi-tool synthesis with narrative output. Requires judgment about what to highlight.
Signals: "summary", "briefing", "why", "health", "needs attention", "owner update".
Examples:
- "Give me an owner summary of building 3."
- "Which buildings need attention this month and why?"
- "Summarize portfolio health for the quarterly board meeting."

If the question doesn't clearly fit any category, default to standard.
"""

# simple model router. ships the question to Haiku with a tight prompt and asks
# it to classify as simple, standard, or complex. no tools, no registry, just
# one cheap call. returns the category string which main() looks up in
# MODEL_BY_CATEGORY to pick which model handles the actual work.
def route(question: str):
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": question}]

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=20,
        system=router_system_prompt(),
        messages=messages,
    )

    return next(b.text for b in response.content if b.type == "text")


def schema_registry(cursor) -> dict:
    registry = {}

    cursor.execute("""
        SELECT table_schema, table_name, column_name
        FROM information_schema.columns
        WHERE table_schema LIKE 'building_%'
        ORDER BY table_schema, table_name, ordinal_position
    """)

    rows = cursor.fetchall()

    for schema, table, column in rows:
        if schema not in registry:
            registry[schema] = {}
        if table not in registry[schema]:
            registry[schema][table] = []
        registry[schema][table].append(column)

    return registry


def run_tool(tool_name: str, cursor, translations: dict, inputs: dict):
    tool_func = TOOLS[tool_name]
    result = tool_func(cursor=cursor, translations=translations, **inputs)
    return json.dumps(result)


# tool-calling loop. send the question to Claude, then keep going as long as it
# wants tools run. each turn we run whatever tools it asks for, hand the results
# back as a user message, and ask again. when Claude stops asking for tools it
# means it has everything it needs and the final response is the synthesized answer.
def ask(question: str, cursor, registry: dict, translations: dict, model: str) -> str:
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": question}]

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=build_system_prompt(registry),
        tools=SCHEMAS,
        messages=messages,
    )

    while response.stop_reason == "tool_use":
        tool_blocks = [b for b in response.content if b.type == "tool_use"]
        messages.append({"role": "assistant", "content": response.content})

        tool_data = []
        for tool in tool_blocks:
            building = tool.input.get("building", "")
            extras = "  ".join(f"{k}={v}" for k, v in tool.input.items() if k != "building")
            print(f"  → {tool.name:<28}{building}{'  ' + extras if extras else ''}")
            result = run_tool(tool.name, cursor, translations, tool.input)
            tool_data.append({
                "type": "tool_result",
                "tool_use_id": tool.id,
                "content": result
            })

        messages.append({"role": "user", "content": tool_data})

        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=build_system_prompt(registry),
            tools=SCHEMAS,
            messages=messages,
        )

    return next(b.text for b in response.content if b.type == "text")
            
def main():
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="ge_demo",
        user="postgres",
        password="password"
    )
    cursor = conn.cursor()
    registry = schema_registry(cursor)
    translations = build_translations(registry)

    print("Chris Two — property portfolio analyst")
    print("Type 'exit' to quit\n")

    while True:
        question = input("Question: ").strip()
        if question.lower() == "exit":
            break
        if not question:
            continue
        
        complexity = route(question).strip().lower()
        model = MODEL_BY_CATEGORY.get(complexity, "claude-sonnet-4-6")
        
        print()
        print(f"[router → {model}]")  
        print()
        answer = ask(question, cursor, registry, translations, model)
        console.print(Markdown(answer))
        print()

    cursor.close()
    conn.close()

            

if __name__ == "__main__":
    main()
