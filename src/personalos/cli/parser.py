"""argparse tree construction for the personalos operator CLI."""

from __future__ import annotations

import argparse

from personalos.cli.briefing import _command_briefing_export, _command_briefing_preview
from personalos.cli.priorities import (
    _command_priorities_create,
    _command_priorities_list,
    _command_priorities_update,
)
from personalos.cli.routines import (
    _command_routines_create,
    _command_routines_list,
    _command_routines_update,
)
from personalos.cli.scheduler import (
    _command_scheduler_jobs,
    _command_scheduler_preview,
    _command_scheduler_run,
    _command_scheduler_seed_dev,
)
from personalos.cli.side_effects import (
    _command_side_effects_record_dry_run,
    _command_side_effects_summary,
)
from personalos.cli.synthesis import _command_synthesis_apply, _command_synthesis_preview
from personalos.cli.today import (
    _command_dashboard_render,
    _command_run_morning,
    _command_today,
)
from personalos.cli.workflows import (
    _command_demo_no_send_e2e,
    _command_status,
    _command_workflows,
)
from personalos.config import DEFAULT_TIMEZONE
from personalos.scheduler import (
    BRIEFING_WINDOWS,
    SAFE_NO_SEND_SEED_PROFILE,
    SIMULATED_JOB_TYPES,
)
from personalos.state import PRIORITY_STATUSES, ROUTINE_STATUSES
from personalos.synthesis_import import ALLOWED_SOURCE_TYPES


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

    run_parser = subparsers.add_parser(
        "run",
        help="Run a real top-level Personal OS job as a foreground no-send simulation only.",
        description=(
            "Run a real top-level Personal OS job as a foreground no-send simulation "
            "only. This is a manual-trigger entry point: it never installs or activates "
            "a scheduler, LaunchAgent, crontab, daemon, background loop, or production "
            "runtime."
        ),
    )
    run_subparsers = run_parser.add_subparsers(dest="run_command", required=True)

    run_morning_parser = run_subparsers.add_parser(
        "morning",
        help="Run the morning no-send briefing job end to end (plan/window/preview/export).",
        description=(
            "Run the morning no-send briefing job end to end through the existing "
            "plan/window/preview/export pipeline. Records one real scheduler_run ledger "
            "row. Manual trigger only; no scheduler activation."
        ),
    )
    _add_db_arg(run_morning_parser)
    run_morning_parser.add_argument(
        "--date",
        help="Source date in YYYY-MM-DD format. Defaults to today in --timezone.",
    )
    run_morning_parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    run_morning_parser.add_argument("--output-file")
    _add_json_arg(run_morning_parser)
    run_morning_parser.set_defaults(func=_command_run_morning)

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

    routines_parser = subparsers.add_parser(
        "routines",
        help="Create, edit, and list dev/test routine records; permission-gated local writes.",
    )
    routines_subparsers = routines_parser.add_subparsers(
        dest="routines_command",
        required=True,
    )

    routines_create_parser = routines_subparsers.add_parser(
        "create",
        help="Create one routine record; requires routine engine write permission.",
    )
    _add_db_arg(routines_create_parser)
    routines_create_parser.add_argument("--routine-id", required=True)
    routines_create_parser.add_argument("--name", required=True)
    routines_create_parser.add_argument("--status", choices=ROUTINE_STATUSES, default="active")
    routines_create_parser.add_argument(
        "--enabled",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    routines_create_parser.add_argument("--notes", default="")
    routines_create_parser.add_argument("--settings-json", default=None)
    _add_json_arg(routines_create_parser)
    routines_create_parser.set_defaults(func=_command_routines_create)

    routines_update_parser = routines_subparsers.add_parser(
        "update",
        help=(
            "Rename/update notes or settings, and/or enable/disable one routine; "
            "requires routine engine write permission."
        ),
    )
    _add_db_arg(routines_update_parser)
    routines_update_parser.add_argument("--routine-id", required=True)
    routines_update_parser.add_argument("--name", default=None)
    routines_update_parser.add_argument("--status", choices=ROUTINE_STATUSES, default=None)
    routines_update_parser.add_argument(
        "--enabled",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    routines_update_parser.add_argument("--notes", default=None)
    routines_update_parser.add_argument("--settings-json", default=None)
    _add_json_arg(routines_update_parser)
    routines_update_parser.set_defaults(func=_command_routines_update)

    routines_list_parser = routines_subparsers.add_parser(
        "list",
        help="List routine records; requires routine engine read permission.",
    )
    _add_db_arg(routines_list_parser)
    _add_json_arg(routines_list_parser)
    routines_list_parser.set_defaults(func=_command_routines_list)

    priorities_parser = subparsers.add_parser(
        "priorities",
        help="Create, edit, and list dev/test priority records; permission-gated local writes.",
    )
    priorities_subparsers = priorities_parser.add_subparsers(
        dest="priorities_command",
        required=True,
    )

    priorities_create_parser = priorities_subparsers.add_parser(
        "create",
        help="Create one priority record; requires priority engine write permission.",
    )
    _add_db_arg(priorities_create_parser)
    priorities_create_parser.add_argument("--priority-id", required=True)
    priorities_create_parser.add_argument("--title", required=True)
    priorities_create_parser.add_argument("--status", choices=PRIORITY_STATUSES, default="active")
    priorities_create_parser.add_argument("--notes", default="")
    priorities_create_parser.add_argument("--metadata-json", default=None)
    _add_json_arg(priorities_create_parser)
    priorities_create_parser.set_defaults(func=_command_priorities_create)

    priorities_update_parser = priorities_subparsers.add_parser(
        "update",
        help=(
            "Rename/update status, notes, or metadata for one priority; requires "
            "priority engine write permission."
        ),
    )
    _add_db_arg(priorities_update_parser)
    priorities_update_parser.add_argument("--priority-id", required=True)
    priorities_update_parser.add_argument("--title", default=None)
    priorities_update_parser.add_argument("--status", choices=PRIORITY_STATUSES, default=None)
    priorities_update_parser.add_argument("--notes", default=None)
    priorities_update_parser.add_argument("--metadata-json", default=None)
    _add_json_arg(priorities_update_parser)
    priorities_update_parser.set_defaults(func=_command_priorities_update)

    priorities_list_parser = priorities_subparsers.add_parser(
        "list",
        help="List priority records; requires priority engine read permission.",
    )
    _add_db_arg(priorities_list_parser)
    priorities_list_parser.add_argument("--status", choices=PRIORITY_STATUSES, default=None)
    _add_json_arg(priorities_list_parser)
    priorities_list_parser.set_defaults(func=_command_priorities_list)

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
