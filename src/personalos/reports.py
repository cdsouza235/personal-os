"""Dev/test-only report jobs and Weekly Chart Pack review foundation."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from typing import Any

from personalos.permissions import PermissionMode
from personalos.state import (
    CHART_PACK_REVIEW_SOURCE_TYPES,
    CHART_PACK_REVIEW_STATUSES,
    REPORT_JOB_CADENCES,
    REPORT_JOB_STATUSES,
    REPORT_JOB_TYPES,
    REPORT_RUN_STATUSES,
    REPORT_RUN_TYPES,
    count_chart_pack_reviews,
    count_report_jobs,
    count_report_runs,
    create_chart_pack_review,
    create_report_job,
    create_report_run,
    get_chart_pack_review,
    get_permission_setting,
    get_report_job,
    get_report_run,
    list_chart_pack_reviews,
    list_report_jobs,
    list_report_runs,
    update_chart_pack_review,
    update_report_job,
    update_report_run,
    validate_chart_pack_review_source_type,
    validate_chart_pack_review_status,
    validate_report_job_cadence,
    validate_report_job_status,
    validate_report_job_type,
    validate_report_run_status,
    validate_report_run_type,
)

REPORT_JOBS_READ_PERMISSION = "report_jobs_dev_test_read"
REPORT_JOBS_WRITE_PERMISSION = "report_jobs_dev_test_write"
REPORT_JOBS_RUN_PERMISSION = "report_jobs_dev_test_run"
CHART_PACK_REVIEWS_READ_PERMISSION = "chart_pack_reviews_dev_test_read"
CHART_PACK_REVIEWS_WRITE_PERMISSION = "chart_pack_reviews_dev_test_write"

REPORT_JOB_SCHEMA_VERSION = "report_job.v1"
REPORT_RUN_SCHEMA_VERSION = "report_run.v1"
REPORT_RUN_OUTPUT_SCHEMA_VERSION = "report_run_output.v1"
CHART_PACK_REVIEW_SCHEMA_VERSION = "chart_pack_review.v1"
FAKE_REPORT_RUNNER_NAME = "fake_report_runner"

CHART_PACK_REQUIRED_SUMMARY_SECTIONS = (
    "market_context",
    "btc_context",
    "eth_context",
    "miner_hpc_context",
    "portfolio_watch_items",
    "week_over_week_changes",
    "followup_candidates",
    "warnings",
)

ACTION_FIELD_NAMES = (
    "action",
    "action_type",
    "recommendation",
    "recommended_action",
    "portfolio_action",
    "execution",
    "execution_type",
    "order",
    "trade",
)
INVESTMENT_ACTION_TERMS = (
    "buy",
    "sell",
    "hold",
    "rebalance",
    "trade",
    "execute",
    "order",
    "increase_position",
    "decrease_position",
    "portfolio_execution",
)
EXECUTION_CANDIDATE_TYPES = (
    "execution_task",
    "portfolio_execution",
    "portfolio_order",
    "trade_order",
    "todoist_task",
    "calendar_block",
)
EXTERNAL_WRITE_FLAGS = (
    "creates_external_action",
    "create_todoist_task",
    "create_calendar_block",
    "external_write",
    "portfolio_execution",
)


class ReportModulePermissionDenied(PermissionError):
    """Raised when a report module permission setting does not allow the action."""


class ReportValidationError(ValueError):
    """Raised when a report job, run, or chart pack review fails validation."""


class FakeReportRunnerError(RuntimeError):
    """Raised by the deterministic fake report runner failure mode."""


class FakeReportRunner:
    """Deterministic local runner; it never touches network, models, or live systems."""

    dev_test_fake_runner = True
    runner_name = FAKE_REPORT_RUNNER_NAME

    def __init__(self, *, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.calls: list[dict[str, Any]] = []

    def run(
        self,
        *,
        job: Mapping[str, Any],
        input_json: Mapping[str, Any],
        run_type: str,
        generated_at: str,
    ) -> dict[str, Any]:
        validated_job = validate_report_job(job)
        input_payload = _validate_metadata("input_json", input_json)
        run_type = validate_report_run_type(run_type)
        generated_at = _validate_iso_datetime("generated_at", generated_at)
        input_digest = _stable_json_digest(input_payload)
        self.calls.append(
            {
                "job_id": validated_job["id"],
                "run_type": run_type,
                "input_digest": input_digest,
            }
        )
        if self.should_fail:
            raise FakeReportRunnerError("Fake report runner failure mode was requested.")

        return build_report_run_output(
            job=validated_job,
            input_json=input_payload,
            run_type=run_type,
            status="completed",
            generated_at=generated_at,
        )


def validate_report_job(job: Mapping[str, Any]) -> dict[str, Any]:
    job = _require_mapping(job, "report_job")
    _require_keys(
        "report_job",
        job,
        {
            "id",
            "job_type",
            "name",
            "cadence",
            "config_json",
            "status",
            "created_at",
            "updated_at",
        },
    )

    description = job.get("description")
    last_run_at = job.get("last_run_at")
    next_due_at = job.get("next_due_at")
    return {
        "schema_version": str(job.get("schema_version", REPORT_JOB_SCHEMA_VERSION)),
        "id": _validate_required_text("id", job["id"]),
        "job_type": validate_report_job_type(str(job["job_type"])),
        "name": _validate_required_text("name", job["name"]),
        "description": None
        if description is None
        else _validate_text("description", description),
        "cadence": validate_report_job_cadence(str(job["cadence"])),
        "config_json": _validate_metadata("config_json", job["config_json"]),
        "status": validate_report_job_status(str(job["status"])),
        "last_run_at": None
        if last_run_at is None
        else _validate_iso_datetime("last_run_at", last_run_at),
        "next_due_at": None
        if next_due_at is None
        else _validate_iso_datetime("next_due_at", next_due_at),
        "created_at": _validate_iso_datetime("created_at", job["created_at"]),
        "updated_at": _validate_iso_datetime("updated_at", job["updated_at"]),
    }


def validate_report_run(run: Mapping[str, Any]) -> dict[str, Any]:
    run = _require_mapping(run, "report_run")
    _require_keys(
        "report_run",
        run,
        {
            "id",
            "job_id",
            "run_type",
            "dry_run",
            "status",
            "input_json",
            "output_json",
            "created_at",
        },
    )

    output_json = _validate_metadata("output_json", run["output_json"])
    _validate_report_run_output_safety(output_json)
    error_message = run.get("error_message")
    completed_at = run.get("completed_at")
    return {
        "schema_version": str(run.get("schema_version", REPORT_RUN_SCHEMA_VERSION)),
        "id": _validate_required_text("id", run["id"]),
        "job_id": _validate_required_text("job_id", run["job_id"]),
        "run_type": validate_report_run_type(str(run["run_type"])),
        "dry_run": _validate_bool("dry_run", run["dry_run"]),
        "status": validate_report_run_status(str(run["status"])),
        "input_json": _validate_metadata("input_json", run["input_json"]),
        "output_json": output_json,
        "error_message": None
        if error_message is None
        else _validate_text("error_message", error_message),
        "created_at": _validate_iso_datetime("created_at", run["created_at"]),
        "completed_at": None
        if completed_at is None
        else _validate_iso_datetime("completed_at", completed_at),
    }


def validate_chart_pack_review(review: Mapping[str, Any]) -> dict[str, Any]:
    review = _require_mapping(review, "chart_pack_review")
    _require_keys(
        "chart_pack_review",
        review,
        {
            "id",
            "review_date",
            "week_start",
            "week_end",
            "source_type",
            "title",
            "chart_pack_json",
            "tradingview_alerts_json",
            "synthesis_markdown",
            "structured_summary_json",
            "status",
            "created_at",
            "updated_at",
        },
    )

    review_date = _validate_iso_date("review_date", review["review_date"])
    week_start = _validate_iso_date("week_start", review["week_start"])
    week_end = _validate_iso_date("week_end", review["week_end"])
    if date.fromisoformat(week_start) > date.fromisoformat(week_end):
        raise ReportValidationError("week_start must be on or before week_end")

    source_id = review.get("source_id")
    thesis_context = review.get("thesis_context")
    structured_summary = _validate_structured_summary(
        review["structured_summary_json"],
    )
    return {
        "schema_version": str(
            review.get("schema_version", CHART_PACK_REVIEW_SCHEMA_VERSION)
        ),
        "id": _validate_required_text("id", review["id"]),
        "review_date": review_date,
        "week_start": week_start,
        "week_end": week_end,
        "source_type": validate_chart_pack_review_source_type(str(review["source_type"])),
        "source_id": None
        if source_id is None
        else _validate_required_text("source_id", source_id),
        "title": _validate_required_text("title", review["title"]),
        "thesis_context": None
        if thesis_context is None
        else _validate_text("thesis_context", thesis_context),
        "chart_pack_json": _validate_metadata("chart_pack_json", review["chart_pack_json"]),
        "tradingview_alerts_json": _validate_metadata(
            "tradingview_alerts_json",
            review["tradingview_alerts_json"],
        ),
        "synthesis_markdown": _validate_required_text(
            "synthesis_markdown",
            review["synthesis_markdown"],
        ),
        "structured_summary_json": structured_summary,
        "status": validate_chart_pack_review_status(str(review["status"])),
        "created_at": _validate_iso_datetime("created_at", review["created_at"]),
        "updated_at": _validate_iso_datetime("updated_at", review["updated_at"]),
    }


def build_report_run_output(
    *,
    job: Mapping[str, Any],
    input_json: Mapping[str, Any],
    run_type: str,
    status: str,
    generated_at: str,
    warnings: Sequence[str] | None = None,
) -> dict[str, Any]:
    validated_job = validate_report_job(job)
    input_payload = _validate_metadata("input_json", input_json)
    run_type = validate_report_run_type(run_type)
    status = validate_report_run_status(status)
    generated_at = _validate_iso_datetime("generated_at", generated_at)
    input_digest = _stable_json_digest(input_payload)
    output = {
        "schema_version": REPORT_RUN_OUTPUT_SCHEMA_VERSION,
        "job_id": validated_job["id"],
        "job_type": validated_job["job_type"],
        "run_type": run_type,
        "status": status,
        "generated_at": generated_at,
        "sections": {
            "job": {
                "name": validated_job["name"],
                "cadence": validated_job["cadence"],
                "status": validated_job["status"],
            },
            "input_digest": {
                "sha256_16": input_digest,
                "top_level_keys": sorted(input_payload.keys()),
            },
            "scope": {
                "local_only": True,
                "coded_job": True,
                "analyst_persona": False,
                "external_writes": False,
            },
        },
        "warnings": [] if warnings is None else [_validate_text("warning", item) for item in warnings],
        "no_external_writes": True,
        "network_called": False,
        "external_mutation": False,
        "model_called": False,
    }
    _validate_report_run_output_safety(output)
    return output


def preview_report_job_output(
    *,
    job: Mapping[str, Any],
    input_json: Mapping[str, Any],
    run_type: str = "preview",
    generated_at: str | None = None,
) -> dict[str, Any]:
    return build_report_run_output(
        job=job,
        input_json=input_json,
        run_type=run_type,
        status="completed",
        generated_at=generated_at or _utc_now(),
    )


def run_fake_report_job(
    connection: sqlite3.Connection,
    *,
    job: Mapping[str, Any],
    input_json: Mapping[str, Any],
    run_type: str = "dry_run",
    runner: FakeReportRunner | None = None,
    run_at: str | None = None,
) -> dict[str, Any]:
    validated_job = validate_report_job(job)
    input_payload = _validate_metadata("input_json", input_json)
    run_type = validate_report_run_type(run_type)
    run_at = _validate_iso_datetime("run_at", run_at or _utc_now())
    run_permission = evaluate_report_module_permission(
        connection,
        category=REPORT_JOBS_RUN_PERMISSION,
    )
    write_permission = evaluate_report_module_permission(
        connection,
        category=REPORT_JOBS_WRITE_PERMISSION,
    )
    if not run_permission["allowed"]:
        return _blocked_result(
            reason=run_permission["reason"],
            job=validated_job,
            permission={"run": run_permission, "write": write_permission},
        )
    if not write_permission["allowed"]:
        return _blocked_result(
            reason=write_permission["reason"],
            job=validated_job,
            permission={"run": run_permission, "write": write_permission},
        )

    selected_runner = runner or FakeReportRunner()
    run_id = stable_report_id(
        "report-run",
        f"{validated_job['id']}|{run_type}|{run_at}|{_stable_json_digest(input_payload)}",
    )
    try:
        output_json = selected_runner.run(
            job=validated_job,
            input_json=input_payload,
            run_type=run_type,
            generated_at=run_at,
        )
        report_run = create_report_run(
            connection,
            run_id=run_id,
            job_id=validated_job["id"],
            run_type=run_type,
            dry_run=True,
            status="completed",
            input_json=input_payload,
            output_json=output_json,
            created_at=run_at,
            completed_at=run_at,
        )
    except FakeReportRunnerError as error:
        output_json = build_report_run_output(
            job=validated_job,
            input_json=input_payload,
            run_type=run_type,
            status="failed",
            generated_at=run_at,
            warnings=["Fake report runner failure mode was requested."],
        )
        report_run = create_report_run(
            connection,
            run_id=run_id,
            job_id=validated_job["id"],
            run_type=run_type,
            dry_run=True,
            status="failed",
            input_json=input_payload,
            output_json=output_json,
            error_message=str(error),
            created_at=run_at,
            completed_at=run_at,
        )
        return {
            "status": "failed",
            "reason": str(error),
            "dry_run": True,
            "no_send": True,
            "database_write": True,
            "external_mutation": False,
            "network_called": False,
            "no_external_writes": True,
            "permission": {"run": run_permission, "write": write_permission},
            "job": validated_job,
            "report_run": report_run,
            "output_json": output_json,
            "runner_name": selected_runner.runner_name,
        }

    return {
        "status": "completed",
        "reason": "Fake report runner created a dev/test report_run record only.",
        "dry_run": True,
        "no_send": True,
        "database_write": True,
        "external_mutation": False,
        "network_called": False,
        "no_external_writes": True,
        "permission": {"run": run_permission, "write": write_permission},
        "job": validated_job,
        "report_run": report_run,
        "output_json": output_json,
        "runner_name": selected_runner.runner_name,
    }


def create_report_job_record(
    connection: sqlite3.Connection,
    *,
    job: Mapping[str, Any],
) -> dict[str, Any]:
    validated_job = validate_report_job(job)
    permission = evaluate_report_module_permission(
        connection,
        category=REPORT_JOBS_WRITE_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(reason=permission["reason"], job=validated_job, permission=permission)

    created = create_report_job(
        connection,
        job_id=validated_job["id"],
        job_type=validated_job["job_type"],
        name=validated_job["name"],
        description=validated_job["description"],
        cadence=validated_job["cadence"],
        config_json=validated_job["config_json"],
        status=validated_job["status"],
        last_run_at=validated_job["last_run_at"],
        next_due_at=validated_job["next_due_at"],
        created_at=validated_job["created_at"],
        updated_at=validated_job["updated_at"],
    )
    return {
        "status": "created",
        "reason": "Report job was stored in the dev/test SQLite database only.",
        "database_write": True,
        "external_mutation": False,
        "no_external_writes": True,
        "permission": permission,
        "job": created,
    }


def update_report_job_record(
    connection: sqlite3.Connection,
    *,
    job_id: str,
    status: str | None = None,
    last_run_at: str | None = None,
    next_due_at: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    permission = evaluate_report_module_permission(
        connection,
        category=REPORT_JOBS_WRITE_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(reason=permission["reason"], job=None, permission=permission)

    updated = update_report_job(
        connection,
        job_id=job_id,
        status=status,
        last_run_at=last_run_at,
        next_due_at=next_due_at,
        updated_at=updated_at,
    )
    return {
        "status": "updated",
        "reason": "Report job was updated in the dev/test SQLite database only.",
        "database_write": True,
        "external_mutation": False,
        "no_external_writes": True,
        "permission": permission,
        "job": updated,
    }


def create_report_run_record(
    connection: sqlite3.Connection,
    *,
    run: Mapping[str, Any],
) -> dict[str, Any]:
    validated_run = validate_report_run(run)
    permission = evaluate_report_module_permission(
        connection,
        category=REPORT_JOBS_WRITE_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(reason=permission["reason"], job=None, permission=permission)

    created = create_report_run(
        connection,
        run_id=validated_run["id"],
        job_id=validated_run["job_id"],
        run_type=validated_run["run_type"],
        dry_run=validated_run["dry_run"],
        status=validated_run["status"],
        input_json=validated_run["input_json"],
        output_json=validated_run["output_json"],
        error_message=validated_run["error_message"],
        created_at=validated_run["created_at"],
        completed_at=validated_run["completed_at"],
    )
    return {
        "status": "created",
        "reason": "Report run was stored in the dev/test SQLite database only.",
        "database_write": True,
        "external_mutation": False,
        "no_external_writes": True,
        "permission": permission,
        "report_run": created,
    }


def update_report_run_record(
    connection: sqlite3.Connection,
    *,
    run_id: str,
    status: str,
    output_json: Mapping[str, Any] | None = None,
    error_message: str | None = None,
    completed_at: str | None = None,
) -> dict[str, Any]:
    if output_json is not None:
        _validate_report_run_output_safety(_validate_metadata("output_json", output_json))
    permission = evaluate_report_module_permission(
        connection,
        category=REPORT_JOBS_WRITE_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(reason=permission["reason"], job=None, permission=permission)

    updated = update_report_run(
        connection,
        run_id=run_id,
        status=status,
        output_json=output_json,
        error_message=error_message,
        completed_at=completed_at,
    )
    return {
        "status": "updated",
        "reason": "Report run was updated in the dev/test SQLite database only.",
        "database_write": True,
        "external_mutation": False,
        "no_external_writes": True,
        "permission": permission,
        "report_run": updated,
    }


def create_chart_pack_review_record(
    connection: sqlite3.Connection,
    *,
    review: Mapping[str, Any],
) -> dict[str, Any]:
    validated_review = validate_chart_pack_review(review)
    permission = evaluate_report_module_permission(
        connection,
        category=CHART_PACK_REVIEWS_WRITE_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(
            reason=permission["reason"],
            job=None,
            permission=permission,
        )

    created = create_chart_pack_review(
        connection,
        review_id=validated_review["id"],
        review_date=validated_review["review_date"],
        week_start=validated_review["week_start"],
        week_end=validated_review["week_end"],
        source_type=validated_review["source_type"],
        source_id=validated_review["source_id"],
        title=validated_review["title"],
        thesis_context=validated_review["thesis_context"],
        chart_pack_json=validated_review["chart_pack_json"],
        tradingview_alerts_json=validated_review["tradingview_alerts_json"],
        synthesis_markdown=validated_review["synthesis_markdown"],
        structured_summary_json=validated_review["structured_summary_json"],
        status=validated_review["status"],
        created_at=validated_review["created_at"],
        updated_at=validated_review["updated_at"],
    )
    return {
        "status": "created",
        "reason": "Chart pack review was stored in the dev/test SQLite database only.",
        "database_write": True,
        "external_mutation": False,
        "no_external_writes": True,
        "permission": permission,
        "review": created,
    }


def update_chart_pack_review_record(
    connection: sqlite3.Connection,
    *,
    review_id: str,
    status: str | None = None,
    structured_summary_json: Mapping[str, Any] | None = None,
    synthesis_markdown: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    if structured_summary_json is not None:
        _validate_structured_summary(structured_summary_json)
    permission = evaluate_report_module_permission(
        connection,
        category=CHART_PACK_REVIEWS_WRITE_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(reason=permission["reason"], job=None, permission=permission)

    updated = update_chart_pack_review(
        connection,
        review_id=review_id,
        status=status,
        structured_summary_json=structured_summary_json,
        synthesis_markdown=synthesis_markdown,
        updated_at=updated_at,
    )
    return {
        "status": "updated",
        "reason": "Chart pack review was updated in the dev/test SQLite database only.",
        "database_write": True,
        "external_mutation": False,
        "no_external_writes": True,
        "permission": permission,
        "review": updated,
    }


def read_report_job(
    connection: sqlite3.Connection,
    *,
    job_id: str,
) -> dict[str, Any] | None:
    require_report_module_permission(connection, category=REPORT_JOBS_READ_PERMISSION)
    return get_report_job(connection, job_id)


def read_report_jobs(
    connection: sqlite3.Connection,
    *,
    job_type: str | None = None,
    cadence: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    require_report_module_permission(connection, category=REPORT_JOBS_READ_PERMISSION)
    return list_report_jobs(connection, job_type=job_type, cadence=cadence, status=status)


def read_report_job_count(
    connection: sqlite3.Connection,
    *,
    job_type: str | None = None,
    cadence: str | None = None,
    status: str | None = None,
) -> int:
    require_report_module_permission(connection, category=REPORT_JOBS_READ_PERMISSION)
    return count_report_jobs(connection, job_type=job_type, cadence=cadence, status=status)


def read_report_run(
    connection: sqlite3.Connection,
    *,
    run_id: str,
) -> dict[str, Any] | None:
    require_report_module_permission(connection, category=REPORT_JOBS_READ_PERMISSION)
    return get_report_run(connection, run_id)


def read_report_runs(
    connection: sqlite3.Connection,
    *,
    job_id: str | None = None,
    run_type: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    require_report_module_permission(connection, category=REPORT_JOBS_READ_PERMISSION)
    return list_report_runs(connection, job_id=job_id, run_type=run_type, status=status)


def read_report_run_count(
    connection: sqlite3.Connection,
    *,
    job_id: str | None = None,
    run_type: str | None = None,
    status: str | None = None,
) -> int:
    require_report_module_permission(connection, category=REPORT_JOBS_READ_PERMISSION)
    return count_report_runs(connection, job_id=job_id, run_type=run_type, status=status)


def read_chart_pack_review(
    connection: sqlite3.Connection,
    *,
    review_id: str,
) -> dict[str, Any] | None:
    require_report_module_permission(
        connection,
        category=CHART_PACK_REVIEWS_READ_PERMISSION,
    )
    return get_chart_pack_review(connection, review_id)


def read_chart_pack_reviews(
    connection: sqlite3.Connection,
    *,
    source_type: str | None = None,
    status: str | None = None,
    week_start: str | None = None,
) -> list[dict[str, Any]]:
    require_report_module_permission(
        connection,
        category=CHART_PACK_REVIEWS_READ_PERMISSION,
    )
    return list_chart_pack_reviews(
        connection,
        source_type=source_type,
        status=status,
        week_start=week_start,
    )


def read_chart_pack_review_count(
    connection: sqlite3.Connection,
    *,
    source_type: str | None = None,
    status: str | None = None,
    week_start: str | None = None,
) -> int:
    require_report_module_permission(
        connection,
        category=CHART_PACK_REVIEWS_READ_PERMISSION,
    )
    return count_chart_pack_reviews(
        connection,
        source_type=source_type,
        status=status,
        week_start=week_start,
    )


def require_report_module_permission(
    connection: sqlite3.Connection,
    *,
    category: str,
) -> dict[str, Any]:
    decision = evaluate_report_module_permission(connection, category=category)
    if not decision["allowed"]:
        raise ReportModulePermissionDenied(decision["reason"])
    return decision


def evaluate_report_module_permission(
    connection: sqlite3.Connection,
    *,
    category: str,
) -> dict[str, Any]:
    category = _validate_required_text("category", category)
    setting = get_permission_setting(connection, category)
    if setting is None:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=None,
            reason=f"Missing report module permission setting: {category}",
            setting=None,
        )

    try:
        mode = PermissionMode(setting["mode"])
    except ValueError:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=setting["mode"],
            reason=f"Invalid report module permission mode: {setting['mode']}",
            setting=setting,
        )

    if mode is PermissionMode.DISABLED:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=mode.value,
            reason=f"Report module permission is disabled: {category}",
            setting=setting,
        )
    if mode is not PermissionMode.AUTO_WRITE:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=mode.value,
            reason=f"Report module permission is not enabled for dev/test use: {category}",
            setting=setting,
        )

    return _permission_decision(
        allowed=True,
        category=category,
        mode=mode.value,
        reason="Report module permission is explicitly enabled for dev/test use.",
        setting=setting,
    )


def stable_report_id(prefix: str, material: str) -> str:
    prefix = _normalize_for_id(_validate_required_text("prefix", prefix))
    material = _validate_required_text("material", material)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _validate_structured_summary(value: Any) -> dict[str, Any]:
    summary = _validate_metadata("structured_summary_json", value)
    missing = [
        section
        for section in CHART_PACK_REQUIRED_SUMMARY_SECTIONS
        if section not in summary
    ]
    if missing:
        raise ReportValidationError(
            "structured_summary_json missing required sections: " + ", ".join(missing)
        )

    followups = summary["followup_candidates"]
    warnings = summary["warnings"]
    if not isinstance(followups, list):
        raise ReportValidationError("followup_candidates must be a list")
    if not isinstance(warnings, list):
        raise ReportValidationError("warnings must be a list")

    for index, candidate in enumerate(followups):
        _validate_followup_candidate(candidate, index)
    for index, warning in enumerate(warnings):
        _validate_text(f"warnings[{index}]", warning)

    _assert_json_safe("structured_summary_json", summary)
    return summary


def _validate_followup_candidate(candidate: Any, index: int) -> dict[str, Any]:
    candidate = _require_mapping(candidate, f"followup_candidates[{index}]")
    candidate_type = str(candidate.get("candidate_type", "review_candidate"))
    risk_level = str(candidate.get("risk_level", "medium"))
    approval_mode = str(candidate.get("approval_mode", "approval_required"))

    if candidate_type in EXECUTION_CANDIDATE_TYPES:
        raise ReportValidationError(
            f"followup_candidates[{index}] must be review/logging only, not execution"
        )
    for flag in EXTERNAL_WRITE_FLAGS:
        if candidate.get(flag) is True:
            raise ReportValidationError(
                f"followup_candidates[{index}] must not request external writes"
            )

    action_text = _structured_action_text(candidate)
    has_investment_action = any(term in action_text for term in INVESTMENT_ACTION_TERMS)
    if has_investment_action:
        if risk_level != "high" or approval_mode not in {"approval_required", "manual_only"}:
            raise ReportValidationError(
                f"followup_candidates[{index}] investment actions must be high risk "
                "and approval_required/manual_only"
            )
        if candidate.get("approval_required") is False:
            raise ReportValidationError(
                f"followup_candidates[{index}] investment actions require manual approval"
            )
        if str(candidate.get("status", "review_candidate")) in {
            "ready_to_execute",
            "approved",
            "proposed_for_execution",
        }:
            raise ReportValidationError(
                f"followup_candidates[{index}] must not be marked executable"
            )

    _assert_json_safe(f"followup_candidates[{index}]", candidate)
    return dict(candidate)


def _structured_action_text(candidate: Mapping[str, Any]) -> str:
    fragments: list[str] = []
    for key, value in candidate.items():
        key_text = str(key).lower()
        if any(field_name in key_text for field_name in ACTION_FIELD_NAMES):
            fragments.append(key_text)
            fragments.append(str(value).lower())
    return " ".join(fragments)


def _validate_report_run_output_safety(output_json: Mapping[str, Any]) -> None:
    if output_json.get("no_external_writes") is not True:
        raise ReportValidationError("report run output_json must include no_external_writes: true")
    for field_name in ("network_called", "external_mutation", "model_called"):
        if output_json.get(field_name) is True:
            raise ReportValidationError(f"report run output_json must not set {field_name}: true")
    _assert_json_safe("output_json", output_json)


def _blocked_result(
    *,
    reason: str,
    job: Mapping[str, Any] | None,
    permission: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": reason,
        "dry_run": True,
        "no_send": True,
        "database_write": False,
        "external_mutation": False,
        "network_called": False,
        "no_external_writes": True,
        "permission": dict(permission),
        "job": None if job is None else dict(job),
        "report_run": None,
        "output_json": None,
    }


def _permission_decision(
    *,
    allowed: bool,
    category: str,
    mode: str | None,
    reason: str,
    setting: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "allowed": allowed,
        "category": category,
        "mode": mode,
        "reason": reason,
        "setting": None if setting is None else dict(setting),
    }


def _require_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReportValidationError(f"{field_name} must be a JSON object")
    return value


def _require_keys(field_name: str, value: Mapping[str, Any], required_keys: set[str]) -> None:
    missing = sorted(required_keys - set(value.keys()))
    if missing:
        raise ReportValidationError(f"{field_name} missing required fields: {', '.join(missing)}")


def _validate_metadata(field_name: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ReportValidationError(f"{field_name} must be a JSON object")
    metadata = dict(value)
    _assert_json_safe(field_name, metadata)
    return metadata


def _assert_json_safe(field_name: str, value: Any) -> None:
    try:
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as error:
        raise ReportValidationError(f"{field_name} must be JSON-safe") from error


def _validate_required_text(field_name: str, value: Any) -> str:
    value = _validate_text(field_name, value)
    if not value.strip():
        raise ReportValidationError(f"{field_name} must not be empty")
    return value


def _validate_text(field_name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise ReportValidationError(f"{field_name} must be a string")
    return value


def _validate_iso_date(field_name: str, value: Any) -> str:
    value = _validate_required_text(field_name, value)
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ReportValidationError(f"{field_name} must be an ISO date") from error
    return value


def _validate_iso_datetime(field_name: str, value: Any) -> str:
    value = _validate_required_text(field_name, value)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ReportValidationError(f"{field_name} must be an ISO datetime") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ReportValidationError(f"{field_name} must include a timezone offset")
    return value


def _validate_bool(field_name: str, value: Any) -> bool:
    if type(value) is not bool:
        raise ReportValidationError(f"{field_name} must be a boolean")
    return value


def _stable_json_digest(value: Mapping[str, Any]) -> str:
    serialized = json.dumps(
        dict(value),
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def _normalize_for_id(value: str) -> str:
    normalized = "-".join(value.strip().lower().replace("_", "-").split())
    return "".join(character for character in normalized if character.isalnum() or character == "-")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


__all__ = [
    "CHART_PACK_REQUIRED_SUMMARY_SECTIONS",
    "CHART_PACK_REVIEW_SOURCE_TYPES",
    "CHART_PACK_REVIEW_STATUSES",
    "CHART_PACK_REVIEWS_READ_PERMISSION",
    "CHART_PACK_REVIEWS_WRITE_PERMISSION",
    "FAKE_REPORT_RUNNER_NAME",
    "FakeReportRunner",
    "FakeReportRunnerError",
    "REPORT_JOB_CADENCES",
    "REPORT_JOB_SCHEMA_VERSION",
    "REPORT_JOB_STATUSES",
    "REPORT_JOB_TYPES",
    "REPORT_JOBS_READ_PERMISSION",
    "REPORT_JOBS_RUN_PERMISSION",
    "REPORT_JOBS_WRITE_PERMISSION",
    "REPORT_RUN_OUTPUT_SCHEMA_VERSION",
    "REPORT_RUN_SCHEMA_VERSION",
    "REPORT_RUN_STATUSES",
    "REPORT_RUN_TYPES",
    "ReportModulePermissionDenied",
    "ReportValidationError",
    "build_report_run_output",
    "create_chart_pack_review_record",
    "create_report_job_record",
    "create_report_run_record",
    "evaluate_report_module_permission",
    "preview_report_job_output",
    "read_chart_pack_review",
    "read_chart_pack_review_count",
    "read_chart_pack_reviews",
    "read_report_job",
    "read_report_job_count",
    "read_report_jobs",
    "read_report_run",
    "read_report_run_count",
    "read_report_runs",
    "require_report_module_permission",
    "run_fake_report_job",
    "stable_report_id",
    "update_chart_pack_review_record",
    "update_report_job_record",
    "update_report_run_record",
    "validate_chart_pack_review",
    "validate_report_job",
    "validate_report_run",
]
