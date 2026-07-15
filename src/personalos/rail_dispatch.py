"""Live rail dispatcher (H2, D-PO-017) -- the sole path by which a real morning-cycle
candidate can reach a live external rail.

Genuinely separate from `run morning`'s foreground no-send simulation and the
simulated scheduler (`scheduler.py`), which actively rejects any live-shaped job type
(`_FORBIDDEN_JOB_TYPE_MARKERS`) and unconditionally stamps `SCHEDULER_SAFETY_FLAGS`.
This module is never called from `run_scheduler_job_simulated` or
`_run_simulated_workflow`; see `cli/dispatch.py` for the sibling CLI command, and
`audits/h2-rail-dispatch-design-consult-fable-report.md` plus D-PO-017
(`governance/living/agent-writable/DECISIONS.md`) for the design this implements.

Candidate computation is delegated entirely to
`personalos.briefings.build_no_send_candidate_output` -- the exact same function the
no-send preview path calls -- so a preview and a dispatch of the same inputs are
provably operating on the same `output_json`.

Per-candidate decision, in fixed order (Todoist candidates dispatch before the Gmail
candidate, so a Gmail failure never blocks or rolls back Todoist tasks already
created):

  1. Route by `RAIL_STATES[rail]` (advisory, cheap): not "live" -> preview, no rail
     call is made.
  2. If "live", call the real rail function with the candidate's own fields. The rail
     function enforces its own four fixed gates (permission -> ledger/dedupe ->
     rail-state -> credentials) and returns a structured refusal; this module never
     pre-checks or re-derives those gates -- it only translates the result into a
     report entry.
  3. Nothing is ever automatically retried.

Calendar candidates and follow-ups are always previewed: calendar dispatch is out of
scope for H2 (D-PO-017 doesn't cover it), and follow-ups have no rail at all.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Any

from personalos.briefings import (
    build_no_send_candidate_output,
    evaluate_briefing_generation_permissions,
)
from personalos.rails import gmail as gmail_rail
from personalos.rails import todoist as todoist_rail
from personalos.status import RAIL_STATES

OUTCOME_DISPATCHED = "dispatched"
OUTCOME_PREVIEW = "preview"
OUTCOME_BLOCKED = "blocked"
OUTCOME_FAILED = "failed"


def dispatch_morning_candidates(
    connection: sqlite3.Connection,
    *,
    source_date: str,
    timezone: str,
    briefing_window_name: str = "morning",
    run_at: str | None = None,
) -> dict[str, Any]:
    """Compute the morning cycle's candidates -- identically to the no-send preview --
    and dispatch each one to its live rail if, and only if, that rail is live; every
    other candidate is reported as a preview. Returns a `dispatch_report`-shaped dict.
    Never raises for an expected rail refusal.
    """
    permissions = evaluate_briefing_generation_permissions(connection)
    denied = next((permission for permission in permissions.values() if not permission["allowed"]), None)
    if denied is not None:
        return _blocked_report(
            reason=denied["reason"],
            source_date=source_date,
            timezone=timezone,
            briefing_window_name=briefing_window_name,
            permissions=permissions,
        )

    candidates = build_no_send_candidate_output(
        connection,
        source_date=source_date,
        timezone=timezone,
        briefing_window_name=briefing_window_name,
        run_at=run_at,
    )
    composer_result = candidates["composer_result"]
    output = composer_result.get("output") if composer_result["status"] == "completed" else None
    if output is None:
        return _generation_failed_report(
            reason=str(composer_result.get("reason", "Candidate generation failed.")),
            source_date=candidates["source_date"],
            timezone=candidates["timezone"],
            briefing_window_name=candidates["briefing_window_name"],
            permissions=permissions,
        )

    output_json = output["output_json"]
    per_candidate: list[dict[str, Any]] = []

    todoist_rollup = {"dispatched": 0, "preview": 0, "blocked": 0, "failed": 0}
    for index, candidate in enumerate(output_json.get("todoist_tasks", [])):
        entry = _dispatch_todoist_candidate(connection, candidate=candidate, index=index)
        per_candidate.append(entry)
        todoist_rollup[entry["outcome"]] += 1

    gmail_rollup = {"dispatched": 0, "preview": 0, "blocked": 0, "failed": 0}
    gmail_entries: list[dict[str, Any]] = []
    for index, candidate in enumerate(output_json.get("email_briefs", [])):
        entry = _dispatch_gmail_candidate(connection, candidate=candidate, index=index)
        per_candidate.append(entry)
        gmail_entries.append(entry)
        gmail_rollup[entry["outcome"]] += 1

    calendar_candidates = output_json.get("calendar_blocks", [])
    for index, candidate in enumerate(calendar_candidates):
        per_candidate.append(
            _preview_entry(
                rail="calendar",
                candidate_type="calendar_block",
                index=index,
                candidate=candidate,
                reason="Calendar dispatch is out of scope for H2 (D-PO-017).",
            )
        )

    followup_candidates = output_json.get("followups", [])
    for index, candidate in enumerate(followup_candidates):
        per_candidate.append(
            _preview_entry(
                rail=None,
                candidate_type="followup",
                index=index,
                candidate=candidate,
                reason="Follow-ups have no rail; always preview.",
            )
        )

    live_write = todoist_rollup["dispatched"] > 0 or gmail_rollup["dispatched"] > 0
    external_writes = _external_writes_text(todoist_rollup=todoist_rollup, gmail_rollup=gmail_rollup)
    warnings: list[str] = []
    if gmail_rollup["failed"]:
        warnings.append(
            "Gmail dispatch failed; not retried. Todoist tasks already dispatched "
            "were not rolled back."
        )

    return {
        "status": "completed",
        "reason": (
            "Rail dispatch attempted for each rail-eligible candidate; see "
            "candidates for the per-candidate outcome."
        ),
        "source_date": candidates["source_date"],
        "timezone": candidates["timezone"],
        "briefing_window_name": candidates["briefing_window_name"],
        "packet_id": candidates["packet_id"],
        "database_write": True,
        "live_write": live_write,
        "external_mutation": live_write,
        "external_writes": external_writes,
        "no_external_writes": not live_write,
        "no_send_mode": not live_write,
        "no_live_model_call": True,
        "no_calendar_writes": True,
        "no_gmail_draft": True,
        "no_todoist_writes": todoist_rollup["dispatched"] == 0,
        "no_gmail_send": gmail_rollup["dispatched"] == 0,
        "permissions": {key: dict(value) for key, value in permissions.items()},
        "candidates": per_candidate,
        "rollup": {
            "todoist": todoist_rollup,
            "gmail": gmail_rollup,
            "calendar": {"preview": len(calendar_candidates)},
            "followups": {"preview": len(followup_candidates)},
        },
        "report_text": _build_report_text(todoist_rollup=todoist_rollup, gmail_entries=gmail_entries),
        "warnings": warnings,
    }


def _dispatch_todoist_candidate(
    connection: sqlite3.Connection,
    *,
    candidate: Mapping[str, Any],
    index: int,
) -> dict[str, Any]:
    candidate = dict(candidate)
    rail_state = RAIL_STATES["todoist"]
    if rail_state != "live":
        return _preview_entry(
            rail="todoist",
            candidate_type="todoist_task",
            index=index,
            candidate=candidate,
            reason=f"Todoist rail state is '{rail_state}', not 'live'; routed to preview.",
        )
    result = todoist_rail.create_live_todoist_task(connection, **candidate)
    external_id = None
    if result.get("status") == todoist_rail.STATUS_CLIENT_CALL_PASSED:
        client_result = result.get("client_result") or {}
        external_id = client_result.get("external_task_id")
    return _translate_rail_result(
        rail="todoist",
        candidate_type="todoist_task",
        index=index,
        candidate=candidate,
        result=result,
        passed_status=todoist_rail.STATUS_CLIENT_CALL_PASSED,
        external_id=external_id,
    )


def _dispatch_gmail_candidate(
    connection: sqlite3.Connection,
    *,
    candidate: Mapping[str, Any],
    index: int,
) -> dict[str, Any]:
    candidate = dict(candidate)
    rail_state = RAIL_STATES["gmail"]
    if rail_state != "live":
        return _preview_entry(
            rail="gmail",
            candidate_type="email_brief",
            index=index,
            candidate=candidate,
            reason=f"Gmail rail state is '{rail_state}', not 'live'; routed to preview.",
        )
    # No recipient pre-check here: `to_address` is populated unconditionally from the
    # controlled-recipient env var at candidate-construction time (composer.py), and
    # `send_live_gmail_message`'s own recipient_scoping gate is the sole authority on
    # whether it's acceptable -- this dispatcher must not re-derive that decision.
    result = gmail_rail.send_live_gmail_message(connection, **candidate)
    external_id = None
    if result.get("status") == gmail_rail.STATUS_CLIENT_CALL_PASSED:
        would_write = result.get("would_write") or {}
        external_id = would_write.get("gmail_message_id")
    return _translate_rail_result(
        rail="gmail",
        candidate_type="email_brief",
        index=index,
        candidate=candidate,
        result=result,
        passed_status=gmail_rail.STATUS_CLIENT_CALL_PASSED,
        external_id=external_id,
    )


def _translate_rail_result(
    *,
    rail: str,
    candidate_type: str,
    index: int,
    candidate: Mapping[str, Any],
    result: Mapping[str, Any],
    passed_status: str,
    external_id: str | None,
) -> dict[str, Any]:
    gate_failed = result.get("gate_failed")
    status = result.get("status")
    if gate_failed is None and status == passed_status:
        outcome = OUTCOME_DISPATCHED
    elif gate_failed is not None:
        outcome = OUTCOME_BLOCKED
    else:
        outcome = OUTCOME_FAILED
    return {
        "candidate_id": _candidate_identifier(candidate, index=index, candidate_type=candidate_type),
        "candidate_type": candidate_type,
        "rail": rail,
        "outcome": outcome,
        "status": status,
        "gate_failed": gate_failed,
        "reason": result.get("reason"),
        "idempotency_key": result.get("idempotency_key"),
        "external_id": external_id if outcome == OUTCOME_DISPATCHED else None,
    }


def _preview_entry(
    *,
    rail: str | None,
    candidate_type: str,
    index: int,
    candidate: Mapping[str, Any],
    reason: str,
) -> dict[str, Any]:
    return {
        "candidate_id": _candidate_identifier(candidate, index=index, candidate_type=candidate_type),
        "candidate_type": candidate_type,
        "rail": rail,
        "outcome": OUTCOME_PREVIEW,
        "status": None,
        "gate_failed": None,
        "reason": reason,
        "idempotency_key": None,
        "external_id": None,
    }


def _candidate_identifier(candidate: Mapping[str, Any], *, index: int, candidate_type: str) -> str:
    dedupe_key = candidate.get("dedupe_key")
    if isinstance(dedupe_key, str) and dedupe_key.strip():
        return dedupe_key
    return f"{candidate_type}[{index}]"


def _build_report_text(
    *,
    todoist_rollup: Mapping[str, int],
    gmail_entries: list[dict[str, Any]],
) -> str:
    todoist_extras = []
    if todoist_rollup["blocked"]:
        todoist_extras.append(f"{todoist_rollup['blocked']} blocked")
    if todoist_rollup["failed"]:
        todoist_extras.append(f"{todoist_rollup['failed']} failed")
    if todoist_rollup["preview"]:
        todoist_extras.append(f"{todoist_rollup['preview']} previewed")
    todoist_text = f"Todoist: {todoist_rollup['dispatched']} dispatched"
    if todoist_extras:
        todoist_text += ", " + ", ".join(todoist_extras)
    todoist_text += "."

    if not gmail_entries:
        gmail_text = "Gmail: no email brief candidate."
    else:
        entry = gmail_entries[0]
        if entry["outcome"] == OUTCOME_DISPATCHED:
            gmail_text = "Gmail: 1 dispatched."
        elif entry["outcome"] == OUTCOME_FAILED:
            gmail_text = "Gmail: FAILED (not retried)."
        elif entry["outcome"] == OUTCOME_BLOCKED:
            gmail_text = f"Gmail: blocked ({entry.get('gate_failed')})."
        else:
            gmail_text = "Gmail: previewed (not live)."

    return f"{todoist_text} {gmail_text}"


def _external_writes_text(
    *,
    todoist_rollup: Mapping[str, int],
    gmail_rollup: Mapping[str, int],
) -> str:
    parts = []
    if todoist_rollup["dispatched"]:
        parts.append(f"todoist:{todoist_rollup['dispatched']}_task(s)_created")
    if gmail_rollup["dispatched"]:
        parts.append("gmail:1_message_sent")
    return ", ".join(parts) if parts else "none"


def _blocked_report(
    *,
    reason: str,
    source_date: str,
    timezone: str,
    briefing_window_name: str,
    permissions: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": reason,
        "source_date": source_date,
        "timezone": timezone,
        "briefing_window_name": briefing_window_name,
        "packet_id": None,
        "database_write": False,
        "live_write": False,
        "external_mutation": False,
        "external_writes": "none",
        "no_external_writes": True,
        "no_send_mode": True,
        "no_live_model_call": True,
        "no_calendar_writes": True,
        "no_gmail_draft": True,
        "no_todoist_writes": True,
        "no_gmail_send": True,
        "permissions": {key: dict(value) for key, value in permissions.items()},
        "candidates": [],
        "rollup": {},
        "report_text": f"Blocked before candidate generation: {reason}",
        "warnings": [reason],
    }


def _generation_failed_report(
    *,
    reason: str,
    source_date: str,
    timezone: str,
    briefing_window_name: str,
    permissions: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "status": "failed",
        "reason": reason,
        "source_date": source_date,
        "timezone": timezone,
        "briefing_window_name": briefing_window_name,
        "packet_id": None,
        "database_write": True,
        "live_write": False,
        "external_mutation": False,
        "external_writes": "none",
        "no_external_writes": True,
        "no_send_mode": True,
        "no_live_model_call": True,
        "no_calendar_writes": True,
        "no_gmail_draft": True,
        "no_todoist_writes": True,
        "no_gmail_send": True,
        "permissions": {key: dict(value) for key, value in permissions.items()},
        "candidates": [],
        "rollup": {},
        "report_text": f"Candidate generation failed before any rail dispatch: {reason}",
        "warnings": [reason],
    }
