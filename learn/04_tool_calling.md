# How Claude Tool Calling Works (part of Layer 3)

## The Core Idea

Claude doesn't run your code. Claude reads descriptions of your tools, decides which ones to call, and tells you what arguments to use. Your Python code runs the actual functions and sends the results back. Claude synthesizes the results into a final answer.

You are always in control of execution. Claude just decides what to ask for.

---

## The Message Structure

The Anthropic API is stateless — it doesn't remember previous calls. You maintain the conversation history yourself as a list of messages and send the full list on every API call.

Each message has a `role` and `content`:

```python
messages = [
    {"role": "user", "content": "Give me an owner update for building 3"}
]
```

Claude responds. You append its response. You append your tool results. You send the whole thing again. The list grows with each round trip.

---

## What Claude's Response Looks Like

When Claude wants to call tools, its response contains `tool_use` blocks instead of text:

```python
response.content = [
    ToolUseBlock(
        type="tool_use",
        id="toolu_01abc",
        name="get_occupancy",
        input={"building": "building_03"}
    ),
    ToolUseBlock(
        type="tool_use",
        id="toolu_01def",
        name="get_financials",
        input={"building": "building_03"}
    )
]
response.stop_reason = "tool_use"
```

`stop_reason = "tool_use"` is your signal to loop. When it's `"end_turn"`, Claude is done and the final text answer is in `response.content`.

---

## The Loop Step by Step

**Round 1 — User question**
```
You send:   messages = [user question]
Claude says: call get_occupancy(building_03), call get_financials(building_03)
stop_reason: "tool_use"
```

**Round 2 — Tool results**
```
You append: Claude's tool_use response to messages
You run:    get_occupancy and get_financials against Postgres
You append: tool_result for each call to messages
You send:   the full message history
Claude says: call get_delinquency(building_03), call get_lease_expirations(building_03)
stop_reason: "tool_use"
```

**Round 3 — More tool results**
```
You append: Claude's tool_use response
You run:    get_delinquency and get_lease_expirations
You append: tool_result for each
You send:   full history again
Claude says: [full owner update report in plain text]
stop_reason: "end_turn"
```

Done.

---

## What the Messages Look Like After Round 2

```python
messages = [
    # Round 1
    {"role": "user", "content": "Give me an owner update for building 3"},
    
    # Claude's tool calls
    {"role": "assistant", "content": [
        ToolUseBlock(id="toolu_01abc", name="get_occupancy", input={...}),
        ToolUseBlock(id="toolu_01def", name="get_financials", input={...})
    ]},
    
    # Your tool results
    {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "toolu_01abc", "content": "{...occupancy data...}"},
        {"type": "tool_result", "tool_use_id": "toolu_01def", "content": "{...financials data...}"}
    ]}
]
```

The `tool_use_id` links each result to the specific tool call that requested it. Claude uses this to track what it asked for and what it got back.

---

## Why Claude Calls Multiple Tools Per Round

Claude can call multiple tools in a single response. For an owner update query it might call `get_occupancy` and `get_financials` together in round 1, then `get_delinquency` and `get_lease_expirations` in round 2.

This is Claude deciding how to break up its work — you don't control it. The loop handles however many rounds Claude needs.

---

## The `stop_reason` Values You Care About

| Value | Meaning |
|---|---|
| `"tool_use"` | Claude wants more tool calls — keep looping |
| `"end_turn"` | Claude is done — extract the text answer |
| `"max_tokens"` | Hit the token limit — answer was cut off |

In the orchestrator the loop condition is simply:
```python
while response.stop_reason == "tool_use":
    # execute tools, send results, get next response
```

---

## Why This Design Is Powerful

Claude decides what to query. You don't hardcode "for an owner update, call these 4 tools." Claude reads the question, reads the tool descriptions, and figures out what it needs. 

This means:
- New question types work automatically if the right tools exist
- Claude can ask follow-up tool calls if the first results raise new questions
- The orchestration logic stays simple even as tools multiply
