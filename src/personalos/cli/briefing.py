"""No-send briefing preview/export commands."""

from __future__ import annotations

import argparse
from contextlib import closing

from personalos.briefings import generate_no_send_briefing_preview, read_briefing_output
from personalos.cli.db import _connect_read_only, _connect_read_write, _with_workflow_context
from personalos.cli.errors import CliError
from personalos.cli.reporting import _emit_report, _safety_flags_from_report
from personalos.path_safety import validate_output_file_path


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
