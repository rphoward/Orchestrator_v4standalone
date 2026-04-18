"""Shared HTTP response and small request-shape helpers (presentation only)."""

from __future__ import annotations

import dataclasses
from typing import Any, Iterable, TypeVar

from flask import jsonify, request

T = TypeVar("T")


def jsonify_dataclass(obj: T) -> Any:
    return jsonify(dataclasses.asdict(obj))


def jsonify_dataclass_list(items: Iterable[T]) -> Any:
    return jsonify([dataclasses.asdict(x) for x in items])


def value_error_http_response(
    exc: ValueError,
    *,
    not_found_error_type: str | None = None,
    bad_request_error_type: str | None = None,
) -> tuple[Any, int]:
    msg = str(exc).lower()
    err = str(exc)
    if "not found" in msg:
        payload: dict[str, str] = {"error": err}
        if not_found_error_type is not None:
            payload["error_type"] = not_found_error_type
        return jsonify(payload), 404
    payload400: dict[str, str] = {"error": err}
    if bad_request_error_type is not None:
        payload400["error_type"] = bad_request_error_type
    return jsonify(payload400), 400


def validation_error_response(
    message: str, *, error_type: str = "validation_error", status: int = 400
) -> tuple[Any, int]:
    return jsonify({"error": message, "error_type": error_type}), status


def json_body_dict() -> dict[str, Any]:
    return request.get_json() or {}


def non_empty_strip(data: dict[str, Any], key: str) -> str | None:
    s = (data.get(key) or "").strip()
    return s if s else None


def parse_optional_target_agent_id(raw: Any) -> tuple[int | None, str | None]:
    """Returns (id or None, error message if invalid)."""
    if raw is None:
        return None, None
    if type(raw) is not int or raw < 1:
        return None, "target_agent_id must be a positive integer"
    return raw, None


def parse_optional_positive_agent_id(raw: Any) -> tuple[int | None, str | None]:
    """For invalidate: None if absent; error if present but not a positive int (rejects bool)."""
    if raw is None:
        return None, None
    if type(raw) is not int or raw < 1:
        return None, "agent_id must be a positive integer"
    return raw, None
