"""Shared serialization/validation helpers used across state submodules."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from datetime import UTC, date, datetime
from typing import Any


def _count_rows(connection: sqlite3.Connection, table_name: str) -> int:
    from personalos.state import COUNTABLE_STATE_TABLES

    if table_name not in COUNTABLE_STATE_TABLES:
        raise ValueError(f"Unsupported state table: {table_name}")

    return int(connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def _serialize_metadata(metadata: Mapping[str, Any]) -> str:
    return json.dumps(
        dict(metadata),
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _deserialize_metadata(metadata_json: str) -> dict[str, Any]:
    metadata = json.loads(metadata_json)
    if not isinstance(metadata, dict):
        raise ValueError("metadata_json must decode to an object")
    return metadata


def _validate_metadata(field_name: str, value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a JSON-safe object")
    return dict(value)


def _validate_required_text(field_name: str, value: str) -> str:
    value = _validate_text(field_name, value)
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    return value


def _validate_text(field_name: str, value: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    return value


def _validate_iso_date(field_name: str, value: str) -> str:
    value = _validate_required_text(field_name, value)
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field_name} must be an ISO date") from error
    return value


def _validate_iso_datetime(field_name: str, value: str) -> str:
    value = _validate_required_text(field_name, value)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field_name} must be an ISO datetime") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone offset")
    return value


def _validate_bool(field_name: str, value: bool) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field_name} must be a boolean")
    return value


def _validate_optional_nonnegative_int(field_name: str, value: int | None) -> int | None:
    if value is None:
        return None
    if type(value) is not int:
        raise ValueError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()

