"""Report-only Google Calendar app bridge payloads for Phase 14-C wide-net."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from personalos.phase14c_wide_net_calendar_bridge import (
    PHASE14C_WIDE_NET_CALENDAR_PRECHECK_CONTRACT,
    validate_wide_net_calendar_create_payload,
    validate_wide_net_calendar_precheck_payload,
)
from personalos.phase14c_wide_net_rehearsal import (
    PHASE14C_WIDE_NET_REHEARSAL_MARKER,
)
from personalos.phase14c_wide_net_rehearsal_live import (
    build_wide_net_calendar_payloads,
)


PHASE14C_WIDE_NET_CALENDAR_APP_BRIDGE_SCHEMA_VERSION = (
    "personal_os_phase14c_wide_net_calendar_app_bridge.v1"
)
PHASE14C_WIDE_NET_CALENDAR_APP_BRIDGE_STATUS = (
    "phase14c_wide_net_calendar_app_bridge_payloads_ready"
)


def build_google_calendar_search_events_args(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Build bounded Google Calendar search args from a validated precheck."""

    precheck = validate_wide_net_calendar_precheck_payload(payload)
    return {
        "calendar_id": precheck["calendar_id"],
        "query": precheck["title"],
        "time_min": precheck["time_min"],
        "time_max": precheck["time_max"],
        "timezone_str": precheck["timezone_str"],
        "max_results": 10,
    }


def build_google_calendar_create_event_args(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Build bounded Google Calendar create args from a validated payload."""

    event = validate_wide_net_calendar_create_payload(payload)
    return {
        "calendar_id": event["calendar_id"],
        "title": event["title"],
        "start_time": event["start_time"],
        "end_time": event["end_time"],
        "timezone_str": event["timezone_str"],
        "description": event["description"],
        "attendees": [],
        "add_google_meet": False,
        "recurrence": None,
    }


def build_phase14c_wide_net_calendar_app_bridge_report(
    *,
    source_date: date | None = None,
) -> dict[str, Any]:
    """Return a no-live app-connector bridge report for the wide-net Calendar rail."""

    payloads = build_wide_net_calendar_payloads(source_date=source_date)
    precheck_payload = payloads["calendar_precheck_payload"]
    create_payload = payloads["calendar_create_payload"]
    return {
        "schema_version": PHASE14C_WIDE_NET_CALENDAR_APP_BRIDGE_SCHEMA_VERSION,
        "status": PHASE14C_WIDE_NET_CALENDAR_APP_BRIDGE_STATUS,
        "marker": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        "calendar_app_connector_called": False,
        "calendar_event_created": False,
        "external_mutation": False,
        "credential_values_read": False,
        "credential_values_logged": False,
        "config_values_reported": False,
        "calendar_client_injected_into_wide_net_runner": False,
        "ready_for_live_execution": False,
        "template_only_not_authorization": True,
        "connector_surface": {
            "connector_type": "Google Calendar app connector",
            "duplicate_precheck_action": "search_events",
            "create_action": "create_event",
            "repo_cli_constructs_connector": False,
            "repo_cli_calls_connector": False,
        },
        "duplicate_precheck": {
            "required": True,
            "runs_before_model_todoist_gmail_or_calendar_create": True,
            "exact_title_match_required_after_connector_read": True,
            "raw_event_details_logged": False,
            "attendee_addresses_logged": False,
            "normalized_response_contract": (
                PHASE14C_WIDE_NET_CALENDAR_PRECHECK_CONTRACT
            ),
            "expected_normalized_fields": (
                "contract",
                "matching_event_count",
                "event_details_logged",
                "attendee_addresses_logged",
            ),
            "google_calendar_search_events_args": build_google_calendar_search_events_args(
                precheck_payload
            ),
        },
        "calendar_create": {
            "requires_prior_duplicate_precheck_count": 0,
            "attendee_count": 0,
            "conference_link": False,
            "recurrence": None,
            "attachments_supported_by_connector_args": False,
            "attachments_required": False,
            "google_calendar_create_event_args": build_google_calendar_create_event_args(
                create_payload
            ),
        },
        "call_limits": {
            "calendar_duplicate_precheck_connector_calls_by_this_command": 0,
            "calendar_create_connector_calls_by_this_command": 0,
            "max_future_calendar_duplicate_precheck_reads": 1,
            "max_future_calendar_event_creates": 1,
        },
        "safety_assertions": {
            "calendar_app_connector_called": False,
            "calendar_event_created": False,
            "credential_values_read": False,
            "credential_values_logged": False,
            "environment_dumped": False,
            "external_mutation": False,
            "production_db_active": False,
            "protected_paths_touched": False,
            "scheduler_or_background_activated": False,
            "broad_live_activation": False,
        },
    }
