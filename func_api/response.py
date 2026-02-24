"""Response formatting helpers — standard JSON envelope."""

from __future__ import annotations

import json
from typing import Any


def success_response(data: Any) -> tuple[int, dict]:
    """Return a (status_code, body_dict) for a successful call."""
    return 200, {"success": True, "data": _serialize(data)}


def error_response(status_code: int, message: str) -> tuple[int, dict]:
    """Return a (status_code, body_dict) for a failed call."""
    return status_code, {
        "success": False,
        "error": {"code": status_code, "message": message},
    }


def to_json_bytes(body: dict) -> bytes:
    """Encode a dict to pretty-printed UTF-8 JSON bytes."""
    return json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _serialize(obj: Any) -> Any:
    """Best-effort JSON-safe serialization."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): _serialize(v) for k, v in obj.items()}
    # Fallback: try __dict__, then str()
    if hasattr(obj, "__dict__"):
        return _serialize(vars(obj))
    return str(obj)
