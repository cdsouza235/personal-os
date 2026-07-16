"""Shared report formatting/emission helpers used across multiple CLI domains."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from personalos.cli.errors import CliError
from personalos.path_safety import is_under_repo, is_under_temp


def _database_target_report(
    database_path: str | Path | None,
    *,
    database_access: str,
) -> dict[str, Any]:
    if database_path is None:
        return {
            "path": None,
            "path_classification": "not_applicable_no_db_opened",
            "access": database_access,
            "safe_local_db": False,
            "production_db_active": False,
        }
    path = Path(database_path).expanduser().resolve()
    if is_under_temp(path):
        classification = "temporary_test_local_safe_db"
    elif is_under_repo(path):
        classification = "repo_local_dev_safe_db"
    else:
        classification = "unknown_explicit_sqlite"
    return {
        "path": str(path),
        "path_classification": classification,
        "access": database_access,
        "safe_local_db": classification in {
            "temporary_test_local_safe_db",
            "repo_local_dev_safe_db",
        },
        "production_db_active": False,
    }


def _output_target_report(
    output_kind: str,
    *,
    output_file: str | Path | None,
) -> dict[str, Any]:
    path = str(Path(output_file).expanduser().resolve()) if output_file else None
    return {
        "kind": output_kind,
        "path": path,
    }


def _format_cli_error(error: BaseException) -> str:
    message = str(error)
    if "No external writes were attempted." in message:
        return message
    if "must contain JSON" in message:
        return (
            f"{message}\n"
            "No external writes were attempted.\n"
            "Next: fix the JSON file and rerun the same no-send command."
        )
    if "must point to an existing SQLite file" in message:
        return (
            f"{message}\n"
            "No external writes were attempted.\n"
            "Next: rerun with --db <path-to-local-test-db>."
        )
    if "must point to an existing file" in message:
        return (
            f"{message}\n"
            "No external writes were attempted.\n"
            "Next: rerun with an explicit temp/dev input file."
        )
    if "not found" in message or "permission" in message.lower() or "blocked" in message:
        return (
            f"{message}\n"
            "No external writes were attempted.\n"
            "Next: use a safe local preview/status command or fix the local dev/test input."
        )
    return message


def _parse_json_object_arg(value: str | None, *, field_name: str) -> dict[str, Any] | None:
    if value is None:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as error:
        raise CliError(f"{field_name} must contain JSON: {error}") from error
    if not isinstance(parsed, dict):
        raise CliError(f"{field_name} JSON must decode to an object")
    return parsed


def _load_json_object(path: Any) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise CliError(f"input file must contain JSON: {error}") from error
    if not isinstance(payload, dict):
        raise CliError("input file JSON must decode to an object")
    return payload


def _loads_json_object(payload_bytes: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise CliError("input file must be UTF-8 JSON") from error
    except json.JSONDecodeError as error:
        raise CliError(f"input file must contain JSON: {error}") from error
    if not isinstance(payload, dict):
        raise CliError("input file JSON must decode to an object")
    return payload


def _safety_flags_from_report(report: object) -> dict[str, bool]:
    source = report if isinstance(report, Mapping) else {}
    return {
        "no_external_writes": source.get("no_external_writes") is True,
        "no_send_mode": source.get("no_send_mode") is True,
        "no_live_model_call": source.get("no_live_model_call") is True,
        "no_todoist_writes": source.get("no_todoist_writes") is True,
        "no_calendar_writes": source.get("no_calendar_writes") is True,
        "no_gmail_send": source.get("no_gmail_send") is True,
        "no_gmail_draft": source.get("no_gmail_draft") is True,
    }


def _emit_report(report: Mapping[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(
            json.dumps(
                report,
                allow_nan=False,
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            )
        )
        return
    print(_human_report(report))


def _human_report(report: Mapping[str, Any]) -> str:
    lines: list[str] = []
    _append_workflow_completion_lines(lines, report)

    if report.get("command") == "workflows":
        _append_workflow_catalog_lines(lines, report)

    lines.extend(
        [
        f"command: {report.get('command', 'unknown')}",
        f"status: {report.get('status', 'unknown')}",
        ]
    )
    for key in (
        "reason",
        "briefing_window_name",
        "briefing_output_id",
        "output_file",
        "database_write",
        "file_write",
        "external_mutation",
        "no_external_writes",
        "no_send_mode",
        "no_live_model_call",
        "no_todoist_writes",
        "no_calendar_writes",
        "no_gmail_send",
        "no_gmail_draft",
        "no_personalos_writes",
        "live_write",
        "internal_state_mutation",
        "simulated_or_dry_run",
        "static_html_only",
        "apply_run_id",
        "scheduler_run_id",
        "scheduler_job_id",
        "scheduler_activation",
        "launch_agent_installed",
        "daemonized",
        "background_process_started",
        "preview_id",
        "approval_source_hash",
        "fixture_set",
        "scan_run_id",
        "media_items_created",
        "media_items_reprocessed",
        "events_created",
        "events_reprocessed",
        "sources_healthy",
        "sources_failed",
        "queue_snapshot_rows_created",
    ):
        if key in report:
            lines.append(f"{key}: {_format_scalar(report[key])}")

    top_level_rail_states = report.get("rail_states")
    if isinstance(top_level_rail_states, Mapping):
        _append_rail_state_lines(lines, top_level_rail_states)

    summary = report.get("summary")
    if isinstance(summary, Mapping):
        counts = summary.get("counts")
        if isinstance(counts, Mapping):
            lines.append(
                "counts: "
                + ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
            )
        source_date = summary.get("source_date")
        timezone = summary.get("timezone")
        if source_date:
            lines.append(f"source_date: {source_date}")
        if timezone:
            lines.append(f"timezone: {timezone}")
    scheduler_run = report.get("scheduler_run")
    if isinstance(scheduler_run, Mapping):
        lines.append(f"scheduler_run_id: {scheduler_run.get('scheduler_run_id')}")
        lines.append(f"job_type: {scheduler_run.get('job_type')}")

    preview_report = report.get("preview_report")
    if isinstance(preview_report, Mapping):
        preview_id = preview_report.get("preview_id")
        candidate_counts = preview_report.get("candidate_counts")
        if preview_id:
            lines.append(f"preview_id: {preview_id}")
        if isinstance(candidate_counts, Mapping):
            lines.append(
                "candidate_counts: "
                + ", ".join(
                    f"{key}={value}" for key, value in sorted(candidate_counts.items())
                )
            )

    queue_summary = report.get("queue_summary")
    if isinstance(queue_summary, Mapping):
        _append_knowledge_edge_queue_lines(lines, queue_summary)

    entity_match = report.get("entity_match")
    if isinstance(entity_match, Mapping):
        lines.append(f"entity_match_id: {entity_match.get('entity_match_id')}")
        lines.append(f"is_false_positive: {_format_scalar(entity_match.get('is_false_positive'))}")

    warnings = report.get("warnings")
    if isinstance(warnings, list) and warnings:
        lines.append("warnings:")
        lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines)


# Mirrors knowledge_edge/dashboard.py's own section titles/order (PRD amendment
# Sec7.2) so the CLI human view surfaces the same section headings as the dashboard,
# not just their row counts.
_KNOWLEDGE_EDGE_SECTION_TITLES: dict[str, str] = {
    "tomorrow_earnings_events": "Tomorrow: Earnings & Corporate Events",
    "p0_consequential_leaders": "P0: Consequential Leader Appearances",
    "p1_core_podcasts": "P1: Core Podcast Releases",
    "p2_market_voices": "P2: Market Voice Appearances",
    "saved_to_reconsider": "Saved to Reconsider",
}
_KNOWLEDGE_EDGE_SECTION_ORDER = (
    "tomorrow_earnings_events",
    "p0_consequential_leaders",
    "p1_core_podcasts",
    "p2_market_voices",
    "saved_to_reconsider",
)


def _append_knowledge_edge_queue_lines(
    lines: list[str],
    queue_summary: Mapping[str, Any],
) -> None:
    lines.append(f"knowledge_edge_feature_mode: {queue_summary.get('feature_mode')}")
    if not queue_summary.get("available"):
        return

    empty_state = queue_summary.get("empty_state")
    if empty_state:
        lines.append(f"knowledge_edge_empty_state: {empty_state}")

    sections = queue_summary.get("sections")
    if isinstance(sections, Mapping):
        for section_name in _KNOWLEDGE_EDGE_SECTION_ORDER:
            cards = sections.get(section_name)
            if not isinstance(cards, list):
                continue
            title = _KNOWLEDGE_EDGE_SECTION_TITLES.get(section_name, section_name)
            lines.append(f"{title} ({len(cards)}):")
            lines.extend(f"- {_format_knowledge_edge_card_line(card)}" for card in cards)

    demoted = queue_summary.get("demoted_ambiguous")
    if isinstance(demoted, list):
        lines.append(f"Demoted / Ambiguous ({len(demoted)}):")
        lines.extend(f"- {_format_knowledge_edge_card_line(card)}" for card in demoted)

    coverage = queue_summary.get("coverage")
    if isinstance(coverage, Mapping):
        lines.append(f"Coverage & Source Health: {coverage.get('overall_summary')}")
        per_adapter_lines = coverage.get("per_adapter_lines")
        if isinstance(per_adapter_lines, list):
            lines.extend(f"- {line}" for line in per_adapter_lines)
        honesty_note = coverage.get("honesty_note")
        if honesty_note:
            lines.append(f"knowledge_edge_coverage_honesty_note: {honesty_note}")


def _format_knowledge_edge_card_line(card: Mapping[str, Any]) -> str:
    if card.get("entity_type") == "scheduled_event":
        link = card.get("link")
        link_text = "no link available"
        if isinstance(link, Mapping):
            label = link.get("label", "")
            url = link.get("url")
            link_text = f"{label}: {url}" if url else label
        return (
            f"{card.get('company_display_name', 'unknown')} "
            f"({card.get('event_type', 'unknown')}, {card.get('scheduled_date', 'unknown')}, "
            f"{card.get('event_status', 'unknown')}) -- {link_text}"
        )
    flag = " [flagged false-positive]" if card.get("false_positive_flagged") else ""
    return (
        f"{card.get('title', 'unknown')} "
        f"[{card.get('directness_class', 'unknown')}]{flag} "
        f"-- {card.get('why_surfaced', '')}"
    )


def _append_workflow_completion_lines(
    lines: list[str],
    report: Mapping[str, Any],
) -> None:
    workflow_name = str(report.get("workflow_name") or report.get("command") or "unknown")
    workflow_mode = str(report.get("workflow_mode") or "inert / no-send / report-only")
    lines.append(f"Workflow complete: {workflow_name}")
    lines.append(f"Mode: {workflow_mode}")
    lines.append(f"DB target: {_database_target_text(report.get('database_target'))}")
    lines.append(
        "Production DB: "
        + ("active" if report.get("production_db_active") is True else "not active")
    )
    lines.append(f"Local SQLite read: {_yes_no_unavailable(report.get('local_sqlite_read'))}")
    lines.append(f"Local SQLite changes: {_local_sqlite_changes_text(report)}")
    if "internal_state_mutation" in report:
        lines.append(
            "Approved local apply: "
            + _yes_no_unavailable(report.get("internal_state_mutation"))
        )
    lines.append(f"External writes: {report.get('external_writes', 'none')}")
    lines.append(f"Credentials: {report.get('credentials', 'not_loaded').replace('_', ' ')}")
    lines.append(f"Output: {_output_target_text(report.get('output_target'))}")

    _append_candidate_or_ledger_summary(lines, report)

    safe_next_actions = report.get("safe_next_actions")
    if isinstance(safe_next_actions, list) and safe_next_actions:
        lines.append("Safe next action:")
        lines.extend(f"- {action}" for action in safe_next_actions)

    blocked_actions = _blocked_actions_for_report(report)
    if blocked_actions:
        lines.append("Blocked:")
        lines.extend(f"- {action}" for action in blocked_actions)


def _append_workflow_catalog_lines(
    lines: list[str],
    report: Mapping[str, Any],
) -> None:
    workflows = report.get("safe_local_workflows")
    if isinstance(workflows, list) and workflows:
        lines.append("Available safe local workflows:")
        for workflow in workflows:
            if not isinstance(workflow, Mapping):
                continue
            lines.append(f"- {workflow.get('name', 'unknown')}")
            lines.append(f"  Command: {workflow.get('command', 'unavailable')}")
            lines.append(f"  Local effect: {workflow.get('local_effect', 'unavailable')}")
            lines.append(f"  Output: {workflow.get('output', 'unavailable')}")
    blocked_actions = report.get("blocked_actions")
    if isinstance(blocked_actions, list) and blocked_actions:
        lines.append("Blocked until a Conductor-gated rail activation:")
        lines.extend(f"- {action}" for action in blocked_actions)


def _database_target_text(database_target: object) -> str:
    if not isinstance(database_target, Mapping):
        return "unavailable"
    classification = str(database_target.get("path_classification", "unavailable"))
    label = {
        "not_applicable_no_db_opened": "not applicable - no DB opened",
        "temporary_test_local_safe_db": "temporary/test/local safe DB",
        "repo_local_dev_safe_db": "repo-local dev safe DB",
        "unknown_explicit_sqlite": "unknown explicit SQLite path",
    }.get(classification, classification)
    access = database_target.get("access")
    path = database_target.get("path")
    if path:
        return f"{label}; access={access}; path={path}"
    return f"{label}; access={access}"


def _output_target_text(output_target: object) -> str:
    if not isinstance(output_target, Mapping):
        return "unavailable"
    kind = str(output_target.get("kind", "unavailable")).replace("_", " ")
    path = output_target.get("path")
    if path:
        return f"{path} ({kind})"
    return kind


def _local_sqlite_changes_text(report: Mapping[str, Any]) -> str:
    changed = report.get("local_sqlite_changed")
    if changed is None:
        return "unavailable"
    if changed is not True:
        return "none"
    if report.get("internal_state_mutation") is True:
        return "internal SQLite state changed"
    command = str(report.get("command", ""))
    if "preview" in command:
        return "local preview/audit rows changed"
    if "ledger" in str(report.get("workflow_mode", "")) or command.startswith("side-effects"):
        return "local ledger rows changed"
    if command.startswith("scheduler"):
        return "local scheduler/dev-test rows changed"
    return "local SQLite audit/dev-test rows changed"


def _append_candidate_or_ledger_summary(
    lines: list[str],
    report: Mapping[str, Any],
) -> None:
    preview_report = report.get("preview_report")
    if isinstance(preview_report, Mapping):
        candidate_counts = preview_report.get("candidate_counts")
        if isinstance(candidate_counts, Mapping):
            lines.append(
                "Candidate changes: "
                + ", ".join(
                    f"{key}={value}" for key, value in sorted(candidate_counts.items())
                )
            )

    completion_report = report.get("completion_report")
    if isinstance(completion_report, Mapping):
        counts = completion_report.get("counts")
        if isinstance(counts, Mapping):
            lines.append(
                "Apply/item counts: "
                + ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
            )
        if completion_report.get("rollback_verified") is True:
            lines.append("Rollback/recovery: verified for failed transaction")

    summary = report.get("summary")
    if isinstance(summary, Mapping):
        if {
            "intent_count",
            "attempt_count",
            "idempotency_record_count",
        }.issubset(summary.keys()):
            lines.append(
                "Ledger/idempotency: "
                f"intents={summary.get('intent_count')}, "
                f"attempts={summary.get('attempt_count')}, "
                f"idempotency_records={summary.get('idempotency_record_count')}"
            )

    if "scheduler_job_count" in report:
        scheduler_text = f"jobs={report.get('scheduler_job_count')}"
        if "due_simulated_job_count" in report:
            scheduler_text += f", due={report.get('due_simulated_job_count')}"
        lines.append(f"Simulated scheduler: {scheduler_text}")


def _blocked_actions_for_report(report: Mapping[str, Any]) -> list[str]:
    blocked = report.get("blocked_actions")
    if isinstance(blocked, list) and blocked:
        return [str(action) for action in blocked]
    return []


def _yes_no_unavailable(value: object) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unavailable"


def _append_rail_state_lines(lines: list[str], rail_states: Mapping[str, Any]) -> None:
    rails = rail_states.get("rails")
    if isinstance(rails, Mapping) and rails:
        lines.append("Rail states:")
        for name, value in sorted(rails.items()):
            lines.append(f"- {name}: {value}")
    lines.append(f"Scheduler: {rail_states.get('scheduler', 'unavailable')}")


def _format_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "none"
    return str(value)
