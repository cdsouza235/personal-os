"""Read-only local status summaries for future dashboard surfaces."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from personalos.config import PersonalOSConfig
from personalos.side_effects import (
    count_external_write_attempts,
    count_external_write_intents,
    count_idempotency_records,
)
from personalos.scheduler import count_scheduler_jobs, count_scheduler_runs
from personalos.synthesis_apply import (
    count_synthesis_apply_items,
    count_synthesis_apply_runs,
)
from personalos.state import (
    count_fitness_file_contracts,
    count_fitness_integration_states,
    count_fitness_validation_runs,
    count_followups,
    count_priorities,
    count_projects,
    count_routines,
    list_permission_settings,
)


def create_status_summary(
    connection: sqlite3.Connection,
    *,
    config: PersonalOSConfig | None = None,
    recent_event_limit: int = 5,
) -> dict[str, Any]:
    permission_settings = list_permission_settings(connection)
    summary: dict[str, Any] = {
        "generated_at_utc": _utc_now(),
        "counts": {
            "routines": count_routines(connection),
            "priorities": count_priorities(connection),
            "projects": count_projects(connection),
            "followups": count_followups(connection),
            "fitness_integration_state": count_fitness_integration_states(connection),
            "fitness_validation_runs": count_fitness_validation_runs(connection),
            "fitness_file_contracts": count_fitness_file_contracts(connection),
            "external_write_intents": count_external_write_intents(connection),
            "external_write_attempts": count_external_write_attempts(connection),
            "idempotency_records": count_idempotency_records(connection),
            "synthesis_apply_runs": count_synthesis_apply_runs(connection),
            "synthesis_apply_items": count_synthesis_apply_items(connection),
            "scheduler_jobs": count_scheduler_jobs(connection),
            "scheduler_runs": count_scheduler_runs(connection),
        },
        "permission_settings": permission_settings,
        "permission_settings_count": len(permission_settings),
        "recent_system_events": list_recent_system_events(
            connection,
            limit=recent_event_limit,
        ),
    }

    if config is not None:
        summary["environment"] = config.environment.value

    return summary


def list_recent_system_events(
    connection: sqlite3.Connection,
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    if limit < 0:
        raise ValueError("limit must be non-negative")

    rows = connection.execute(
        """
        SELECT event_id, timestamp_utc, source, event_type, message, metadata_json
        FROM system_events
        ORDER BY timestamp_utc DESC, event_id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [_system_event_row_to_dict(row) for row in rows]


def _system_event_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "event_id": row["event_id"],
        "timestamp_utc": row["timestamp_utc"],
        "source": row["source"],
        "event_type": row["event_type"],
        "message": row["message"],
        "metadata": _deserialize_metadata(row["metadata_json"]),
    }


def _deserialize_metadata(metadata_json: str) -> dict[str, Any]:
    metadata = json.loads(metadata_json)
    if not isinstance(metadata, dict):
        raise ValueError("metadata_json must decode to an object")
    return metadata


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
