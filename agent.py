import os
import sys
import requests

BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:6655/anthropic")
API_KEY  = os.getenv("LLM_API_KEY") or sys.exit("Set LLM_API_KEY first (see .env.example). Never hardcode keys.")
MODEL    = os.getenv("LLM_MODEL", "claude-haiku-4-5")

# ── 1. The real tools (MY code, not the model) ────────────────────────────────

def calculator(operation: str, a: float, b: float) -> float:
    ops = {"add": a + b, "subtract": a - b, "multiply": a * b, "divide": a / b}
    if operation not in ops:
        raise ValueError(f"Unknown operation: {operation}")
    return ops[operation]

def get_exchange_rate(from_currency: str, to_currency: str) -> dict:
    rates = {("USD", "INR"): 83.5, ("EUR", "INR"): 90.1}
    rate = rates.get((from_currency.upper(), to_currency.upper()))
    if rate is None:
        return {"error": f"No rate for {from_currency}->{to_currency}"}
    return {"from": from_currency, "to": to_currency, "rate": rate}

def lookup_product(name: str) -> dict:
    db = {
        "laptop":   {"price_usd": 999, "stock": 12},
        "mouse":    {"price_usd": 29,  "stock": 0},
        "keyboard": {"price_usd": 79,  "stock": 5},
    }
    return db.get(name.lower(), {"error": f"Product '{name}' not found"})

# ── 2. Tool definitions (what I SEND to the model) ────────────────────────────

TOOLS = [
    {
        "name": "calculator",
        "description": "Performs basic arithmetic. Use for any math: add, subtract, multiply, divide.",
        "input_schema": {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["operation", "a", "b"],
        },
    },
    {
        "name": "get_exchange_rate",
        "description": "Returns the exchange rate between two currencies.",
        "input_schema": {
            "type": "object",
            "properties": {
                "from_currency": {"type": "string"},
                "to_currency":   {"type": "string"},
            },
            "required": ["from_currency", "to_currency"],
        },
    },
    {
        "name": "lookup_product",
        "description": "Looks up a product by name and returns price in USD and stock count.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        },
    },
]

# ── 3. The dispatcher — MY code runs the tool the model asked for ─────────────

def run_tool(name: str, inputs: dict):
    if name == "calculator":
        return calculator(**inputs)
    elif name == "get_exchange_rate":
        return get_exchange_rate(**inputs)
    elif name == "lookup_product":
        return lookup_product(**inputs)
    else:
        return {"error": f"Unknown tool: {name}"}

# ── 4. One HTTP call to the model ─────────────────────────────────────────────

def call_model(messages: list) -> dict:
    resp = requests.post(
        f"{BASE_URL}/v1/messages",
        headers={
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={"model": MODEL, "max_tokens": 1024, "tools": TOOLS, "messages": messages},
    )
    resp.raise_for_status()
    return resp.json()

# ── 5. The agent loop ─────────────────────────────────────────────────────────

def agent(user_question: str) -> str:
    messages = [{"role": "user", "content": user_question}]

    while True:
        response = call_model(messages)

        # Model is stateless, so I must record what it just said before replying.
        messages.append({"role": "assistant", "content": response["content"]})

        # FORK: is the model ANSWERING, or asking me to CALL a tool?
        if response["stop_reason"] == "end_turn":
            for block in response["content"]:
                if block["type"] == "text":
                    return block["text"]
            return ""

        if response["stop_reason"] == "tool_use":
            tool_results = []
            for block in response["content"]:
                if block["type"] == "tool_use":
                    # The model only REQUESTED this. MY code runs it, right here.
                    result = run_tool(block["name"], block["input"])
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block["id"],
                        "content": str(result),
                    })
            # Hand the results back and loop — the model sees them and continues.
            messages.append({"role": "user", "content": tool_results})

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # Windows console prints the ₹ symbol
    questions = [
        "What is 847 multiplied by 23?",
        "What's the USD to INR exchange rate, and how much is a laptop in INR?",
        "Is the mouse in stock? If so, what does it cost in INR?",
    ]
    for q in questions:
        print(f"\nQ: {q}")
        print(f"A: {agent(q)}")
