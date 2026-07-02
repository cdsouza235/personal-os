"""Repo-local Calendar bridge contract for the Phase 14-C wide-net runner."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from personalos.phase14c_wide_net_rehearsal import (
    PHASE14C_WIDE_NET_REHEARSAL_MARKER,
)


PHASE14C_WIDE_NET_CALENDAR_BRIDGE_SCHEMA_VERSION = (
    "personal_os_phase14c_wide_net_calendar_bridge.v1"
)
PHASE14C_WIDE_NET_CALENDAR_PRECHECK_CONTRACT = (
    "phase14c_wide_net_calendar_precheck.v1"
)


class CalendarBridgeContractError(ValueError):
    """Raised when a Calendar bridge response is not safe to trust."""


class WideNetGoogleCalendarConnectorBridge:
    """Narrow adapter for an audited Google Calendar connector wrapper.

    The callables are intentionally injected. This module does not import or
    initialize a live connector, read credentials, or perform network I/O by
    itself.
    """

    def __init__(
        self,
        *,
        search_events: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        create_event: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    ) -> None:
        self._search_events = search_events
        self._create_event = create_event

    def find_events_by_title(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        precheck_payload = validate_wide_net_calendar_precheck_payload(payload)
        raw = self._search_events(precheck_payload)
        return {
            "schema_version": PHASE14C_WIDE_NET_CALENDAR_BRIDGE_SCHEMA_VERSION,
            "contract": PHASE14C_WIDE_NET_CALENDAR_PRECHECK_CONTRACT,
            "matching_event_count": count_matching_calendar_events(
                raw,
                title=str(precheck_payload["title"]),
            ),
            "event_details_logged": False,
            "attendee_addresses_logged": False,
        }

    def create_event(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        event_payload = validate_wide_net_calendar_create_payload(payload)
        return dict(self._create_event(event_payload))


def require_explicit_calendar_matching_event_count(result: Mapping[str, Any]) -> int:
    """Return a bridge-normalized matching count or fail closed."""

    contract = result.get("contract")
    if contract != PHASE14C_WIDE_NET_CALENDAR_PRECHECK_CONTRACT:
        raise CalendarBridgeContractError(
            "Calendar precheck response contract missing or unrecognized."
        )
    count = result.get("matching_event_count")
    if not isinstance(count, int) or count < 0:
        raise CalendarBridgeContractError(
            "Calendar precheck response must include a non-negative count."
        )
    return count


def count_matching_calendar_events(result: Mapping[str, Any], *, title: str) -> int:
    """Count exact-title matches from a connector response or fail closed."""

    explicit_count = result.get("matching_event_count")
    if isinstance(explicit_count, int) and explicit_count >= 0:
        return explicit_count

    for key in ("events", "items"):
        if key not in result:
            continue
        value = result[key]
        if not isinstance(value, list | tuple):
            raise CalendarBridgeContractError(
                "Calendar precheck events payload must be a list."
            )
        return _count_event_title_matches(value, title=title)

    raise CalendarBridgeContractError(
        "Calendar precheck response did not include a recognized result shape."
    )


def validate_wide_net_calendar_precheck_payload(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    title = _required_string(payload, "title")
    if title != PHASE14C_WIDE_NET_REHEARSAL_MARKER:
        raise CalendarBridgeContractError("Calendar precheck title is not approved.")
    calendar_id = _required_string(payload, "calendar_id")
    if calendar_id != "primary":
        raise CalendarBridgeContractError("Calendar precheck must target primary.")
    if payload.get("exact_title_match_required") is not True:
        raise CalendarBridgeContractError("Calendar precheck must require exact title.")
    if payload.get("attendee_data_required") is not False:
        raise CalendarBridgeContractError("Calendar precheck must not request attendees.")
    return {
        "calendar_id": calendar_id,
        "title": title,
        "time_min": _required_string(payload, "time_min"),
        "time_max": _required_string(payload, "time_max"),
        "timezone_str": _required_string(payload, "timezone_str"),
        "exact_title_match_required": True,
        "attendee_data_required": False,
    }


def validate_wide_net_calendar_create_payload(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    title = _required_string(payload, "title")
    if title != PHASE14C_WIDE_NET_REHEARSAL_MARKER:
        raise CalendarBridgeContractError("Calendar event title is not approved.")
    calendar_id = _required_string(payload, "calendar_id")
    if calendar_id != "primary":
        raise CalendarBridgeContractError("Calendar event must target primary.")
    if payload.get("attendees") != []:
        raise CalendarBridgeContractError("Calendar event must not include attendees.")
    if payload.get("add_google_meet") is not False:
        raise CalendarBridgeContractError("Calendar event must not add a conference.")
    if payload.get("recurrence") is not None:
        raise CalendarBridgeContractError("Calendar event must not recur.")
    if payload.get("attachments") != []:
        raise CalendarBridgeContractError("Calendar event must not include attachments.")
    return {
        "calendar_id": calendar_id,
        "title": title,
        "start_time": _required_string(payload, "start_time"),
        "end_time": _required_string(payload, "end_time"),
        "timezone_str": _required_string(payload, "timezone_str"),
        "attendees": [],
        "add_google_meet": False,
        "recurrence": None,
        "attachments": [],
        "description": _optional_string(payload.get("description")),
    }


def _count_event_title_matches(events: list[Any] | tuple[Any, ...], *, title: str) -> int:
    matched = 0
    for item in events:
        if not isinstance(item, Mapping):
            raise CalendarBridgeContractError(
                "Calendar precheck event entries must be mappings."
            )
        candidate = item.get("title", item.get("summary"))
        if candidate == title:
            matched += 1
    return matched


def _required_string(payload: Mapping[str, Any], key: str) -> str:
    value = _optional_string(payload.get(key))
    if value is None:
        raise CalendarBridgeContractError(f"Calendar payload missing {key}.")
    return value


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
