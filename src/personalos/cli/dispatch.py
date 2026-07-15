"""Live rail dispatch CLI command (H2, D-PO-017).

Genuinely separate from `personalos run morning` (`cli/today.py`): that command is a
permanent foreground no-send simulation and never reaches a live rail. This command
CAN make a real external write -- once, and only for, a rail that is actually live
(`personalos.status.RAIL_STATES`) -- via `personalos.rail_dispatch`.
"""

from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from personalos.cli.db import _connect_read_write, _with_workflow_context
from personalos.cli.errors import CliError
from personalos.cli.reporting import _emit_report
from personalos.rail_dispatch import dispatch_morning_candidates


def _command_dispatch_morning(args: argparse.Namespace) -> int:
    resolved_date = args.date or _today_iso(args.timezone)

    # NOT allow_production_path=True: D-PO-011/P-SCHED-04 approved the production DB
    # path exemption for `run morning` only. Widening that exemption to this new
    # command is a separate decision this packet does not make -- it belongs with
    # whichever future G5 packet actually flips a rail live (D-PO-017 item 7), not
    # with making the dispatch path reachable against explicit temp/dev DBs.
    with closing(_connect_read_write(args.db)) as connection:
        result = dispatch_morning_candidates(
            connection,
            source_date=resolved_date,
            timezone=args.timezone,
            briefing_window_name="morning",
        )

    report = _with_workflow_context(
        {"command": "dispatch morning", **result},
        workflow_name="Morning rail dispatch (manual trigger)",
        workflow_mode=(
            "live-capable / per-rail dispatch-or-preview -- see rail_states for what "
            "is actually live right now"
        ),
        database_path=args.db,
        database_access="read_write_local_morning_dispatch",
        local_sqlite_read=True,
        local_sqlite_changed=bool(result.get("database_write", False)),
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Review the dispatch report's per-candidate outcomes and rail rollup counts.",
            "Inspect side-effects/idempotency ledger rows for anything with outcome=dispatched.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0 if result.get("status") == "completed" else 1


def _today_iso(timezone: str) -> str:
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as error:
        raise CliError(f"timezone must be a valid IANA timezone name: {timezone}") from error
    return datetime.now(zone).date().isoformat()
