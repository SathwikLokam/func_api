"""Request parsing helpers — extract and cast parameters from HTTP requests."""

from __future__ import annotations

import inspect
import json
from typing import Any, Callable, get_type_hints
from urllib.parse import parse_qs

from func_api.errors import BadRequest


# Types we know how to cast from strings
_CASTABLE = (int, float, bool, str)


def extract_params(
    func: Callable,
    query_string: str,
    body: bytes | None,
    content_type: str | None,
) -> dict[str, Any]:
    """Build a kwargs dict for *func* from the incoming request data.

    Priority: JSON body values override query-string values.
    Values are cast to the types declared in the function's annotations.
    """
    sig = inspect.signature(func)
    try:
        hints = get_type_hints(func)
    except Exception:
        hints = {}

    # --- collect raw values ------------------------------------------------
    raw: dict[str, Any] = {}

    # Query string
    if query_string:
        qs = parse_qs(query_string, keep_blank_values=True)
        for key, values in qs.items():
            raw[key] = values[0] if len(values) == 1 else values

    # JSON body
    if body and content_type and "application/json" in content_type:
        try:
            parsed = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise BadRequest(f"Invalid JSON body: {exc}") from exc
        if isinstance(parsed, dict):
            raw.update(parsed)

    # --- cast & validate ---------------------------------------------------
    kwargs: dict[str, Any] = {}
    for name, param in sig.parameters.items():
        if name in raw:
            kwargs[name] = _cast(raw[name], hints.get(name), name)
        elif param.default is not inspect.Parameter.empty:
            # has a default — skip, Python will fill it in
            continue
        else:
            raise BadRequest(f"Missing required parameter: '{name}'")

    return kwargs


def _cast(value: Any, target_type: type | None, name: str) -> Any:
    """Attempt to cast *value* to *target_type*."""
    if target_type is None or target_type is inspect.Parameter.empty:
        return value  # no hint — pass through as-is

    if isinstance(value, target_type):
        return value

    # Bool from string needs special handling ("true"/"false")
    if target_type is bool and isinstance(value, str):
        if value.lower() in ("true", "1", "yes"):
            return True
        if value.lower() in ("false", "0", "no"):
            return False
        raise BadRequest(f"Cannot cast parameter '{name}' value '{value}' to bool")

    if target_type in _CASTABLE:
        try:
            return target_type(value)
        except (ValueError, TypeError) as exc:
            raise BadRequest(
                f"Cannot cast parameter '{name}' value '{value}' to {target_type.__name__}: {exc}"
            ) from exc

    # Complex types — pass through and let the function deal with it
    return value
