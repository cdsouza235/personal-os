"""Operator CLI for safe no-send Personal OS workflows."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections.abc import Iterable, Mapping, Sequence
from contextlib import closing
from pathlib import Path
from typing import Any
from urllib.parse import quote

from personalos.briefings import generate_no_send_briefing_preview, read_briefing_output
from personalos.config import DEFAULT_TIMEZONE
from personalos.dashboard import render_today_view_html_from_connection
from personalos.path_safety import (
    is_under_repo,
    is_under_temp,
    validate_existing_input_file_path,
    validate_existing_sqlite_path,
    validate_output_file_path,
)
from personalos.side_effects import (
    create_external_write_intent_and_record_dry_run,
    summarize_side_effect_ledgers,
)
from personalos.scheduler import (
    BRIEFING_WINDOWS,
    SAFE_NO_SEND_SEED_PROFILE,
    SIMULATED_JOB_TYPES,
    list_scheduler_jobs,
    preview_scheduler_jobs,
    run_scheduler_job_simulated,
    seed_dev_scheduler_jobs,
)
from personalos.synthesis_apply import (
    SynthesisApplyValidationError,
    apply_synthesis_import_preview,
    stable_approval_source_hash,
)
from personalos.status import create_rail_state_report, create_status_summary
from personalos.synthesis_import import (
    ALLOWED_SOURCE_TYPES,
    REPORT_SAFETY_FLAGS,
    SynthesisImportValidationError,
    create_synthesis_import_preview_record,
)
from personalos.today import create_today_view_summary


class CliError(RuntimeError):
    """Raised for expected fail-closed CLI errors."""


SAFE_LOCAL_WORKFLOW_SPECS: tuple[dict[str, Any], ...] = (
    {
        "name": "ChatGPT synthesis import preview",
        "safe_local_action": "Preview ChatGPT synthesis import",
        "command": (
            "personalos synthesis preview --db <safe_db> "
            "--input-file <safe_json_or_markdown> --source-type chatgpt_synthesis"
        ),
        "mode": "inert / no-send / preview",
        "local_effect": "valid previews persist one local SQLite preview record",
        "output": "stdout report with preview_id and candidate counts",
    },
    {
        "name": "approved synthesis apply to local SQLite only",
        "safe_local_action": "Apply approved synthesis preview to local SQLite state only",
        "command": (
            "personalos synthesis apply --db <safe_db> "
            "--preview-id <preview_id> --approval-file <safe_approval_json>"
        ),
        "mode": "approved local apply / no-send",
        "local_effect": (
            "approved priorities/projects/followups may be inserted into local SQLite only"
        ),
        "output": "stdout report with apply_run_id and item counts",
    },
    {
        "name": "no-send briefing preview/export",
        "safe_local_action": "Generate no-send briefing preview",
        "command": (
            "personalos briefing preview --db <safe_db> --date <YYYY-MM-DD> --window <window>; "
            "personalos briefing export --db <safe_db> --briefing-output-id <id> "
            "--output-file <safe_output_file>"
        ),
        "mode": "inert / no-send / fake Composer",
        "local_effect": (
            "preview writes local daily_plan/briefing/composer/model rows; "
            "export reads DB and writes only the explicit output file"
        ),
        "output": "stdout report, optional explicit Markdown export file",
    },
    {
        "name": "Today View/status preview",
        "safe_local_action": "Inspect local status",
        "command": (
            "personalos today --db <safe_db> --date <YYYY-MM-DD>; "
            "personalos status --db <safe_db>"
        ),
        "mode": "inert / report-only",
        "local_effect": "read explicit safe local SQLite only",
        "output": "stdout human report or stdout JSON",
    },
    {
        "name": "side-effect/idempotency ledger inspection",
        "safe_local_action": "Inspect side-effect/idempotency ledgers",
        "command": "personalos side-effects summary --db <safe_db> [--json]",
        "mode": "inert / report-only / ledger",
        "local_effect": "read local dev/test ledger counts only",
        "output": "stdout ledger summary",
    },
    {
        "name": "simulated scheduler preview",
        "safe_local_action": "Preview simulated scheduler jobs",
        "command": (
            "personalos scheduler jobs --db <safe_db>; "
            "personalos scheduler preview --db <safe_db> --date <YYYY-MM-DD>"
        ),
        "mode": "inert / no-send / simulated scheduler",
        "local_effect": "read local scheduler job records only; no scheduler activation",
        "output": "stdout report with simulated job counts",
    },
    {
        "name": "synthetic no-send end-to-end demo",
        "safe_local_action": "Generate Phase 13E-D synthetic no-send evidence bundle",
        "command": "personalos demo no-send-e2e --output-dir <safe_output_dir> --json",
        "mode": "inert / no-send / synthetic fixture demo",
        "local_effect": (
            "writes fixture artifacts and one demo SQLite DB only under the explicit "
            "safe output directory"
        ),
        "output": "stdout completion JSON plus evidence bundle files",
    },
)


class PersonalOSArgumentParser(argparse.ArgumentParser):
    """argparse parser with no-send specific operator error text."""

    def error(self, message: str) -> None:
        if "--db" in message and "required" in message:
            message = (
                "Cannot run this safe local no-send workflow: --db is required. "
                "No external writes were attempted. "
                "Next: rerun with --db <path-to-local-test-db>."
            )
        elif "--input-file" in message and "required" in message:
            message = (
                "Cannot run this safe local no-send workflow: --input-file is required. "
                "No external writes were attempted. "
                "Next: rerun with an explicit temp/dev input file."
            )
        elif "--output-file" in message and "required" in message:
            message = (
                "Cannot export this no-send workflow output: --output-file is required. "
                "No external writes were attempted. "
                "Next: rerun with --output-file <explicit-safe-output-path>."
            )
        elif "--approval-file" in message and "required" in message:
            message = (
                "Cannot apply synthesis: --approval-file is required. "
                "No external writes were attempted. "
                "Next: rerun with an explicit temp/dev approval JSON file."
            )
        super().error(message)


def build_parser() -> argparse.ArgumentParser:
    parser = PersonalOSArgumentParser(
        prog="personalos",
        description=(
            "Safe local operator CLI for inert/no-send Personal OS workflows. "
            "Rail activation is a Conductor-gated packet (governance/HUMAN_GATES.md)."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    workflows_parser = subparsers.add_parser(
        "workflows",
        help="List available inert/no-send workflows and blocked live actions.",
        description=(
            "List safe local report-only, preview, export, approved local apply, "
            "ledger, and simulated scheduler workflows."
        ),
    )
    _add_json_arg(workflows_parser)
    workflows_parser.set_defaults(func=_command_workflows)

    demo_parser = subparsers.add_parser(
        "demo",
        help="Synthetic local no-send demo workflows.",
    )
    demo_subparsers = demo_parser.add_subparsers(dest="demo_command", required=True)
    demo_no_send_parser = demo_subparsers.add_parser(
        "no-send-e2e",
        help="Run the Phase 13E-D synthetic end-to-end no-send evidence demo.",
        description=(
            "Run the deterministic Phase 13E-D synthetic end-to-end no-send demo. "
            "Artifacts and the demo SQLite DB are written only under --output-dir. "
            "Live rails, credentials, production DB, schedulers, OpenClaw, and "
            "external writes remain blocked."
        ),
    )
    demo_no_send_parser.add_argument("--output-dir", required=True)
    _add_json_arg(demo_no_send_parser)
    demo_no_send_parser.set_defaults(func=_command_demo_no_send_e2e)

    status_parser = subparsers.add_parser(
        "status",
        help="Render inert local status and rail states from an explicit safe DB.",
    )
    _add_db_arg(status_parser)
    _add_json_arg(status_parser)
    status_parser.set_defaults(func=_command_status)

    today_parser = subparsers.add_parser(
        "today",
        help="Preview the read-only Today View from an explicit safe DB.",
    )
    _add_db_arg(today_parser)
    _add_date_timezone_args(today_parser)
    _add_json_arg(today_parser)
    today_parser.set_defaults(func=_command_today)


    briefing_parser = subparsers.add_parser("briefing", help="No-send briefing workflows.")
    briefing_subparsers = briefing_parser.add_subparsers(dest="briefing_command", required=True)

    briefing_preview_parser = briefing_subparsers.add_parser(
        "preview",
        help="Generate a no-send briefing preview through the fake Composer path.",
    )
    _add_db_arg(briefing_preview_parser)
    _add_date_timezone_args(briefing_preview_parser)
    briefing_preview_parser.add_argument(
        "--window",
        required=True,
        choices=("morning", "midday", "afternoon", "evening"),
    )
    _add_json_arg(briefing_preview_parser)
    briefing_preview_parser.set_defaults(func=_command_briefing_preview)

    briefing_export_parser = briefing_subparsers.add_parser(
        "export",
        help="Export an existing no-send briefing output to an explicit safe file path.",
    )
    _add_db_arg(briefing_export_parser)
    briefing_export_parser.add_argument("--briefing-output-id", required=True)
    briefing_export_parser.add_argument("--output-file", required=True)
    _add_json_arg(briefing_export_parser)
    briefing_export_parser.set_defaults(func=_command_briefing_export)

    synthesis_parser = subparsers.add_parser(
        "synthesis",
        help="ChatGPT synthesis preview and approved local SQLite apply workflows.",
    )
    synthesis_subparsers = synthesis_parser.add_subparsers(
        dest="synthesis_command",
        required=True,
    )

    synthesis_preview_parser = synthesis_subparsers.add_parser(
        "preview",
        help="Validate and persist one ChatGPT synthesis preview record; no external writes.",
    )
    _add_db_arg(synthesis_preview_parser)
    synthesis_preview_parser.add_argument("--input-file", required=True)
    synthesis_preview_parser.add_argument(
        "--source-type",
        required=True,
        choices=ALLOWED_SOURCE_TYPES,
    )
    _add_json_arg(synthesis_preview_parser)
    synthesis_preview_parser.set_defaults(func=_command_synthesis_preview)

    synthesis_apply_parser = synthesis_subparsers.add_parser(
        "apply",
        help="Apply approved synthesis candidates to local SQLite only; no external writes.",
    )
    _add_db_arg(synthesis_apply_parser)
    synthesis_apply_parser.add_argument("--preview-id", required=True)
    synthesis_apply_parser.add_argument("--approval-file", required=True)
    _add_json_arg(synthesis_apply_parser)
    synthesis_apply_parser.set_defaults(func=_command_synthesis_apply)

    side_effects_parser = subparsers.add_parser(
        "side-effects",
        help="Side-effect/idempotency ledger summaries and no-send dry-run records.",
    )
    side_effects_subparsers = side_effects_parser.add_subparsers(
        dest="side_effects_command",
        required=True,
    )

    side_effects_summary_parser = side_effects_subparsers.add_parser(
        "summary",
        help="Inspect side-effect and idempotency ledger counts without mutation.",
    )
    _add_db_arg(side_effects_summary_parser)
    _add_json_arg(side_effects_summary_parser)
    side_effects_summary_parser.set_defaults(func=_command_side_effects_summary)

    side_effects_record_parser = side_effects_subparsers.add_parser(
        "record-dry-run",
        help="Record one local dry-run ledger intent/attempt from a safe JSON file.",
    )
    _add_db_arg(side_effects_record_parser)
    side_effects_record_parser.add_argument("--input-file", required=True)
    _add_json_arg(side_effects_record_parser)
    side_effects_record_parser.set_defaults(func=_command_side_effects_record_dry_run)

    dashboard_parser = subparsers.add_parser(
        "dashboard",
        help="Static report-only dashboard exports.",
    )
    dashboard_subparsers = dashboard_parser.add_subparsers(
        dest="dashboard_command",
        required=True,
    )

    dashboard_render_parser = dashboard_subparsers.add_parser(
        "render",
        help="Render static read-only Today View HTML to an explicit safe file path.",
    )
    _add_db_arg(dashboard_render_parser)
    _add_date_timezone_args(dashboard_render_parser)
    dashboard_render_parser.add_argument("--output-file", required=True)
    _add_json_arg(dashboard_render_parser)
    dashboard_render_parser.set_defaults(func=_command_dashboard_render)

    scheduler_parser = subparsers.add_parser(
        "scheduler",
        help="No-send scheduler job records and foreground-only simulations.",
        description=(
            "No-send scheduler job records and foreground-only simulations. These "
            "commands never activate a scheduler, LaunchAgent, crontab, daemon, "
            "background loop, or production runtime."
        ),
    )
    scheduler_subparsers = scheduler_parser.add_subparsers(
        dest="scheduler_command",
        required=True,
    )

    scheduler_jobs_parser = scheduler_subparsers.add_parser(
        "jobs",
        help="List configured no-send scheduler job records without activating a scheduler.",
        description=(
            "List configured no-send scheduler job records from an explicit safe DB. "
            "This is inert/report-only and does not activate a scheduler, LaunchAgent, "
            "crontab, daemon, background loop, or production runtime."
        ),
    )
    _add_db_arg(scheduler_jobs_parser)
    _add_json_arg(scheduler_jobs_parser)
    scheduler_jobs_parser.set_defaults(func=_command_scheduler_jobs)

    scheduler_preview_parser = scheduler_subparsers.add_parser(
        "preview",
        help="Preview due dev/test scheduler jobs without running or activating them.",
        description=(
            "Preview due dev/test scheduler jobs without running them. This is a "
            "simulated no-send workflow and does not activate a scheduler, LaunchAgent, "
            "crontab, daemon, background loop, or production runtime."
        ),
    )
    _add_db_arg(scheduler_preview_parser)
    _add_date_timezone_args(scheduler_preview_parser)
    _add_json_arg(scheduler_preview_parser)
    scheduler_preview_parser.set_defaults(func=_command_scheduler_preview)

    scheduler_run_parser = scheduler_subparsers.add_parser(
        "run",
        help="Run one scheduler job as a foreground no-send simulation only.",
        description=(
            "Run one scheduler job as a foreground no-send simulation only. This never "
            "installs or activates a scheduler, LaunchAgent, crontab, daemon, background "
            "loop, or production runtime."
        ),
    )
    _add_db_arg(scheduler_run_parser)
    scheduler_run_parser.add_argument("--scheduler-job-id")
    scheduler_run_parser.add_argument("--job-type", choices=SIMULATED_JOB_TYPES)
    scheduler_run_parser.add_argument("--date", help="Source date in YYYY-MM-DD format.")
    scheduler_run_parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    scheduler_run_parser.add_argument("--window", choices=BRIEFING_WINDOWS)
    scheduler_run_parser.add_argument("--scheduled-for")
    scheduler_run_parser.add_argument("--output-file")
    _add_json_arg(scheduler_run_parser)
    scheduler_run_parser.set_defaults(func=_command_scheduler_run)

    scheduler_seed_parser = scheduler_subparsers.add_parser(
        "seed-dev",
        help="Insert safe dev/test no-send scheduler job records; no scheduler activation.",
        description=(
            "Insert safe dev/test no-send scheduler job records into an explicit safe DB. "
            "This does not activate a scheduler, LaunchAgent, crontab, daemon, background "
            "loop, or production runtime."
        ),
    )
    _add_db_arg(scheduler_seed_parser)
    scheduler_seed_parser.add_argument(
        "--profile",
        required=True,
        choices=(SAFE_NO_SEND_SEED_PROFILE,),
    )
    scheduler_seed_parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    _add_json_arg(scheduler_seed_parser)
    scheduler_seed_parser.set_defaults(func=_command_scheduler_seed_dev)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.func(args)
    except CliError as error:
        print(f"error: {_format_cli_error(error)}", file=sys.stderr)
        return 1
    except (OSError, PermissionError, sqlite3.Error, ValueError) as error:
        print(f"error: {_format_cli_error(error)}", file=sys.stderr)
        return 1
    return result


def _command_workflows(args: argparse.Namespace) -> int:
    report = _with_workflow_context(
        {
            "command": "workflows",
            "status": "completed",
            "database_write": False,
            "external_mutation": False,
            "file_write": False,
            "no_external_writes": True,
            "no_credentials_loaded": True,
            "safe_local_workflows": list(SAFE_LOCAL_WORKFLOW_SPECS),
            "rail_states": create_rail_state_report(),
        },
        workflow_name="No-send workflow catalog",
        workflow_mode="inert / no-send / report-only",
        database_access="not_applicable_no_db_opened",
        local_sqlite_read=False,
        local_sqlite_changed=False,
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Choose one listed command and run it against an explicit safe DB if needed.",
            "Use --json when pasting output back to ChatGPT for audit.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0


def _command_demo_no_send_e2e(args: argparse.Namespace) -> int:
    from personalos.demo.no_send_e2e import run_no_send_e2e_demo

    report = run_no_send_e2e_demo(args.output_dir)
    _emit_report(report, json_output=args.json)
    return 0


def _command_status(args: argparse.Namespace) -> int:
    with closing(_connect_read_only(args.db)) as connection:
        summary = create_status_summary(connection, database_path=args.db)
    report = _with_workflow_context(
        {
            "command": "status",
            "status": "completed",
            "database_write": False,
            "external_mutation": False,
            "no_external_writes": True,
            "summary": summary,
            "rail_states": summary["rail_states"],
        },
        workflow_name="Local status preview",
        workflow_mode="inert / no-send / report-only",
        database_path=args.db,
        database_access="read_only_status",
        local_sqlite_read=True,
        local_sqlite_changed=False,
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Review rail states and counts.",
            "Run personalos workflows to discover other no-send commands.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0


def _command_today(args: argparse.Namespace) -> int:
    with closing(_connect_read_only(args.db)) as connection:
        summary = create_today_view_summary(
            connection,
            source_date=args.date,
            timezone=args.timezone,
        )
    report = _with_workflow_context(
        {
            "command": "today",
            "status": "completed",
            "database_write": False,
            "external_mutation": False,
            "no_external_writes": True,
            "summary": summary,
        },
        workflow_name="Today View/status preview",
        workflow_mode="inert / no-send / report-only",
        database_path=args.db,
        database_access="read_only_today_view",
        local_sqlite_read=True,
        local_sqlite_changed=False,
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Review Today View preview.",
            "Use personalos dashboard render for an explicit static HTML export.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0




























































































def _has_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _command_briefing_preview(args: argparse.Namespace) -> int:
    with closing(_connect_read_write(args.db)) as connection:
        result = generate_no_send_briefing_preview(
            connection,
            source_date=args.date,
            timezone=args.timezone,
            briefing_window_name=args.window,
            delivery_mode="no_send",
        )
    report = _with_workflow_context(
        {"command": "briefing preview", **result},
        workflow_name="No-send briefing preview",
        workflow_mode="inert / no-send / fake Composer",
        database_path=args.db,
        database_access="read_write_local_preview",
        local_sqlite_read=True,
        local_sqlite_changed=bool(result.get("database_write")),
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Review the generated preview output.",
            (
                "Export with personalos briefing export only if an explicit safe output path "
                "is appropriate."
            ),
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0 if result.get("status") == "generated" else 1


def _command_briefing_export(args: argparse.Namespace) -> int:
    output_path = validate_output_file_path(
        args.output_file,
        path_label="operator output_file",
    )
    with closing(_connect_read_only(args.db)) as connection:
        briefing_output = read_briefing_output(
            connection,
            briefing_output_id=args.briefing_output_id,
        )
    if briefing_output is None:
        raise CliError(f"briefing output not found: {args.briefing_output_id}")

    output_path.write_text(briefing_output["manual_export_markdown"], encoding="utf-8")
    completion_report = briefing_output.get("completion_report_json")
    safety_flags = _safety_flags_from_report(completion_report)
    report = _with_workflow_context(
        {
            "command": "briefing export",
            "status": "exported",
            "briefing_output_id": briefing_output["id"],
            "output_file": str(output_path),
            "file_write": True,
            "database_write": False,
            "external_mutation": False,
            **safety_flags,
        },
        workflow_name="No-send briefing export",
        workflow_mode="inert / no-send / explicit export",
        database_path=args.db,
        database_access="read_only_briefing_export",
        local_sqlite_read=True,
        local_sqlite_changed=False,
        output_kind="file",
        output_file=str(output_path),
        safe_next_actions=(
            "Review the exported Markdown file.",
            "Paste the completion report back to ChatGPT for audit if needed.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0


def _command_synthesis_preview(args: argparse.Namespace) -> int:
    input_path = validate_existing_input_file_path(
        args.input_file,
        path_label="operator input_file",
    )
    raw_input = input_path.read_text(encoding="utf-8")
    raw_input = _merge_synthesis_source_type(raw_input, source_type=args.source_type)
    try:
        with closing(_connect_read_write(args.db)) as connection:
            result = create_synthesis_import_preview_record(connection, raw_input)
    except SynthesisImportValidationError as error:
        result = _synthesis_rejected_result(reason=str(error), source_type=args.source_type)
    report = _with_workflow_context(
        {"command": "synthesis preview", **result},
        workflow_name="ChatGPT synthesis preview",
        workflow_mode="inert / no-send / preview",
        database_path=args.db,
        database_access="read_write_local_preview",
        local_sqlite_read=True,
        local_sqlite_changed=bool(result.get("database_write")),
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Review preview candidate changes.",
            "Apply approved synthesis to local SQLite only if appropriate.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0 if result.get("status") == "created" else 1


def _command_synthesis_apply(args: argparse.Namespace) -> int:
    approval_path = validate_existing_input_file_path(
        args.approval_file,
        path_label="operator approval_file",
    )
    approval_bytes = approval_path.read_bytes()
    try:
        approval = _loads_json_object(approval_bytes)
        with closing(_connect_read_write(args.db)) as connection:
            result = apply_synthesis_import_preview(
                connection,
                preview_id=args.preview_id,
                approval=approval,
                approval_source_type="json_file",
                approval_source_hash=stable_approval_source_hash(approval_bytes),
            )
    except SynthesisApplyValidationError as error:
        raise CliError(str(error)) from error
    report = _with_workflow_context(
        {"command": "synthesis apply", **result},
        workflow_name="Approved synthesis apply",
        workflow_mode="approved local apply / no-send",
        database_path=args.db,
        database_access="read_write_local_apply",
        local_sqlite_read=True,
        local_sqlite_changed=bool(result.get("database_write")),
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Review apply run and item counts.",
            "Inspect status or Today View from the same safe local DB.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0 if result.get("status") in {"completed", "partially_completed", "no_op"} else 1


def _command_side_effects_summary(args: argparse.Namespace) -> int:
    with closing(_connect_read_only(args.db)) as connection:
        summary = summarize_side_effect_ledgers(connection)
    report = _with_workflow_context(
        {
            "command": "side-effects summary",
            "status": "completed",
            "database_write": False,
            "external_mutation": False,
            "summary": summary,
            **summary["safety_flags"],
        },
        workflow_name="Side-effect/idempotency ledger inspection",
        workflow_mode="inert / no-send / report-only",
        database_path=args.db,
        database_access="read_only_ledger_summary",
        local_sqlite_read=True,
        local_sqlite_changed=False,
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Review ledger counts and duplicate evidence.",
            "Use record-dry-run only for local dev/test ledger evidence.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0


def _command_side_effects_record_dry_run(args: argparse.Namespace) -> int:
    input_path = validate_existing_input_file_path(
        args.input_file,
        path_label="operator input_file",
    )
    payload = _load_json_object(input_path)
    intent = payload.get("intent")
    if not isinstance(intent, Mapping):
        raise CliError("side-effects input JSON must include an object at key: intent")
    attempt = payload.get("attempt")
    if attempt is not None and not isinstance(attempt, Mapping):
        raise CliError("side-effects input JSON key attempt must be an object when provided")

    with closing(_connect_read_write(args.db)) as connection:
        result = create_external_write_intent_and_record_dry_run(
            connection,
            intent=intent,
            attempt=attempt,
        )
    report = _with_workflow_context(
        {"command": "side-effects record-dry-run", **result},
        workflow_name="Side-effect dry-run ledger record",
        workflow_mode="inert / no-send / dry-run ledger",
        database_path=args.db,
        database_access="read_write_local_ledger_dry_run",
        local_sqlite_read=True,
        local_sqlite_changed=bool(result.get("database_write")),
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Review ledger intent, attempt, and idempotency result.",
            "Inspect side-effects summary from the same safe local DB.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0 if result.get("status") in {"recorded", "skipped_duplicate"} else 1


def _command_dashboard_render(args: argparse.Namespace) -> int:
    output_path = validate_output_file_path(
        args.output_file,
        path_label="operator output_file",
    )
    with closing(_connect_read_only(args.db)) as connection:
        html = render_today_view_html_from_connection(
            connection,
            source_date=args.date,
            timezone=args.timezone,
            include_synthesis_import_form=False,
        )
    output_path.write_text(html, encoding="utf-8")
    report = _with_workflow_context(
        {
            "command": "dashboard render",
            "status": "rendered",
            "output_file": str(output_path),
            "file_write": True,
            "database_write": False,
            "external_mutation": False,
            "no_external_writes": True,
            "no_send_mode": True,
            "static_html_only": True,
        },
        workflow_name="Static Today View dashboard export",
        workflow_mode="inert / no-send / static export",
        database_path=args.db,
        database_access="read_only_dashboard_render",
        local_sqlite_read=True,
        local_sqlite_changed=False,
        output_kind="file",
        output_file=str(output_path),
        safe_next_actions=(
            "Open or review the static HTML file locally.",
            "Paste the completion report back to ChatGPT for audit if needed.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0


def _command_scheduler_jobs(args: argparse.Namespace) -> int:
    with closing(_connect_read_only(args.db)) as connection:
        jobs = list_scheduler_jobs(connection)
    report = _with_workflow_context(
        {
            "command": "scheduler jobs",
            "status": "completed",
            "database_write": False,
            "external_mutation": False,
            "scheduler_activation": False,
            "launch_agent_installed": False,
            "no_external_writes": True,
            "no_send_mode": True,
            "scheduler_job_count": len(jobs),
            "scheduler_jobs": jobs,
        },
        workflow_name="No-send scheduler job inspection",
        workflow_mode="inert / no-send / simulated scheduler",
        database_path=args.db,
        database_access="read_only_scheduler_jobs",
        local_sqlite_read=True,
        local_sqlite_changed=False,
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Review configured simulated jobs.",
            "Run scheduler preview to see due simulations without activation.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0


def _command_scheduler_preview(args: argparse.Namespace) -> int:
    with closing(_connect_read_only(args.db)) as connection:
        result = preview_scheduler_jobs(
            connection,
            source_date=args.date,
            timezone=args.timezone,
        )
    report = _with_workflow_context(
        {"command": "scheduler preview", **result},
        workflow_name="Simulated scheduler preview",
        workflow_mode="inert / no-send / simulated scheduler",
        database_path=args.db,
        database_access="read_only_scheduler_preview",
        local_sqlite_read=True,
        local_sqlite_changed=False,
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Review due simulated jobs.",
            "Run one foreground simulation only if local DB effects are appropriate.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0


def _command_scheduler_run(args: argparse.Namespace) -> int:
    if args.scheduler_job_id is None and args.job_type is None:
        raise CliError("scheduler run requires --job-type or --scheduler-job-id")
    with closing(_connect_read_write(args.db)) as connection:
        result = run_scheduler_job_simulated(
            connection,
            job_type=args.job_type,
            scheduler_job_id=args.scheduler_job_id,
            source_date=args.date,
            timezone=args.timezone,
            briefing_window_name=args.window,
            scheduled_for=args.scheduled_for,
            output_file=args.output_file,
        )
    report = _with_workflow_context(
        {"command": "scheduler run", **result},
        workflow_name="Foreground scheduler simulation",
        workflow_mode="inert / no-send / foreground simulation",
        database_path=args.db,
        database_access="read_write_local_scheduler_run",
        local_sqlite_read=True,
        local_sqlite_changed=bool(result.get("database_write")),
        output_kind="stdout_json" if args.json else "stdout_human",
        output_file=args.output_file,
        safe_next_actions=(
            "Review scheduler run completion report.",
            "Inspect scheduler jobs or status from the same safe local DB.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0 if result.get("status") == "completed" else 1


def _command_scheduler_seed_dev(args: argparse.Namespace) -> int:
    with closing(_connect_read_write(args.db)) as connection:
        result = seed_dev_scheduler_jobs(
            connection,
            profile=args.profile,
            timezone=args.timezone,
        )
    report = _with_workflow_context(
        {"command": "scheduler seed-dev", **result},
        workflow_name="Seed no-send scheduler dev jobs",
        workflow_mode="inert / no-send / dev-test seed",
        database_path=args.db,
        database_access="read_write_local_scheduler_seed",
        local_sqlite_read=True,
        local_sqlite_changed=bool(result.get("database_write")),
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Review seeded simulated jobs.",
            "Run scheduler preview; no LaunchAgent/crontab/daemon is activated.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0


def _with_workflow_context(
    report: dict[str, Any],
    *,
    workflow_name: str,
    workflow_mode: str,
    database_path: str | Path | None = None,
    database_access: str,
    local_sqlite_read: bool,
    local_sqlite_changed: bool | None,
    output_kind: str,
    output_file: str | Path | None = None,
    safe_next_actions: Sequence[str] = (),
) -> dict[str, Any]:
    database_target = _database_target_report(
        database_path,
        database_access=database_access,
    )
    enriched = {
        **report,
        "workflow_name": workflow_name,
        "workflow_mode": workflow_mode,
        "database_target": database_target,
        "local_sqlite_read": local_sqlite_read,
        "local_sqlite_changed": local_sqlite_changed,
        "external_writes": report.get("external_writes", "none"),
        "credentials": report.get("credentials", "not_loaded"),
        "production_db_active": report.get("production_db_active", False),
        "output_target": _output_target_report(output_kind, output_file=output_file),
        "safe_next_actions": list(safe_next_actions),
    }
    enriched.setdefault("rail_states", create_rail_state_report())
    return enriched


def _database_target_report(
    database_path: str | Path | None,
    *,
    database_access: str,
) -> dict[str, Any]:
    if database_path is None:
        return {
            "path": None,
            "path_classification": "not_applicable_no_db_opened",
            "access": database_access,
            "safe_local_db": False,
            "production_db_active": False,
        }
    path = Path(database_path).expanduser().resolve()
    if is_under_temp(path):
        classification = "temporary_test_local_safe_db"
    elif is_under_repo(path):
        classification = "repo_local_dev_safe_db"
    else:
        classification = "unknown_explicit_sqlite"
    return {
        "path": str(path),
        "path_classification": classification,
        "access": database_access,
        "safe_local_db": classification in {
            "temporary_test_local_safe_db",
            "repo_local_dev_safe_db",
        },
        "production_db_active": False,
    }


def _output_target_report(
    output_kind: str,
    *,
    output_file: str | Path | None,
) -> dict[str, Any]:
    path = str(Path(output_file).expanduser().resolve()) if output_file else None
    return {
        "kind": output_kind,
        "path": path,
    }


def _connect_read_only(db_path: str) -> sqlite3.Connection:
    validated_path = validate_existing_sqlite_path(db_path, path_label="operator db_path")
    db_uri = f"file:{quote(str(validated_path), safe='/')}?mode=ro"
    connection = sqlite3.connect(db_uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _connect_read_write(db_path: str) -> sqlite3.Connection:
    validated_path = validate_existing_sqlite_path(db_path, path_label="operator db_path")
    connection = sqlite3.connect(validated_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _add_db_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--db",
        required=True,
        help="Explicit absolute temp/dev SQLite DB path.",
    )


def _add_date_timezone_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--date", required=True, help="Source date in YYYY-MM-DD format.")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)


def _add_json_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the completion report as JSON.",
    )


def _format_cli_error(error: BaseException) -> str:
    message = str(error)
    if "No external writes were attempted." in message:
        return message
    if "must contain JSON" in message:
        return (
            f"{message}\n"
            "No external writes were attempted.\n"
            "Next: fix the JSON file and rerun the same no-send command."
        )
    if "must point to an existing SQLite file" in message:
        return (
            f"{message}\n"
            "No external writes were attempted.\n"
            "Next: rerun with --db <path-to-local-test-db>."
        )
    if "must point to an existing file" in message:
        return (
            f"{message}\n"
            "No external writes were attempted.\n"
            "Next: rerun with an explicit temp/dev input file."
        )
    if "not found" in message or "permission" in message.lower() or "blocked" in message:
        return (
            f"{message}\n"
            "No external writes were attempted.\n"
            "Next: use a safe local preview/status command or fix the local dev/test input."
        )
    return message


def _merge_synthesis_source_type(raw_input: str, *, source_type: str) -> str:
    text = raw_input.strip()
    if not text.startswith("{"):
        return raw_input
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return raw_input
    if not isinstance(payload, dict):
        return raw_input
    if not payload.get("source_type"):
        payload["source_type"] = source_type
    return json.dumps(payload, allow_nan=False, ensure_ascii=True, sort_keys=True)


def _load_json_object(path: Any) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise CliError(f"input file must contain JSON: {error}") from error
    if not isinstance(payload, dict):
        raise CliError("input file JSON must decode to an object")
    return payload


def _loads_json_object(payload_bytes: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise CliError("input file must be UTF-8 JSON") from error
    except json.JSONDecodeError as error:
        raise CliError(f"input file must contain JSON: {error}") from error
    if not isinstance(payload, dict):
        raise CliError("input file JSON must decode to an object")
    return payload


def _synthesis_rejected_result(*, reason: str, source_type: str) -> dict[str, Any]:
    return {
        "status": "rejected",
        "reason": reason,
        "dry_run": False,
        "database_write": False,
        "external_mutation": False,
        "permission": None,
        "preview_report": {
            "preview_id": None,
            "source_type": source_type,
            "input_format": None,
            "candidate_counts": {},
            "accepted_candidates": [],
            "rejected_candidates": [],
            "blocked_candidates": [],
            "review_required_candidates": [],
            "manual_only_candidates": [],
            "warnings": [reason],
            "questions_for_review": [],
            **REPORT_SAFETY_FLAGS,
        },
        "record": None,
        "would_write": None,
        **REPORT_SAFETY_FLAGS,
    }


def _safety_flags_from_report(report: object) -> dict[str, bool]:
    source = report if isinstance(report, Mapping) else {}
    return {
        "no_external_writes": source.get("no_external_writes") is True,
        "no_send_mode": source.get("no_send_mode") is True,
        "no_live_model_call": source.get("no_live_model_call") is True,
        "no_todoist_writes": source.get("no_todoist_writes") is True,
        "no_calendar_writes": source.get("no_calendar_writes") is True,
        "no_gmail_send": source.get("no_gmail_send") is True,
        "no_gmail_draft": source.get("no_gmail_draft") is True,
    }


def _emit_report(report: Mapping[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(
            json.dumps(
                report,
                allow_nan=False,
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            )
        )
        return
    print(_human_report(report))


def _human_report(report: Mapping[str, Any]) -> str:
    lines: list[str] = []
    _append_workflow_completion_lines(lines, report)

    if report.get("command") == "workflows":
        _append_workflow_catalog_lines(lines, report)

    lines.extend(
        [
        f"command: {report.get('command', 'unknown')}",
        f"status: {report.get('status', 'unknown')}",
        ]
    )
    for key in (
        "reason",
        "briefing_window_name",
        "briefing_output_id",
        "output_file",
        "database_write",
        "file_write",
        "external_mutation",
        "no_external_writes",
        "no_send_mode",
        "no_live_model_call",
        "no_todoist_writes",
        "no_calendar_writes",
        "no_gmail_send",
        "no_gmail_draft",
        "no_personalos_writes",
        "live_write",
        "internal_state_mutation",
        "simulated_or_dry_run",
        "static_html_only",
        "apply_run_id",
        "scheduler_run_id",
        "scheduler_job_id",
        "scheduler_activation",
        "launch_agent_installed",
        "daemonized",
        "background_process_started",
        "preview_id",
        "approval_source_hash",
    ):
        if key in report:
            lines.append(f"{key}: {_format_scalar(report[key])}")

    top_level_rail_states = report.get("rail_states")
    if isinstance(top_level_rail_states, Mapping):
        _append_rail_state_lines(lines, top_level_rail_states)

    summary = report.get("summary")
    if isinstance(summary, Mapping):
        counts = summary.get("counts")
        if isinstance(counts, Mapping):
            lines.append(
                "counts: "
                + ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
            )
        source_date = summary.get("source_date")
        timezone = summary.get("timezone")
        if source_date:
            lines.append(f"source_date: {source_date}")
        if timezone:
            lines.append(f"timezone: {timezone}")
    scheduler_run = report.get("scheduler_run")
    if isinstance(scheduler_run, Mapping):
        lines.append(f"scheduler_run_id: {scheduler_run.get('scheduler_run_id')}")
        lines.append(f"job_type: {scheduler_run.get('job_type')}")

    preview_report = report.get("preview_report")
    if isinstance(preview_report, Mapping):
        preview_id = preview_report.get("preview_id")
        candidate_counts = preview_report.get("candidate_counts")
        if preview_id:
            lines.append(f"preview_id: {preview_id}")
        if isinstance(candidate_counts, Mapping):
            lines.append(
                "candidate_counts: "
                + ", ".join(
                    f"{key}={value}" for key, value in sorted(candidate_counts.items())
                )
            )

    warnings = report.get("warnings")
    if isinstance(warnings, list) and warnings:
        lines.append("warnings:")
        lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines)


def _append_workflow_completion_lines(
    lines: list[str],
    report: Mapping[str, Any],
) -> None:
    workflow_name = str(report.get("workflow_name") or report.get("command") or "unknown")
    workflow_mode = str(report.get("workflow_mode") or "inert / no-send / report-only")
    lines.append(f"Workflow complete: {workflow_name}")
    lines.append(f"Mode: {workflow_mode}")
    lines.append(f"DB target: {_database_target_text(report.get('database_target'))}")
    lines.append(
        "Production DB: "
        + ("active" if report.get("production_db_active") is True else "not active")
    )
    lines.append(f"Local SQLite read: {_yes_no_unavailable(report.get('local_sqlite_read'))}")
    lines.append(f"Local SQLite changes: {_local_sqlite_changes_text(report)}")
    if "internal_state_mutation" in report:
        lines.append(
            "Approved local apply: "
            + _yes_no_unavailable(report.get("internal_state_mutation"))
        )
    lines.append(f"External writes: {report.get('external_writes', 'none')}")
    lines.append(f"Credentials: {report.get('credentials', 'not_loaded').replace('_', ' ')}")
    lines.append(f"Output: {_output_target_text(report.get('output_target'))}")

    _append_candidate_or_ledger_summary(lines, report)

    safe_next_actions = report.get("safe_next_actions")
    if isinstance(safe_next_actions, list) and safe_next_actions:
        lines.append("Safe next action:")
        lines.extend(f"- {action}" for action in safe_next_actions)

    blocked_actions = _blocked_actions_for_report(report)
    if blocked_actions:
        lines.append("Blocked:")
        lines.extend(f"- {action}" for action in blocked_actions)


def _append_workflow_catalog_lines(
    lines: list[str],
    report: Mapping[str, Any],
) -> None:
    workflows = report.get("safe_local_workflows")
    if isinstance(workflows, list) and workflows:
        lines.append("Available safe local workflows:")
        for workflow in workflows:
            if not isinstance(workflow, Mapping):
                continue
            lines.append(f"- {workflow.get('name', 'unknown')}")
            lines.append(f"  Command: {workflow.get('command', 'unavailable')}")
            lines.append(f"  Local effect: {workflow.get('local_effect', 'unavailable')}")
            lines.append(f"  Output: {workflow.get('output', 'unavailable')}")
    blocked_actions = report.get("blocked_actions")
    if isinstance(blocked_actions, list) and blocked_actions:
        lines.append("Blocked until a Conductor-gated rail activation:")
        lines.extend(f"- {action}" for action in blocked_actions)


def _database_target_text(database_target: object) -> str:
    if not isinstance(database_target, Mapping):
        return "unavailable"
    classification = str(database_target.get("path_classification", "unavailable"))
    label = {
        "not_applicable_no_db_opened": "not applicable - no DB opened",
        "temporary_test_local_safe_db": "temporary/test/local safe DB",
        "repo_local_dev_safe_db": "repo-local dev safe DB",
        "unknown_explicit_sqlite": "unknown explicit SQLite path",
    }.get(classification, classification)
    access = database_target.get("access")
    path = database_target.get("path")
    if path:
        return f"{label}; access={access}; path={path}"
    return f"{label}; access={access}"


def _output_target_text(output_target: object) -> str:
    if not isinstance(output_target, Mapping):
        return "unavailable"
    kind = str(output_target.get("kind", "unavailable")).replace("_", " ")
    path = output_target.get("path")
    if path:
        return f"{path} ({kind})"
    return kind


def _local_sqlite_changes_text(report: Mapping[str, Any]) -> str:
    changed = report.get("local_sqlite_changed")
    if changed is None:
        return "unavailable"
    if changed is not True:
        return "none"
    if report.get("internal_state_mutation") is True:
        return "internal SQLite state changed"
    command = str(report.get("command", ""))
    if "preview" in command:
        return "local preview/audit rows changed"
    if "ledger" in str(report.get("workflow_mode", "")) or command.startswith("side-effects"):
        return "local ledger rows changed"
    if command.startswith("scheduler"):
        return "local scheduler/dev-test rows changed"
    return "local SQLite audit/dev-test rows changed"


def _append_candidate_or_ledger_summary(
    lines: list[str],
    report: Mapping[str, Any],
) -> None:
    preview_report = report.get("preview_report")
    if isinstance(preview_report, Mapping):
        candidate_counts = preview_report.get("candidate_counts")
        if isinstance(candidate_counts, Mapping):
            lines.append(
                "Candidate changes: "
                + ", ".join(
                    f"{key}={value}" for key, value in sorted(candidate_counts.items())
                )
            )

    completion_report = report.get("completion_report")
    if isinstance(completion_report, Mapping):
        counts = completion_report.get("counts")
        if isinstance(counts, Mapping):
            lines.append(
                "Apply/item counts: "
                + ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
            )
        if completion_report.get("rollback_verified") is True:
            lines.append("Rollback/recovery: verified for failed transaction")

    summary = report.get("summary")
    if isinstance(summary, Mapping):
        if {
            "intent_count",
            "attempt_count",
            "idempotency_record_count",
        }.issubset(summary.keys()):
            lines.append(
                "Ledger/idempotency: "
                f"intents={summary.get('intent_count')}, "
                f"attempts={summary.get('attempt_count')}, "
                f"idempotency_records={summary.get('idempotency_record_count')}"
            )

    if "scheduler_job_count" in report:
        scheduler_text = f"jobs={report.get('scheduler_job_count')}"
        if "due_simulated_job_count" in report:
            scheduler_text += f", due={report.get('due_simulated_job_count')}"
        lines.append(f"Simulated scheduler: {scheduler_text}")


def _blocked_actions_for_report(report: Mapping[str, Any]) -> list[str]:
    blocked = report.get("blocked_actions")
    if isinstance(blocked, list) and blocked:
        return [str(action) for action in blocked]
    return []


def _yes_no_unavailable(value: object) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unavailable"


def _append_rail_state_lines(lines: list[str], rail_states: Mapping[str, Any]) -> None:
    rails = rail_states.get("rails")
    if isinstance(rails, Mapping) and rails:
        lines.append("Rail states:")
        for name, value in sorted(rails.items()):
            lines.append(f"- {name}: {value}")
    lines.append(f"Scheduler: {rail_states.get('scheduler', 'unavailable')}")


def _format_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "none"
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
