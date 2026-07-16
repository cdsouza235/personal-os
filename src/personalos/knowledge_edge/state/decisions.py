"""Knowledge Edge decision/queue audit state: user_decision, decision_history,
queue_snapshot (amendment §13.1, §13.4, §7.2, §7.4).

``ke_decision_history`` is append-only by construction: this module exposes no update
or delete for it, only ``record_decision_history`` (insert) and list/read helpers.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from personalos.knowledge_edge.state._shared import (
    _count_rows,
    _utc_now,
    _validate_bool,
    _validate_enum,
    _validate_optional_iso_datetime,
    _validate_required_text,
    _validate_text,
)
from personalos.knowledge_edge.state.media import ENTITY_MATCH_TARGET_TYPES as ENTITY_TYPES

DECISION_TRACKS = ("content_status", "decision_state", "queue_visibility_state")
DECISION_STATES = (
    "undecided",
    "watch",
    "save_for_later",
    "skip",
    "watched",
    "watch_live",
    "save_replay",
)
MEDIA_ITEM_DECISION_STATES = ("undecided", "watch", "save_for_later", "skip", "watched")
SCHEDULED_EVENT_DECISION_STATES = ("undecided", "watch_live", "save_replay", "skip", "watched")

QUEUE_SECTIONS = (
    "tomorrow_earnings_events",
    "p0_consequential_leaders",
    "p1_core_podcasts",
    "p2_market_voices",
    "saved_to_reconsider",
    "coverage_and_source_health",
)


def validate_entity_type(value: str) -> str:
    return _validate_enum("entity_type", value, ENTITY_TYPES)


def validate_decision_state(value: str, *, entity_type: str) -> str:
    entity_type = validate_entity_type(entity_type)
    allowed = (
        MEDIA_ITEM_DECISION_STATES
        if entity_type == "media_item"
        else SCHEDULED_EVENT_DECISION_STATES
    )
    return _validate_enum("decision_state", value, allowed)


def validate_decision_track(value: str) -> str:
    return _validate_enum("track", value, DECISION_TRACKS)


def validate_queue_section(value: str) -> str:
    return _validate_enum("section", value, QUEUE_SECTIONS)


# ------------------------------------------------------------------------- user decisions


def upsert_user_decision(
    connection: sqlite3.Connection,
    *,
    decision_id: str,
    entity_type: str,
    entity_id: str,
    decision_state: str,
    live_reminder_opt_in: bool = False,
    decided_at: str | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Create or replace the single current decision record for ``(entity_type, entity_id)``."""
    decision_id = _validate_required_text("decision_id", decision_id)
    entity_type = validate_entity_type(entity_type)
    entity_id = _validate_required_text("entity_id", entity_id)
    decision_state = validate_decision_state(decision_state, entity_type=entity_type)
    live_reminder_opt_in = _validate_bool("live_reminder_opt_in", live_reminder_opt_in)
    decided_at = _validate_optional_iso_datetime("decided_at", decided_at or _utc_now())
    notes = _validate_text("notes", notes)
    now = _utc_now()

    existing = get_user_decision(connection, entity_type=entity_type, entity_id=entity_id)

    with connection:
        if existing is None:
            connection.execute(
                """
                INSERT INTO ke_user_decisions (
                    decision_id, entity_type, entity_id, decision_state,
                    live_reminder_opt_in, decided_at, notes, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_id, entity_type, entity_id, decision_state,
                    int(live_reminder_opt_in), decided_at, notes, now, now,
                ),
            )
        else:
            connection.execute(
                """
                UPDATE ke_user_decisions
                SET decision_state = ?, live_reminder_opt_in = ?, decided_at = ?,
                    notes = ?, updated_at = ?
                WHERE entity_type = ? AND entity_id = ?
                """,
                (
                    decision_state, int(live_reminder_opt_in), decided_at, notes, now,
                    entity_type, entity_id,
                ),
            )

    decision = get_user_decision(connection, entity_type=entity_type, entity_id=entity_id)
    if decision is None:
        raise RuntimeError(
            f"User decision was not persisted for entity_type={entity_type}, entity_id={entity_id}"
        )
    return decision


def get_user_decision(
    connection: sqlite3.Connection, *, entity_type: str, entity_id: str
) -> dict[str, Any] | None:
    entity_type = validate_entity_type(entity_type)
    entity_id = _validate_required_text("entity_id", entity_id)
    row = connection.execute(
        "SELECT * FROM ke_user_decisions WHERE entity_type = ? AND entity_id = ?",
        (entity_type, entity_id),
    ).fetchone()
    return _user_decision_row_to_dict(row) if row is not None else None


def count_user_decisions(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "ke_user_decisions")


def _user_decision_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["live_reminder_opt_in"] = bool(item["live_reminder_opt_in"])
    return item


# ----------------------------------------------------------------------- decision history


def record_decision_history(
    connection: sqlite3.Connection,
    *,
    history_id: str,
    entity_type: str,
    entity_id: str,
    track: str,
    to_value: str,
    from_value: str | None = None,
    changed_at: str | None = None,
    changed_by: str = "system",
    reason: str = "",
) -> dict[str, Any]:
    """Append one immutable audit row. Never updated or deleted (amendment §13.4)."""
    history_id = _validate_required_text("history_id", history_id)
    entity_type = validate_entity_type(entity_type)
    entity_id = _validate_required_text("entity_id", entity_id)
    track = validate_decision_track(track)
    to_value = _validate_required_text("to_value", to_value)
    from_value = None if from_value is None else _validate_required_text("from_value", from_value)
    changed_at = _validate_optional_iso_datetime("changed_at", changed_at or _utc_now())
    changed_by = _validate_required_text("changed_by", changed_by)
    reason = _validate_text("reason", reason)
    now = _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO ke_decision_history (
                history_id, entity_type, entity_id, track, from_value, to_value,
                changed_at, changed_by, reason, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                history_id, entity_type, entity_id, track, from_value, to_value,
                changed_at, changed_by, reason, now,
            ),
        )

    row = connection.execute(
        "SELECT * FROM ke_decision_history WHERE history_id = ?", (history_id,)
    ).fetchone()
    if row is None:
        raise RuntimeError(f"Decision history was not persisted for history_id: {history_id}")
    return dict(row)


def list_decision_history(
    connection: sqlite3.Connection, *, entity_type: str, entity_id: str
) -> list[dict[str, Any]]:
    entity_type = validate_entity_type(entity_type)
    entity_id = _validate_required_text("entity_id", entity_id)
    rows = connection.execute(
        """
        SELECT * FROM ke_decision_history
        WHERE entity_type = ? AND entity_id = ?
        ORDER BY changed_at, history_id
        """,
        (entity_type, entity_id),
    ).fetchall()
    return [dict(row) for row in rows]


def count_decision_history(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "ke_decision_history")


# ------------------------------------------------------------------------ queue snapshots


def record_queue_snapshot(
    connection: sqlite3.Connection,
    *,
    snapshot_id: str,
    queue_date: str,
    section: str,
    entity_type: str,
    entity_id: str,
    rank_position: int,
    explanation: str = "",
) -> dict[str, Any]:
    snapshot_id = _validate_required_text("snapshot_id", snapshot_id)
    queue_date = _validate_required_text("queue_date", queue_date)
    section = validate_queue_section(section)
    entity_type = validate_entity_type(entity_type)
    entity_id = _validate_required_text("entity_id", entity_id)
    if type(rank_position) is not int or rank_position <= 0:
        raise ValueError("rank_position must be a positive integer")
    explanation = _validate_text("explanation", explanation)
    now = _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO ke_queue_snapshots (
                snapshot_id, queue_date, section, entity_type, entity_id, rank_position,
                explanation, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id, queue_date, section, entity_type, entity_id, rank_position,
                explanation, now,
            ),
        )

    row = connection.execute(
        "SELECT * FROM ke_queue_snapshots WHERE snapshot_id = ?", (snapshot_id,)
    ).fetchone()
    if row is None:
        raise RuntimeError(f"Queue snapshot was not persisted for snapshot_id: {snapshot_id}")
    return dict(row)


def list_queue_snapshot(
    connection: sqlite3.Connection, *, queue_date: str, section: str | None = None
) -> list[dict[str, Any]]:
    queue_date = _validate_required_text("queue_date", queue_date)
    if section is None:
        rows = connection.execute(
            """
            SELECT * FROM ke_queue_snapshots WHERE queue_date = ?
            ORDER BY section, rank_position
            """,
            (queue_date,),
        ).fetchall()
    else:
        section = validate_queue_section(section)
        rows = connection.execute(
            """
            SELECT * FROM ke_queue_snapshots WHERE queue_date = ? AND section = ?
            ORDER BY rank_position
            """,
            (queue_date, section),
        ).fetchall()
    return [dict(row) for row in rows]


def count_queue_snapshots(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "ke_queue_snapshots")
