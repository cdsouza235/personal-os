"""Sanitized Calendar connector transcript checks for Phase 14-C wide-net."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from personalos.phase14c_safety_utils import (
    PHASE14C_REDACTION_MAX_DEPTH,
    PHASE14C_REDACTION_MAX_NODES,
    redaction_failure_reasons,
    unique_reason_codes,
)
from personalos.phase14c_wide_net_calendar_app_bridge import (
    build_phase14c_wide_net_calendar_app_bridge_report,
)
from personalos.phase14c_wide_net_calendar_bridge import (
    PHASE14C_WIDE_NET_CALENDAR_PRECHECK_CONTRACT,
    require_explicit_calendar_matching_event_count,
)
from personalos.phase14c_wide_net_rehearsal import (
    PHASE14C_WIDE_NET_REHEARSAL_MARKER,
)


PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_SCHEMA_VERSION = (
    "personal_os_phase14c_wide_net_calendar_transcript.v1"
)
PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_TEMPLATE_STATUS = (
    "phase14c_wide_net_calendar_transcript_template_ready"
)
PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_VALID = (
    "phase14c_wide_net_calendar_transcript_valid"
)
PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_BLOCKED = (
    "phase14c_wide_net_calendar_transcript_blocked"
)
PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_INPUT_MAX_BYTES = 262_144

_ALLOWED_CREATE_RESULT_KEYS = frozenset({"id", "event_id", "status"})


def build_phase14c_wide_net_calendar_transcript_template(
    *,
    source_date: date | None = None,
) -> dict[str, Any]:
    """Build a no-live template for a sanitized Calendar connector transcript."""

    bridge = build_phase14c_wide_net_calendar_app_bridge_report(
        source_date=source_date
    )
    return {
        "schema_version": PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_SCHEMA_VERSION,
        "status": PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_TEMPLATE_STATUS,
        "marker": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        "ready_for_live_execution": False,
        "template_only_not_authorization": True,
        "calendar_app_connector_called": False,
        "credential_values_read": False,
        "external_mutation": False,
        "raw_event_details_allowed": False,
        "attendee_addresses_allowed": False,
        "expected_duplicate_precheck": {
            "connector_action": "search_events",
            "connector_args": bridge["duplicate_precheck"][
                "google_calendar_search_events_args"
            ],
            "normalized_response_contract": (
                PHASE14C_WIDE_NET_CALENDAR_PRECHECK_CONTRACT
            ),
            "required_matching_event_count_to_continue": 0,
        },
        "expected_calendar_create": {
            "connector_action": "create_event",
            "connector_args": bridge["calendar_create"][
                "google_calendar_create_event_args"
            ],
            "allowed_sanitized_result_keys": tuple(sorted(_ALLOWED_CREATE_RESULT_KEYS)),
        },
        "accepted_sanitized_input_shape": {
            "marker": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
            "duplicate_precheck": {
                "performed": True,
                "connector_action": "search_events",
                "connector_args": "<exact expected_duplicate_precheck.connector_args>",
                "normalized_response": {
                    "contract": PHASE14C_WIDE_NET_CALENDAR_PRECHECK_CONTRACT,
                    "matching_event_count": 0,
                    "event_details_logged": False,
                    "attendee_addresses_logged": False,
                },
            },
            "calendar_create": {
                "performed": False,
                "connector_action": "create_event",
                "connector_args": "<exact expected_calendar_create.connector_args>",
                "sanitized_result": {"id": "<optional id>", "status": "<optional>"},
            },
        },
        "input_limits": {
            "max_input_file_size_bytes": (
                PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_INPUT_MAX_BYTES
            ),
            "redaction_scan_max_depth": PHASE14C_REDACTION_MAX_DEPTH,
            "redaction_scan_max_nodes": PHASE14C_REDACTION_MAX_NODES,
        },
        "safety_assertions": _inert_safety_assertions(),
    }


def build_phase14c_wide_net_calendar_transcript_input_size_report(
    input_size_bytes: int,
) -> dict[str, Any]:
    """Build a blocked transcript report without reading oversized input."""

    return {
        "schema_version": PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_SCHEMA_VERSION,
        "status": PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_BLOCKED,
        "accepted": False,
        "stage": "not_loaded_input_file_too_large",
        "failure_reasons": ["input_file_too_large"],
        "raw_transcript_returned": False,
        "input_values_echoed": False,
        "credential_values_reported": False,
        "unmasked_emails_reported": False,
        "input_file_size_bytes": input_size_bytes,
        "max_input_file_size_bytes": (
            PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_INPUT_MAX_BYTES
        ),
        "precheck_summary": _empty_precheck_summary(),
        "calendar_create_summary": _empty_create_summary(),
        "safety_summary": _empty_safety_summary(),
    }


def validate_phase14c_wide_net_calendar_transcript(
    transcript_payload: Mapping[str, Any],
    *,
    source_date: date | None = None,
) -> dict[str, Any]:
    """Validate a sanitized Calendar connector transcript without echoing it."""

    expected = build_phase14c_wide_net_calendar_transcript_template(
        source_date=source_date
    )
    transcript = _extract_transcript(transcript_payload)
    reasons: list[str] = []
    if transcript is None:
        reasons.append("calendar_transcript_missing_or_not_mapping")
        transcript = {}

    marker_matched = transcript.get("marker") == PHASE14C_WIDE_NET_REHEARSAL_MARKER
    if not marker_matched:
        reasons.append("marker_mismatch_or_missing")

    precheck = _mapping(transcript.get("duplicate_precheck"))
    precheck_summary, precheck_count = _validate_precheck(
        precheck,
        expected_args=_mapping(
            expected["expected_duplicate_precheck"]["connector_args"]
        ),
        reasons=reasons,
    )

    create = _mapping(transcript.get("calendar_create"))
    create_summary = _validate_create(
        create,
        expected_args=_mapping(expected["expected_calendar_create"]["connector_args"]),
        precheck_count=precheck_count,
        reasons=reasons,
    )

    leak_reasons = redaction_failure_reasons(transcript)
    reasons.extend(leak_reasons)
    unique_reasons = unique_reason_codes(reasons)
    accepted = not unique_reasons
    create_performed = create_summary["performed"] is True
    stage = (
        "calendar_create_confirmed"
        if accepted and create_performed
        else "duplicate_precheck_clear"
        if accepted
        else "blocked"
    )
    return {
        "schema_version": PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_SCHEMA_VERSION,
        "status": (
            PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_VALID
            if accepted
            else PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_BLOCKED
        ),
        "accepted": accepted,
        "stage": stage,
        "marker_matched": marker_matched,
        "failure_reasons": unique_reasons,
        "raw_transcript_returned": False,
        "input_values_echoed": False,
        "credential_values_reported": False,
        "unmasked_emails_reported": False,
        "create_allowed_after_precheck": (
            accepted and precheck_count == 0 and not create_performed
        ),
        "precheck_summary": precheck_summary,
        "calendar_create_summary": create_summary,
        "safety_summary": _empty_safety_summary(),
    }


def _validate_precheck(
    precheck: Mapping[str, Any],
    *,
    expected_args: Mapping[str, Any],
    reasons: list[str],
) -> tuple[dict[str, Any], int | None]:
    performed = precheck.get("performed") is True
    connector_args_matched = precheck.get("connector_args") == dict(expected_args)
    normalized = _mapping(precheck.get("normalized_response"))
    matching_event_count: int | None = None

    if not performed:
        reasons.append("calendar_duplicate_precheck_not_performed")
    if precheck.get("connector_action") != "search_events":
        reasons.append("calendar_duplicate_precheck_action_mismatch")
    if not connector_args_matched:
        reasons.append("calendar_duplicate_precheck_args_mismatch")

    try:
        matching_event_count = require_explicit_calendar_matching_event_count(
            normalized
        )
    except ValueError:
        reasons.append("calendar_duplicate_precheck_contract_invalid")

    if matching_event_count is not None and matching_event_count != 0:
        reasons.append("calendar_duplicate_precheck_count_not_zero")
    if normalized.get("event_details_logged") is not False:
        reasons.append("calendar_precheck_event_details_logged")
    if normalized.get("attendee_addresses_logged") is not False:
        reasons.append("calendar_precheck_attendee_addresses_logged")

    return (
        {
            "performed": performed,
            "connector_action_matched": (
                precheck.get("connector_action") == "search_events"
            ),
            "connector_args_matched": connector_args_matched,
            "matching_event_count": matching_event_count,
            "duplicate_marker_found": (
                matching_event_count is not None and matching_event_count > 0
            ),
            "event_details_logged": normalized.get("event_details_logged") is True,
            "attendee_addresses_logged": normalized.get("attendee_addresses_logged")
            is True,
        },
        matching_event_count,
    )


def _validate_create(
    create: Mapping[str, Any],
    *,
    expected_args: Mapping[str, Any],
    precheck_count: int | None,
    reasons: list[str],
) -> dict[str, Any]:
    performed = create.get("performed") is True
    connector_args_matched = create.get("connector_args") == dict(expected_args)
    result = _mapping(create.get("sanitized_result"))
    result_key_count = len(result)
    allowed_result_keys = tuple(
        sorted(
            str(key)
            for key in result
            if isinstance(key, str) and key in _ALLOWED_CREATE_RESULT_KEYS
        )
    )
    result_keys_allowed = result_key_count == len(allowed_result_keys)

    if not performed and create:
        if create.get("performed") not in (False, None):
            reasons.append("calendar_create_performed_field_invalid")
    if performed:
        if precheck_count != 0:
            reasons.append("calendar_create_without_clear_precheck")
        if create.get("connector_action") != "create_event":
            reasons.append("calendar_create_action_mismatch")
        if not connector_args_matched:
            reasons.append("calendar_create_args_mismatch")
        if not isinstance(create.get("sanitized_result"), Mapping):
            reasons.append("calendar_create_sanitized_result_missing")
        if not result_keys_allowed:
            reasons.append("calendar_create_result_contains_unapproved_fields")
    elif create.get("connector_args") not in (None, {}, dict(expected_args)):
        reasons.append("calendar_create_args_mismatch")

    return {
        "performed": performed,
        "connector_action_matched": create.get("connector_action") == "create_event",
        "connector_args_matched": connector_args_matched,
        "safe_result_present": bool(result),
        "result_key_count": result_key_count,
        "allowed_result_keys": allowed_result_keys,
        "result_keys_allowed": result_keys_allowed,
    }


def _extract_transcript(payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
    direct = payload.get("wide_net_calendar_connector_transcript")
    if isinstance(direct, Mapping):
        return direct
    if payload.get("marker") == PHASE14C_WIDE_NET_REHEARSAL_MARKER:
        return payload
    return None


def _mapping(value: object) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _empty_precheck_summary() -> dict[str, Any]:
    return {
        "performed": False,
        "connector_action_matched": False,
        "connector_args_matched": False,
        "matching_event_count": None,
        "duplicate_marker_found": None,
        "event_details_logged": False,
        "attendee_addresses_logged": False,
    }


def _empty_create_summary() -> dict[str, Any]:
    return {
        "performed": False,
        "connector_action_matched": False,
        "connector_args_matched": False,
        "safe_result_present": False,
        "result_key_count": 0,
        "allowed_result_keys": (),
        "result_keys_allowed": False,
    }


def _empty_safety_summary() -> dict[str, bool]:
    return {
        "credential_values_reported": False,
        "raw_event_details_returned": False,
        "attendee_addresses_reported": False,
        "unmasked_emails_reported": False,
        "external_mutation_performed_by_validator": False,
    }


def _inert_safety_assertions() -> dict[str, bool]:
    return {
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
    }
