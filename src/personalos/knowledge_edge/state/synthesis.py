"""Knowledge Edge synthesis-handoff state (amendment §7.6).

Creating a row here is a no-network, no-Obsidian-write, local-state-only action; the
actual Obsidian draft write is a later-packet concern gated at Session 3.
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
    _validate_required_text,
)
from personalos.knowledge_edge.state.media import ENTITY_MATCH_TARGET_TYPES as ENTITY_TYPES

SYNTHESIS_HANDOFF_TYPES = (
    "copy_synthesis_packet",
    "create_obsidian_draft",
    "no_thesis_impact",
    "promote_to_session_note",
)
SYNTHESIS_HANDOFF_STATUSES = ("staged", "completed")


def validate_synthesis_handoff_entity_type(value: str) -> str:
    return _validate_enum("entity_type", value, ENTITY_TYPES)


def validate_synthesis_handoff_type(value: str) -> str:
    return _validate_enum("handoff_type", value, SYNTHESIS_HANDOFF_TYPES)


def validate_synthesis_handoff_status(value: str) -> str:
    return _validate_enum("status", value, SYNTHESIS_HANDOFF_STATUSES)


def create_synthesis_handoff(
    connection: sqlite3.Connection,
    *,
    handoff_id: str,
    entity_type: str,
    entity_id: str,
    handoff_type: str,
    packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    handoff_id = _validate_required_text("handoff_id", handoff_id)
    entity_type = validate_synthesis_handoff_entity_type(entity_type)
    entity_id = _validate_required_text("entity_id", entity_id)
    handoff_type = validate_synthesis_handoff_type(handoff_type)
    packet_json = _serialize_json(dict(packet or {}))
    now = _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO ke_synthesis_handoffs (
                handoff_id, entity_type, entity_id, handoff_type, packet_json, status,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, 'staged', ?, ?)
            """,
            (handoff_id, entity_type, entity_id, handoff_type, packet_json, now, now),
        )

    handoff = get_synthesis_handoff(connection, handoff_id)
    if handoff is None:
        raise RuntimeError(f"Synthesis handoff was not persisted for handoff_id: {handoff_id}")
    return handoff


def get_synthesis_handoff(
    connection: sqlite3.Connection, handoff_id: str
) -> dict[str, Any] | None:
    handoff_id = _validate_required_text("handoff_id", handoff_id)
    row = connection.execute(
        "SELECT * FROM ke_synthesis_handoffs WHERE handoff_id = ?", (handoff_id,)
    ).fetchone()
    return _handoff_row_to_dict(row) if row is not None else None


def list_synthesis_handoffs(
    connection: sqlite3.Connection, *, entity_type: str | None = None, status: str | None = None
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if entity_type is not None:
        clauses.append("entity_type = ?")
        params.append(validate_synthesis_handoff_entity_type(entity_type))
    if status is not None:
        clauses.append("status = ?")
        params.append(validate_synthesis_handoff_status(status))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = connection.execute(
        f"SELECT * FROM ke_synthesis_handoffs {where} ORDER BY created_at, handoff_id",
        params,
    ).fetchall()
    return [_handoff_row_to_dict(row) for row in rows]


def count_synthesis_handoffs(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "ke_synthesis_handoffs")


def complete_synthesis_handoff(
    connection: sqlite3.Connection, *, handoff_id: str
) -> dict[str, Any]:
    handoff = get_synthesis_handoff(connection, handoff_id)
    if handoff is None:
        raise ValueError(f"Synthesis handoff does not exist: {handoff_id}")
    now = _utc_now()

    with connection:
        connection.execute(
            "UPDATE ke_synthesis_handoffs SET status = 'completed', updated_at = ? WHERE handoff_id = ?",
            (now, handoff_id),
        )

    updated = get_synthesis_handoff(connection, handoff_id)
    if updated is None:
        raise RuntimeError(f"Synthesis handoff was not found after update: {handoff_id}")
    return updated


def _handoff_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["packet"] = _deserialize_json_object(item.pop("packet_json"))
    return item
