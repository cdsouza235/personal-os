"""Today View, dashboard render, and morning-run commands."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from contextlib import closing
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from personalos.cli.db import _connect_read_only, _connect_read_write, _with_workflow_context
from personalos.cli.errors import CliError
from personalos.cli.reporting import _emit_report
from personalos.config import DEFAULT_TIMEZONE
from personalos.dashboard import render_today_view_html_from_connection
from personalos.path_safety import validate_output_file_path
from personalos.scheduler import run_scheduler_job_simulated
from personalos.today import create_today_view_summary


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


def _command_run_morning(args: argparse.Namespace) -> int:
    output_path = None
    if args.output_file:
        output_path = validate_output_file_path(
            args.output_file,
            path_label="operator output_file",
        )
    resolved_date = args.date or _today_iso(args.timezone)

    with closing(_connect_read_write(args.db)) as connection:
        result = run_scheduler_job_simulated(
            connection,
            job_type="briefing_preview",
            briefing_window_name="morning",
            source_date=resolved_date,
            timezone=args.timezone,
            run_type="manual_simulated",
        )

    workflow_report = result.get("workflow_report")
    manual_export_markdown = (
        workflow_report.get("manual_export_markdown")
        if isinstance(workflow_report, Mapping)
        else None
    )
    file_write = False
    if output_path is not None and _has_text(manual_export_markdown):
        output_path.write_text(manual_export_markdown, encoding="utf-8")
        file_write = True

    report = _with_workflow_context(
        {"command": "run morning", **result, "file_write": file_write},
        workflow_name="Morning briefing job (manual trigger)",
        workflow_mode="inert / no-send / foreground simulation",
        database_path=args.db,
        database_access="read_write_local_morning_run",
        local_sqlite_read=True,
        local_sqlite_changed=bool(result.get("database_write")),
        output_kind="file" if file_write else ("stdout_json" if args.json else "stdout_human"),
        output_file=str(output_path) if file_write else None,
        safe_next_actions=(
            "Review the morning briefing completion report."
            if file_write
            else "Rerun with --output-file to export the would-have-sent Markdown artifact.",
            "Inspect scheduler jobs or status from the same safe local DB.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0 if result.get("status") == "completed" else 1


def _today_iso(timezone: str) -> str:
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as error:
        raise CliError(f"timezone must be a valid IANA timezone name: {timezone}") from error
    return datetime.now(zone).date().isoformat()


def _has_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


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
