"""Knowledge Edge scheduled-event state, plus the three-track transition tables shared by
both media items and scheduled events (amendment §8.4, §13.3).

Every media item and scheduled event carries three independent state tracks:
    content_status / event_status  -- the pipeline's own processing/lifecycle status
    decision_state                 -- the user's Watch/Save/Skip/Watched-shaped decision
    queue_visibility_state         -- candidate -> queued | suppressed | expired -> archived

``watched``, ``skipped``, and ``expired`` never appear in the content/event-status track;
they only ever appear in ``decision_state`` / ``queue_visibility_state``. This module is
the single source of truth for which values exist and which transitions between them are
valid, for both entity types. It performs no I/O beyond the ``ke_scheduled_events`` CRUD
functions at the bottom of the file -- the transition tables and validators are pure.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from personalos.knowledge_edge.state._shared import (
    _count_rows,
    _deserialize_json_array,
    _serialize_json,
    _utc_now,
    _validate_enum,
    _validate_iso_date,
    _validate_optional_iso_datetime,
    _validate_optional_text,
    _validate_required_text,
    _validate_text,
)

# --------------------------------------------------------------- media content status

MEDIA_CONTENT_STATUSES = (
    "discovered",
    "normalized",
    "ranked",
    "corrected",
    "superseded",
    "archived",
)
MEDIA_CONTENT_TRANSITIONS: dict[str, frozenset[str]] = {
    "discovered": frozenset({"normalized", "superseded"}),
    "normalized": frozenset({"ranked", "corrected", "superseded"}),
    "ranked": frozenset({"corrected", "superseded", "archived"}),
    "corrected": frozenset({"normalized"}),
    "superseded": frozenset(),
    "archived": frozenset(),
}

# --------------------------------------------------------------- media decision state

MEDIA_DECISION_STATES = ("undecided", "watch", "save_for_later", "skip", "watched")
MEDIA_DECISION_TRANSITIONS: dict[str, frozenset[str]] = {
    "undecided": frozenset({"watch", "save_for_later", "skip"}),
    "watch": frozenset({"watched", "skip"}),
    "save_for_later": frozenset({"watch", "watched", "skip"}),
    "skip": frozenset(),
    "watched": frozenset(),
}

# ------------------------------------------------------------------------ event status

EVENT_STATUSES = (
    "discovered",
    "tentative",
    "confirmed",
    "scheduled",
    "live",
    "ended",
    "replay_pending",
    "replay_available",
    "archived",
    "changed",
    "cancelled",
)
EVENT_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    "discovered": frozenset({"tentative", "confirmed", "changed", "cancelled"}),
    "tentative": frozenset({"confirmed", "changed", "cancelled"}),
    "confirmed": frozenset({"scheduled", "changed", "cancelled"}),
    "scheduled": frozenset({"live", "changed", "cancelled"}),
    "live": frozenset({"ended"}),
    "ended": frozenset({"replay_pending"}),
    "replay_pending": frozenset({"replay_available"}),
    "replay_available": frozenset({"archived"}),
    "changed": frozenset({"tentative", "confirmed", "scheduled", "cancelled"}),
    "cancelled": frozenset(),
    "archived": frozenset(),
}
# Any pre-event status may transition to changed/cancelled (amendment §8.4). "Pre-event"
# is everything before `live`.
EVENT_PRE_EVENT_STATUSES = frozenset(
    {"discovered", "tentative", "confirmed", "scheduled", "changed"}
)

# ------------------------------------------------------------------------ event decision

EVENT_DECISION_STATES = ("undecided", "watch_live", "save_replay", "skip", "watched")
EVENT_DECISION_TRANSITIONS: dict[str, frozenset[str]] = {
    "undecided": frozenset({"watch_live", "save_replay", "skip"}),
    "watch_live": frozenset({"watched", "skip"}),
    "save_replay": frozenset({"watched", "skip"}),
    "skip": frozenset(),
    "watched": frozenset(),
}

# ------------------------------------------------------------------- queue visibility

QUEUE_VISIBILITY_STATES = ("candidate", "queued", "suppressed", "expired", "archived")
QUEUE_VISIBILITY_TRANSITIONS: dict[str, frozenset[str]] = {
    "candidate": frozenset({"queued", "suppressed", "expired"}),
    "queued": frozenset({"suppressed", "expired", "archived"}),
    "suppressed": frozenset({"archived"}),
    "expired": frozenset({"archived"}),
    "archived": frozenset(),
}


class InvalidTransitionError(ValueError):
    """Raised when a requested state transition is not in the track's transition table."""

    def __init__(self, *, track: str, from_value: str, to_value: str) -> None:
        super().__init__(
            f"Invalid {track} transition: {from_value!r} -> {to_value!r} is not allowed"
        )
        self.track = track
        self.from_value = from_value
        self.to_value = to_value


def _validate_transition(
    *, track: str, transitions: dict[str, frozenset[str]], from_value: str, to_value: str
) -> None:
    allowed = transitions.get(from_value)
    if allowed is None or to_value not in allowed:
        raise InvalidTransitionError(track=track, from_value=from_value, to_value=to_value)


def validate_media_content_transition(from_value: str, to_value: str) -> None:
    _validate_enum("from_value", from_value, MEDIA_CONTENT_STATUSES)
    _validate_enum("to_value", to_value, MEDIA_CONTENT_STATUSES)
    _validate_transition(
        track="content_status",
        transitions=MEDIA_CONTENT_TRANSITIONS,
        from_value=from_value,
        to_value=to_value,
    )


def validate_media_decision_transition(from_value: str, to_value: str) -> None:
    _validate_enum("from_value", from_value, MEDIA_DECISION_STATES)
    _validate_enum("to_value", to_value, MEDIA_DECISION_STATES)
    _validate_transition(
        track="decision_state",
        transitions=MEDIA_DECISION_TRANSITIONS,
        from_value=from_value,
        to_value=to_value,
    )


def validate_event_status_transition(from_value: str, to_value: str) -> None:
    _validate_enum("from_value", from_value, EVENT_STATUSES)
    _validate_enum("to_value", to_value, EVENT_STATUSES)
    if to_value in ("changed", "cancelled") and from_value in EVENT_PRE_EVENT_STATUSES:
        return
    _validate_transition(
        track="event_status",
        transitions=EVENT_STATUS_TRANSITIONS,
        from_value=from_value,
        to_value=to_value,
    )


def validate_event_decision_transition(from_value: str, to_value: str) -> None:
    _validate_enum("from_value", from_value, EVENT_DECISION_STATES)
    _validate_enum("to_value", to_value, EVENT_DECISION_STATES)
    _validate_transition(
        track="decision_state",
        transitions=EVENT_DECISION_TRANSITIONS,
        from_value=from_value,
        to_value=to_value,
    )


def validate_queue_visibility_transition(from_value: str, to_value: str) -> None:
    _validate_enum("from_value", from_value, QUEUE_VISIBILITY_STATES)
    _validate_enum("to_value", to_value, QUEUE_VISIBILITY_STATES)
    _validate_transition(
        track="queue_visibility_state",
        transitions=QUEUE_VISIBILITY_TRANSITIONS,
        from_value=from_value,
        to_value=to_value,
    )


# ------------------------------------------------------------------------------- events

EVENT_TYPES = (
    "quarterly_earnings",
    "annual_results",
    "investor_day",
    "capital_markets_day",
    "strategy_webcast",
)
EVENT_TIME_PRECISIONS = ("date_only", "approximate", "exact")
EVENT_TIMING_LABELS = ("before_open", "after_close", "during_market")
EVENT_SCHEDULE_CONFIDENCES = ("confirmed_official", "confirmed_secondary", "estimated", "unknown")


def validate_event_type(value: str) -> str:
    return _validate_enum("event_type", value, EVENT_TYPES)


def validate_event_time_precision(value: str) -> str:
    return _validate_enum("time_precision", value, EVENT_TIME_PRECISIONS)


def validate_event_schedule_confidence(value: str) -> str:
    return _validate_enum("schedule_confidence", value, EVENT_SCHEDULE_CONFIDENCES)


def create_scheduled_event(
    connection: sqlite3.Connection,
    *,
    event_id: str,
    company_id: str,
    event_type: str,
    scheduled_date: str,
    fiscal_period: str | None = None,
    start_time_utc: str | None = None,
    end_time_utc: str | None = None,
    time_precision: str = "date_only",
    source_timezone: str = "UTC",
    timing_label: str | None = None,
    schedule_confidence: str = "unknown",
    schedule_source: str = "",
    official_event_page_url: str | None = None,
    live_webcast_url: str | None = None,
    replay_url: str | None = None,
    earnings_release_url: str | None = None,
    filing_urls: list[str] | None = None,
    slides_url: str | None = None,
    shareholder_letter_url: str | None = None,
    prepared_remarks_url: str | None = None,
) -> dict[str, Any]:
    event_id = _validate_required_text("event_id", event_id)
    company_id = _validate_required_text("company_id", company_id)
    event_type = validate_event_type(event_type)
    scheduled_date = _validate_iso_date("scheduled_date", scheduled_date)
    fiscal_period = _validate_optional_text("fiscal_period", fiscal_period)
    start_time_utc = _validate_optional_iso_datetime("start_time_utc", start_time_utc)
    end_time_utc = _validate_optional_iso_datetime("end_time_utc", end_time_utc)
    time_precision = validate_event_time_precision(time_precision)
    source_timezone = _validate_required_text("source_timezone", source_timezone)
    if timing_label is not None:
        timing_label = _validate_enum("timing_label", timing_label, EVENT_TIMING_LABELS)
    schedule_confidence = validate_event_schedule_confidence(schedule_confidence)
    schedule_source = _validate_text("schedule_source", schedule_source)
    filing_urls_json = _serialize_json(list(filing_urls or []))
    now = _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO ke_scheduled_events (
                event_id, company_id, fiscal_period, event_type, scheduled_date,
                start_time_utc, end_time_utc, time_precision, source_timezone,
                timing_label, schedule_confidence, schedule_source,
                official_event_page_url, live_webcast_url, replay_url,
                earnings_release_url, filing_urls_json, slides_url,
                shareholder_letter_url, prepared_remarks_url, event_status,
                decision_state, queue_visibility_state, created_at, updated_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                'discovered', 'undecided', 'candidate', ?, ?
            )
            """,
            (
                event_id, company_id, fiscal_period, event_type, scheduled_date,
                start_time_utc, end_time_utc, time_precision, source_timezone,
                timing_label, schedule_confidence, schedule_source,
                official_event_page_url, live_webcast_url, replay_url,
                earnings_release_url, filing_urls_json, slides_url,
                shareholder_letter_url, prepared_remarks_url, now, now,
            ),
        )

    event = get_scheduled_event(connection, event_id)
    if event is None:
        raise RuntimeError(f"Scheduled event was not persisted for event_id: {event_id}")
    return event


def get_scheduled_event(connection: sqlite3.Connection, event_id: str) -> dict[str, Any] | None:
    event_id = _validate_required_text("event_id", event_id)
    row = connection.execute(
        "SELECT * FROM ke_scheduled_events WHERE event_id = ?", (event_id,)
    ).fetchone()
    return _event_row_to_dict(row) if row is not None else None


def list_scheduled_events(
    connection: sqlite3.Connection,
    *,
    company_id: str | None = None,
    event_status: str | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if company_id is not None:
        clauses.append("company_id = ?")
        params.append(company_id)
    if event_status is not None:
        clauses.append("event_status = ?")
        params.append(_validate_enum("event_status", event_status, EVENT_STATUSES))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = connection.execute(
        f"SELECT * FROM ke_scheduled_events {where} ORDER BY scheduled_date, event_id",
        params,
    ).fetchall()
    return [_event_row_to_dict(row) for row in rows]


def count_scheduled_events(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "ke_scheduled_events")


def update_event_status(
    connection: sqlite3.Connection, *, event_id: str, event_status: str
) -> dict[str, Any]:
    event = get_scheduled_event(connection, event_id)
    if event is None:
        raise ValueError(f"Scheduled event does not exist: {event_id}")
    validate_event_status_transition(event["event_status"], event_status)

    now = _utc_now()
    with connection:
        connection.execute(
            "UPDATE ke_scheduled_events SET event_status = ?, updated_at = ? WHERE event_id = ?",
            (event_status, now, event_id),
        )

    updated = get_scheduled_event(connection, event_id)
    if updated is None:
        raise RuntimeError(f"Scheduled event was not found after update: {event_id}")
    return updated


def update_event_queue_visibility(
    connection: sqlite3.Connection, *, event_id: str, queue_visibility_state: str
) -> dict[str, Any]:
    event = get_scheduled_event(connection, event_id)
    if event is None:
        raise ValueError(f"Scheduled event does not exist: {event_id}")
    validate_queue_visibility_transition(
        event["queue_visibility_state"], queue_visibility_state
    )

    now = _utc_now()
    with connection:
        connection.execute(
            """
            UPDATE ke_scheduled_events
            SET queue_visibility_state = ?, updated_at = ?
            WHERE event_id = ?
            """,
            (queue_visibility_state, now, event_id),
        )

    updated = get_scheduled_event(connection, event_id)
    if updated is None:
        raise RuntimeError(f"Scheduled event was not found after update: {event_id}")
    return updated


def update_event_decision_state(
    connection: sqlite3.Connection, *, event_id: str, decision_state: str
) -> dict[str, Any]:
    event = get_scheduled_event(connection, event_id)
    if event is None:
        raise ValueError(f"Scheduled event does not exist: {event_id}")
    validate_event_decision_transition(event["decision_state"], decision_state)

    now = _utc_now()
    with connection:
        connection.execute(
            "UPDATE ke_scheduled_events SET decision_state = ?, updated_at = ? WHERE event_id = ?",
            (decision_state, now, event_id),
        )

    updated = get_scheduled_event(connection, event_id)
    if updated is None:
        raise RuntimeError(f"Scheduled event was not found after update: {event_id}")
    return updated


def _event_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["pinned"] = bool(item["pinned"])
    item["filing_urls"] = _deserialize_json_array(item.pop("filing_urls_json"))
    return item
