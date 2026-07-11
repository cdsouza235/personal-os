"""ChatGPT synthesis preview and approved local apply commands."""

from __future__ import annotations

import argparse
import json
from contextlib import closing
from typing import Any

from personalos.cli.db import _connect_read_write, _with_workflow_context
from personalos.cli.errors import CliError
from personalos.cli.reporting import _emit_report, _loads_json_object
from personalos.path_safety import validate_existing_input_file_path
from personalos.synthesis_apply import (
    SynthesisApplyValidationError,
    apply_synthesis_import_preview,
    stable_approval_source_hash,
)
from personalos.synthesis_import import (
    REPORT_SAFETY_FLAGS,
    SynthesisImportValidationError,
    create_synthesis_import_preview_record,
)


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
