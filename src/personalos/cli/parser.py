"""argparse tree construction for the personalos operator CLI."""

from __future__ import annotations

import argparse

from personalos.cli.briefing import _command_briefing_export, _command_briefing_preview
from personalos.cli.dispatch import _command_dispatch_morning
from personalos.cli.knowledge_edge import (
    _command_knowledge_edge_decide_save,
    _command_knowledge_edge_decide_save_replay,
    _command_knowledge_edge_decide_skip,
    _command_knowledge_edge_decide_watch,
    _command_knowledge_edge_decide_watch_live,
    _command_knowledge_edge_decide_watched,
    _command_knowledge_edge_flag_false_positive,
    _command_knowledge_edge_queue_show,
    _command_knowledge_edge_scan,
    _command_knowledge_edge_shadow_bootstrap,
    _command_knowledge_edge_shadow_grade_init,
    _command_knowledge_edge_shadow_report,
    _command_knowledge_edge_shadow_sample_freeze,
    _command_knowledge_edge_shadow_scan,
    _command_knowledge_edge_synthesis_export,
    _command_knowledge_edge_synthesis_list,
)
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
from personalos.knowledge_edge.dashboard import (
    DEFAULT_KNOWLEDGE_EDGE_FEATURE_MODE,
    KNOWLEDGE_EDGE_FEATURE_MODES,
)
from personalos.scheduler import (
    BRIEFING_WINDOWS,
    SAFE_NO_SEND_SEED_PROFILE,
    SIMULATED_JOB_TYPES,
)
from personalos.state import (
    PRIORITY_STATUSES,
    ROUTINE_CADENCE_TYPES,
    ROUTINE_MISSED_BEHAVIOR_TYPES,
    ROUTINE_STATUSES,
)
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

    dispatch_parser = subparsers.add_parser(
        "dispatch",
        help=(
            "Dispatch a real top-level Personal OS job to its live rails; CAN make a "
            "real external write."
        ),
        description=(
            "Dispatch a real top-level Personal OS job. For each computed candidate, "
            "if -- and only if -- its rail is live (personalos.status.RAIL_STATES), "
            "this calls the real rail adapter and CAN make a genuine external write "
            "(a real Todoist task, a real Gmail send to the one controlled recipient). "
            "Every candidate whose rail is not live is reported as a preview, exactly "
            "like `run morning`. This is a manual-trigger entry point: it never "
            "installs or activates a scheduler, LaunchAgent, crontab, daemon, "
            "background loop, or production runtime, and it is NOT threaded through "
            "the simulated scheduler."
        ),
    )
    dispatch_subparsers = dispatch_parser.add_subparsers(dest="dispatch_command", required=True)

    dispatch_morning_parser = dispatch_subparsers.add_parser(
        "morning",
        help="Dispatch the morning cycle's candidates: live rails write for real, inert rails preview.",
        description=(
            "Compute the morning cycle's candidates identically to `run morning`, then "
            "for each candidate: if its rail (Todoist, Gmail) is live, call the real "
            "rail adapter (a genuine external write CAN happen); otherwise report a "
            "preview. Calendar candidates and follow-ups are always previewed (no live "
            "calendar rail in scope, and follow-ups have no rail at all). Todoist "
            "candidates dispatch before the Gmail candidate, in that order, so a Gmail "
            "failure never blocks or rolls back Todoist tasks already created; nothing "
            "is ever automatically retried."
        ),
    )
    _add_db_arg(dispatch_morning_parser)
    dispatch_morning_parser.add_argument(
        "--date",
        help="Source date in YYYY-MM-DD format. Defaults to today in --timezone.",
    )
    dispatch_morning_parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    _add_json_arg(dispatch_morning_parser)
    dispatch_morning_parser.set_defaults(func=_command_dispatch_morning)

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
    routines_create_parser.add_argument(
        "--cadence-type",
        choices=ROUTINE_CADENCE_TYPES,
        default=None,
    )
    routines_create_parser.add_argument("--cadence-config-json", default=None)
    routines_create_parser.add_argument(
        "--missed-behavior",
        choices=ROUTINE_MISSED_BEHAVIOR_TYPES,
        default=None,
    )
    routines_create_parser.add_argument("--rotation-group", default=None)
    routines_create_parser.add_argument("--weekly-target", type=int, default=None)
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
    routines_update_parser.add_argument(
        "--cadence-type",
        choices=ROUTINE_CADENCE_TYPES,
        default=None,
    )
    routines_update_parser.add_argument("--cadence-config-json", default=None)
    routines_update_parser.add_argument(
        "--missed-behavior",
        choices=ROUTINE_MISSED_BEHAVIOR_TYPES,
        default=None,
    )
    routines_update_parser.add_argument("--rotation-group", default=None)
    routines_update_parser.add_argument("--weekly-target", type=int, default=None)
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
    dashboard_render_parser.add_argument(
        "--knowledge-edge-mode",
        choices=KNOWLEDGE_EDGE_FEATURE_MODES,
        default=DEFAULT_KNOWLEDGE_EDGE_FEATURE_MODE,
        help="Knowledge Edge dashboard section feature mode (default: disabled/invisible).",
    )
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

    knowledge_edge_parser = subparsers.add_parser(
        "knowledge-edge",
        help="Knowledge Edge fixture scan, queue preview, and false-positive flag (Phase 1: fixture-only).",
        description=(
            "Knowledge Edge Daily Intelligence Queue commands. Phase 1: fixture-only, "
            "no live network access, no scheduler activation."
        ),
    )
    knowledge_edge_subparsers = knowledge_edge_parser.add_subparsers(
        dest="knowledge_edge_command",
        required=True,
    )

    knowledge_edge_scan_parser = knowledge_edge_subparsers.add_parser(
        "scan",
        help="Run a fixture-only Knowledge Edge scan (no live network access).",
    )
    _add_db_arg(knowledge_edge_scan_parser)
    knowledge_edge_scan_parser.add_argument(
        "--date", required=True, help="Queue date in YYYY-MM-DD format."
    )
    knowledge_edge_scan_parser.add_argument(
        "--now", default=None, help="ISO-8601 UTC instant to run the scan as of (default: current time)."
    )
    knowledge_edge_scan_parser.add_argument("--scan-run-id", default=None)
    _add_json_arg(knowledge_edge_scan_parser)
    knowledge_edge_scan_parser.set_defaults(func=_command_knowledge_edge_scan)

    knowledge_edge_queue_parser = knowledge_edge_subparsers.add_parser(
        "queue",
        help="Show the composed Daily Intelligence Queue for one date.",
    )
    knowledge_edge_queue_subparsers = knowledge_edge_queue_parser.add_subparsers(
        dest="knowledge_edge_queue_command",
        required=True,
    )
    knowledge_edge_queue_show_parser = knowledge_edge_queue_subparsers.add_parser(
        "show",
        help="Show the composed four-lane queue, demoted/ambiguous items, and coverage.",
    )
    _add_db_arg(knowledge_edge_queue_show_parser)
    knowledge_edge_queue_show_parser.add_argument(
        "--date", required=True, help="Queue date in YYYY-MM-DD format."
    )
    _add_json_arg(knowledge_edge_queue_show_parser)
    knowledge_edge_queue_show_parser.set_defaults(func=_command_knowledge_edge_queue_show)

    knowledge_edge_flag_parser = knowledge_edge_subparsers.add_parser(
        "flag-false-positive",
        help="Flag one entity match as a false positive.",
    )
    _add_db_arg(knowledge_edge_flag_parser)
    knowledge_edge_flag_parser.add_argument("--entity-match-id", required=True)
    _add_json_arg(knowledge_edge_flag_parser)
    knowledge_edge_flag_parser.set_defaults(func=_command_knowledge_edge_flag_false_positive)

    knowledge_edge_decide_parser = knowledge_edge_subparsers.add_parser(
        "decide",
        help="Accept a Watch/Save/Skip/Watched or Watch-live/Save-replay decision.",
    )
    knowledge_edge_decide_subparsers = knowledge_edge_decide_parser.add_subparsers(
        dest="knowledge_edge_decide_command",
        required=True,
    )

    knowledge_edge_decide_watch_parser = knowledge_edge_decide_subparsers.add_parser(
        "watch",
        help="Watch a media item tonight (Tonight cap: 3 items / 90 known-duration minutes).",
    )
    _add_db_arg(knowledge_edge_decide_watch_parser)
    knowledge_edge_decide_watch_parser.add_argument("--media-item-id", required=True)
    _add_json_arg(knowledge_edge_decide_watch_parser)
    knowledge_edge_decide_watch_parser.set_defaults(func=_command_knowledge_edge_decide_watch)

    knowledge_edge_decide_save_parser = knowledge_edge_decide_subparsers.add_parser(
        "save",
        help="Save a media item for later (Saved cap: 12 items).",
    )
    _add_db_arg(knowledge_edge_decide_save_parser)
    knowledge_edge_decide_save_parser.add_argument("--media-item-id", required=True)
    _add_json_arg(knowledge_edge_decide_save_parser)
    knowledge_edge_decide_save_parser.set_defaults(func=_command_knowledge_edge_decide_save)

    knowledge_edge_decide_skip_parser = knowledge_edge_decide_subparsers.add_parser(
        "skip",
        help="Skip a media item or scheduled event.",
    )
    _add_db_arg(knowledge_edge_decide_skip_parser)
    knowledge_edge_decide_skip_parser.add_argument("--media-item-id")
    knowledge_edge_decide_skip_parser.add_argument("--event-id")
    _add_json_arg(knowledge_edge_decide_skip_parser)
    knowledge_edge_decide_skip_parser.set_defaults(func=_command_knowledge_edge_decide_skip)

    knowledge_edge_decide_watched_parser = knowledge_edge_decide_subparsers.add_parser(
        "watched",
        help="Mark a media item or scheduled event watched; stages a synthesis handoff.",
    )
    _add_db_arg(knowledge_edge_decide_watched_parser)
    knowledge_edge_decide_watched_parser.add_argument("--media-item-id")
    knowledge_edge_decide_watched_parser.add_argument("--event-id")
    _add_json_arg(knowledge_edge_decide_watched_parser)
    knowledge_edge_decide_watched_parser.set_defaults(func=_command_knowledge_edge_decide_watched)

    knowledge_edge_decide_watch_live_parser = knowledge_edge_decide_subparsers.add_parser(
        "watch-live",
        help="Watch a scheduled event live (2/day is an advisory limit only; not enforced).",
    )
    _add_db_arg(knowledge_edge_decide_watch_live_parser)
    knowledge_edge_decide_watch_live_parser.add_argument("--event-id", required=True)
    _add_json_arg(knowledge_edge_decide_watch_live_parser)
    knowledge_edge_decide_watch_live_parser.set_defaults(func=_command_knowledge_edge_decide_watch_live)

    knowledge_edge_decide_save_replay_parser = knowledge_edge_decide_subparsers.add_parser(
        "save-replay",
        help="Monitor a scheduled event for its official replay instead of attending live.",
    )
    _add_db_arg(knowledge_edge_decide_save_replay_parser)
    knowledge_edge_decide_save_replay_parser.add_argument("--event-id", required=True)
    _add_json_arg(knowledge_edge_decide_save_replay_parser)
    knowledge_edge_decide_save_replay_parser.set_defaults(func=_command_knowledge_edge_decide_save_replay)

    knowledge_edge_synthesis_parser = knowledge_edge_subparsers.add_parser(
        "synthesis",
        help="List or export staged synthesis handoffs (from Watched decisions).",
    )
    knowledge_edge_synthesis_subparsers = knowledge_edge_synthesis_parser.add_subparsers(
        dest="knowledge_edge_synthesis_command",
        required=True,
    )

    knowledge_edge_synthesis_list_parser = knowledge_edge_synthesis_subparsers.add_parser(
        "list",
        help="List synthesis handoffs, optionally filtered by status.",
    )
    _add_db_arg(knowledge_edge_synthesis_list_parser)
    knowledge_edge_synthesis_list_parser.add_argument(
        "--status", choices=("staged", "completed"), default=None
    )
    _add_json_arg(knowledge_edge_synthesis_list_parser)
    knowledge_edge_synthesis_list_parser.set_defaults(func=_command_knowledge_edge_synthesis_list)

    knowledge_edge_synthesis_export_parser = knowledge_edge_synthesis_subparsers.add_parser(
        "export",
        help="Export one staged synthesis handoff's packet and mark it completed.",
    )
    _add_db_arg(knowledge_edge_synthesis_export_parser)
    knowledge_edge_synthesis_export_parser.add_argument("--handoff-id", required=True)
    _add_json_arg(knowledge_edge_synthesis_export_parser)
    knowledge_edge_synthesis_export_parser.set_defaults(func=_command_knowledge_edge_synthesis_export)

    knowledge_edge_shadow_parser = knowledge_edge_subparsers.add_parser(
        "shadow",
        help="P-KE-2C shadow_live bootstrap/scan/sample-freeze/report commands.",
        description=(
            "Knowledge Edge shadow_live commands (amendment §14.4). Every command "
            "requires --db to resolve to exactly the one shadow database path and "
            "refuses otherwise; no production database path or notification/Obsidian/"
            "scheduler surface is ever reachable through this command group."
        ),
    )
    knowledge_edge_shadow_subparsers = knowledge_edge_shadow_parser.add_subparsers(
        dest="knowledge_edge_shadow_command",
        required=True,
    )

    knowledge_edge_shadow_bootstrap_parser = knowledge_edge_shadow_subparsers.add_parser(
        "bootstrap",
        help="Create/migrate the shadow DB and re-apply the 9 Lane A verification flips.",
    )
    _add_db_arg(knowledge_edge_shadow_bootstrap_parser)
    _add_json_arg(knowledge_edge_shadow_bootstrap_parser)
    knowledge_edge_shadow_bootstrap_parser.set_defaults(func=_command_knowledge_edge_shadow_bootstrap)

    knowledge_edge_shadow_scan_parser = knowledge_edge_shadow_subparsers.add_parser(
        "scan",
        help="Run one bounded shadow_live Lane A scan (live RSS, verified-active sources only).",
    )
    _add_db_arg(knowledge_edge_shadow_scan_parser)
    knowledge_edge_shadow_scan_parser.add_argument(
        "--date", required=True, help="Queue date in YYYY-MM-DD format."
    )
    knowledge_edge_shadow_scan_parser.add_argument(
        "--now", default=None, help="ISO-8601 UTC instant to run the scan as of (default: current time)."
    )
    knowledge_edge_shadow_scan_parser.add_argument("--scan-run-id", default=None)
    _add_json_arg(knowledge_edge_shadow_scan_parser)
    knowledge_edge_shadow_scan_parser.set_defaults(func=_command_knowledge_edge_shadow_scan)

    knowledge_edge_shadow_sample_freeze_parser = knowledge_edge_shadow_subparsers.add_parser(
        "sample-freeze",
        help="Construct and freeze the R3-04 ground-truth sample (PENDING acknowledgment).",
    )
    _add_db_arg(knowledge_edge_shadow_sample_freeze_parser)
    knowledge_edge_shadow_sample_freeze_parser.add_argument("--window-start", required=True)
    knowledge_edge_shadow_sample_freeze_parser.add_argument("--window-end", required=True)
    knowledge_edge_shadow_sample_freeze_parser.add_argument("--lane-d-window-end", default=None)
    knowledge_edge_shadow_sample_freeze_parser.add_argument("--sample-date", required=True)
    knowledge_edge_shadow_sample_freeze_parser.add_argument("--now", default=None)
    knowledge_edge_shadow_sample_freeze_parser.add_argument(
        "--coverage-gap", action="append", default=None, help="May be repeated."
    )
    knowledge_edge_shadow_sample_freeze_parser.add_argument("--markdown-output-file", required=True)
    knowledge_edge_shadow_sample_freeze_parser.add_argument("--json-output-file", required=True)
    _add_json_arg(knowledge_edge_shadow_sample_freeze_parser)
    knowledge_edge_shadow_sample_freeze_parser.set_defaults(
        func=_command_knowledge_edge_shadow_sample_freeze
    )

    knowledge_edge_shadow_grade_init_parser = knowledge_edge_shadow_subparsers.add_parser(
        "grade-init",
        help=(
            "Render a blank grades-file skeleton for an already-frozen sample "
            "(precision item ids pre-populated, referencing the frozen checksum)."
        ),
    )
    knowledge_edge_shadow_grade_init_parser.add_argument("--sample-json-file", required=True)
    knowledge_edge_shadow_grade_init_parser.add_argument("--output-file", required=True)
    _add_json_arg(knowledge_edge_shadow_grade_init_parser)
    knowledge_edge_shadow_grade_init_parser.set_defaults(
        func=_command_knowledge_edge_shadow_grade_init
    )

    knowledge_edge_shadow_report_parser = knowledge_edge_shadow_subparsers.add_parser(
        "report",
        help="Generate the shadow report from an ACKNOWLEDGED sample paired with a matching grades file (R3-04).",
    )
    _add_db_arg(knowledge_edge_shadow_report_parser)
    knowledge_edge_shadow_report_parser.add_argument("--sample-markdown-file", required=True)
    knowledge_edge_shadow_report_parser.add_argument("--sample-json-file", required=True)
    knowledge_edge_shadow_report_parser.add_argument("--grades-json-file", required=True)
    knowledge_edge_shadow_report_parser.add_argument("--report-date", required=True)
    knowledge_edge_shadow_report_parser.add_argument(
        "--person-search-calls-made", type=int, default=None
    )
    knowledge_edge_shadow_report_parser.add_argument("--output-file", required=True)
    _add_json_arg(knowledge_edge_shadow_report_parser)
    knowledge_edge_shadow_report_parser.set_defaults(func=_command_knowledge_edge_shadow_report)

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
