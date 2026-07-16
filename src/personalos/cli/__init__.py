"""Operator CLI for safe no-send Personal OS workflows.

This package re-exports the full historical public+private API of the
former ``personalos.cli`` module (now split by domain across submodules),
so every existing ``from personalos import cli`` / ``cli.<name>`` call site
-- including the installed ``personalos = "personalos.cli:main"`` entry
point and direct private-name access such as ``cli._connect_read_write``
-- keeps working unchanged.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections.abc import Iterable, Mapping, Sequence
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from personalos.briefings import generate_no_send_briefing_preview, read_briefing_output
from personalos.config import DEFAULT_TIMEZONE
from personalos.dashboard import render_today_view_html_from_connection
from personalos.path_safety import (
    is_under_repo,
    is_under_temp,
    validate_existing_input_file_path,
    validate_existing_sqlite_path,
    validate_output_file_path,
)
from personalos.priorities import (
    PriorityEnginePermissionDenied,
    create_priority_flow,
    read_priorities,
    update_priority_flow,
)
from personalos.routines import (
    RoutineEnginePermissionDenied,
    create_routine_record,
    read_routines,
    update_routine_record,
)
from personalos.side_effects import (
    create_external_write_intent_and_record_dry_run,
    summarize_side_effect_ledgers,
)
from personalos.scheduler import (
    BRIEFING_WINDOWS,
    SAFE_NO_SEND_SEED_PROFILE,
    SIMULATED_JOB_TYPES,
    list_scheduler_jobs,
    preview_scheduler_jobs,
    run_scheduler_job_simulated,
    seed_dev_scheduler_jobs,
)
from personalos.state import PRIORITY_STATUSES, ROUTINE_STATUSES
from personalos.synthesis_apply import (
    SynthesisApplyValidationError,
    apply_synthesis_import_preview,
    stable_approval_source_hash,
)
from personalos.status import create_rail_state_report, create_status_summary
from personalos.synthesis_import import (
    ALLOWED_SOURCE_TYPES,
    REPORT_SAFETY_FLAGS,
    SynthesisImportValidationError,
    create_synthesis_import_preview_record,
)
from personalos.today import create_today_view_summary

from personalos.cli.briefing import _command_briefing_export, _command_briefing_preview
from personalos.cli.db import _connect_read_only, _connect_read_write, _with_workflow_context
from personalos.cli.dispatch import _command_dispatch_morning
from personalos.cli.errors import CliError
from personalos.cli.knowledge_edge import (
    _command_knowledge_edge_flag_false_positive,
    _command_knowledge_edge_queue_show,
    _command_knowledge_edge_scan,
)
from personalos.cli.parser import (
    PersonalOSArgumentParser,
    _add_date_timezone_args,
    _add_db_arg,
    _add_json_arg,
    build_parser,
)
from personalos.cli.priorities import (
    _command_priorities_create,
    _command_priorities_list,
    _command_priorities_update,
)
from personalos.cli.reporting import (
    _append_candidate_or_ledger_summary,
    _append_rail_state_lines,
    _append_workflow_catalog_lines,
    _append_workflow_completion_lines,
    _blocked_actions_for_report,
    _database_target_report,
    _database_target_text,
    _emit_report,
    _format_cli_error,
    _format_scalar,
    _human_report,
    _load_json_object,
    _loads_json_object,
    _local_sqlite_changes_text,
    _output_target_report,
    _output_target_text,
    _parse_json_object_arg,
    _safety_flags_from_report,
    _yes_no_unavailable,
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
from personalos.cli.synthesis import (
    _command_synthesis_apply,
    _command_synthesis_preview,
    _merge_synthesis_source_type,
    _synthesis_rejected_result,
)
from personalos.cli.today import (
    _command_dashboard_render,
    _command_run_morning,
    _command_today,
    _has_text,
    _today_iso,
)
from personalos.cli.workflows import (
    SAFE_LOCAL_WORKFLOW_SPECS,
    _command_demo_no_send_e2e,
    _command_status,
    _command_workflows,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.func(args)
    except CliError as error:
        print(f"error: {_format_cli_error(error)}", file=sys.stderr)
        return 1
    except (OSError, PermissionError, sqlite3.Error, ValueError) as error:
        print(f"error: {_format_cli_error(error)}", file=sys.stderr)
        return 1
    return result
