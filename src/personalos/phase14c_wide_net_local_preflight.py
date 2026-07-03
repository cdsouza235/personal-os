"""Names-only local preflight for the Phase 14-C wide-net rehearsal."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from personalos.phase14c_safety_utils import config_names_only
from personalos.phase14c_wide_net_rehearsal import (
    PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
    PHASE14C_WIDE_NET_REHEARSAL_MARKER,
    PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE,
)
from personalos.phase14c_wide_net_rehearsal_live import WIDE_NET_REQUIRED_CONFIG_NAMES


PHASE14C_WIDE_NET_LOCAL_PREFLIGHT_SCHEMA_VERSION = (
    "personal_os_phase14c_wide_net_local_preflight.v1"
)
PHASE14C_WIDE_NET_LOCAL_PREFLIGHT_STATUS = (
    "phase14c_wide_net_local_preflight_reported"
)


def build_phase14c_wide_net_local_preflight_report(
    *,
    available_config_names: Iterable[str] | Mapping[str, Any] = (),
    ssl_cert_file_is_file: bool = False,
) -> dict[str, Any]:
    """Build a no-live local preflight report using names and file metadata only."""

    available_names = config_names_only(available_config_names)
    missing_names = tuple(
        name for name in WIDE_NET_REQUIRED_CONFIG_NAMES if name not in available_names
    )
    config_names_present = not missing_names
    local_preflight_passed = config_names_present and ssl_cert_file_is_file

    return {
        "schema_version": PHASE14C_WIDE_NET_LOCAL_PREFLIGHT_SCHEMA_VERSION,
        "status": PHASE14C_WIDE_NET_LOCAL_PREFLIGHT_STATUS,
        "marker": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        "approval_reference_to_request": PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
        "ready_for_live_execution": False,
        "wide_net_live_run_authorized_by_this_report": False,
        "template_only_not_authorization": True,
        "human_live_approval_still_required": True,
        "claude_code_audit_required_before_live_run": True,
        "calendar_cli_connector_wiring_present": False,
        "credential_values_read": False,
        "credential_values_logged": False,
        "config_values_reported": False,
        "present_config_names_reported": False,
        "config_preflight": {
            "required_config_entry_names": tuple(WIDE_NET_REQUIRED_CONFIG_NAMES),
            "required_config_entry_count": len(WIDE_NET_REQUIRED_CONFIG_NAMES),
            "missing_config_entry_names": missing_names,
            "missing_config_entry_count": len(missing_names),
            "all_required_config_names_present": config_names_present,
            "available_config_entry_names_reported": False,
        },
        "ssl_cert_file": {
            "path": PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE,
            "is_file": bool(ssl_cert_file_is_file),
            "content_read": False,
            "path_is_secret": False,
        },
        "local_preflight": {
            "config_names_present": config_names_present,
            "ssl_cert_file_available": bool(ssl_cert_file_is_file),
            "local_preflight_passed": local_preflight_passed,
            "calendar_connector_wiring_still_required": True,
            "openrouter_budget_check_still_required": True,
            "fresh_human_live_approval_still_required": True,
            "claude_code_audit_still_required": True,
        },
        "safety_assertions": {
            "credential_values_read": False,
            "credential_values_logged": False,
            "environment_dumped": False,
            "present_config_names_reported": False,
            "ssl_cert_file_content_read": False,
            "calendar_app_connector_called": False,
            "calendar_client_injected_into_runner": False,
            "external_mutation": False,
            "model_provider_called": False,
            "todoist_task_created": False,
            "gmail_email_sent": False,
            "calendar_event_created": False,
            "protected_openclaw_runtime_called": False,
            "scheduler_or_background_activated": False,
            "production_db_active": False,
            "protected_paths_touched": False,
            "dynamic_cleaning_triggered": False,
            "broad_live_activation": False,
        },
    }
