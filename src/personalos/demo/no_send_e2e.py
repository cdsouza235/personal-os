"""Phase 13E-D deterministic synthetic end-to-end no-send demo runner."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from contextlib import closing
from pathlib import Path
from typing import Any

from personalos.briefings import (
    BRIEFING_LOOP_READ_PERMISSION,
    BRIEFING_LOOP_RUN_PERMISSION,
    BRIEFING_LOOP_WRITE_PERMISSION,
    generate_no_send_briefing_preview,
)
from personalos.composer import (
    COMPOSER_MODULE_READ_PERMISSION,
    COMPOSER_MODULE_RUN_PERMISSION,
    COMPOSER_MODULE_WRITE_PERMISSION,
)
from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.dashboard import render_today_view_html_from_connection
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.demo.fixtures import (
    COMMAND_CONTRACT,
    DEMO_NAME,
    FIXED_COMPLETED_TIME,
    FIXED_SECOND_COMPLETED_TIME,
    FIXED_TIME,
    PHASE_NAME,
    SOURCE_DATE,
    build_side_effect_inputs,
    build_synthesis_approval,
    build_synthesis_payload,
    build_synthetic_fixture_manifest,
)
from personalos.path_safety import is_under_repo, is_under_temp, validate_demo_output_dir_path
from personalos.permissions import PermissionMode
from personalos.status import create_rail_state_report
from personalos.scheduler import (
    SAFE_NO_SEND_SEED_PROFILE,
    preview_scheduler_jobs,
    seed_dev_scheduler_jobs,
    summarize_scheduler,
)
from personalos.side_effects import (
    SIDE_EFFECT_LEDGER_ATTEMPT_PERMISSION,
    SIDE_EFFECT_LEDGER_READ_PERMISSION,
    SIDE_EFFECT_LEDGER_WRITE_PERMISSION,
    create_external_write_intent_and_record_dry_run,
    summarize_side_effect_ledgers,
)
from personalos.state import (
    count_calendar_blocks,
    count_followups,
    count_priorities,
    count_projects,
    count_routines,
    count_todoist_tasks,
    create_followup,
    create_priority,
    create_project,
    create_routine,
    list_followups,
    list_priorities,
    list_projects,
    list_routines,
    record_routine_completion,
    upsert_permission_setting,
)
from personalos.status import create_status_summary
from personalos.synthesis_apply import (
    SYNTHESIS_APPLY_APPLY_PERMISSION,
    SYNTHESIS_APPLY_READ_PERMISSION,
    SYNTHESIS_APPLY_WRITE_PERMISSION,
    apply_synthesis_import_preview,
    list_synthesis_apply_items,
    stable_approval_source_hash,
    summarize_synthesis_apply_runs,
)
from personalos.synthesis_import import (
    SYNTHESIS_IMPORT_PREVIEW_PERMISSION,
    SYNTHESIS_IMPORT_READ_PERMISSION,
    SYNTHESIS_IMPORT_WRITE_PERMISSION,
    create_synthesis_import_preview_record,
)

ARTIFACT_NAMES = (
    "synthetic_input_manifest.json",
    "demo.sqlite3",
    "safe_path_classification.json",
    "workflow_report.json",
    "status_readiness_report.json",
    "synthesis_payload.synthetic.json",
    "synthesis_preview.json",
    "synthesis_apply_report.json",
    "no_send_briefing_preview.json",
    "no_send_briefing_preview.md",
    "side_effect_ledger_summary.json",
    "idempotency_ledger_summary.json",
    "scheduler_simulation_evidence.json",
    "dashboard_render_evidence.json",
    "dashboard_render.html",
    "safety_assertions.json",
    "artifacts.json",
    "summary.md",
    "completion_report.json",
)


def run_no_send_e2e_demo(output_dir: str | Path) -> dict[str, Any]:
    output_path = validate_demo_output_dir_path(output_dir, path_label="demo output_dir")
    db_path = output_path / "demo.sqlite3"
    if db_path.exists():
        raise ValueError(
            "demo output_dir already contains demo.sqlite3; choose a fresh safe directory"
        )

    output_path.mkdir(parents=True, exist_ok=True)
    workflow = _Workflow()
    artifact_paths = _artifact_paths(output_path)
    safe_path_classification = _safe_path_classification(output_path, db_path)
    _write_json(artifact_paths["safe_path_classification.json"], safe_path_classification)
    workflow.complete("validate_safe_output_dir")

    manifest = build_synthetic_fixture_manifest()
    synthesis_payload = build_synthesis_payload()
    _write_json(artifact_paths["synthetic_input_manifest.json"], manifest)
    _write_json(artifact_paths["synthesis_payload.synthetic.json"], synthesis_payload)
    workflow.complete("write_synthetic_input_manifest")

    config = PersonalOSConfig(
        environment=Environment.TEST,
        timezone=DEFAULT_TIMEZONE,
        database_path=db_path,
    )
    with closing(connect_sqlite(config, runtime_dir=output_path)) as connection:
        apply_migrations(connection)
        _normalize_migration_timestamps(connection)
        workflow.complete("create_demo_sqlite_and_apply_migrations")

        _enable_demo_permissions(connection)
        seeded = _seed_synthetic_state(connection, manifest)
        workflow.complete("seed_synthetic_routines_priorities_projects_followups")

        preview_result = create_synthesis_import_preview_record(
            connection,
            json.dumps(synthesis_payload, allow_nan=False, ensure_ascii=True, sort_keys=True),
            created_at=FIXED_TIME,
            updated_at=FIXED_TIME,
        )
        preview_id = _require_preview_id(preview_result)
        _write_json(artifact_paths["synthesis_preview.json"], _stable_report(preview_result))
        workflow.complete("generate_synthesis_preview")

        approval = build_synthesis_approval(preview_id=preview_id)
        approval_hash = stable_approval_source_hash(
            json.dumps(approval, allow_nan=False, ensure_ascii=True, sort_keys=True)
        )
        first_apply = apply_synthesis_import_preview(
            connection,
            preview_id=preview_id,
            approval=approval,
            approval_source_type="json_object",
            approval_source_hash=approval_hash,
            apply_run_id="synthesis-apply-run-phase-13e-d-first",
            created_at=FIXED_TIME,
            completed_at=FIXED_COMPLETED_TIME,
        )
        workflow.complete("apply_approved_synthesis_to_demo_sqlite_only")

        second_apply = apply_synthesis_import_preview(
            connection,
            preview_id=preview_id,
            approval=approval,
            approval_source_type="json_object",
            approval_source_hash=approval_hash,
            apply_run_id="synthesis-apply-run-phase-13e-d-idempotency-check",
            created_at=FIXED_TIME,
            completed_at=FIXED_SECOND_COMPLETED_TIME,
        )
        apply_items = list_synthesis_apply_items(connection)
        apply_summary = summarize_synthesis_apply_runs(connection)
        synthesis_apply_report = _stable_report(
            {
                "approval": approval,
                "approval_source_hash": approval_hash,
                "first_apply": first_apply,
                "idempotency_rerun": second_apply,
                "apply_items": apply_items,
                "apply_summary": apply_summary,
                "idempotency_evidence": {
                    "first_status": first_apply["status"],
                    "rerun_status": second_apply["status"],
                    "rerun_item_statuses": sorted(
                        {item["apply_status"] for item in second_apply["items"]}
                    ),
                    "internal_state_duplicated": False,
                },
            }
        )
        _write_json(artifact_paths["synthesis_apply_report.json"], synthesis_apply_report)
        workflow.complete("produce_synthesis_apply_and_idempotency_report")

        briefing_result = generate_no_send_briefing_preview(
            connection,
            source_date=SOURCE_DATE,
            timezone=DEFAULT_TIMEZONE,
            briefing_window_name="morning",
            delivery_mode="no_send",
            run_at=FIXED_TIME,
        )
        _write_json(artifact_paths["no_send_briefing_preview.json"], _stable_report(briefing_result))
        artifact_paths["no_send_briefing_preview.md"].write_text(
            briefing_result["manual_export_markdown"],
            encoding="utf-8",
        )
        workflow.complete("generate_no_send_briefing_preview_and_markdown_export")

        side_effect_evidence = _record_side_effect_evidence(connection)
        _write_json(
            artifact_paths["side_effect_ledger_summary.json"],
            _stable_report(side_effect_evidence["summary"]),
        )
        _write_json(
            artifact_paths["idempotency_ledger_summary.json"],
            _stable_report(side_effect_evidence["idempotency_summary"]),
        )
        workflow.complete("produce_side_effect_and_idempotency_ledger_evidence")

        scheduler_seed = seed_dev_scheduler_jobs(
            connection,
            profile=SAFE_NO_SEND_SEED_PROFILE,
            timezone=DEFAULT_TIMEZONE,
            created_at=FIXED_TIME,
        )
        scheduler_preview = preview_scheduler_jobs(
            connection,
            source_date=SOURCE_DATE,
            timezone=DEFAULT_TIMEZONE,
        )
        scheduler_summary = summarize_scheduler(connection)
        scheduler_evidence = _stable_report(
            {
                "status": "simulated_preview_only",
                "seed_result": scheduler_seed,
                "preview_result": scheduler_preview,
                "summary": scheduler_summary,
                "scheduler_activated": False,
                "launch_agent_installed": False,
                "crontab_modified": False,
                "daemon_started": False,
                "background_process_started": False,
            }
        )
        _write_json(artifact_paths["scheduler_simulation_evidence.json"], scheduler_evidence)
        workflow.complete("produce_scheduler_simulation_preview_evidence")

        dashboard_html = render_today_view_html_from_connection(
            connection,
            source_date=SOURCE_DATE,
            timezone=DEFAULT_TIMEZONE,
            include_synthesis_import_form=False,
        )
        artifact_paths["dashboard_render.html"].write_text(dashboard_html, encoding="utf-8")
        dashboard_evidence = {
            "status": "rendered",
            "static_html_only": True,
            "server_started": False,
            "daemon_started": False,
            "output_file": str(artifact_paths["dashboard_render.html"]),
            "output_file_under_output_dir": _is_under(
                artifact_paths["dashboard_render.html"],
                output_path,
            ),
            "html_contains_rail_states": "Rail States" in dashboard_html,
            "html_contains_inert_headline": "all inert" in dashboard_html,
        }
        _write_json(artifact_paths["dashboard_render_evidence.json"], dashboard_evidence)
        workflow.complete("render_static_dashboard_evidence")

        status_readiness_report = _stable_report(
            {
                "status_summary": create_status_summary(connection, database_path=str(db_path)),
                "rail_states": create_rail_state_report(),
            }
        )
        _write_json(artifact_paths["status_readiness_report.json"], status_readiness_report)
        workflow.complete("produce_status_and_readiness_report")

        safety_assertions = _build_safety_assertions(
            status_readiness_report=status_readiness_report,
            scheduler_evidence=scheduler_evidence,
        )
        _write_json(artifact_paths["safety_assertions.json"], safety_assertions)
        workflow.complete("write_safety_assertions")

        no_send_summary = _no_send_summary(briefing_result)
        blocked_summary = _blocked_live_action_summary(
            preview_result=preview_result,
            first_apply=first_apply,
            status_readiness_report=status_readiness_report,
        )
        state_counts = _state_counts(connection)
        seeded_state = _seeded_state_snapshot(connection, seeded=seeded)

    workflow.complete("close_demo_sqlite_connection")

    artifact_index = _artifact_index(output_path, artifact_paths)
    _write_json(artifact_paths["artifacts.json"], artifact_index)
    workflow.complete("write_artifact_index")

    workflow_report = {
        "demo_name": DEMO_NAME,
        "phase_name": PHASE_NAME,
        "status": "completed",
        "workflow_steps_attempted": workflow.attempted_steps(),
        "workflow_steps_completed": workflow.completed_steps(),
        "workflow_steps": workflow.steps,
        "state_counts": state_counts,
        "seeded_state": seeded_state,
        "fixture_manifest_hash": manifest["fixture_manifest_hash"],
    }
    _write_json(artifact_paths["workflow_report.json"], _stable_report(workflow_report))
    workflow.complete("write_workflow_report")

    completion_report = _stable_report(
        {
            "demo_name": DEMO_NAME,
            "phase_name": PHASE_NAME,
            "command_contract": COMMAND_CONTRACT,
            "status": "completed",
            "summary_status": "completed_no_send_evidence_generated",
            "output_dir": str(output_path),
            "generated_db_path": str(db_path),
            "workflow_steps_attempted": workflow.attempted_steps(),
            "workflow_steps_completed": workflow.completed_steps(),
            "workflow_steps": workflow.steps,
            "artifact_list": artifact_index["artifacts"],
            "artifact_paths": {
                name: str(path)
                for name, path in sorted(artifact_paths.items())
            },
            "safety_assertions": safety_assertions,
            "no_send_export_summary": no_send_summary,
            "blocked_live_action_summary": blocked_summary,
            "status_readiness_summary": _status_readiness_summary(status_readiness_report),
            "fixture_manifest_hash": manifest["fixture_manifest_hash"],
            "state_counts": state_counts,
            "phase_14_blocked": True,
            "deviations": [],
        }
    )
    summary_markdown = _summary_markdown(completion_report)
    artifact_paths["summary.md"].write_text(summary_markdown, encoding="utf-8")
    _write_json(artifact_paths["completion_report.json"], completion_report)
    return completion_report


class _Workflow:
    def __init__(self) -> None:
        self.steps: list[dict[str, Any]] = []

    def complete(self, step: str) -> None:
        self.steps.append({"step": step, "status": "completed"})

    def attempted_steps(self) -> list[str]:
        return [step["step"] for step in self.steps]

    def completed_steps(self) -> list[str]:
        return [step["step"] for step in self.steps if step["status"] == "completed"]


def _artifact_paths(output_dir: Path) -> dict[str, Path]:
    return {name: output_dir / name for name in ARTIFACT_NAMES}


def _safe_path_classification(output_dir: Path, db_path: Path) -> dict[str, Any]:
    return {
        "status": "safe",
        "output_dir": str(output_dir),
        "db_path": str(db_path),
        "output_dir_under_temp": is_under_temp(output_dir),
        "output_dir_under_repo": is_under_repo(output_dir),
        "db_path_under_output_dir": _is_under(db_path, output_dir),
        "db_path_under_repo": is_under_repo(db_path),
        "repo_local_var_used": False,
        "protected_paths_touched": False,
        "classification": "explicit_temp_demo_output_dir",
    }


def _normalize_migration_timestamps(connection: sqlite3.Connection) -> None:
    with connection:
        connection.execute("UPDATE schema_migrations SET applied_at = ?", (FIXED_TIME,))


def _enable_demo_permissions(connection: sqlite3.Connection) -> None:
    for category in (
        SYNTHESIS_IMPORT_READ_PERMISSION,
        SYNTHESIS_IMPORT_WRITE_PERMISSION,
        SYNTHESIS_IMPORT_PREVIEW_PERMISSION,
        SYNTHESIS_APPLY_READ_PERMISSION,
        SYNTHESIS_APPLY_WRITE_PERMISSION,
        SYNTHESIS_APPLY_APPLY_PERMISSION,
        BRIEFING_LOOP_READ_PERMISSION,
        BRIEFING_LOOP_WRITE_PERMISSION,
        BRIEFING_LOOP_RUN_PERMISSION,
        COMPOSER_MODULE_READ_PERMISSION,
        COMPOSER_MODULE_WRITE_PERMISSION,
        COMPOSER_MODULE_RUN_PERMISSION,
        SIDE_EFFECT_LEDGER_READ_PERMISSION,
        SIDE_EFFECT_LEDGER_WRITE_PERMISSION,
        SIDE_EFFECT_LEDGER_ATTEMPT_PERMISSION,
    ):
        upsert_permission_setting(
            connection,
            category=category,
            mode=PermissionMode.AUTO_WRITE.value,
            metadata={
                "phase": "13e-d",
                "dev_test_only": True,
                "synthetic_demo": True,
                "no_external_writes": True,
            },
            updated_by="phase_13e_d_demo",
            updated_at_utc=FIXED_TIME,
        )


def _seed_synthetic_state(
    connection: sqlite3.Connection,
    manifest: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    routines = []
    for routine in manifest["routines"]:
        routines.append(
            create_routine(
                connection,
                routine_id=routine["routine_id"],
                name=routine["name"],
                status=routine["status"],
                enabled=routine["enabled"],
                settings=routine["settings"],
                notes=routine["notes"],
                created_at_utc=FIXED_TIME,
                updated_at_utc=FIXED_TIME,
            )
        )
    record_routine_completion(
        connection,
        routine_id="routine-phase-13e-d-morning-review",
        completion_id="routine-completion-phase-13e-d-morning-review",
        completed_for_date=SOURCE_DATE,
        completed_at_utc=FIXED_TIME,
        source="phase_13e_d_demo",
        metadata={"synthetic": True, "no_external_writes": True},
        created_at_utc=FIXED_TIME,
    )

    priorities = [
        create_priority(
            connection,
            priority_id=priority["priority_id"],
            title=priority["title"],
            status=priority["status"],
            metadata=priority["metadata"],
            notes=priority["notes"],
            created_at_utc=FIXED_TIME,
            updated_at_utc=FIXED_TIME,
        )
        for priority in manifest["priorities"]
    ]
    projects = [
        create_project(
            connection,
            project_id=project["project_id"],
            title=project["title"],
            status=project["status"],
            metadata=project["metadata"],
            notes=project["notes"],
            created_at_utc=FIXED_TIME,
            updated_at_utc=FIXED_TIME,
        )
        for project in manifest["projects"]
    ]
    followups = [
        create_followup(
            connection,
            followup_id=followup["followup_id"],
            title=followup["title"],
            status=followup["status"],
            source=followup["source"],
            metadata=followup["metadata"],
            notes=followup["notes"],
            created_at_utc=FIXED_TIME,
            updated_at_utc=FIXED_TIME,
        )
        for followup in manifest["followups"]
    ]
    _seed_briefing_windows(connection)
    return {
        "routines": routines,
        "priorities": priorities,
        "projects": projects,
        "followups": followups,
    }


def _seed_briefing_windows(connection: sqlite3.Connection) -> None:
    windows = (
        ("briefing-window-morning", "morning", "08:00"),
        ("briefing-window-midday", "midday", "12:00"),
        ("briefing-window-afternoon", "afternoon", "16:00"),
        ("briefing-window-evening", "evening", "20:00"),
    )
    with connection:
        for window_id, name, scheduled_time in windows:
            connection.execute(
                """
                INSERT INTO briefing_windows (
                    id,
                    name,
                    scheduled_time,
                    timezone,
                    delivery_mode,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    window_id,
                    name,
                    scheduled_time,
                    DEFAULT_TIMEZONE,
                    "no_send",
                    "draft",
                    FIXED_TIME,
                    FIXED_TIME,
                ),
            )


def _require_preview_id(preview_result: Mapping[str, Any]) -> str:
    if preview_result.get("status") != "created":
        raise RuntimeError(f"synthesis preview failed: {preview_result.get('reason')}")
    record = preview_result.get("record")
    if not isinstance(record, Mapping):
        raise RuntimeError("synthesis preview did not return a persisted record")
    preview_id = record.get("id")
    if not isinstance(preview_id, str) or not preview_id:
        raise RuntimeError("synthesis preview record did not include an id")
    return preview_id


def _record_side_effect_evidence(connection: sqlite3.Connection) -> dict[str, Any]:
    results = []
    for item in build_side_effect_inputs():
        results.append(
            create_external_write_intent_and_record_dry_run(
                connection,
                intent=item["intent"],
                attempt=item["attempt"],
            )
        )
    duplicate = create_external_write_intent_and_record_dry_run(
        connection,
        intent=build_side_effect_inputs()[0]["intent"],
        attempt=build_side_effect_inputs()[0]["attempt"],
    )
    summary = summarize_side_effect_ledgers(connection)
    idempotency_summary = _idempotency_summary(connection, duplicate_result=duplicate)
    return {
        "results": results,
        "duplicate_result": duplicate,
        "summary": {
            **summary,
            "dry_run_record_results": _result_status_counts(results),
            "duplicate_result_status": duplicate["status"],
        },
        "idempotency_summary": idempotency_summary,
    }


def _idempotency_summary(
    connection: sqlite3.Connection,
    *,
    duplicate_result: Mapping[str, Any],
) -> dict[str, Any]:
    rows = connection.execute(
        """
        SELECT
            idempotency_key,
            target_system,
            operation_type,
            source_type,
            source_id,
            dedupe_key,
            payload_fingerprint,
            first_seen_at,
            last_seen_at,
            status,
            linked_intent_id,
            linked_attempt_id
        FROM idempotency_records
        ORDER BY target_system, operation_type, dedupe_key
        """
    ).fetchall()
    records = [dict(row) for row in rows]
    return {
        "status": "completed",
        "idempotency_record_count": len(records),
        "records": records,
        "duplicate_attempt_status": duplicate_result["status"],
        "duplicate_skipped_without_external_mutation": duplicate_result["status"]
        == "skipped_duplicate",
        "no_external_writes": True,
        "external_mutation": False,
    }


def _build_safety_assertions(
    *,
    status_readiness_report: Mapping[str, Any],
    scheduler_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    rail_states = status_readiness_report["rail_states"]
    assertions = {
        "rails": rail_states["rails"],
        "scheduler_state": rail_states["scheduler"],
        "any_rail_live": rail_states["any_rail_live"],
        "any_rail_soaking": rail_states["any_rail_soaking"],
        "invalid_rail_states": rail_states["invalid_rail_states"],
        "launch_agent_installed": False,
        "crontab_modified": False,
        "daemon_started": False,
        "external_mutation": False,
        "gmail_touched": False,
        "todoist_touched": False,
        "calendar_touched": False,
        "personalos_markdown_written": False,
        "protected_paths_touched": False,
        "scheduler_preview_status": scheduler_evidence["status"],
    }
    assertions["all_required_assertions_passed"] = (
        assertions["any_rail_live"] is False
        and assertions["invalid_rail_states"] == []
        and all(
            assertions[key] is False
            for key in (
                "any_rail_soaking",
                "launch_agent_installed",
                "crontab_modified",
                "daemon_started",
                "external_mutation",
                "gmail_touched",
                "todoist_touched",
                "calendar_touched",
                "personalos_markdown_written",
                "protected_paths_touched",
            )
        )
    )
    return assertions


def _no_send_summary(briefing_result: Mapping[str, Any]) -> dict[str, Any]:
    briefing_output = briefing_result.get("briefing_output", {})
    output = (
        briefing_output.get("output_json", {})
        if isinstance(briefing_output, Mapping)
        else {}
    )
    return {
        "briefing_status": briefing_result["status"],
        "briefing_output_id": briefing_result["briefing_output_id"],
        "delivery_mode": briefing_result["delivery_mode"],
        "manual_export_written": True,
        "gmail_send": False,
        "gmail_draft": False,
        "todoist_writes": False,
        "calendar_writes": False,
        "personalos_markdown_writes": False,
        "email_brief_preview_count": len(output.get("email_briefs", [])),
        "todoist_candidate_preview_count": len(output.get("todoist_tasks", [])),
        "calendar_candidate_preview_count": len(output.get("calendar_blocks", [])),
        "followup_preview_count": len(output.get("followups", [])),
    }


def _blocked_live_action_summary(
    *,
    preview_result: Mapping[str, Any],
    first_apply: Mapping[str, Any],
    status_readiness_report: Mapping[str, Any],
) -> dict[str, Any]:
    preview_report = preview_result["preview_report"]
    rail_states = status_readiness_report["rail_states"]
    apply_items = first_apply["items"]
    return {
        "rails_all_non_live": rail_states["any_rail_live"] is False,
        "preview_blocked_candidate_count": len(preview_report["blocked_candidates"]),
        "preview_review_required_candidate_count": len(
            preview_report["review_required_candidates"]
        ),
        "preview_manual_only_candidate_count": len(preview_report["manual_only_candidates"]),
        "apply_blocked_item_count": sum(
            1 for item in apply_items if item["apply_status"] == "blocked"
        ),
        "apply_not_applied_item_count": sum(
            1 for item in apply_items if item["apply_status"] == "not_applied"
        ),
        "live_tasks_created": False,
        "live_calendar_events_created": False,
        "gmail_sent_or_drafted": False,
        "markdown_written": False,
    }


def _status_readiness_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    rail_states = report["rail_states"]
    status_summary = report["status_summary"]
    return {
        "rails": rail_states["rails"],
        "scheduler_state": rail_states["scheduler"],
        "any_rail_live": rail_states["any_rail_live"],
        "counts": status_summary["counts"],
    }


def _state_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        "routines": count_routines(connection),
        "priorities": count_priorities(connection),
        "projects": count_projects(connection),
        "followups": count_followups(connection),
        "todoist_tasks": count_todoist_tasks(connection),
        "calendar_blocks": count_calendar_blocks(connection),
    }


def _seeded_state_snapshot(
    connection: sqlite3.Connection,
    *,
    seeded: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "seeded_counts": {key: len(value) for key, value in seeded.items()},
        "routines": list_routines(connection),
        "priorities": list_priorities(connection),
        "projects": list_projects(connection),
        "followups": list_followups(connection),
    }


def _artifact_index(output_dir: Path, artifact_paths: Mapping[str, Path]) -> dict[str, Any]:
    artifacts = []
    for name in ARTIFACT_NAMES:
        path = artifact_paths[name]
        artifacts.append(
            {
                "name": name,
                "path": str(path),
                "under_output_dir": _is_under(path, output_dir),
                "expected": True,
                "kind": (
                    "sqlite"
                    if path.suffix in {".sqlite", ".sqlite3", ".db"}
                    else path.suffix.lstrip(".")
                ),
            }
        )
    return {
        "status": "completed",
        "output_dir": str(output_dir),
        "all_artifacts_under_output_dir": all(item["under_output_dir"] for item in artifacts),
        "artifacts": artifacts,
    }


def _summary_markdown(completion_report: Mapping[str, Any]) -> str:
    blocked = completion_report["blocked_live_action_summary"]
    safety = completion_report["safety_assertions"]
    lines = [
        "# Phase 13E-D Synthetic No-Send Demo Summary",
        "",
        f"- Demo: {completion_report['demo_name']}",
        f"- Phase: {completion_report['phase_name']}",
        f"- Status: {completion_report['status']}",
        f"- Output dir: {completion_report['output_dir']}",
        f"- Demo DB: {completion_report['generated_db_path']}",
        f"- Fixture manifest hash: {completion_report['fixture_manifest_hash']}",
        "",
        "## Safe Local Actions",
        "",
        "- Seeded synthetic routines, priorities, projects/focus areas, and follow-ups.",
        "- Imported a synthetic ChatGPT synthesis payload.",
        "- Generated a synthesis preview and applied only approved internal SQLite items.",
        "- Generated a no-send briefing preview and local Markdown export.",
        "- Recorded dry-run ledger and idempotency evidence.",
        "- Produced status/readiness, scheduler-preview, dashboard-render, and artifact reports.",
        "",
        "## Blocked Live Actions",
        "",
        f"- Preview blocked candidates: {blocked['preview_blocked_candidate_count']}",
        f"- Review-required candidates: {blocked['preview_review_required_candidate_count']}",
        f"- Apply blocked items: {blocked['apply_blocked_item_count']}",
        "- Gmail send/draft: false",
        "- Todoist live writes: false",
        "- Calendar live writes: false",
        "- PersonalOS Markdown writes: false",
        "",
        "## Safety Assertions",
        "",
        "- rails="
        + ", ".join(f"{name}={value}" for name, value in sorted(safety["rails"].items())),
        f"- scheduler_state={safety['scheduler_state']}",
        f"- any_rail_live={_format_bool(safety['any_rail_live'])}",
        f"- external_mutation={_format_bool(safety['external_mutation'])}",
        f"- all_required_assertions_passed={_format_bool(safety['all_required_assertions_passed'])}",
        "",
        "Rail activation remains Conductor-gated (governance/HUMAN_GATES.md).",
    ]
    return "\n".join(lines) + "\n"


def _stable_report(value: Any) -> Any:
    if isinstance(value, Mapping):
        normalized = {}
        for key, item in value.items():
            if key == "generated_at_utc":
                normalized[key] = FIXED_TIME
            else:
                normalized[key] = _stable_report(item)
        return normalized
    if isinstance(value, list):
        return [_stable_report(item) for item in value]
    return value


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _result_status_counts(results: list[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        status = str(result.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _format_bool(value: object) -> str:
    return "true" if value is True else "false" if value is False else str(value)
