# The Orchestrator (Layer 3 + Layer 4)

## What It Does

The orchestrator is the glue. It connects all four layers into a working system:

- Opens the Postgres connection
- Builds the schema registry
- Defines which tools Claude can use
- Runs the tool calling loop
- Prints the final answer

Everything lives in `orchestrator.py`.

---

## Startup Sequence

When you run `python orchestrator.py`:

```
1. Load .env (ANTHROPIC_API_KEY)
2. Connect to Postgres
3. Build schema registry from information_schema
4. Build translation map from registry
5. Start the terminal input loop
```

Both the registry and translations are built once at startup and reused for every question. Neither changes while the program is running.

---

## The Tool Registry

The orchestrator imports every tool's schema and function and assembles two structures:

```python
# List of JSON schemas — sent to Claude on every API call
TOOLS = [
    OCCUPANCY_SCHEMA,
    FINANCIALS_SCHEMA,
    DELINQUENCY_SCHEMA,
    LEASE_EXPIRATIONS_SCHEMA,
    WORK_ORDERS_SCHEMA,
]

# Map of name → function — used to execute tool calls
TOOL_FUNCTIONS = {
    "get_occupancy": get_occupancy,
    "get_financials": get_financials,
    "get_delinquency": get_delinquency,
    "get_lease_expirations": get_lease_expirations,
    "get_work_orders": get_work_orders,
}
```

When Claude calls `get_occupancy`, the orchestrator looks up `"get_occupancy"` in `TOOL_FUNCTIONS` and calls it.

---

## The `ask` Function — Full Walk Through

```python
def ask(question: str, cursor, registry: dict, translations: dict) -> str:
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": question}]

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=4096,
        system=build_system_prompt(registry),  # schema registry injected here
        tools=TOOLS,                            # tool schemas sent here
        messages=messages,
    )

    while response.stop_reason == "tool_use":
        tool_calls = [block for block in response.content if block.type == "tool_use"]

        # Append Claude's response (with tool_use blocks) to history
        messages.append({"role": "assistant", "content": response.content})

        # Execute each tool call and collect results
        tool_results = []
        for call in tool_calls:
            print(f"  -> calling {call.name}({call.input})")
            result = run_tool(call.name, call.input, cursor, translations)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": call.id,
                "content": result,
            })

        # Append tool results to history and send back to Claude
        messages.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=4096,
            system=build_system_prompt(registry),
            tools=TOOLS,
            messages=messages,
        )

    # stop_reason is now "end_turn" — extract the text
    return next(block.text for block in response.content if block.type == "text")
```

Line by line what happens:

1. Build a single-message history with the user's question
2. Send to Claude with the schema registry as system context and all tool schemas attached
3. Check `stop_reason` — if `"tool_use"`, Claude wants to call tools
4. Extract all `tool_use` blocks from the response
5. Append Claude's full response to message history (required — Claude needs to see its own tool calls)
6. Execute each tool call against Postgres via `run_tool`
7. Package results as `tool_result` messages matched by `tool_use_id`
8. Append results to history and send everything back to Claude
9. Repeat until `stop_reason == "end_turn"`
10. Pull the text answer out of the final response

---

## The `run_tool` Function

```python
def run_tool(name: str, inputs: dict, cursor, translations: dict) -> str:
    fn = TOOL_FUNCTIONS[name]
    result = fn(cursor=cursor, translations=translations, **inputs)
    return json.dumps(result)
```

Four things happen here:

- Look up the function by name
- Call it with `cursor` (the Postgres connection), `translations` (the drift map), plus whatever arguments Claude passed
- Serialize the result to JSON — tool results must be strings

`**inputs` unpacks Claude's argument dict as keyword arguments. If Claude passed `{"building": "building_03", "period": "2026-03"}`, this becomes `fn(cursor=cursor, translations=translations, building="building_03", period="2026-03")`.

`translations` is passed to every tool uniformly — tools that don't need it (occupancy, financials, etc.) accept it as `translations=None` and ignore it. This keeps `run_tool` simple — it doesn't need to know which tools care about drift.

---

## The System Prompt

```python
def build_system_prompt(registry: dict) -> str:
    return f"""You are Chris Two, an AI analyst for a property management portfolio.
You have access to tools that query live data across 8 building schemas in a Postgres database.

Schema registry (actual column names per building — use this to understand drift):
{json.dumps(registry, indent=2)}

When answering questions:
- Call all relevant tools before synthesizing a response
- Be specific with numbers — don't round unless asked
- Flag any schema drift you encounter
"""
```

This is sent on every API call. It gives Claude:
- Its persona and role
- The full schema registry so it understands every building's structure
- Behavioral instructions for how to answer

---

## The Terminal Loop

```python
while True:
    question = input("Question: ").strip()
    if question.lower() == "exit":
        break
    if not question:
        continue
    answer = ask(question, cursor, registry, translations)
    print(f"\n{answer}\n")
```

Minimal by design. Ask a question, get an answer, repeat. The `print(f"  -> calling {call.name}({call.input})")` inside `ask` lets you watch the tool calls fire in real time as Claude works through the question.

---

## What Happens When You Ask a Portfolio-Wide Question

```
"Which buildings had the highest late payment rate last month?"
```

Claude needs to check delinquency for all 8 buildings. It will call `get_delinquency` 8 times — once per building. You'll see 8 tool call lines print. Claude then gets all 8 results back, ranks the buildings by late payment rate, and returns a sorted comparison.

This is called **fan-out** — one question triggers many parallel-ish tool calls. In the demo they run sequentially. In production you'd parallelize them with threading or async to cut latency dramatically.
