"""Shared dev/test validation helpers for execution rail modules."""

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import StrEnum

from personalos.permissions import RiskLevel


class ApprovalMode(StrEnum):
    AUTO_ALLOWED = "auto_allowed"
    APPROVAL_REQUIRED = "approval_required"
    MANUAL_ONLY = "manual_only"


class ExecutionRailStatus(StrEnum):
    PROPOSED = "proposed"
    NEEDS_APPROVAL = "needs_approval"
    APPROVED_FOR_DEV_TEST = "approved_for_dev_test"
    SIMULATED_CREATED = "simulated_created"
    CANCELLED = "cancelled"
    FAILED = "failed"


APPROVAL_MODE_VALUES = tuple(mode.value for mode in ApprovalMode)
EXECUTION_RAIL_STATUS_VALUES = tuple(status.value for status in ExecutionRailStatus)
RISK_LEVEL_VALUES = tuple(level.value for level in RiskLevel)


class DedupeConflictError(ValueError):
    """Raised when a create would silently duplicate a module-level dedupe key."""


def validate_required_text(field_name: str, value: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    return value


def validate_text(field_name: str, value: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    return value


def validate_labels(labels: list[str]) -> list[str]:
    if not isinstance(labels, list):
        raise ValueError("labels must be a list of strings")
    for label in labels:
        if not isinstance(label, str):
            raise ValueError("labels must be a list of strings")
    return list(labels)


def validate_todoist_priority(priority: int) -> int:
    if type(priority) is not int:
        raise ValueError("priority must be an integer")
    if priority < 1 or priority > 4:
        raise ValueError("priority must be between 1 and 4")
    return priority


def validate_positive_integer(field_name: str, value: int) -> int:
    if type(value) is not int:
        raise ValueError(f"{field_name} must be an integer")
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")
    return value


def validate_risk_level(risk_level: RiskLevel | str) -> str:
    if isinstance(risk_level, RiskLevel):
        return risk_level.value
    try:
        return RiskLevel(risk_level).value
    except ValueError as error:
        allowed = ", ".join(RISK_LEVEL_VALUES)
        raise ValueError(f"risk_level must be one of: {allowed}") from error


def validate_approval_mode(
    approval_mode: ApprovalMode | str | None,
    *,
    risk_level: RiskLevel | str,
) -> str:
    risk = validate_risk_level(risk_level)
    mode = default_approval_mode(risk) if approval_mode is None else _coerce_approval_mode(
        approval_mode
    )

    if mode is ApprovalMode.AUTO_ALLOWED and risk != RiskLevel.LOW.value:
        raise ValueError("approval_mode auto_allowed is valid only with low risk")
    if risk == RiskLevel.HIGH.value and mode not in (
        ApprovalMode.APPROVAL_REQUIRED,
        ApprovalMode.MANUAL_ONLY,
    ):
        raise ValueError("high risk objects must be approval_required or manual_only")
    return mode.value


def default_approval_mode(risk_level: RiskLevel | str) -> ApprovalMode:
    risk = validate_risk_level(risk_level)
    if risk == RiskLevel.LOW.value:
        return ApprovalMode.AUTO_ALLOWED
    return ApprovalMode.APPROVAL_REQUIRED


def default_status_for_approval(approval_mode: ApprovalMode | str) -> str:
    mode = _coerce_approval_mode(approval_mode)
    if mode is ApprovalMode.APPROVAL_REQUIRED:
        return ExecutionRailStatus.NEEDS_APPROVAL.value
    return ExecutionRailStatus.PROPOSED.value


def validate_execution_status(status: ExecutionRailStatus | str) -> str:
    if isinstance(status, ExecutionRailStatus):
        return status.value
    try:
        return ExecutionRailStatus(status).value
    except ValueError as error:
        allowed = ", ".join(EXECUTION_RAIL_STATUS_VALUES)
        raise ValueError(f"status must be one of: {allowed}") from error


def build_approval_result(risk_level: RiskLevel | str, approval_mode: ApprovalMode | str) -> dict:
    risk = validate_risk_level(risk_level)
    mode = _coerce_approval_mode(approval_mode).value
    return {
        "risk_level": risk,
        "approval_mode": mode,
        "auto_allowed": mode == ApprovalMode.AUTO_ALLOWED.value,
        "requires_approval": mode == ApprovalMode.APPROVAL_REQUIRED.value,
        "manual_only": mode == ApprovalMode.MANUAL_ONLY.value,
        "external_write_route_allowed": mode != ApprovalMode.MANUAL_ONLY.value,
    }


def normalize_dedupe_key(dedupe_key: str) -> str:
    normalized = normalize_for_dedupe(validate_required_text("dedupe_key", dedupe_key))
    if not normalized:
        raise ValueError("dedupe_key must not be empty")
    return normalized


def generate_dedupe_key(
    *,
    module_name: str,
    object_type: str,
    source_type: str,
    source_id: str,
    title: str,
    scheduled_marker: str,
) -> str:
    material = "|".join(
        (
            normalize_for_dedupe(validate_required_text("module_name", module_name)),
            normalize_for_dedupe(validate_required_text("object_type", object_type)),
            normalize_for_dedupe(validate_required_text("source_type", source_type)),
            normalize_for_dedupe(validate_required_text("source_id", source_id)),
            normalize_for_dedupe(validate_required_text("title", title)),
            normalize_for_dedupe(validate_required_text("scheduled_marker", scheduled_marker)),
        )
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
    return f"{normalize_for_dedupe(module_name)}:{normalize_for_dedupe(object_type)}:{digest}"


def stable_local_id(prefix: str, dedupe_key: str) -> str:
    normalized_key = normalize_dedupe_key(dedupe_key)
    digest = hashlib.sha256(normalized_key.encode("utf-8")).hexdigest()[:16]
    return f"{normalize_for_dedupe(prefix)}-{digest}"


def stable_fake_external_id(prefix: str, dedupe_key: str) -> str:
    normalized_key = normalize_dedupe_key(dedupe_key)
    digest = hashlib.sha256(normalized_key.encode("utf-8")).hexdigest()[:16]
    return f"fake-{normalize_for_dedupe(prefix)}-{digest}"


def normalize_for_dedupe(value: str) -> str:
    return " ".join(value.strip().lower().split())


def validate_timezone_aware_datetime(field_name: str, value: str) -> datetime:
    value = validate_required_text(field_name, value)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field_name} must be an ISO datetime") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone offset")
    return parsed


def validate_duration_matches_window(
    *,
    start_time: str,
    end_time: str,
    duration_minutes: int,
    tolerance_seconds: int = 30,
) -> int:
    duration = validate_positive_integer("duration_minutes", duration_minutes)
    start = validate_timezone_aware_datetime("start_time", start_time)
    end = validate_timezone_aware_datetime("end_time", end_time)
    if end <= start:
        raise ValueError("end_time must be after start_time")

    expected_seconds = duration * 60
    actual_seconds = (end - start).total_seconds()
    if abs(actual_seconds - expected_seconds) > tolerance_seconds:
        raise ValueError("duration_minutes must match start_time and end_time")
    return duration


def _coerce_approval_mode(approval_mode: ApprovalMode | str) -> ApprovalMode:
    if isinstance(approval_mode, ApprovalMode):
        return approval_mode
    try:
        return ApprovalMode(approval_mode)
    except ValueError as error:
        allowed = ", ".join(APPROVAL_MODE_VALUES)
        raise ValueError(f"approval_mode must be one of: {allowed}") from error
