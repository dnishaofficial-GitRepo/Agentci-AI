# Multi-Tool Agent (BUILD #1)

A minimal AI agent built on raw HTTP calls to a Claude-compatible API — no SDK, no framework. It shows the core mechanism behind every "AI agent": **the model only outputs a request to call a tool; my own code decides whether and how to run it, then feeds the result back.**

> `agent = LLM + tools + a loop`

## What it does

Given a plain-English question, the agent decides which tool(s) to call, in what order, and chains them to produce an answer. Three tools:

| Tool | What it does |
|------|--------------|
| `calculator` | add / subtract / multiply / divide |
| `get_exchange_rate` | mock currency rate lookup (USD/EUR → INR) |
| `lookup_product` | mock product "database" (price + stock) |

Example — *"What's the USD to INR rate, and how much is a laptop in INR?"* — makes the model chain **three** tools (`get_exchange_rate` → `lookup_product` → `calculator`) on its own.

## The loop

1. Send the prompt + tool definitions to the model.
2. The model replies with **either** a final answer **or** a tool-call request.
3. If it's a request, **my code** runs the tool and appends the result to the transcript.
4. Repeat until the model returns an answer instead of a request.

The branch is `stop_reason`: `tool_use` (call) vs `end_turn` (answer).

## Run it

```bash
pip install -r requirements.txt

# set your endpoint + key (see .env.example)
export LLM_BASE_URL="http://localhost:6655/anthropic"
export LLM_API_KEY="your-key-here"
export LLM_MODEL="claude-haiku-4-5"

python agent.py
```

On Windows PowerShell, set the vars with `$env:LLM_API_KEY="..."` before running.

## Security note

The model only *requests* a tool call — it never executes anything. The executor (`run_tool`) is where control lives: that's the boundary where validation, access limits, and audit logging belong. Keys are read from environment variables only; nothing sensitive is committed.
