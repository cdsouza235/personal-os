"""Shared serialization/validation helpers used across Knowledge Edge state submodules.

Mirrors ``personalos.state._shared``'s helper shapes exactly (same function names and
behavior) rather than importing them, so ``personalos.knowledge_edge.state`` stays a
self-contained sibling package per
``docs/knowledge_edge/PHASE0_ARCHITECTURE_DECISIONS.md`` AD-1 and never depends on
``personalos.state``.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from datetime import UTC, date, datetime
from typing import Any


def _count_rows(connection: sqlite3.Connection, table_name: str) -> int:
    from personalos.knowledge_edge.state import KE_COUNTABLE_TABLES

    if table_name not in KE_COUNTABLE_TABLES:
        raise ValueError(f"Unsupported Knowledge Edge state table: {table_name}")

    return int(connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def _serialize_json(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _deserialize_json_object(value_json: str) -> dict[str, Any]:
    value = json.loads(value_json)
    if not isinstance(value, dict):
        raise ValueError("value must decode to a JSON object")
    return value


def _deserialize_json_array(value_json: str) -> list[Any]:
    value = json.loads(value_json)
    if not isinstance(value, list):
        raise ValueError("value must decode to a JSON array")
    return value


def _validate_json_object(field_name: str, value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a JSON-safe object")
    return dict(value)


def _validate_json_array(field_name: str, value: list[Any]) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a JSON-safe array")
    return list(value)


def _validate_required_text(field_name: str, value: str) -> str:
    value = _validate_text(field_name, value)
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    return value


def _validate_text(field_name: str, value: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    return value


def _validate_optional_text(field_name: str, value: str | None) -> str | None:
    if value is None:
        return None
    return _validate_text(field_name, value)


def _validate_iso_date(field_name: str, value: str) -> str:
    value = _validate_required_text(field_name, value)
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field_name} must be an ISO date") from error
    return value


def _validate_optional_iso_date(field_name: str, value: str | None) -> str | None:
    if value is None:
        return None
    return _validate_iso_date(field_name, value)


def _validate_iso_datetime(field_name: str, value: str) -> str:
    value = _validate_required_text(field_name, value)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field_name} must be an ISO datetime") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone offset")
    return value


def _validate_optional_iso_datetime(field_name: str, value: str | None) -> str | None:
    if value is None:
        return None
    return _validate_iso_datetime(field_name, value)


def _validate_bool(field_name: str, value: bool) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field_name} must be a boolean")
    return value


def _validate_confidence(field_name: str, value: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be a number")
    value = float(value)
    if not (0.0 <= value <= 1.0):
        raise ValueError(f"{field_name} must be between 0 and 1 inclusive")
    return value


def _validate_enum(field_name: str, value: str, allowed: tuple[str, ...]) -> str:
    if not isinstance(value, str) or value not in allowed:
        joined = ", ".join(allowed)
        raise ValueError(f"{field_name} must be one of: {joined}")
    return value


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
