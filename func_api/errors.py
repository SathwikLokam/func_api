"""Custom exceptions and JSON error response helpers."""

from __future__ import annotations


class APIError(Exception):
    """Base exception for all func_api errors."""

    def __init__(self, status_code: int = 500, message: str = "Internal Server Error"):
        self.status_code = status_code
        self.message = message
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "success": False,
            "error": {
                "code": self.status_code,
                "message": self.message,
            },
        }


class BadRequest(APIError):
    """400 — malformed or missing parameters."""

    def __init__(self, message: str = "Bad Request"):
        super().__init__(400, message)


class Unauthorized(APIError):
    """401 — missing or invalid API key."""

    def __init__(self, message: str = "Unauthorized – invalid or missing API key"):
        super().__init__(401, message)


class Forbidden(APIError):
    """403 — origin not allowed (CORS)."""

    def __init__(self, message: str = "Forbidden"):
        super().__init__(403, message)


class NotFound(APIError):
    """404 — route does not exist."""

    def __init__(self, message: str = "Not Found"):
        super().__init__(404, message)


class MethodNotAllowed(APIError):
    """405 — HTTP method not supported for this route."""

    def __init__(self, allowed: list[str] | None = None):
        self.allowed = allowed or []
        msg = "Method Not Allowed"
        if self.allowed:
            msg += f". Allowed: {', '.join(self.allowed)}"
        super().__init__(405, msg)


class RateLimited(APIError):
    """429 — too many requests."""

    def __init__(self, message: str = "Rate limit exceeded – try again later"):
        super().__init__(429, message)
