"""Deterministic OpenClaw model lane strategy for Phase 14-C smoke work."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


OPENCLAW_MODEL_STRATEGY_SCHEMA_VERSION = "personal_os_openclaw_model_strategy.v1"

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
