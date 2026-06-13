"""Structured completion reports for future dry-run and runtime operations."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from personalos.validation import ValidationResult, ValidationStatus


class CompletionStatus(StrEnum):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    BLOCKED = "blocked"


class CompletionMode(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    DRY_RUN = "dry_run"


@dataclass(frozen=True)
class CompletionReport:
    report_id: str
    status: CompletionStatus
    mode: CompletionMode
    dry_run: bool
    no_send: bool
    started_at_utc: str
    finished_at_utc: str
    actions_considered: int
    actions_allowed_dry_run: int
    actions_requiring_approval: int
    actions_blocked: int
    safety_flags: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    executed: bool = False
    sent: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "status": self.status.value,
            "mode": self.mode.value,
            "dry_run": self.dry_run,
            "no_send": self.no_send,
            "started_at_utc": self.started_at_utc,
            "finished_at_utc": self.finished_at_utc,
            "actions_considered": self.actions_considered,
            "actions_allowed_dry_run": self.actions_allowed_dry_run,
            "actions_requiring_approval": self.actions_requiring_approval,
            "actions_blocked": self.actions_blocked,
            "safety_flags": list(self.safety_flags),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": self.metadata,
            "executed": self.executed,
            "sent": self.sent,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=True, sort_keys=True)


def create_completion_report(
    *,
    status: CompletionStatus | str,
    mode: CompletionMode | str,
    dry_run: bool,
    no_send: bool,
    started_at_utc: str | None = None,
    finished_at_utc: str | None = None,
    actions_considered: int = 0,
    actions_allowed_dry_run: int = 0,
    actions_requiring_approval: int = 0,
    actions_blocked: int = 0,
    safety_flags: list[str] | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> CompletionReport:
    started = started_at_utc or _utc_now()
    finished = finished_at_utc or _utc_now()
    return CompletionReport(
        report_id=str(uuid4()),
        status=CompletionStatus(status),
        mode=CompletionMode(mode),
        dry_run=dry_run,
        no_send=no_send,
        started_at_utc=started,
        finished_at_utc=finished,
        actions_considered=actions_considered,
        actions_allowed_dry_run=actions_allowed_dry_run,
        actions_requiring_approval=actions_requiring_approval,
        actions_blocked=actions_blocked,
        safety_flags=safety_flags or [],
        warnings=warnings or [],
        errors=errors or [],
        metadata=metadata or {},
        executed=False,
        sent=False,
    )


def completion_report_from_validation_results(
    validation_results: list[ValidationResult],
    *,
    status: CompletionStatus | str = CompletionStatus.SUCCESS,
    mode: CompletionMode | str = CompletionMode.DRY_RUN,
    dry_run: bool = True,
    no_send: bool = True,
    safety_flags: list[str] | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> CompletionReport:
    return create_completion_report(
        status=status,
        mode=mode,
        dry_run=dry_run,
        no_send=no_send,
        actions_considered=len(validation_results),
        actions_allowed_dry_run=_count_status(
            validation_results,
            ValidationStatus.ALLOWED_DRY_RUN,
        ),
        actions_requiring_approval=_count_status(
            validation_results,
            ValidationStatus.REQUIRES_APPROVAL,
        ),
        actions_blocked=_count_status(validation_results, ValidationStatus.BLOCKED),
        safety_flags=safety_flags,
        warnings=warnings,
        errors=errors,
        metadata=metadata,
    )


def _count_status(
    validation_results: list[ValidationResult],
    status: ValidationStatus,
) -> int:
    return sum(1 for result in validation_results if result.status is status)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
