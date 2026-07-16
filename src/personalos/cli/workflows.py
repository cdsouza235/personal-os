"""Workflow catalog, demo, and status commands."""

from __future__ import annotations

import argparse
from contextlib import closing
from typing import Any

from personalos.cli.db import _connect_read_only, _with_workflow_context
from personalos.cli.reporting import _emit_report
from personalos.status import create_rail_state_report, create_status_summary

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
        "name": "Knowledge Edge fixture scan/queue/false-positive flag",
        "safe_local_action": "Run a fixture-only Knowledge Edge scan and review the queue",
        "command": (
            "personalos knowledge-edge scan --db <safe_db> --date <YYYY-MM-DD>; "
            "personalos knowledge-edge queue show --db <safe_db> --date <YYYY-MM-DD>; "
            "personalos knowledge-edge flag-false-positive --db <safe_db> "
            "--entity-match-id <id>"
        ),
        "mode": "inert / no-send / fixture-only (Phase 1: no live network, no scheduler)",
        "local_effect": (
            "scan writes local SQLite ke_* rows only from a built-in synthetic fixture "
            "dataset; queue show is read-only; flag-false-positive updates one "
            "ke_entity_matches row"
        ),
        "output": "stdout report with queue sections, coverage, and false-positive flags",
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
