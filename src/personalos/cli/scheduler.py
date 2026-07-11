"""No-send scheduler job listing, preview, run, and dev-seed commands."""

from __future__ import annotations

import argparse
from contextlib import closing

from personalos.cli.db import _connect_read_only, _connect_read_write, _with_workflow_context
from personalos.cli.errors import CliError
from personalos.cli.reporting import _emit_report
from personalos.scheduler import (
    list_scheduler_jobs,
    preview_scheduler_jobs,
    run_scheduler_job_simulated,
    seed_dev_scheduler_jobs,
)


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
