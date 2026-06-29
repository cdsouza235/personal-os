"""Deterministic OpenClaw model lane strategy for Phase 14-C smoke work."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Protocol


OPENCLAW_MODEL_STRATEGY_SCHEMA_VERSION = "personal_os_openclaw_model_strategy.v1"
OPENCLAW_MODEL_READINESS_DEFAULT_GENERATED_AT_UTC = "2026-06-29T18:00:00+00:00"
OPENCLAW_MODEL_SMOKE_PROMPT = (
    "Personal OS Phase 14-C model smoke probe. Reply with PHASE14C_MODEL_SMOKE_OK."
)
OPENCLAW_MODEL_SMOKE_EXPECTED_TEXT = "PHASE14C_MODEL_SMOKE_OK"
OPENCLAW_MODEL_SMOKE_PASSED = "openclaw_model_smoke_passed"
OPENCLAW_MODEL_SMOKE_MISSING_PROVIDER_CONFIG = (
    "openclaw_model_smoke_not_run_missing_provider_config"
)
OPENCLAW_MODEL_SMOKE_MISSING_CLIENT = "openclaw_model_smoke_not_run_missing_client"

SMOKE_LANE = "smoke"
REASONING_LANE = "reasoning"
OPENCLAW_MODEL_LANES: tuple[str, ...] = (SMOKE_LANE, REASONING_LANE)

OPENCLAW_MODEL_ALIASES: dict[str, dict[str, str]] = {
    "nemotron_super": {
        "alias": "nemotron_super",
        "provider_model_hint": "nvidia/nemotron-3-super-120b-a12b",
    },
    "glm_5_2": {
        "alias": "glm_5_2",
        "provider_model_hint": "z-ai/glm-5.2",
    },
}

OPENCLAW_MODEL_LANE_POLICY: dict[str, dict[str, Any]] = {
    SMOKE_LANE: {
        "lane": SMOKE_LANE,
        "task_types": (
            "openclaw_no_op_smoke_probe",
            "cheap_sanity_check",
            "basic_tool_call_format_check",
            "local_test_sandbox_operator_check",
        ),
        "primary_alias": "nemotron_super",
        "fallback_alias": "glm_5_2",
        "max_primary_calls": 1,
        "max_fallback_calls": 1,
        "max_output_tokens": 256,
    },
    REASONING_LANE: {
        "lane": REASONING_LANE,
        "task_types": (
            "harder_planning",
            "ambiguous_multi_step_operator_reasoning",
            "future_high_complexity_openclaw_planning",
        ),
        "primary_alias": "glm_5_2",
        "fallback_alias": "nemotron_super",
        "max_primary_calls": 1,
        "max_fallback_calls": 1,
        "max_output_tokens": 768,
    },
}

FALLBACK_CONDITIONS: tuple[str, ...] = (
    "provider_client_failure",
    "timeout",
    "malformed_response",
    "explicit_validation_failure",
)

SAFE_METADATA_FIELDS: tuple[str, ...] = (
    "provider_alias",
    "model_alias",
    "lane",
    "success",
    "failure_category",
    "latency_ms",
    "input_tokens",
    "output_tokens",
)

OPENCLAW_MODEL_PROVIDER_CONFIG_ENTRY_NAMES: tuple[str, ...] = (
    "PERSONALOS_OPENCLAW_MODEL_PROVIDER",
    "PERSONALOS_OPENCLAW_MODEL_API_KEY",
    "PERSONALOS_OPENCLAW_NEMOTRON_SUPER_MODEL",
    "PERSONALOS_OPENCLAW_GLM_5_2_MODEL",
)


class OpenClawModelSmokeClient(Protocol):
    def run_probe(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        """Run one model smoke probe with the supplied safe request."""


def build_openclaw_model_strategy_config(
    *,
    model_aliases: Mapping[str, Mapping[str, str]] | None = None,
) -> dict[str, Any]:
    """Build the explicit OpenClaw model strategy using configurable aliases."""

    aliases = _normalize_model_aliases(model_aliases or OPENCLAW_MODEL_ALIASES)
    return {
        "schema_version": OPENCLAW_MODEL_STRATEGY_SCHEMA_VERSION,
        "strategy": "deterministic_explicit_lane_routing",
        "model_aliases": aliases,
        "lanes": {
            lane: build_openclaw_model_call_plan(lane, model_aliases=aliases)
            for lane in OPENCLAW_MODEL_LANES
        },
        "constraints": {
            "routing_explicit_by_lane": True,
            "self_modifying_routing_logic": False,
            "hidden_model_choice": False,
            "provider_auto_escalation": False,
            "max_primary_calls_per_probe": 1,
            "max_fallback_calls_per_probe": 1,
            "fallback_conditions": list(FALLBACK_CONDITIONS),
            "log_full_prompts": False,
            "log_credential_values": False,
            "safe_metadata_fields": list(SAFE_METADATA_FIELDS),
        },
    }


def build_openclaw_model_call_plan(
    lane: str,
    *,
    task_type: str | None = None,
    model_aliases: Mapping[str, Mapping[str, str]] | None = None,
) -> dict[str, Any]:
    """Return the deterministic primary/fallback plan for one lane."""

    if lane not in OPENCLAW_MODEL_LANE_POLICY:
        raise ValueError("OpenClaw model lane must be smoke or reasoning.")
    aliases = _normalize_model_aliases(model_aliases or OPENCLAW_MODEL_ALIASES)
    policy = OPENCLAW_MODEL_LANE_POLICY[lane]
    primary_alias = str(policy["primary_alias"])
    fallback_alias = str(policy["fallback_alias"])
    primary = aliases[primary_alias]
    fallback = aliases[fallback_alias]
    task_types = tuple(str(task) for task in policy["task_types"])
    if task_type is not None and task_type not in task_types:
        raise ValueError("OpenClaw model task_type is not allowed for this lane.")
    return {
        "lane": lane,
        "task_type": task_type,
        "allowed_task_types": list(task_types),
        "primary": primary,
        "fallback": fallback,
        "max_primary_calls": policy["max_primary_calls"],
        "max_fallback_calls": policy["max_fallback_calls"],
        "max_total_calls": 2,
        "max_output_tokens": policy["max_output_tokens"],
        "fallback_conditions": list(FALLBACK_CONDITIONS),
        "routing_mode": "explicit_lane_policy",
        "provider_auto_escalation": False,
        "hidden_model_choice": False,
        "log_full_prompt": False,
        "log_credential_values": False,
        "safe_metadata_fields": list(SAFE_METADATA_FIELDS),
    }


def run_openclaw_model_smoke_probe(
    *,
    available_config_names: Iterable[str] | Mapping[str, Any] = (),
    client: OpenClawModelSmokeClient | None = None,
    client_type: str | None = None,
    generated_at_utc: str = OPENCLAW_MODEL_READINESS_DEFAULT_GENERATED_AT_UTC,
    credential_values_read: bool = False,
    model_provider_called: bool = False,
) -> dict[str, Any]:
    """Run at most one primary and one fallback OpenClaw model smoke probe.

    The function does not construct a provider SDK client, read credential
    values, log prompts, or call tools. A future supervised operator path must
    inject a configured model client explicitly.
    """

    plan = build_openclaw_model_call_plan(
        SMOKE_LANE,
        task_type="openclaw_no_op_smoke_probe",
    )
    preflight = _model_provider_config_preflight(available_config_names)
    if preflight["missing_config_entry_names"]:
        return _model_smoke_not_run_report(
            status=OPENCLAW_MODEL_SMOKE_MISSING_PROVIDER_CONFIG,
            generated_at_utc=generated_at_utc,
            plan=plan,
            preflight=preflight,
            client_type=client_type,
            reason="model_provider_config_missing",
        )
    if client is None:
        return _model_smoke_not_run_report(
            status=OPENCLAW_MODEL_SMOKE_MISSING_CLIENT,
            generated_at_utc=generated_at_utc,
            plan=plan,
            preflight=preflight,
            client_type=client_type,
            reason="model_client_missing",
        )

    primary_result = _run_one_model_probe(
        client=client,
        plan=plan,
        selected_model=plan["primary"],
        attempt="primary",
    )
    probe_results = [primary_result]
    if primary_result["validation_passed"] is not True:
        fallback_result = _run_one_model_probe(
            client=client,
            plan=plan,
            selected_model=plan["fallback"],
            attempt="fallback",
        )
        probe_results.append(fallback_result)

    passed = any(result["validation_passed"] is True for result in probe_results)
    return {
        "schema_version": OPENCLAW_MODEL_STRATEGY_SCHEMA_VERSION,
        "generated_at_utc": generated_at_utc,
        "status": (
            OPENCLAW_MODEL_SMOKE_PASSED
            if passed
            else "openclaw_model_smoke_validation_failed"
        ),
        "lane": SMOKE_LANE,
        "task_type": "openclaw_no_op_smoke_probe",
        "model_smoke_probe_executed": True,
        "provider_config": preflight,
        "client": {
            "available": True,
            "type": _optional_string(client_type) or "injected_model_smoke_client",
        },
        "call_limits": {
            "max_primary_calls": plan["max_primary_calls"],
            "max_fallback_calls": plan["max_fallback_calls"],
            "primary_calls": 1,
            "fallback_calls": len(probe_results) - 1,
        },
        "routing": _safe_model_plan_summary(plan),
        "probe_results": probe_results,
        "selected_result": next(
            (result for result in probe_results if result["validation_passed"] is True),
            probe_results[-1],
        ),
        "safety_assertions": _model_smoke_safety_assertions(
            credential_values_read=credential_values_read,
            model_provider_called=model_provider_called,
        ),
    }


def build_openclaw_model_provider_readiness_report(
    *,
    available_config_names: Iterable[str] | Mapping[str, Any] = (),
    client_available: bool = False,
    client_type: str | None = None,
    generated_at_utc: str = OPENCLAW_MODEL_READINESS_DEFAULT_GENERATED_AT_UTC,
) -> dict[str, Any]:
    """Report model-provider readiness without running a model/API call."""

    preflight = _model_provider_config_preflight(available_config_names)
    plan = build_openclaw_model_call_plan(
        SMOKE_LANE,
        task_type="openclaw_no_op_smoke_probe",
    )
    if preflight["missing_config_entry_names"]:
        status = OPENCLAW_MODEL_SMOKE_MISSING_PROVIDER_CONFIG
        reason = "model_provider_config_missing"
    elif not client_available:
        status = OPENCLAW_MODEL_SMOKE_MISSING_CLIENT
        reason = "model_client_missing"
    else:
        status = "openclaw_model_smoke_ready_for_injected_client_probe"
        reason = None

    return _model_smoke_not_run_report(
        status=status,
        generated_at_utc=generated_at_utc,
        plan=plan,
        preflight=preflight,
        client_type=client_type,
        reason=reason,
        client_available=client_available,
    )


def sanitize_openclaw_model_run_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Keep only safe model-run metadata fields for smoke reports."""

    sanitized: dict[str, Any] = {}
    for field in SAFE_METADATA_FIELDS:
        if field in metadata:
            sanitized[field] = metadata[field]
    if "success" not in sanitized:
        sanitized["success"] = False
    return sanitized


def _normalize_model_aliases(
    aliases: Mapping[str, Mapping[str, str]],
) -> dict[str, dict[str, str]]:
    normalized: dict[str, dict[str, str]] = {}
    for required in ("nemotron_super", "glm_5_2"):
        entry = aliases.get(required)
        if not isinstance(entry, Mapping):
            raise ValueError(f"Missing OpenClaw model alias: {required}")
        alias = str(entry.get("alias", "")).strip()
        provider_model_hint = str(entry.get("provider_model_hint", "")).strip()
        if alias != required:
            raise ValueError(f"OpenClaw model alias key mismatch: {required}")
        if not provider_model_hint:
            raise ValueError(f"OpenClaw model alias missing provider hint: {required}")
        normalized[required] = {
            "alias": alias,
            "provider_model_hint": provider_model_hint,
        }
    return normalized


def _model_provider_config_preflight(
    available_config_names: Iterable[str] | Mapping[str, Any],
) -> dict[str, Any]:
    available_names = set(_config_names_only(available_config_names))
    missing = tuple(
        name
        for name in OPENCLAW_MODEL_PROVIDER_CONFIG_ENTRY_NAMES
        if name not in available_names
    )
    return {
        "required_config_entry_count": len(OPENCLAW_MODEL_PROVIDER_CONFIG_ENTRY_NAMES),
        "missing_config_entry_names": list(missing),
        "reports_missing_names_only": True,
        "available_config_entry_names_reported": False,
        "credential_values_read": False,
        "credential_values_logged": False,
        "credential_values_copied": False,
        "credential_values_committed": False,
    }


def _model_smoke_not_run_report(
    *,
    status: str,
    generated_at_utc: str,
    plan: Mapping[str, Any],
    preflight: Mapping[str, Any],
    client_type: str | None,
    reason: str | None,
    client_available: bool = False,
) -> dict[str, Any]:
    return {
        "schema_version": OPENCLAW_MODEL_STRATEGY_SCHEMA_VERSION,
        "generated_at_utc": generated_at_utc,
        "status": status,
        "reason": reason,
        "lane": SMOKE_LANE,
        "task_type": "openclaw_no_op_smoke_probe",
        "model_smoke_probe_executed": False,
        "provider_config": dict(preflight),
        "client": {
            "available": client_available,
            "type": _optional_string(client_type),
        },
        "call_limits": {
            "max_primary_calls": plan["max_primary_calls"],
            "max_fallback_calls": plan["max_fallback_calls"],
            "primary_calls": 0,
            "fallback_calls": 0,
        },
        "routing": _safe_model_plan_summary(plan),
        "safety_assertions": _model_smoke_safety_assertions(),
    }


def _run_one_model_probe(
    *,
    client: OpenClawModelSmokeClient,
    plan: Mapping[str, Any],
    selected_model: Mapping[str, Any],
    attempt: str,
) -> dict[str, Any]:
    request = {
        "lane": SMOKE_LANE,
        "task_type": "openclaw_no_op_smoke_probe",
        "attempt": attempt,
        "model_alias": selected_model["alias"],
        "provider_model_hint": selected_model["provider_model_hint"],
        "max_output_tokens": plan["max_output_tokens"],
        "prompt": OPENCLAW_MODEL_SMOKE_PROMPT,
    }
    raw_result = dict(client.run_probe(request))
    metadata = sanitize_openclaw_model_run_metadata(
        {
            **raw_result,
            "model_alias": selected_model["alias"],
            "lane": SMOKE_LANE,
        }
    )
    return {
        "attempt": attempt,
        "model_alias": selected_model["alias"],
        "provider_model_hint": selected_model["provider_model_hint"],
        "metadata": metadata,
        "validation_passed": _model_probe_validation_passed(raw_result),
        "prompt_logged": False,
        "credential_values_logged": False,
    }


def _model_probe_validation_passed(result: Mapping[str, Any]) -> bool:
    if result.get("success") is not True:
        return False
    response_text = result.get("response_text")
    if response_text is None:
        return True
    return response_text == OPENCLAW_MODEL_SMOKE_EXPECTED_TEXT


def _safe_model_plan_summary(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "routing_mode": plan["routing_mode"],
        "primary_alias": plan["primary"]["alias"],
        "primary_provider_model_hint": plan["primary"]["provider_model_hint"],
        "fallback_alias": plan["fallback"]["alias"],
        "fallback_provider_model_hint": plan["fallback"]["provider_model_hint"],
        "fallback_conditions": list(plan["fallback_conditions"]),
        "provider_auto_escalation": plan["provider_auto_escalation"],
        "hidden_model_choice": plan["hidden_model_choice"],
        "log_full_prompt": plan["log_full_prompt"],
        "log_credential_values": plan["log_credential_values"],
        "safe_metadata_fields": list(plan["safe_metadata_fields"]),
    }


def _model_smoke_safety_assertions(
    *,
    credential_values_read: bool = False,
    model_provider_called: bool = False,
) -> dict[str, bool]:
    return {
        "credential_values_read": credential_values_read,
        "credential_values_logged": False,
        "full_prompt_logged": False,
        "model_provider_called": model_provider_called,
        "protected_paths_touched": False,
        "tool_execution": False,
        "scheduler_activated": False,
        "production_db_active": False,
        "external_mutation": False,
        "broad_openclaw_runtime_handoff": False,
    }


def _config_names_only(
    available_config_names: Iterable[str] | Mapping[str, Any],
) -> tuple[str, ...]:
    if isinstance(available_config_names, Mapping):
        return tuple(str(name) for name in available_config_names.keys())
    return tuple(str(name) for name in available_config_names)


def _optional_string(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
