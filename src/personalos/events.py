"""Structured system events for development and test runtime activity."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class EventType(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SAFETY_BLOCK = "safety_block"


@dataclass(frozen=True)
class SystemEvent:
    event_id: str
    timestamp_utc: str
    source: str
    event_type: EventType
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)


def create_system_event(
    *,
    source: str,
    event_type: EventType | str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> SystemEvent:
    return SystemEvent(
        event_id=str(uuid4()),
        timestamp_utc=datetime.now(UTC).isoformat(),
        source=source,
        event_type=EventType(event_type),
        message=message,
        metadata=metadata or {},
    )


def record_system_event(connection: sqlite3.Connection, event: SystemEvent) -> None:
    metadata_json = serialize_metadata(event.metadata)
    with connection:
        connection.execute(
            """
            INSERT INTO system_events (
                event_id,
                timestamp_utc,
                source,
                event_type,
                message,
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.timestamp_utc,
                event.source,
                event.event_type.value,
                event.message,
                metadata_json,
            ),
        )


def serialize_metadata(metadata: dict[str, Any]) -> str:
    return json.dumps(
        metadata,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
