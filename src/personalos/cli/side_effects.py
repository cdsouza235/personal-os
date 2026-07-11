"""Side-effect and idempotency ledger inspection/recording commands."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from contextlib import closing

from personalos.cli.db import _connect_read_only, _connect_read_write, _with_workflow_context
from personalos.cli.errors import CliError
from personalos.cli.reporting import _emit_report, _load_json_object
from personalos.path_safety import validate_existing_input_file_path
from personalos.side_effects import (
    create_external_write_intent_and_record_dry_run,
    summarize_side_effect_ledgers,
)


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
