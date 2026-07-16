"""Knowledge Edge roster-change proposal state (amendment §18.3).

Deterministic, human-approved-only roster/threshold recommendations. Nothing here is
ever applied automatically: ``status`` only moves to ``applied`` after an explicit
human decision recorded via ``decide_roster_change_proposal``.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from personalos.knowledge_edge.state._shared import (
    _count_rows,
    _deserialize_json_object,
    _serialize_json,
    _utc_now,
    _validate_enum,
    _validate_optional_text,
    _validate_required_text,
)

ROSTER_PROPOSAL_TYPES = (
    "retire_source",
    "demote_person",
    "promote_company",
    "demote_company",
    "adjust_expiry",
    "add_alias",
    "repair_source",
    "other",
)
ROSTER_PROPOSAL_TARGET_ENTITY_TYPES = ("source", "person", "company", "role", "topic")
ROSTER_PROPOSAL_STATUSES = ("proposed", "approved", "rejected", "applied")


def validate_roster_proposal_type(value: str) -> str:
    return _validate_enum("proposal_type", value, ROSTER_PROPOSAL_TYPES)


def validate_roster_proposal_target_entity_type(value: str) -> str:
    return _validate_enum("target_entity_type", value, ROSTER_PROPOSAL_TARGET_ENTITY_TYPES)


def validate_roster_proposal_status(value: str) -> str:
    return _validate_enum("status", value, ROSTER_PROPOSAL_STATUSES)


def create_roster_change_proposal(
    connection: sqlite3.Connection,
    *,
    proposal_id: str,
    proposal_type: str,
    target_entity_type: str,
    proposed_change: dict[str, Any],
    rationale: str,
    target_entity_id: str | None = None,
) -> dict[str, Any]:
    proposal_id = _validate_required_text("proposal_id", proposal_id)
    proposal_type = validate_roster_proposal_type(proposal_type)
    target_entity_type = validate_roster_proposal_target_entity_type(target_entity_type)
    target_entity_id = _validate_optional_text("target_entity_id", target_entity_id)
    proposed_change_json = _serialize_json(dict(proposed_change))
    rationale = _validate_required_text("rationale", rationale)
    now = _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO ke_roster_change_proposals (
                proposal_id, proposal_type, target_entity_type, target_entity_id,
                proposed_change_json, rationale, status, created_at, updated_at,
                decided_at, decided_by
            )
            VALUES (?, ?, ?, ?, ?, ?, 'proposed', ?, ?, NULL, NULL)
            """,
            (
                proposal_id, proposal_type, target_entity_type, target_entity_id,
                proposed_change_json, rationale, now, now,
            ),
        )

    proposal = get_roster_change_proposal(connection, proposal_id)
    if proposal is None:
        raise RuntimeError(f"Roster change proposal was not persisted for proposal_id: {proposal_id}")
    return proposal


def get_roster_change_proposal(
    connection: sqlite3.Connection, proposal_id: str
) -> dict[str, Any] | None:
    proposal_id = _validate_required_text("proposal_id", proposal_id)
    row = connection.execute(
        "SELECT * FROM ke_roster_change_proposals WHERE proposal_id = ?", (proposal_id,)
    ).fetchone()
    return _proposal_row_to_dict(row) if row is not None else None


def list_roster_change_proposals(
    connection: sqlite3.Connection, *, status: str | None = None
) -> list[dict[str, Any]]:
    if status is None:
        rows = connection.execute(
            "SELECT * FROM ke_roster_change_proposals ORDER BY created_at, proposal_id"
        ).fetchall()
    else:
        status = validate_roster_proposal_status(status)
        rows = connection.execute(
            """
            SELECT * FROM ke_roster_change_proposals WHERE status = ?
            ORDER BY created_at, proposal_id
            """,
            (status,),
        ).fetchall()
    return [_proposal_row_to_dict(row) for row in rows]


def count_roster_change_proposals(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "ke_roster_change_proposals")


def decide_roster_change_proposal(
    connection: sqlite3.Connection,
    *,
    proposal_id: str,
    status: str,
    decided_by: str,
    decided_at: str | None = None,
) -> dict[str, Any]:
    """Record a human decision. ``status`` must be one of approved/rejected/applied --
    ``decided_by`` is required because the schema's own CHECK constraint requires it
    for any non-'proposed' status."""
    proposal = get_roster_change_proposal(connection, proposal_id)
    if proposal is None:
        raise ValueError(f"Roster change proposal does not exist: {proposal_id}")
    status = validate_roster_proposal_status(status)
    if status == "proposed":
        raise ValueError("decide_roster_change_proposal cannot set status back to 'proposed'")
    decided_by = _validate_required_text("decided_by", decided_by)
    decided_at = decided_at or _utc_now()
    now = _utc_now()

    with connection:
        connection.execute(
            """
            UPDATE ke_roster_change_proposals
            SET status = ?, decided_at = ?, decided_by = ?, updated_at = ?
            WHERE proposal_id = ?
            """,
            (status, decided_at, decided_by, now, proposal_id),
        )

    updated = get_roster_change_proposal(connection, proposal_id)
    if updated is None:
        raise RuntimeError(f"Roster change proposal was not found after update: {proposal_id}")
    return updated


def _proposal_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["proposed_change"] = _deserialize_json_object(item.pop("proposed_change_json"))
    return item
