"""Route decorator — registers functions as API endpoints."""

from __future__ import annotations

import inspect
import traceback
from typing import Any, Callable

from func_api.errors import APIError, MethodNotAllowed
from func_api.request import extract_params
from func_api.response import success_response, error_response
from func_api.security import (
    check_api_key,
    check_rate_limit,
    check_cors_origin,
    cors_headers,
)


class Route:
    """Metadata + handler for a single registered endpoint."""

    __slots__ = (
        "path", "methods", "func",
        "api_key", "rate_limit", "allowed_origins",
    )

    def __init__(
        self,
        path: str,
        func: Callable,
        methods: list[str],
        api_key: str | None,
        rate_limit: int | None,
        allowed_origins: list[str] | None,
    ):
        self.path = path
        self.func = func
        self.methods = [m.upper() for m in methods]
        self.api_key = api_key
        self.rate_limit = rate_limit
        self.allowed_origins = allowed_origins

    def handle(
        self,
        method: str,
        query_string: str,
        body: bytes | None,
        content_type: str | None,
        headers: dict[str, str],
        client_ip: str,
    ) -> tuple[int, dict, dict[str, str]]:
        """Process an incoming request. Returns (status, body_dict, extra_headers)."""
        extra_headers: dict[str, str] = {}

        # ── CORS preflight ───────────────────────────────────────────
        if self.allowed_origins is not None:
            origin = check_cors_origin(headers, self.allowed_origins)
            extra_headers.update(cors_headers(origin, self.methods))
            if method == "OPTIONS":
                return 204, {}, extra_headers

        # ── Method check ─────────────────────────────────────────────
        if method not in self.methods:
            raise MethodNotAllowed(self.methods)

        # ── API key ──────────────────────────────────────────────────
        if self.api_key is not None:
            check_api_key(headers, self.api_key)

        # ── Rate limit ───────────────────────────────────────────────
        if self.rate_limit is not None:
            check_rate_limit(self.path, client_ip, self.rate_limit)

        # ── Extract params & call function ───────────────────────────
        kwargs = extract_params(self.func, query_string, body, content_type)

        result = self.func(**kwargs)

        # Handle async / coroutine results
        if inspect.iscoroutine(result):
            import asyncio
            result = asyncio.run(result)

        status, response_body = success_response(result)
        return status, response_body, extra_headers
