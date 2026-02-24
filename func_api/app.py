"""FuncAPI — lightweight app that serves decorated functions as HTTP endpoints.

Uses only the Python standard library (http.server + json).
"""

from __future__ import annotations

import json
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Callable, Any
from urllib.parse import urlparse, unquote

from func_api.decorators import Route
from func_api.errors import APIError, NotFound
from func_api.response import error_response, to_json_bytes


class FuncAPI:
    """Collect decorated endpoints and serve them over HTTP.

    Usage::

        app = FuncAPI(title="My Service")

        @app.api("/add", methods=["GET", "POST"])
        def add(a: int, b: int) -> int:
            return a + b

        app.run()                       # default 127.0.0.1:8000
    """

    def __init__(self, title: str = "FuncAPI", version: str = "1.0.0"):
        self.title = title
        self.version = version
        self._routes: dict[str, Route] = {}

    # ── Decorator ─────────────────────────────────────────────────────

    def api(
        self,
        path: str,
        *,
        methods: list[str] | None = None,
        api_key: str | None = None,
        rate_limit: int | None = None,
        allowed_origins: list[str] | None = None,
    ) -> Callable:
        """Register a function as an HTTP endpoint.

        Parameters
        ----------
        path : str
            URL path, e.g. ``"/add"``.
        methods : list[str], optional
            Allowed HTTP methods (default ``["GET"]``).
        api_key : str, optional
            If set, requests must include ``X-API-Key: <value>`` header.
        rate_limit : int, optional
            Max requests per minute per client IP.
        allowed_origins : list[str], optional
            CORS allowed origins (``["*"]`` for any).
        """
        if methods is None:
            methods = ["GET"]

        def decorator(func: Callable) -> Callable:
            route = Route(
                path=path,
                func=func,
                methods=methods,
                api_key=api_key,
                rate_limit=rate_limit,
                allowed_origins=allowed_origins,
            )
            self._routes[path] = route
            return func  # return original function untouched

        return decorator

    # ── Built-in info endpoint ────────────────────────────────────────

    def _info(self) -> dict:
        return {
            "title": self.title,
            "version": self.version,
            "endpoints": [
                {
                    "path": r.path,
                    "methods": r.methods,
                    "secured": r.api_key is not None,
                    "rate_limited": r.rate_limit is not None,
                }
                for r in self._routes.values()
            ],
        }

    # ── Server ────────────────────────────────────────────────────────

    def run(self, host: str = "127.0.0.1", port: int = 8000) -> None:
        """Start the HTTP server (blocking)."""
        app = self  # capture for inner class

        class Handler(BaseHTTPRequestHandler):
            """Thin HTTP handler that dispatches to registered Routes."""

            def _dispatch(self):
                parsed = urlparse(self.path)
                path = unquote(parsed.path).rstrip("/") or "/"
                query = parsed.query
                method = self.command.upper()

                # Read body
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length) if content_length else None
                content_type = self.headers.get("Content-Type")

                # Lowercase header dict for easy lookup
                headers = {k.lower(): v for k, v in self.headers.items()}
                client_ip = self.client_address[0]

                # Built-in /info route
                if path == "/info":
                    self._send_json(200, {"success": True, "data": app._info()})
                    return

                route = app._routes.get(path)
                if route is None:
                    raise NotFound(f"No endpoint registered at '{path}'")

                status, body_dict, extra_headers = route.handle(
                    method, query, body, content_type, headers, client_ip,
                )
                self._send_json(status, body_dict, extra_headers)

            # --- HTTP verbs all go through _dispatch ---
            def do_GET(self):       self._safe_dispatch()
            def do_POST(self):      self._safe_dispatch()
            def do_PUT(self):       self._safe_dispatch()
            def do_PATCH(self):     self._safe_dispatch()
            def do_DELETE(self):    self._safe_dispatch()
            def do_OPTIONS(self):   self._safe_dispatch()

            def _safe_dispatch(self):
                try:
                    self._dispatch()
                except APIError as exc:
                    status, body_dict = error_response(exc.status_code, exc.message)
                    extra = {}
                    if hasattr(exc, "allowed") and exc.allowed:
                        extra["Allow"] = ", ".join(exc.allowed)
                    self._send_json(status, body_dict, extra)
                except Exception:
                    traceback.print_exc()
                    status, body_dict = error_response(500, "Internal Server Error")
                    self._send_json(status, body_dict)

            def _send_json(
                self,
                status: int,
                body: dict,
                extra_headers: dict[str, str] | None = None,
            ):
                payload = to_json_bytes(body)
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                if extra_headers:
                    for k, v in extra_headers.items():
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format, *args):
                # Compact one-line logging
                print(f"[{self.log_date_time_string()}] {args[0]}")

        server = HTTPServer((host, port), Handler)
        print(f"\n  🚀  {app.title} v{app.version}")
        print(f"  ➜  http://{host}:{port}")
        print(f"  ➜  {len(app._routes)} endpoint(s) registered")
        print(f"  ➜  /info for auto-generated endpoint list\n")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n  ⏹  Server stopped.")
            server.server_close()
