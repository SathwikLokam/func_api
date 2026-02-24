"""Security middleware — API key, rate limiting, CORS."""

from __future__ import annotations

import time
import threading
from typing import Any

from func_api.errors import Unauthorized, RateLimited, Forbidden


# ── API Key ───────────────────────────────────────────────────────────────────

def check_api_key(headers: dict[str, str], expected_key: str) -> None:
    """Raise Unauthorized if the X-API-Key header doesn't match."""
    provided = headers.get("x-api-key", "")
    if not provided:
        raise Unauthorized("Missing API key – supply it via the X-API-Key header")
    if provided != expected_key:
        raise Unauthorized("Invalid API key")


# ── Rate Limiting (token-bucket per IP) ───────────────────────────────────────

class _RateLimiter:
    """Simple in-memory token-bucket rate limiter, thread-safe."""

    def __init__(self, max_calls_per_minute: int):
        self.capacity = max_calls_per_minute
        self.refill_rate = max_calls_per_minute / 60.0  # tokens per second
        self._buckets: dict[str, tuple[float, float]] = {}  # ip -> (tokens, last_ts)
        self._lock = threading.Lock()

    def allow(self, client_ip: str) -> bool:
        now = time.monotonic()
        with self._lock:
            tokens, last = self._buckets.get(client_ip, (float(self.capacity), now))
            elapsed = now - last
            tokens = min(self.capacity, tokens + elapsed * self.refill_rate)
            if tokens >= 1:
                self._buckets[client_ip] = (tokens - 1, now)
                return True
            self._buckets[client_ip] = (tokens, now)
            return False


# Cache of limiters keyed by (route, capacity)
_limiters: dict[tuple[str, int], _RateLimiter] = {}
_limiters_lock = threading.Lock()


def get_limiter(route: str, max_per_min: int) -> _RateLimiter:
    key = (route, max_per_min)
    with _limiters_lock:
        if key not in _limiters:
            _limiters[key] = _RateLimiter(max_per_min)
        return _limiters[key]


def check_rate_limit(route: str, client_ip: str, max_per_min: int) -> None:
    """Raise RateLimited if the client exceeds the allowed rate."""
    limiter = get_limiter(route, max_per_min)
    if not limiter.allow(client_ip):
        raise RateLimited()


# ── CORS ──────────────────────────────────────────────────────────────────────

def check_cors_origin(headers: dict[str, str], allowed_origins: list[str]) -> str | None:
    """Return the matching origin, or raise Forbidden if not allowed.

    If allowed_origins is ["*"], any origin is permitted.
    Returns the origin string for the response header.
    """
    origin = headers.get("origin", "")
    if not origin:
        # Non-browser request — no Origin header — allow by default
        return None
    if "*" in allowed_origins or origin in allowed_origins:
        return origin
    raise Forbidden(f"Origin '{origin}' is not allowed by CORS policy")


def cors_headers(origin: str | None, methods: list[str]) -> dict[str, str]:
    """Build CORS response headers."""
    if origin is None:
        return {}
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": ", ".join(methods),
        "Access-Control-Allow-Headers": "Content-Type, X-API-Key",
        "Access-Control-Max-Age": "86400",
    }
