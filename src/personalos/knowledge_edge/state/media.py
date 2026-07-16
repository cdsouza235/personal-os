"""Knowledge Edge media state: media_item, discovery_occurrence, entity_match,
canonical_group (amendment §13.1, §13.2, §11.3, §11.4).
"""

from __future__ import annotations

import sqlite3
from typing import Any

from personalos.knowledge_edge.state._shared import (
    _count_rows,
    _deserialize_json_array,
    _deserialize_json_object,
    _serialize_json,
    _utc_now,
    _validate_confidence,
    _validate_enum,
    _validate_optional_iso_datetime,
    _validate_optional_text,
    _validate_required_text,
    _validate_text,
)
from personalos.knowledge_edge.state.events import (
    MEDIA_CONTENT_STATUSES,
    MEDIA_DECISION_STATES,
    QUEUE_VISIBILITY_STATES,
    validate_media_content_transition,
    validate_media_decision_transition,
    validate_queue_visibility_transition,
)

MEDIA_SOURCE_PRECEDENCES = (
    "official",
    "regulator_exchange",
    "approved_structured_provider",
    "reputable_secondary",
    "broad_search",
)
MEDIA_TYPES = (
    "podcast_episode",
    "video_interview",
    "panel",
    "keynote",
    "clip",
    "earnings_call_recording",
    "other",
)
DIRECTNESS_CLASSES = (
    "direct_primary",
    "direct_secondary_upload",
    "panel_participant",
    "host_or_interviewer",
    "mentioned_only",
    "commentary_about",
    "ambiguous",
)
CANONICAL_GROUP_DEDUPE_RULES = (
    "shared_feed_guid",
    "same_channel_video_id",
    "same_underlying_id_title_change",
    "live_and_official_replay",
    "manual",
)
ENTITY_MATCH_TARGET_TYPES = ("media_item", "scheduled_event")
ENTITY_MATCH_ENTITY_TYPES = ("person", "role", "company", "topic")
ENTITY_MATCH_METHODS = (
    "exact_alias",
    "spelling_variant",
    "role_occupant_resolution",
    "company_ticker_mention",
    "topic_keyword",
    "manual",
)


def validate_media_source_precedence(value: str) -> str:
    return _validate_enum("source_precedence", value, MEDIA_SOURCE_PRECEDENCES)


def validate_media_type(value: str) -> str:
    return _validate_enum("media_type", value, MEDIA_TYPES)


def validate_directness_class(value: str) -> str:
    return _validate_enum("directness_class", value, DIRECTNESS_CLASSES)


def validate_canonical_group_dedupe_rule(value: str) -> str:
    return _validate_enum("dedupe_rule", value, CANONICAL_GROUP_DEDUPE_RULES)


def validate_entity_match_target_type(value: str) -> str:
    return _validate_enum("target_type", value, ENTITY_MATCH_TARGET_TYPES)


def validate_entity_match_entity_type(value: str) -> str:
    return _validate_enum("matched_entity_type", value, ENTITY_MATCH_ENTITY_TYPES)


def validate_entity_match_method(value: str) -> str:
    return _validate_enum("match_method", value, ENTITY_MATCH_METHODS)


# ------------------------------------------------------------------------ canonical groups


def create_canonical_group(
    connection: sqlite3.Connection,
    *,
    canonical_group_id: str,
    dedupe_rule: str,
    notes: str = "",
) -> dict[str, Any]:
    canonical_group_id = _validate_required_text("canonical_group_id", canonical_group_id)
    dedupe_rule = validate_canonical_group_dedupe_rule(dedupe_rule)
    notes = _validate_text("notes", notes)
    now = _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO ke_canonical_groups (canonical_group_id, dedupe_rule, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (canonical_group_id, dedupe_rule, notes, now, now),
        )

    row = connection.execute(
        "SELECT * FROM ke_canonical_groups WHERE canonical_group_id = ?", (canonical_group_id,)
    ).fetchone()
    if row is None:
        raise RuntimeError(
            f"Canonical group was not persisted for canonical_group_id: {canonical_group_id}"
        )
    return dict(row)


def list_canonical_group_members(
    connection: sqlite3.Connection, *, canonical_group_id: str
) -> list[dict[str, Any]]:
    canonical_group_id = _validate_required_text("canonical_group_id", canonical_group_id)
    rows = connection.execute(
        """
        SELECT * FROM ke_media_items
        WHERE canonical_group_id = ?
        ORDER BY is_canonical DESC, media_item_id
        """,
        (canonical_group_id,),
    ).fetchall()
    return [_media_item_row_to_dict(row) for row in rows]


# ---------------------------------------------------------------------------- media items


def create_media_item(
    connection: sqlite3.Connection,
    *,
    media_item_id: str,
    source_id: str,
    source_specific_id: str,
    canonical_url: str,
    title: str,
    source_precedence: str,
    media_type: str,
    dedupe_key: str,
    alternate_urls: list[str] | None = None,
    description_excerpt: str = "",
    published_at: str | None = None,
    discovered_at: str | None = None,
    duration_seconds: int | None = None,
    directness_class: str | None = None,
    match_confidence: float | None = None,
    priority_score: float | None = None,
    priority_explanation: str = "",
    canonical_group_id: str | None = None,
    is_canonical: bool = True,
    pinned: bool = False,
    coverage_notes: str = "",
) -> dict[str, Any]:
    media_item_id = _validate_required_text("media_item_id", media_item_id)
    source_id = _validate_required_text("source_id", source_id)
    source_specific_id = _validate_required_text("source_specific_id", source_specific_id)
    canonical_url = _validate_required_text("canonical_url", canonical_url)
    title = _validate_required_text("title", title)
    source_precedence = validate_media_source_precedence(source_precedence)
    media_type = validate_media_type(media_type)
    dedupe_key = _validate_required_text("dedupe_key", dedupe_key)
    description_excerpt = _validate_text("description_excerpt", description_excerpt)
    published_at = _validate_optional_iso_datetime("published_at", published_at)
    discovered_at = _validate_optional_iso_datetime("discovered_at", discovered_at or _utc_now())
    if duration_seconds is not None and duration_seconds < 0:
        raise ValueError("duration_seconds must be non-negative")
    if directness_class is not None:
        directness_class = validate_directness_class(directness_class)
    if match_confidence is not None:
        match_confidence = _validate_confidence("match_confidence", match_confidence)
    priority_explanation = _validate_text("priority_explanation", priority_explanation)
    coverage_notes = _validate_text("coverage_notes", coverage_notes)
    alternate_urls_json = _serialize_json(list(alternate_urls or []))
    now = _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO ke_media_items (
                media_item_id, source_id, source_specific_id, canonical_url,
                alternate_urls_json, title, description_excerpt, source_precedence,
                published_at, discovered_at, media_type, duration_seconds,
                directness_class, match_confidence, priority_score, priority_explanation,
                canonical_group_id, is_canonical, dedupe_key, content_status,
                decision_state, queue_visibility_state, pinned, coverage_notes,
                created_at, updated_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                'discovered', 'undecided', 'candidate', ?, ?, ?, ?
            )
            """,
            (
                media_item_id, source_id, source_specific_id, canonical_url,
                alternate_urls_json, title, description_excerpt, source_precedence,
                published_at, discovered_at, media_type, duration_seconds,
                directness_class, match_confidence, priority_score, priority_explanation,
                canonical_group_id, int(bool(is_canonical)), dedupe_key,
                int(bool(pinned)), coverage_notes, now, now,
            ),
        )

    media_item = get_media_item(connection, media_item_id)
    if media_item is None:
        raise RuntimeError(f"Media item was not persisted for media_item_id: {media_item_id}")
    return media_item


def get_media_item(connection: sqlite3.Connection, media_item_id: str) -> dict[str, Any] | None:
    media_item_id = _validate_required_text("media_item_id", media_item_id)
    row = connection.execute(
        "SELECT * FROM ke_media_items WHERE media_item_id = ?", (media_item_id,)
    ).fetchone()
    return _media_item_row_to_dict(row) if row is not None else None


def get_media_item_by_dedupe_key(
    connection: sqlite3.Connection, dedupe_key: str
) -> dict[str, Any] | None:
    dedupe_key = _validate_required_text("dedupe_key", dedupe_key)
    row = connection.execute(
        "SELECT * FROM ke_media_items WHERE dedupe_key = ?", (dedupe_key,)
    ).fetchone()
    return _media_item_row_to_dict(row) if row is not None else None


def list_media_items(
    connection: sqlite3.Connection,
    *,
    source_id: str | None = None,
    queue_visibility_state: str | None = None,
    decision_state: str | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if source_id is not None:
        clauses.append("source_id = ?")
        params.append(source_id)
    if queue_visibility_state is not None:
        clauses.append("queue_visibility_state = ?")
        params.append(_validate_enum("queue_visibility_state", queue_visibility_state, QUEUE_VISIBILITY_STATES))
    if decision_state is not None:
        clauses.append("decision_state = ?")
        params.append(_validate_enum("decision_state", decision_state, MEDIA_DECISION_STATES))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = connection.execute(
        f"SELECT * FROM ke_media_items {where} ORDER BY discovered_at DESC, media_item_id",
        params,
    ).fetchall()
    return [_media_item_row_to_dict(row) for row in rows]


def count_media_items(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "ke_media_items")


def update_media_content_status(
    connection: sqlite3.Connection, *, media_item_id: str, content_status: str
) -> dict[str, Any]:
    _validate_enum("content_status", content_status, MEDIA_CONTENT_STATUSES)
    media_item = get_media_item(connection, media_item_id)
    if media_item is None:
        raise ValueError(f"Media item does not exist: {media_item_id}")
    validate_media_content_transition(media_item["content_status"], content_status)
    return _update_media_item_field(connection, media_item_id, "content_status", content_status)


def update_media_decision_state(
    connection: sqlite3.Connection, *, media_item_id: str, decision_state: str
) -> dict[str, Any]:
    _validate_enum("decision_state", decision_state, MEDIA_DECISION_STATES)
    media_item = get_media_item(connection, media_item_id)
    if media_item is None:
        raise ValueError(f"Media item does not exist: {media_item_id}")
    validate_media_decision_transition(media_item["decision_state"], decision_state)
    return _update_media_item_field(connection, media_item_id, "decision_state", decision_state)


def update_media_queue_visibility(
    connection: sqlite3.Connection, *, media_item_id: str, queue_visibility_state: str
) -> dict[str, Any]:
    _validate_enum("queue_visibility_state", queue_visibility_state, QUEUE_VISIBILITY_STATES)
    media_item = get_media_item(connection, media_item_id)
    if media_item is None:
        raise ValueError(f"Media item does not exist: {media_item_id}")
    validate_queue_visibility_transition(
        media_item["queue_visibility_state"], queue_visibility_state
    )
    return _update_media_item_field(
        connection, media_item_id, "queue_visibility_state", queue_visibility_state
    )


def _update_media_item_field(
    connection: sqlite3.Connection, media_item_id: str, column: str, value: str
) -> dict[str, Any]:
    if column not in ("content_status", "decision_state", "queue_visibility_state"):
        raise ValueError(f"Unsupported media item transition column: {column}")
    now = _utc_now()
    with connection:
        connection.execute(
            f"UPDATE ke_media_items SET {column} = ?, updated_at = ? WHERE media_item_id = ?",
            (value, now, media_item_id),
        )
    updated = get_media_item(connection, media_item_id)
    if updated is None:
        raise RuntimeError(f"Media item was not found after update: {media_item_id}")
    return updated


def _media_item_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["is_canonical"] = bool(item["is_canonical"])
    item["pinned"] = bool(item["pinned"])
    item["alternate_urls"] = _deserialize_json_array(item.pop("alternate_urls_json"))
    return item


# ------------------------------------------------------------------- discovery occurrences


def create_discovery_occurrence(
    connection: sqlite3.Connection,
    *,
    occurrence_id: str,
    media_item_id: str,
    source_id: str,
    scan_run_id: str | None = None,
    discovered_at: str | None = None,
    raw_payload_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    occurrence_id = _validate_required_text("occurrence_id", occurrence_id)
    media_item_id = _validate_required_text("media_item_id", media_item_id)
    source_id = _validate_required_text("source_id", source_id)
    discovered_at = _validate_optional_iso_datetime("discovered_at", discovered_at or _utc_now())
    raw_payload_summary_json = _serialize_json(dict(raw_payload_summary or {}))
    now = _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO ke_discovery_occurrences (
                occurrence_id, media_item_id, source_id, scan_run_id, discovered_at,
                raw_payload_summary_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                occurrence_id, media_item_id, source_id, scan_run_id, discovered_at,
                raw_payload_summary_json, now,
            ),
        )

    row = connection.execute(
        "SELECT * FROM ke_discovery_occurrences WHERE occurrence_id = ?", (occurrence_id,)
    ).fetchone()
    if row is None:
        raise RuntimeError(f"Discovery occurrence was not persisted for occurrence_id: {occurrence_id}")
    return _occurrence_row_to_dict(row)


def list_discovery_occurrences(
    connection: sqlite3.Connection, *, media_item_id: str
) -> list[dict[str, Any]]:
    media_item_id = _validate_required_text("media_item_id", media_item_id)
    rows = connection.execute(
        "SELECT * FROM ke_discovery_occurrences WHERE media_item_id = ? ORDER BY discovered_at",
        (media_item_id,),
    ).fetchall()
    return [_occurrence_row_to_dict(row) for row in rows]


def _occurrence_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["raw_payload_summary"] = _deserialize_json_object(item.pop("raw_payload_summary_json"))
    return item


# ------------------------------------------------------------------------- entity matches


def create_entity_match(
    connection: sqlite3.Connection,
    *,
    entity_match_id: str,
    target_type: str,
    target_id: str,
    matched_entity_type: str,
    matched_entity_id: str,
    match_method: str,
    confidence: float,
    reason: str,
) -> dict[str, Any]:
    entity_match_id = _validate_required_text("entity_match_id", entity_match_id)
    target_type = validate_entity_match_target_type(target_type)
    target_id = _validate_required_text("target_id", target_id)
    matched_entity_type = validate_entity_match_entity_type(matched_entity_type)
    matched_entity_id = _validate_required_text("matched_entity_id", matched_entity_id)
    match_method = validate_entity_match_method(match_method)
    confidence = _validate_confidence("confidence", confidence)
    reason = _validate_required_text("reason", reason)
    now = _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO ke_entity_matches (
                entity_match_id, target_type, target_id, matched_entity_type,
                matched_entity_id, match_method, confidence, reason, is_false_positive,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                entity_match_id, target_type, target_id, matched_entity_type,
                matched_entity_id, match_method, confidence, reason, now, now,
            ),
        )

    match = get_entity_match(connection, entity_match_id)
    if match is None:
        raise RuntimeError(f"Entity match was not persisted for entity_match_id: {entity_match_id}")
    return match


def get_entity_match(connection: sqlite3.Connection, entity_match_id: str) -> dict[str, Any] | None:
    entity_match_id = _validate_required_text("entity_match_id", entity_match_id)
    row = connection.execute(
        "SELECT * FROM ke_entity_matches WHERE entity_match_id = ?", (entity_match_id,)
    ).fetchone()
    return _entity_match_row_to_dict(row) if row is not None else None


def list_entity_matches(
    connection: sqlite3.Connection, *, target_type: str, target_id: str
) -> list[dict[str, Any]]:
    target_type = validate_entity_match_target_type(target_type)
    target_id = _validate_required_text("target_id", target_id)
    rows = connection.execute(
        """
        SELECT * FROM ke_entity_matches
        WHERE target_type = ? AND target_id = ?
        ORDER BY confidence DESC, entity_match_id
        """,
        (target_type, target_id),
    ).fetchall()
    return [_entity_match_row_to_dict(row) for row in rows]


def flag_entity_match_false_positive(
    connection: sqlite3.Connection, *, entity_match_id: str, flagged_at: str | None = None
) -> dict[str, Any]:
    entity_match_id = _validate_required_text("entity_match_id", entity_match_id)
    flagged_at = _validate_optional_iso_datetime("flagged_at", flagged_at or _utc_now())
    now = _utc_now()

    with connection:
        connection.execute(
            """
            UPDATE ke_entity_matches
            SET is_false_positive = 1, flagged_at = ?, updated_at = ?
            WHERE entity_match_id = ?
            """,
            (flagged_at, now, entity_match_id),
        )

    match = get_entity_match(connection, entity_match_id)
    if match is None:
        raise ValueError(f"Entity match does not exist: {entity_match_id}")
    return match


def _entity_match_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["is_false_positive"] = bool(item["is_false_positive"])
    return item
