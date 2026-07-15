"""Routine record create/update/list commands."""

from __future__ import annotations

import argparse
from contextlib import closing

from personalos.cli.db import _connect_read_only, _connect_read_write, _with_workflow_context
from personalos.cli.errors import CliError
from personalos.cli.reporting import _emit_report, _parse_json_object_arg
from personalos.routines import (
    RoutineEnginePermissionDenied,
    create_routine_record,
    read_routines,
    update_routine_record,
)


def _command_routines_create(args: argparse.Namespace) -> int:
    settings = _parse_json_object_arg(args.settings_json, field_name="--settings-json")
    cadence_config = _parse_json_object_arg(
        args.cadence_config_json,
        field_name="--cadence-config-json",
    )
    try:
        with closing(_connect_read_write(args.db)) as connection:
            routine = create_routine_record(
                connection,
                routine_id=args.routine_id,
                name=args.name,
                status=args.status,
                enabled=args.enabled,
                settings=settings,
                notes=args.notes,
                cadence_type=args.cadence_type,
                cadence_config=cadence_config,
                missed_behavior_default=args.missed_behavior,
                rotation_group=args.rotation_group,
                weekly_target=args.weekly_target,
            )
    except RoutineEnginePermissionDenied as error:
        raise CliError(str(error)) from error
    report = _with_workflow_context(
        {
            "command": "routines create",
            "status": "created",
            "database_write": True,
            "external_mutation": False,
            "no_external_writes": True,
            "routine": routine,
        },
        workflow_name="Create routine record",
        workflow_mode="inert / no-send / local write",
        database_path=args.db,
        database_access="read_write_routine_create",
        local_sqlite_read=True,
        local_sqlite_changed=True,
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Review the created routine record.",
            "Run personalos routines list to confirm it appears.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0


def _command_routines_update(args: argparse.Namespace) -> int:
    settings = _parse_json_object_arg(args.settings_json, field_name="--settings-json")
    cadence_config = _parse_json_object_arg(
        args.cadence_config_json,
        field_name="--cadence-config-json",
    )
    if (
        args.name is None
        and args.status is None
        and args.enabled is None
        and args.notes is None
        and settings is None
        and args.cadence_type is None
        and cadence_config is None
        and args.missed_behavior is None
        and args.rotation_group is None
        and args.weekly_target is None
    ):
        raise CliError(
            "routines update requires at least one of "
            "--name/--status/--enabled/--no-enabled/--notes/--settings-json/"
            "--cadence-type/--cadence-config-json/--missed-behavior/--rotation-group/"
            "--weekly-target"
        )
    try:
        with closing(_connect_read_write(args.db)) as connection:
            routine = update_routine_record(
                connection,
                routine_id=args.routine_id,
                name=args.name,
                status=args.status,
                enabled=args.enabled,
                settings=settings,
                notes=args.notes,
                cadence_type=args.cadence_type,
                cadence_config=cadence_config,
                missed_behavior_default=args.missed_behavior,
                rotation_group=args.rotation_group,
                weekly_target=args.weekly_target,
            )
    except RoutineEnginePermissionDenied as error:
        raise CliError(str(error)) from error
    report = _with_workflow_context(
        {
            "command": "routines update",
            "status": "updated",
            "database_write": True,
            "external_mutation": False,
            "no_external_writes": True,
            "routine": routine,
        },
        workflow_name="Update routine record",
        workflow_mode="inert / no-send / local write",
        database_path=args.db,
        database_access="read_write_routine_update",
        local_sqlite_read=True,
        local_sqlite_changed=True,
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Review the updated routine record.",
            "Run personalos routines list to confirm the change.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0


def _command_routines_list(args: argparse.Namespace) -> int:
    try:
        with closing(_connect_read_only(args.db)) as connection:
            routines = read_routines(connection)
    except RoutineEnginePermissionDenied as error:
        raise CliError(str(error)) from error
    report = _with_workflow_context(
        {
            "command": "routines list",
            "status": "completed",
            "database_write": False,
            "external_mutation": False,
            "no_external_writes": True,
            "routine_count": len(routines),
            "routines": routines,
        },
        workflow_name="List routine records",
        workflow_mode="inert / no-send / report-only",
        database_path=args.db,
        database_access="read_only_routine_list",
        local_sqlite_read=True,
        local_sqlite_changed=False,
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Review routine records.",
            "Run personalos routines update to edit or disable a routine.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0
