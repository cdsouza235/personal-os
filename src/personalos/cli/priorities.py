"""Priority record create/update/list commands."""

from __future__ import annotations

import argparse
from contextlib import closing

from personalos.cli.db import _connect_read_only, _connect_read_write, _with_workflow_context
from personalos.cli.errors import CliError
from personalos.cli.reporting import _emit_report, _parse_json_object_arg
from personalos.priorities import (
    PriorityEnginePermissionDenied,
    create_priority_flow,
    read_priorities,
    update_priority_flow,
)


def _command_priorities_create(args: argparse.Namespace) -> int:
    metadata = _parse_json_object_arg(args.metadata_json, field_name="--metadata-json")
    with closing(_connect_read_write(args.db)) as connection:
        result = create_priority_flow(
            connection,
            priority_id=args.priority_id,
            title=args.title,
            status=args.status,
            metadata=metadata,
            notes=args.notes,
            dry_run=False,
        )
    report = _with_workflow_context(
        {"command": "priorities create", **result},
        workflow_name="Create priority record",
        workflow_mode="inert / no-send / local write",
        database_path=args.db,
        database_access="read_write_priority_create",
        local_sqlite_read=True,
        local_sqlite_changed=bool(result.get("database_write")),
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Review the created priority record.",
            "Run personalos priorities list to confirm it appears.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0 if result.get("status") == "created" else 1


def _command_priorities_update(args: argparse.Namespace) -> int:
    metadata = _parse_json_object_arg(args.metadata_json, field_name="--metadata-json")
    if (
        args.title is None
        and args.status is None
        and args.notes is None
        and metadata is None
    ):
        raise CliError(
            "priorities update requires at least one of "
            "--title/--status/--notes/--metadata-json"
        )
    with closing(_connect_read_write(args.db)) as connection:
        result = update_priority_flow(
            connection,
            priority_id=args.priority_id,
            title=args.title,
            status=args.status,
            metadata=metadata,
            notes=args.notes,
            dry_run=False,
        )
    report = _with_workflow_context(
        {"command": "priorities update", **result},
        workflow_name="Update priority record",
        workflow_mode="inert / no-send / local write",
        database_path=args.db,
        database_access="read_write_priority_update",
        local_sqlite_read=True,
        local_sqlite_changed=bool(result.get("database_write")),
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Review the updated priority record.",
            "Run personalos priorities list to confirm the change.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0 if result.get("status") == "updated" else 1


def _command_priorities_list(args: argparse.Namespace) -> int:
    try:
        with closing(_connect_read_only(args.db)) as connection:
            priorities = read_priorities(connection, status=args.status)
    except PriorityEnginePermissionDenied as error:
        raise CliError(str(error)) from error
    report = _with_workflow_context(
        {
            "command": "priorities list",
            "status": "completed",
            "database_write": False,
            "external_mutation": False,
            "no_external_writes": True,
            "priority_count": len(priorities),
            "priorities": priorities,
        },
        workflow_name="List priority records",
        workflow_mode="inert / no-send / report-only",
        database_path=args.db,
        database_access="read_only_priority_list",
        local_sqlite_read=True,
        local_sqlite_changed=False,
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Review priority records.",
            "Run personalos priorities update to edit a priority.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0
