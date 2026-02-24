# func_api

> Convert ordinary Python functions into HTTP API endpoints with a single decorator.  
> Zero external dependencies — pure Python standard library.

## Installation

```bash
pip install -e .
```

## Quick Start

```python
from func_api import FuncAPI

app = FuncAPI(title="My API")

@app.api("/add", methods=["GET", "POST"])
def add(a: int, b: int) -> int:
    return a + b

app.run()  # http://127.0.0.1:8000
```

```bash
curl "http://127.0.0.1:8000/add?a=2&b=3"
# → {"success": true, "data": 5}
```

## Security

Pass security options directly to the `@app.api()` decorator:

```python
@app.api(
    "/secret",
    methods=["POST"],
    api_key="my-secret-key",       # Require X-API-Key header
    rate_limit=60,                 # Max 60 requests/min per IP
    allowed_origins=["*"],         # CORS allowed origins
)
def secret(msg: str) -> str:
    return f"received: {msg}"
```

| Option | Type | Description |
|---|---|---|
| `api_key` | `str` | Require this value in `X-API-Key` header |
| `rate_limit` | `int` | Max calls per minute per client IP |
| `allowed_origins` | `list[str]` | CORS whitelist (`["*"]` = any origin) |

## Features

- **Type-aware parameter parsing** — auto-casts from query string / JSON body using type hints
- **GET + POST** — query params for GET, JSON body for POST (or both)
- **Built-in `/info`** — auto-generated endpoint listing
- **Zero dependencies** — runs on Python 3.9+ with nothing to install

## License

MIT
