"""Names-only Phase 14-C connectivity setup reporting."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from personalos.openclaw_model_strategy import (
    OPENCLAW_MODEL_PROVIDER_CONFIG_ENTRY_NAMES,
)
from personalos.phase14c_gmail_live_smoke import (
    PHASE14C_GMAIL_SMTP_CONFIG_ENTRY_NAMES,
)
from personalos.phase14c_supervised_smoke import REQUIRED_CONFIG_ENTRY_NAMES


PHASE14C_CONNECTIVITY_SETUP_SCHEMA_VERSION = (
    "personal_os_phase14c_connectivity_setup.v1"
)

PHASE14C_CONNECTIVITY_SETUP_ENV_FILE = ".env.local"

PHASE14C_CONNECTIVITY_SETUP_ENTRY_NAMES: dict[str, tuple[str, ...]] = {
    "gmail": PHASE14C_GMAIL_SMTP_CONFIG_ENTRY_NAMES,
    "todoist": (
        "PERSONALOS_PHASE14C_TODOIST_TOKEN",
    ),
    "openrouter": OPENCLAW_MODEL_PROVIDER_CONFIG_ENTRY_NAMES,
    "phase14c_smoke": REQUIRED_CONFIG_ENTRY_NAMES,
}


def build_phase14c_connectivity_setup_report(
    available_config_names: Iterable[str] | Mapping[str, Any],
) -> dict[str, Any]:
    """Build a setup report using config entry names only."""

    available_names = set(_config_names_only(available_config_names))
    rails = {
        rail: _rail_setup_report(rail, required_names, available_names)
        for rail, required_names in PHASE14C_CONNECTIVITY_SETUP_ENTRY_NAMES.items()
    }
    missing_by_rail = {
        rail: report["missing_config_entry_names"]
        for rail, report in rails.items()
        if report["missing_config_entry_names"]
    }
    return {
        "schema_version": PHASE14C_CONNECTIVITY_SETUP_SCHEMA_VERSION,
        "status": (
            "connectivity_config_names_present"
            if not missing_by_rail
            else "connectivity_config_names_missing"
        ),
        "env_file": {
            "path": PHASE14C_CONNECTIVITY_SETUP_ENV_FILE,
            "gitignored": True,
            "created_by_this_command": False,
            "credential_values_reported": False,
        },
        "rails": rails,
        "missing_config_entry_names_by_rail": missing_by_rail,
        "setup_script": {
            "path": "scripts/phase14c_connectivity_setup.sh",
            "prompts_for_secret_values_without_echo": True,
            "plain_controlled_recipient_prompt_echoes_for_typo_check": True,
            "writes_gitignored_env_file": True,
            "writes_via_temp_file_before_final_move": True,
            "refuses_to_overwrite_existing_env_file": True,
            "prints_values": False,
            "commits_values": False,
        },
        "verification_commands": [
            (
                "set -a; source .env.local; set +a; "
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "connectivity-setup --json"
            ),
            (
                "set -a; source .env.local; set +a; "
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "supervised-smoke-credential-preflight --json"
            ),
            (
                "set -a; source .env.local; set +a; "
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "openclaw-model-readiness --json"
            ),
            (
                "set -a; source .env.local; set +a; "
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "gmail-smtp-smoke --json"
            ),
            (
                "set -a; source .env.local; set +a; "
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "todoist-inbox-smoke --json"
            ),
            (
                "set -a; source .env.local; set +a; "
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "openrouter-model-smoke --json"
            ),
        ],
        "safety_assertions": {
            "credential_values_read": False,
            "credential_values_logged": False,
            "credential_values_copied": False,
            "credential_values_committed": False,
            "present_config_entry_names_reported": False,
            "environment_dumped": False,
            "live_clients_initialized": False,
            "external_mutation": False,
            "gmail_sent_or_drafted": False,
            "todoist_task_created": False,
            "model_provider_called": False,
            "openclaw_runtime_called": False,
            "scheduler_activated": False,
            "production_db_active": False,
            "protected_paths_touched": False,
        },
    }


def _rail_setup_report(
    rail: str,
    required_names: tuple[str, ...],
    available_names: set[str],
) -> dict[str, Any]:
    missing = [name for name in required_names if name not in available_names]
    return {
        "rail": rail,
        "status": "config_names_present" if not missing else "missing_config_names",
        "required_config_entry_count": len(required_names),
        "missing_config_entry_names": missing,
        "present_config_entry_names_reported": False,
        "credential_values_read": False,
        "credential_values_logged": False,
    }


def _config_names_only(
    available_config_names: Iterable[str] | Mapping[str, Any],
) -> tuple[str, ...]:
    if isinstance(available_config_names, Mapping):
        return tuple(str(name) for name in available_config_names.keys())
    return tuple(str(name) for name in available_config_names)
