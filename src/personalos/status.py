"""Read-only local status summaries for future dashboard surfaces."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime
from types import MappingProxyType
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


# Rail activation states (governance/HUMAN_GATES.md activation ladder). Each value moves
# inert -> soaking -> live ONLY via a Conductor-gated (G5) activation packet editing the
# private literal below (RISK_REGISTER promotes any change to this file).
#
# Fail-closed by construction, not by label:
#   * the literal is validated AT IMPORT — an invalid value makes this module (and thus
#     every consumer) refuse to load, RailStateError;
#   * the exported view is a MappingProxyType — item assignment raises TypeError;
#   * report creation reads the PRIVATE literal and re-validates — rebinding the public
#     module attribute changes nothing a consumer sees.
# Honest residual: Python cannot stop a caller rewriting module privates; that is host-level
# tampering, outside this model (same bound as the harness's trusted-host residual).

class RailStateError(ValueError):
    """An activation-ladder state is outside the legal set — refuse to operate."""


_VALID_RAIL_STATES = frozenset({"inert", "soaking", "live"})
_VALID_SCHEDULER_STATES = frozenset({"off", "manual", "background"})

_RAIL_STATES: dict[str, str] = {
    "todoist": "inert",
    "gmail": "inert",
    "calendar": "inert",
    "model_api": "inert",
}
_SCHEDULER_STATE: str = "off"  # off -> manual -> background (P-SCHED-01/02, G4+G5)


def _validate_rail_states(rails: Mapping[str, str], scheduler: str) -> None:
    """Raise RailStateError on any illegal state value (called at import + every report)."""
    invalid = sorted(
        name for name, value in rails.items() if value not in _VALID_RAIL_STATES
    )
    if scheduler not in _VALID_SCHEDULER_STATES:
        invalid.append("scheduler")
    if invalid:
        raise RailStateError(
            "illegal activation-ladder state(s): "
            + ", ".join(invalid)
            + " — legal rail states are "
            + "/".join(sorted(_VALID_RAIL_STATES))
            + ", legal scheduler states are "
            + "/".join(sorted(_VALID_SCHEDULER_STATES))
        )


_validate_rail_states(_RAIL_STATES, _SCHEDULER_STATE)  # import-time gate: fail closed

RAIL_STATES: Mapping[str, str] = MappingProxyType(_RAIL_STATES)  # immutable public view
SCHEDULER_STATE: str = _SCHEDULER_STATE


def create_rail_state_report() -> dict[str, Any]:
    """Lean rail-state posture (replaces the retired readiness machinery, D-PO-006).

    Reads the private literals (public-attribute rebinding is inert) and re-validates on
    every call; an illegal state raises RailStateError instead of producing a report.
    """
    _validate_rail_states(_RAIL_STATES, _SCHEDULER_STATE)
    states = dict(_RAIL_STATES)
    return {
        "rails": states,
        "scheduler": _SCHEDULER_STATE,
        "any_rail_live": any(value == "live" for value in states.values()),
        "any_rail_soaking": any(value == "soaking" for value in states.values()),
        "posture_note": (
            "Rail activation is a Conductor-gated packet (governance/HUMAN_GATES.md); "
            "state transitions happen only by editing status.py under G5."
        ),
    }


def create_status_summary(
    connection: sqlite3.Connection,
    *,
    config: PersonalOSConfig | None = None,
    recent_event_limit: int = 5,
    database_path: str | None = None,
) -> dict[str, Any]:
    permission_settings = list_permission_settings(connection)
    generated_at_utc = _utc_now()
    counts = {
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
    }
    summary: dict[str, Any] = {
        "generated_at_utc": generated_at_utc,
        "counts": counts,
        "permission_settings": permission_settings,
        "permission_settings_count": len(permission_settings),
        "rail_states": create_rail_state_report(),
        "database_path": database_path,
        "database_access": "read_only_status",
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
