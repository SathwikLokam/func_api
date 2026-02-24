#!/usr/bin/env python3
"""demo.py — runnable example for func_api.

Start:
    python examples/demo.py

Test:
    curl "http://127.0.0.1:8000/add?a=2&b=3"
    curl "http://127.0.0.1:8000/greet?name=World"
    curl -X POST http://127.0.0.1:8000/multiply -H "Content-Type: application/json" -d '{"x":6,"y":7}'
    curl -X POST http://127.0.0.1:8000/secret -H "Content-Type: application/json" -H "X-API-Key: my-secret-key" -d '{"msg":"hello"}'
    curl http://127.0.0.1:8000/info
"""

import sys, os

# Allow running from repo root without installing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from func_api import FuncAPI

app = FuncAPI(title="Demo API", version="1.0.0")


# ── Public endpoints ──────────────────────────────────────────────────────────

@app.api("/add", methods=["GET", "POST"])
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@app.api("/greet", methods=["GET"])
def greet(name: str = "World") -> str:
    """Return a greeting."""
    return f"Hello, {name}!"


@app.api("/multiply", methods=["POST"])
def multiply(x: float, y: float) -> float:
    """Multiply two numbers."""
    return x * y


# ── Secured endpoint ─────────────────────────────────────────────────────────

@app.api(
    "/secret",
    methods=["POST"],
    api_key="my-secret-key",
    rate_limit=10,                            # 10 req/min per IP
    allowed_origins=["*"],                    # any CORS origin OK
)
def secret(msg: str) -> str:
    """Echo a message — requires API key."""
    return f"🔒 received: {msg}"


# ── Rate-limited only endpoint ───────────────────────────────────────────────

@app.api("/ping", methods=["GET"], rate_limit=5)
def ping() -> str:
    """Rate-limited health check."""
    return "pong"


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
