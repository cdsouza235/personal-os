"""Knowledge Edge CLI surface: fixture scan, queue preview, false-positive flag,
decision surface, synthesis-handoff export (P-KE-1C, plus the ``decide``/
``synthesis`` groups added by P-KE-1D closing the phase-end checkpoint's C1
condition -- audits/ke-phase-1-phase-end-fable-report.md).

Mirrors ``cli/priorities.py``/``cli/routines.py`` conventions. No network-capable
import appears anywhere in this module except the ``shadow`` command group's own
import of ``rails.knowledge_edge.podcasts.LivePodcastFeedAdapter`` (P-KE-2C) --
``scan`` (this module's other, older command) runs the same fixture-only
``run_scan`` entrypoint Packet 1B's own tests exercise (``adapters/fixtures.py``)
against a small built-in synthetic dataset; it is never a live scan and never
activates a scheduler.

The ``shadow`` command group (P-KE-2C) is the first production wiring of a live
Knowledge Edge adapter: ``shadow bootstrap``/``scan``/``sample-freeze``/
``grade-init``/``report`` implement the Conductor-supervised procedure in
``docs/knowledge_edge/PACKET_2C_FIRST_SHADOW_RUN.md``. Every one of these commands
except ``grade-init`` (a pure frozen-JSON-to-blank-grades-JSON file transform, no
database of any kind involved) calls ``shadow_mode.validate_shadow_admission`` first
-- the §14.4 fence -- which refuses unless ``--db`` resolves to exactly the one
shadow database path (``shadow_mode.SHADOW_DB_PATH``); no other database, and never
the production path, is ever reachable through this command group. ``shadow scan``
constructs
``LivePodcastFeedAdapter`` with ``feature_mode="shadow_live"`` for Lane A only --
structurally reachable, not actually reached by this suite: every test exercising
this command does so against a freshly-bootstrapped-but-unverified (still ``trial``)
registry, so the adapter's own per-source verification gate
(``rails/knowledge_edge/podcasts.py`` ``_evaluate_gates``) refuses before any HTTP
client is ever constructed. The real live fetch only happens when the Conductor runs
this command by hand, post-merge, against a registry the supervised procedure has
already verified.

``decide`` is the first production caller of the decision APIs
(``upsert_user_decision``, ``update_media_decision_state``,
``update_event_decision_state``), ``record_decision_history``, and the Tonight/
Saved caps: before this packet those had zero callers outside tests (C1). Every
decide subcommand writes an append-only ``ke_decision_history`` row and mirrors
the accepted decision into both the entity's own ``decision_state`` column
(read by the sweep/saved-media paths in ``scan_orchestrator.py``) and
``ke_user_decisions`` (read by the queue-section/skip-exclusion paths there) --
see those two tables' docstrings in ``state/decisions.py``/``state/events.py``
for why both exist. ``synthesis export`` is the first production caller of
``state/synthesis.py``.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import uuid
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import personalos.knowledge_edge.state as ke
from personalos.cli.db import _connect_read_only, _connect_read_write, _with_workflow_context
from personalos.cli.errors import CliError
from personalos.cli.reporting import _emit_report
from personalos.idempotency import stable_side_effect_id
from personalos.knowledge_edge import shadow_mode
from personalos.knowledge_edge.adapters.contracts import (
    DiscoveredEvent,
    DiscoveredFiling,
    DiscoveredMediaItem,
)
from personalos.knowledge_edge.adapters.fixtures import (
    FixtureChannelVideoAdapter,
    FixtureEarningsEventAdapter,
    FixtureFilingsAdapter,
    FixturePodcastFeedAdapter,
)
from personalos.knowledge_edge.dashboard import build_knowledge_edge_queue_summary
from personalos.knowledge_edge.engine import ranking
from personalos.knowledge_edge.ground_truth_sample import (
    SampleAcknowledgmentError,
    build_ground_truth_sample,
    render_frozen_sample_files,
    require_acknowledged_sample,
    utc_now_iso,
)
from personalos.knowledge_edge.sample_grades import (
    SampleGradingError,
    render_blank_grades_file,
    require_paired_grades,
)
from personalos.knowledge_edge.scan_orchestrator import run_scan
from personalos.knowledge_edge.shadow_bootstrap import bootstrap_shadow_database
from personalos.knowledge_edge.shadow_report import (
    build_lane_a_coverage,
    compute_lane_metrics,
    evaluate_recall_minimum,
    merge_precision_verdicts,
    render_shadow_report,
)
from personalos.path_safety import validate_output_file_path
from personalos.rails.knowledge_edge.podcasts import LivePodcastFeedAdapter

BUILTIN_FIXTURE_SET_NAME = "cli-builtin-demo"

_BUILTIN_SOURCES: tuple[dict[str, str], ...] = (
    {"source_id": "ke-cli-src-dwarkesh", "source_type": "podcast_feed", "lane": "curated_podcasts", "name": "Dwarkesh Podcast"},
    {"source_id": "ke-cli-src-cnbc", "source_type": "youtube_channel", "lane": "market_voices", "name": "CNBC Television"},
    {"source_id": "ke-cli-src-frontier-ai", "source_type": "youtube_channel", "lane": "consequential_leaders", "name": "Official Frontier AI Lab Channel"},
    {"source_id": "ke-cli-src-calendar", "source_type": "calendar_provider", "lane": "earnings_events", "name": "Earnings Calendar"},
    {"source_id": "ke-cli-src-edgar", "source_type": "sec_edgar", "lane": "earnings_events", "name": "SEC EDGAR"},
)
_BUILTIN_PEOPLE: tuple[dict[str, str], ...] = (
    {"person_id": "ke-cli-person-tom-lee", "display_name": "Tom Lee", "category": "market_voice"},
    {"person_id": "ke-cli-person-jensen-huang", "display_name": "Jensen Huang", "category": "consequential_leader"},
)
_BUILTIN_COMPANY_ID = "ke-cli-company-nvda"


def _seed_builtin_registries_if_missing(connection) -> None:
    for source in _BUILTIN_SOURCES:
        if ke.get_source(connection, source["source_id"]) is None:
            ke.create_source(connection, **source)
    for person in _BUILTIN_PEOPLE:
        if ke.get_person(connection, person["person_id"]) is None:
            ke.create_person(connection, **person)
    if ke.get_company(connection, _BUILTIN_COMPANY_ID) is None:
        ke.create_company(
            connection,
            company_id=_BUILTIN_COMPANY_ID,
            legal_name="NVIDIA Corporation",
            display_name="NVIDIA",
            roster_group="nasdaq100_top10",
            roster_status="confirmed",
            priority_tier="tier_a",
        )


def _builtin_fixture_adapters(*, queue_date: str):
    podcast_adapter = FixturePodcastFeedAdapter(
        {
            "ke-cli-src-dwarkesh": (
                DiscoveredMediaItem(
                    source_id="ke-cli-src-dwarkesh",
                    source_specific_id=f"ep-{queue_date}",
                    canonical_url=f"https://dwarkesh.com/ep-{queue_date}",
                    title="A Long Conversation",
                    media_type="podcast_episode",
                    source_precedence="official",
                    format_hint="original_podcast_guest",
                    feed_guid=f"dwarkesh-guid-{queue_date}",
                    published_at=f"{queue_date}T18:00:00+00:00",
                    duration_seconds=5400,
                    cursor_value=f"{queue_date}T18:00:00+00:00",
                ),
            ),
        }
    )
    channel_adapter = FixtureChannelVideoAdapter(
        {
            "ke-cli-src-frontier-ai": (
                DiscoveredMediaItem(
                    source_id="ke-cli-src-frontier-ai",
                    source_specific_id=f"vid-jensen-{queue_date}",
                    canonical_url=f"https://example.com/watch?v=jensen-{queue_date}",
                    title="Jensen Huang: The Future of Compute",
                    media_type="video_interview",
                    source_precedence="official",
                    format_hint="original_long_form_interview",
                    underlying_id=f"jensen-interview-{queue_date}",
                    matched_person_id="ke-cli-person-jensen-huang",
                    matched_company_id=_BUILTIN_COMPANY_ID,
                    published_at=f"{queue_date}T12:00:00+00:00",
                    duration_seconds=3600,
                    cursor_value=f"{queue_date}T12:00:00+00:00",
                ),
            ),
            "ke-cli-src-cnbc": (
                DiscoveredMediaItem(
                    source_id="ke-cli-src-cnbc",
                    source_specific_id=f"vid-tomlee-{queue_date}",
                    canonical_url=f"https://example.com/watch?v=tomlee-{queue_date}",
                    title="Tom Lee on Bitcoin and Market Outlook",
                    media_type="video_interview",
                    source_precedence="official",
                    format_hint="financial_media_segment",
                    matched_person_id="ke-cli-person-tom-lee",
                    published_at=f"{queue_date}T14:00:00+00:00",
                    duration_seconds=900,
                    cursor_value=f"{queue_date}T14:00:00+00:00",
                ),
            ),
        }
    )
    earnings_adapter = FixtureEarningsEventAdapter(
        {
            "ke-cli-src-calendar": (
                DiscoveredEvent(
                    source_id="ke-cli-src-calendar",
                    company_id=_BUILTIN_COMPANY_ID,
                    event_id_hint=queue_date,
                    event_type="quarterly_earnings",
                    scheduled_date=queue_date,
                    fiscal_period="2026-Q2",
                    time_precision="date_only",
                    schedule_confidence="confirmed_secondary",
                    schedule_source="fixture calendar provider",
                    cursor_value="0001",
                ),
            ),
        }
    )
    filings_adapter = FixtureFilingsAdapter(
        {
            "ke-cli-src-edgar": (
                DiscoveredFiling(
                    company_id=_BUILTIN_COMPANY_ID,
                    filing_type="8-K",
                    filing_url="https://www.sec.gov/example/nvda-8k",
                    filed_at=f"{queue_date}T00:00:00+00:00",
                    fiscal_period="2026-Q2",
                    cursor_value="0001",
                ),
            ),
        }
    )
    return podcast_adapter, channel_adapter, earnings_adapter, filings_adapter


def _command_knowledge_edge_scan(args: argparse.Namespace) -> int:
    queue_date = args.date
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(UTC)
    scan_run_id = args.scan_run_id or f"cli-scan-{queue_date}-{uuid.uuid4().hex}"

    with closing(_connect_read_write(args.db)) as connection:
        _seed_builtin_registries_if_missing(connection)
        podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = _builtin_fixture_adapters(
            queue_date=queue_date
        )
        summary = run_scan(
            connection,
            scan_run_id=scan_run_id,
            run_type="manual_scan_now",
            triggered_by="operator",
            now=now,
            queue_date=queue_date,
            podcast_adapter=podcast_adapter,
            channel_adapter=channel_adapter,
            earnings_adapter=earnings_adapter,
            filings_adapter=filings_adapter,
        )

    report = _with_workflow_context(
        {
            "command": "knowledge-edge scan",
            "status": summary.status,
            "database_write": True,
            "external_mutation": False,
            "no_external_writes": True,
            "fixture_set": BUILTIN_FIXTURE_SET_NAME,
            "scan_run_id": summary.scan_run_id,
            "media_items_created": summary.media_items_created,
            "media_items_reprocessed": summary.media_items_reprocessed,
            "events_created": summary.events_created,
            "events_reprocessed": summary.events_reprocessed,
            "sources_healthy": summary.sources_healthy,
            "sources_failed": summary.sources_failed,
            "queue_snapshot_rows_created": summary.queue_snapshot_rows_created,
        },
        workflow_name="Knowledge Edge fixture scan",
        workflow_mode="inert / no-send / fixture-only local write",
        database_path=args.db,
        database_access="read_write_knowledge_edge_scan",
        local_sqlite_read=True,
        local_sqlite_changed=True,
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Run personalos knowledge-edge queue show --date <date> to review the composed queue.",
            "No live network access occurred; this is a fixture-only scan.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0 if summary.status in ("completed", "partially_completed") else 1


def _command_knowledge_edge_queue_show(args: argparse.Namespace) -> int:
    with closing(_connect_read_only(args.db)) as connection:
        queue_summary = build_knowledge_edge_queue_summary(
            connection, queue_date=args.date, feature_mode="fixture"
        )
    report = _with_workflow_context(
        {
            "command": "knowledge-edge queue show",
            "status": "completed",
            "database_write": False,
            "external_mutation": False,
            "no_external_writes": True,
            "queue_summary": queue_summary,
        },
        workflow_name="Knowledge Edge queue preview",
        workflow_mode="inert / no-send / report-only",
        database_path=args.db,
        database_access="read_only_knowledge_edge_queue",
        local_sqlite_read=True,
        local_sqlite_changed=False,
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Review queue sections, demoted/ambiguous items, and coverage.",
            "Run personalos knowledge-edge flag-false-positive to correct a bad match.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0


def _command_knowledge_edge_flag_false_positive(args: argparse.Namespace) -> int:
    with closing(_connect_read_write(args.db)) as connection:
        try:
            match = ke.flag_entity_match_false_positive(
                connection, entity_match_id=args.entity_match_id
            )
        except ValueError as error:
            raise CliError(str(error)) from error
    report = _with_workflow_context(
        {
            "command": "knowledge-edge flag-false-positive",
            "status": "flagged",
            "database_write": True,
            "external_mutation": False,
            "no_external_writes": True,
            "entity_match": match,
        },
        workflow_name="Flag Knowledge Edge entity match as false positive",
        workflow_mode="inert / no-send / local write",
        database_path=args.db,
        database_access="read_write_knowledge_edge_false_positive",
        local_sqlite_read=True,
        local_sqlite_changed=True,
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Re-run personalos knowledge-edge queue show to confirm the flag is reflected.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0


# --------------------------------------------------------------------- decision surface


def _decision_id_for(entity_type: str, entity_id: str) -> str:
    return stable_side_effect_id("ke-decision", f"{entity_type}:{entity_id}")


def _record_decision(
    connection,
    *,
    entity_type: str,
    entity_id: str,
    decision_state: str,
    from_value: str,
    changed_by: str,
) -> None:
    """Write both decision-acceptance side effects that C1 found missing:
    the ``ke_user_decisions`` row (read by the queue-section/skip-exclusion
    paths in ``scan_orchestrator.py``) and one append-only ``ke_decision_history``
    row (§13.4). Called after the entity's own ``decision_state`` column has
    already been updated (and validated) by the caller.
    """
    ke.upsert_user_decision(
        connection,
        decision_id=_decision_id_for(entity_type, entity_id),
        entity_type=entity_type,
        entity_id=entity_id,
        decision_state=decision_state,
    )
    ke.record_decision_history(
        connection,
        history_id=f"ke-decision-history-{uuid.uuid4().hex}",
        entity_type=entity_type,
        entity_id=entity_id,
        track="decision_state",
        from_value=from_value,
        to_value=decision_state,
        changed_by=changed_by,
    )


def _stage_watched_synthesis_handoff(connection, *, entity_type: str, entity_id: str, packet: dict) -> dict:
    return ke.create_synthesis_handoff(
        connection,
        handoff_id=f"ke-synthesis-{uuid.uuid4().hex}",
        entity_type=entity_type,
        entity_id=entity_id,
        handoff_type="copy_synthesis_packet",
        packet=packet,
    )


def _enforce_tonight_cap(connection, *, candidate_duration_seconds: int | None) -> None:
    """§12.1 Tonight cap, enforced at decision-acceptance (C1). Refuses honestly
    rather than silently dropping or bumping another item off Tonight.
    """
    active = ke.list_media_items(connection, decision_state="watch")
    if len(active) >= ranking.TONIGHT_ITEM_CAP:
        raise CliError(
            f"Tonight cap reached: {ranking.TONIGHT_ITEM_CAP} items are already on "
            "Watch for tonight. Mark one Watched or Skip it before adding another."
        )
    if candidate_duration_seconds is not None:
        known_duration_total = sum(
            item["duration_seconds"] for item in active if item["duration_seconds"] is not None
        )
        projected_minutes = (known_duration_total + candidate_duration_seconds) / 60.0
        cap_minutes = ranking.TONIGHT_KNOWN_DURATION_CAP_SECONDS / 60.0
        if (known_duration_total + candidate_duration_seconds) > ranking.TONIGHT_KNOWN_DURATION_CAP_SECONDS:
            raise CliError(
                f"Tonight known-duration cap reached: adding this item would bring "
                f"tonight's known-duration Watch total to {projected_minutes:.0f} minutes, "
                f"over the {cap_minutes:.0f}-minute cap. Mark one Watched or Skip it "
                "before adding another."
            )


def _enforce_saved_cap(connection) -> None:
    """§12.1 Saved cap (12 items), enforced at decision-acceptance (C1). Only
    active saved items count (mirrors the filter ``scan_orchestrator.py`` already
    uses to decide what is resurfaced) -- an item already swept to
    ``queue_visibility_state == "expired"`` is no longer occupying a saved slot.
    """
    active = [
        item
        for item in ke.list_media_items(connection, decision_state="save_for_later")
        if item["queue_visibility_state"] not in ("expired", "archived")
    ]
    if len(active) >= ranking.SAVED_CAP:
        raise CliError(
            f"Saved cap reached: {ranking.SAVED_CAP} items are already saved for later. "
            "Watch, Skip, or let one expire before saving another."
        )


def _accept_media_decision(connection, *, media_item_id: str, decision_state: str, changed_by: str) -> tuple[dict, dict | None]:
    media_item = ke.get_media_item(connection, media_item_id)
    if media_item is None:
        raise CliError(f"Media item does not exist: {media_item_id}")
    from_value = media_item["decision_state"]

    if decision_state == "watch":
        _enforce_tonight_cap(connection, candidate_duration_seconds=media_item["duration_seconds"])
    elif decision_state == "save_for_later":
        _enforce_saved_cap(connection)

    try:
        updated = ke.update_media_decision_state(
            connection, media_item_id=media_item_id, decision_state=decision_state
        )
    except ValueError as error:
        raise CliError(str(error)) from error

    _record_decision(
        connection,
        entity_type="media_item",
        entity_id=media_item_id,
        decision_state=decision_state,
        from_value=from_value,
        changed_by=changed_by,
    )

    handoff = None
    if decision_state == "watched":
        handoff = _stage_watched_synthesis_handoff(
            connection,
            entity_type="media_item",
            entity_id=media_item_id,
            packet={
                "media_item_id": media_item_id,
                "title": media_item["title"],
                "canonical_url": media_item["canonical_url"],
            },
        )
    return updated, handoff


def _accept_event_decision(connection, *, event_id: str, decision_state: str, changed_by: str) -> tuple[dict, dict | None]:
    event = ke.get_scheduled_event(connection, event_id)
    if event is None:
        raise CliError(f"Scheduled event does not exist: {event_id}")
    from_value = event["decision_state"]

    try:
        updated = ke.update_event_decision_state(
            connection, event_id=event_id, decision_state=decision_state
        )
    except ValueError as error:
        raise CliError(str(error)) from error

    _record_decision(
        connection,
        entity_type="scheduled_event",
        entity_id=event_id,
        decision_state=decision_state,
        from_value=from_value,
        changed_by=changed_by,
    )

    handoff = None
    if decision_state == "watched":
        handoff = _stage_watched_synthesis_handoff(
            connection,
            entity_type="scheduled_event",
            entity_id=event_id,
            packet={
                "event_id": event_id,
                "company_id": event["company_id"],
                "event_type": event["event_type"],
            },
        )
    return updated, handoff


def _decide_report(
    args: argparse.Namespace,
    *,
    command: str,
    entity_type: str,
    entity_id: str,
    entity: dict,
    handoff: dict | None,
) -> dict:
    payload = {
        "command": command,
        "status": "decided",
        "database_write": True,
        "external_mutation": False,
        "no_external_writes": True,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "decision_state": entity["decision_state"],
    }
    if handoff is not None:
        payload["synthesis_handoff_id"] = handoff["handoff_id"]
        payload["synthesis_handoff_status"] = handoff["status"]
    safe_next_actions = [
        "Run personalos knowledge-edge queue show to confirm the decision is reflected.",
    ]
    if handoff is not None:
        safe_next_actions.append(
            f"Run personalos knowledge-edge synthesis export --handoff-id {handoff['handoff_id']} "
            "to retrieve the staged synthesis packet."
        )
    return _with_workflow_context(
        payload,
        workflow_name=f"Knowledge Edge decision: {command}",
        workflow_mode="inert / no-send / local write",
        database_path=args.db,
        database_access="read_write_knowledge_edge_decision",
        local_sqlite_read=True,
        local_sqlite_changed=True,
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=tuple(safe_next_actions),
    )


def _command_knowledge_edge_decide_watch(args: argparse.Namespace) -> int:
    with closing(_connect_read_write(args.db)) as connection:
        media_item, handoff = _accept_media_decision(
            connection, media_item_id=args.media_item_id, decision_state="watch", changed_by="operator"
        )
    report = _decide_report(
        args,
        command="knowledge-edge decide watch",
        entity_type="media_item",
        entity_id=args.media_item_id,
        entity=media_item,
        handoff=handoff,
    )
    _emit_report(report, json_output=args.json)
    return 0


def _command_knowledge_edge_decide_save(args: argparse.Namespace) -> int:
    with closing(_connect_read_write(args.db)) as connection:
        media_item, handoff = _accept_media_decision(
            connection, media_item_id=args.media_item_id, decision_state="save_for_later", changed_by="operator"
        )
    report = _decide_report(
        args,
        command="knowledge-edge decide save",
        entity_type="media_item",
        entity_id=args.media_item_id,
        entity=media_item,
        handoff=handoff,
    )
    _emit_report(report, json_output=args.json)
    return 0


def _command_knowledge_edge_decide_watch_live(args: argparse.Namespace) -> int:
    with closing(_connect_read_write(args.db)) as connection:
        event, handoff = _accept_event_decision(
            connection, event_id=args.event_id, decision_state="watch_live", changed_by="operator"
        )
    report = _decide_report(
        args,
        command="knowledge-edge decide watch-live",
        entity_type="scheduled_event",
        entity_id=args.event_id,
        entity=event,
        handoff=handoff,
    )
    _emit_report(report, json_output=args.json)
    return 0


def _command_knowledge_edge_decide_save_replay(args: argparse.Namespace) -> int:
    with closing(_connect_read_write(args.db)) as connection:
        event, handoff = _accept_event_decision(
            connection, event_id=args.event_id, decision_state="save_replay", changed_by="operator"
        )
    report = _decide_report(
        args,
        command="knowledge-edge decide save-replay",
        entity_type="scheduled_event",
        entity_id=args.event_id,
        entity=event,
        handoff=handoff,
    )
    _emit_report(report, json_output=args.json)
    return 0


def _require_exactly_one_entity_id(args: argparse.Namespace) -> tuple[str, str]:
    media_item_id = getattr(args, "media_item_id", None)
    event_id = getattr(args, "event_id", None)
    if bool(media_item_id) == bool(event_id):
        raise CliError("Specify exactly one of --media-item-id or --event-id.")
    if media_item_id:
        return "media_item", media_item_id
    return "scheduled_event", event_id


def _command_knowledge_edge_decide_skip(args: argparse.Namespace) -> int:
    entity_type, entity_id = _require_exactly_one_entity_id(args)
    with closing(_connect_read_write(args.db)) as connection:
        if entity_type == "media_item":
            entity, handoff = _accept_media_decision(
                connection, media_item_id=entity_id, decision_state="skip", changed_by="operator"
            )
        else:
            entity, handoff = _accept_event_decision(
                connection, event_id=entity_id, decision_state="skip", changed_by="operator"
            )
    report = _decide_report(
        args,
        command="knowledge-edge decide skip",
        entity_type=entity_type,
        entity_id=entity_id,
        entity=entity,
        handoff=handoff,
    )
    _emit_report(report, json_output=args.json)
    return 0


def _command_knowledge_edge_decide_watched(args: argparse.Namespace) -> int:
    entity_type, entity_id = _require_exactly_one_entity_id(args)
    with closing(_connect_read_write(args.db)) as connection:
        if entity_type == "media_item":
            entity, handoff = _accept_media_decision(
                connection, media_item_id=entity_id, decision_state="watched", changed_by="operator"
            )
        else:
            entity, handoff = _accept_event_decision(
                connection, event_id=entity_id, decision_state="watched", changed_by="operator"
            )
    report = _decide_report(
        args,
        command="knowledge-edge decide watched",
        entity_type=entity_type,
        entity_id=entity_id,
        entity=entity,
        handoff=handoff,
    )
    _emit_report(report, json_output=args.json)
    return 0


# ------------------------------------------------------------------ synthesis handoff


def _command_knowledge_edge_synthesis_list(args: argparse.Namespace) -> int:
    with closing(_connect_read_only(args.db)) as connection:
        handoffs = ke.list_synthesis_handoffs(connection, status=args.status)
    report = _with_workflow_context(
        {
            "command": "knowledge-edge synthesis list",
            "status": "completed",
            "database_write": False,
            "external_mutation": False,
            "no_external_writes": True,
            "synthesis_handoffs": handoffs,
        },
        workflow_name="List Knowledge Edge synthesis handoffs",
        workflow_mode="inert / no-send / report-only",
        database_path=args.db,
        database_access="read_only_knowledge_edge_synthesis",
        local_sqlite_read=True,
        local_sqlite_changed=False,
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Run personalos knowledge-edge synthesis export --handoff-id <id> to export one.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0


def _command_knowledge_edge_synthesis_export(args: argparse.Namespace) -> int:
    """Production caller of ``state/synthesis.py`` (C1): exports one staged
    handoff's packet to stdout/JSON and marks it completed. This is the
    fixture-rung stand-in for the later-phase Obsidian draft write (Session 3
    gate) -- it performs no file write and no network call, only a local state
    transition plus a report emission.
    """
    with closing(_connect_read_write(args.db)) as connection:
        handoff = ke.get_synthesis_handoff(connection, args.handoff_id)
        if handoff is None:
            raise CliError(f"Synthesis handoff does not exist: {args.handoff_id}")
        exported_packet = handoff["packet"]
        completed = ke.complete_synthesis_handoff(connection, handoff_id=args.handoff_id)
    report = _with_workflow_context(
        {
            "command": "knowledge-edge synthesis export",
            "status": "exported",
            "database_write": True,
            "external_mutation": False,
            "no_external_writes": True,
            "handoff_id": completed["handoff_id"],
            "entity_type": completed["entity_type"],
            "entity_id": completed["entity_id"],
            "synthesis_packet": exported_packet,
        },
        workflow_name="Export Knowledge Edge synthesis handoff",
        workflow_mode="inert / no-send / local write",
        database_path=args.db,
        database_access="read_write_knowledge_edge_synthesis",
        local_sqlite_read=True,
        local_sqlite_changed=True,
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Copy the synthesis_packet contents into the manual ChatGPT/Obsidian loop.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0


# ------------------------------------------------------------------------- shadow


def _require_shadow_admission(database_path: str) -> None:
    """Wraps `shadow_mode.validate_shadow_admission` as a `CliError` -- that
    function raises `shadow_mode.ShadowModeViolation` (a `RuntimeError` subclass),
    which `cli.main`'s exception handling does not catch by default; every other
    domain refusal in this module surfaces the same way (compare
    `_command_knowledge_edge_flag_false_positive`'s `ValueError` -> `CliError`
    wrapping), so this mirrors that house convention for the shadow_live fence.
    """
    try:
        shadow_mode.validate_shadow_admission(
            feature_mode=shadow_mode.SHADOW_LIVE_MODE, database_path=database_path
        )
    except shadow_mode.ShadowModeViolation as error:
        raise CliError(str(error)) from error


def _mkdir_shadow_parents_0700(database_path: Path) -> None:
    """Creates every missing ancestor directory of `database_path`, outermost
    missing one first, mode `0o700`. `Path.mkdir(mode=..., parents=True)` only
    applies `mode` to the one directory actually named in the call -- any
    intermediate directories it also has to create along the way get the default
    mode instead (CPython's own recursive-parent-creation fallback never forwards
    `mode`). Since the admitted shadow path now lives under `~/.personalos/` (P-KE-2E)
    rather than the repo's `var/`, both `~/.personalos` and `~/.personalos/shadow`
    are typically newly created here, and both must end up private (0700), not just
    the innermost one.
    """
    missing = []
    for ancestor in database_path.parents:
        if ancestor.exists():
            break
        missing.append(ancestor)
    for ancestor in reversed(missing):
        ancestor.mkdir(mode=0o700)


def _command_knowledge_edge_shadow_bootstrap(args: argparse.Namespace) -> int:
    """Create/migrate the shadow DB and re-apply the nine Lane A verification flips
    from the smoke transcript (literal config, no re-fetching -- see
    ``shadow_bootstrap.py``). Unlike every other command in this module, this one
    may create the database file if it does not exist yet (mirrors
    ``config.bootstrap_production_database``'s own mkdir-then-connect shape), so it
    cannot use ``_connect_read_write`` (which requires the file to already exist).
    """
    _require_shadow_admission(args.db)
    database_path = Path(args.db).expanduser().resolve()
    _mkdir_shadow_parents_0700(database_path)

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        result = bootstrap_shadow_database(connection)
    finally:
        connection.close()

    report = _with_workflow_context(
        {
            "command": "knowledge-edge shadow bootstrap",
            "status": "completed",
            "database_write": True,
            "external_mutation": False,
            "no_external_writes": True,
            "feature_mode": shadow_mode.SHADOW_LIVE_MODE,
            "migrations_applied": list(result.migrations_applied),
            "sources_flipped_to_active": list(result.sources_flipped_to_active),
            "endpoints_verified": list(result.endpoints_verified),
            "already_bootstrapped": list(result.already_bootstrapped),
        },
        workflow_name="Knowledge Edge shadow database bootstrap",
        workflow_mode="inert / no-send / shadow-db-only local write",
        database_path=args.db,
        database_access="read_write_knowledge_edge_shadow_bootstrap",
        local_sqlite_read=True,
        local_sqlite_changed=True,
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Run personalos knowledge-edge shadow scan for a bounded Lane A shadow scan.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0


def _command_knowledge_edge_shadow_scan(args: argparse.Namespace) -> int:
    """Run one bounded shadow scan: Lane A live RSS for whatever sources the
    shadow registry currently has verified+active, via ``LivePodcastFeedAdapter``
    in ``shadow_live`` mode. Lane B/C/D adapters are empty fixtures -- the shadow
    registry seeds no youtube_channel/calendar_provider/sec_edgar sources (see
    ``shadow_bootstrap.py``'s own scope note), so ``run_scan`` never calls them;
    they are passed only because ``run_scan`` requires one of each contract.
    """
    _require_shadow_admission(args.db)
    queue_date = args.date
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(UTC)
    scan_run_id = args.scan_run_id or f"shadow-scan-{queue_date}-{uuid.uuid4().hex}"

    with closing(_connect_read_write(args.db)) as connection:
        podcast_adapter = LivePodcastFeedAdapter(connection, feature_mode=shadow_mode.SHADOW_LIVE_MODE)
        summary = run_scan(
            connection,
            scan_run_id=scan_run_id,
            run_type="full_scan",
            triggered_by="conductor_supervised_shadow_run",
            now=now,
            queue_date=queue_date,
            podcast_adapter=podcast_adapter,
            channel_adapter=FixtureChannelVideoAdapter({}),
            earnings_adapter=FixtureEarningsEventAdapter({}),
            filings_adapter=FixtureFilingsAdapter({}),
        )

    report = _with_workflow_context(
        {
            "command": "knowledge-edge shadow scan",
            "status": summary.status,
            "database_write": True,
            "external_mutation": False,
            "no_external_writes": True,
            "feature_mode": shadow_mode.SHADOW_LIVE_MODE,
            "scan_run_id": summary.scan_run_id,
            "media_items_created": summary.media_items_created,
            "media_items_reprocessed": summary.media_items_reprocessed,
            "sources_healthy": summary.sources_healthy,
            "sources_failed": summary.sources_failed,
        },
        workflow_name="Knowledge Edge bounded shadow scan (Lane A live RSS only)",
        workflow_mode=(
            "shadow_live / no-send / shadow-db-only write; live Lane A network reads "
            "only from Conductor-verified-active sources"
        ),
        database_path=args.db,
        database_access="read_write_knowledge_edge_shadow_scan",
        local_sqlite_read=True,
        local_sqlite_changed=True,
        output_kind="stdout_json" if args.json else "stdout_human",
        safe_next_actions=(
            "Run personalos knowledge-edge shadow sample-freeze to construct the "
            "ground-truth sample once the sampling window has elapsed.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0 if summary.status in ("completed", "partially_completed") else 1


def _command_knowledge_edge_shadow_sample_freeze(args: argparse.Namespace) -> int:
    """Construct and freeze the ground-truth sample (R3-04): writes the frozen
    JSON + the human-readable ``PENDING CONDUCTOR ACKNOWLEDGMENT`` markdown doc to
    two explicit, caller-provided output paths. This command never marks a sample
    acknowledged -- that is a Conductor hand-edit-and-commit action, per
    ``docs/knowledge_edge/PACKET_2C_FIRST_SHADOW_RUN.md``.
    """
    _require_shadow_admission(args.db)
    generated_at = args.now or utc_now_iso()
    coverage_gaps = tuple(args.coverage_gap or ())

    with closing(_connect_read_only(args.db)) as connection:
        sample = build_ground_truth_sample(
            connection,
            window_start=args.window_start,
            window_end=args.window_end,
            lane_d_window_end=args.lane_d_window_end,
            generated_at=generated_at,
            coverage_gaps=coverage_gaps,
        )

    markdown_output_path = validate_output_file_path(
        args.markdown_output_file, path_label="operator markdown_output_file"
    )
    json_output_path = validate_output_file_path(
        args.json_output_file, path_label="operator json_output_file"
    )
    files = render_frozen_sample_files(
        sample,
        sample_date=args.sample_date,
        frozen_json_relative_path=args.json_output_file,
        markdown_relative_path=args.markdown_output_file,
    )
    json_output_path.write_text(files.frozen_json_text, encoding="utf-8")
    markdown_output_path.write_text(files.markdown_text, encoding="utf-8")

    report = _with_workflow_context(
        {
            "command": "knowledge-edge shadow sample-freeze",
            "status": "frozen_pending_acknowledgment",
            "database_write": False,
            "external_mutation": False,
            "no_external_writes": True,
            "file_write": True,
            "checksum_sha256": files.checksum_sha256,
            "lane_a_sample_size": len(sample.lane_a_precision_check),
            "lane_b_precision_sample_size": len(sample.lane_b_precision_check),
            "lane_c_precision_sample_size": len(sample.lane_c_precision_check),
            "lane_d_event_count": len(sample.lane_d_events),
        },
        workflow_name="Knowledge Edge ground-truth sample freeze (R3-04)",
        workflow_mode="inert / no-send / local file write only",
        database_path=args.db,
        database_access="read_only_knowledge_edge_shadow_sample_freeze",
        local_sqlite_read=True,
        local_sqlite_changed=False,
        output_kind="file",
        output_file=str(markdown_output_path),
        safe_next_actions=(
            f"Send {markdown_output_path} for Codex review and Chris's R3-04 "
            "acknowledgment before any grading or threshold tuning begins.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0


def _command_knowledge_edge_shadow_grade_init(args: argparse.Namespace) -> int:
    """Renders a blank grades-file skeleton (`sample_grades.py`) for an ACKNOWLEDGED
    frozen sample: one `null`-valued `precision_verdicts` entry per frozen
    precision-check item id, referencing the frozen file's own checksum, plus empty
    recall arrays. Pure file-to-file transform -- reads only the frozen markdown +
    JSON files the Conductor points it at and never touches any database, so this
    command (and only this one in the `shadow` group) takes no `--db` and needs no
    shadow admission check: there is no database or production surface for it to
    reach.

    Gate order (R3-04): freeze -> CONDUCTOR ACK -> grade-init -> grading -> report.
    This command refuses to generate a grades skeleton for a sample that is not yet
    Conductor-acknowledged -- same `require_acknowledged_sample` check `shadow
    report` performs, applied one step earlier so an unacknowledged sample can never
    even acquire a grades file, let alone a report.
    """
    markdown_text = Path(args.sample_markdown_file).read_text(encoding="utf-8")
    frozen_json_text = Path(args.sample_json_file).read_text(encoding="utf-8")
    try:
        require_acknowledged_sample(markdown_text, frozen_json_text=frozen_json_text)
    except SampleAcknowledgmentError as error:
        raise CliError(str(error)) from error

    try:
        grades_text = render_blank_grades_file(frozen_json_text)
    except SampleGradingError as error:
        raise CliError(str(error)) from error

    output_path = validate_output_file_path(args.output_file, path_label="operator output_file")
    output_path.write_text(grades_text, encoding="utf-8")

    report = _with_workflow_context(
        {
            "command": "knowledge-edge shadow grade-init",
            "status": "completed",
            "database_write": False,
            "external_mutation": False,
            "no_external_writes": True,
            "file_write": True,
        },
        workflow_name="Knowledge Edge ground-truth grades-file skeleton (R3-04)",
        workflow_mode="inert / no-send / local file write only, no database access",
        database_path=None,
        database_access="no_database_knowledge_edge_shadow_grade_init",
        local_sqlite_read=False,
        local_sqlite_changed=False,
        output_kind="file",
        output_file=str(output_path),
        safe_next_actions=(
            "Hand-edit the grades file's precision_verdicts and recall arrays per "
            "docs/knowledge_edge/PACKET_2C_FIRST_SHADOW_RUN.md §7, then run "
            "personalos knowledge-edge shadow report.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0


def _command_knowledge_edge_shadow_report(args: argparse.Namespace) -> int:
    """Generate the shadow report from an ACKNOWLEDGED frozen sample paired with a
    matching, hand-graded grades file (refuses otherwise -- R3-04) plus live
    coverage read from ``--db``. Three refusal arms, checked in order: (1) the
    frozen sample itself is not ACKNOWLEDGED or its bytes no longer hash to the
    acknowledged checksum (``require_acknowledged_sample``); (2) the grades file
    does not reference that same acknowledged checksum, or its ``precision_verdicts``
    do not cover exactly the frozen sample's item ids (``require_paired_grades``).
    See ``shadow_report.py``'s module docstring and ``sample_grades.py`` for the
    two-file grading protocol this command expects.
    """
    _require_shadow_admission(args.db)

    markdown_text = Path(args.sample_markdown_file).read_text(encoding="utf-8")
    frozen_json_text = Path(args.sample_json_file).read_text(encoding="utf-8")
    try:
        header_fields = require_acknowledged_sample(markdown_text, frozen_json_text=frozen_json_text)
    except SampleAcknowledgmentError as error:
        raise CliError(str(error)) from error

    grades_json_text = Path(args.grades_json_file).read_text(encoding="utf-8")
    try:
        paired_grades = require_paired_grades(
            frozen_json_text=frozen_json_text,
            acknowledged_checksum=header_fields["checksum_sha256"],
            grades_json_text=grades_json_text,
        )
    except SampleGradingError as error:
        raise CliError(str(error)) from error

    sample = json.loads(frozen_json_text)

    with closing(_connect_read_only(args.db)) as connection:
        lane_a_coverage = build_lane_a_coverage(connection)

    lane_a_metrics = compute_lane_metrics(
        lane="curated_podcasts",
        precision_items=merge_precision_verdicts(
            sample["lane_a_precision_check"], paired_grades.precision_verdicts
        ),
        recall_items=[],
    )
    lane_b_metrics = compute_lane_metrics(
        lane="market_voices",
        precision_items=merge_precision_verdicts(
            sample["lane_b_precision_check"], paired_grades.precision_verdicts
        ),
        recall_items=paired_grades.lane_b_recall_check,
    )
    lane_c_metrics = compute_lane_metrics(
        lane="consequential_leaders",
        precision_items=merge_precision_verdicts(
            sample["lane_c_precision_check"], paired_grades.precision_verdicts
        ),
        recall_items=paired_grades.lane_c_recall_check,
    )

    lane_b_recall_status = evaluate_recall_minimum(
        lane_b_metrics, minimum=sample["lane_b_recall_check_minimum"]
    )
    lane_c_recall_status = evaluate_recall_minimum(
        lane_c_metrics, minimum=sample["lane_c_recall_check_minimum"]
    )

    report_text = render_shadow_report(
        report_date=args.report_date,
        lane_a_coverage=lane_a_coverage,
        lane_a_metrics=lane_a_metrics,
        lane_b_metrics=lane_b_metrics,
        lane_c_metrics=lane_c_metrics,
        lane_b_recall_minimum=sample["lane_b_recall_check_minimum"],
        lane_c_recall_minimum=sample["lane_c_recall_check_minimum"],
        lane_d_event_count=len(sample["lane_d_events"]),
        lane_d_window_start=sample["window_start"],
        lane_d_window_end=sample["lane_d_window_end"],
        person_search_calls_made=args.person_search_calls_made,
        sample_markdown_path=args.sample_markdown_file,
        sample_checksum=header_fields["checksum_sha256"],
    )

    output_path = validate_output_file_path(args.output_file, path_label="operator output_file")
    output_path.write_text(report_text, encoding="utf-8")

    report = _with_workflow_context(
        {
            "command": "knowledge-edge shadow report",
            "status": "completed",
            "database_write": False,
            "external_mutation": False,
            "no_external_writes": True,
            "file_write": True,
            "lane_a_precision": lane_a_metrics.precision,
            "lane_b_precision": lane_b_metrics.precision,
            "lane_b_recall": lane_b_metrics.recall,
            "lane_b_recall_check_minimum": lane_b_recall_status.minimum,
            "lane_b_recall_check_graded": lane_b_recall_status.graded_count,
            "lane_b_recall_check_meets_minimum": lane_b_recall_status.meets_minimum,
            "lane_c_precision": lane_c_metrics.precision,
            "lane_c_recall": lane_c_metrics.recall,
            "lane_c_recall_check_minimum": lane_c_recall_status.minimum,
            "lane_c_recall_check_graded": lane_c_recall_status.graded_count,
            "lane_c_recall_check_meets_minimum": lane_c_recall_status.meets_minimum,
            "lane_d_event_count": len(sample["lane_d_events"]),
        },
        workflow_name="Knowledge Edge shadow report generation",
        workflow_mode="inert / no-send / local file write only",
        database_path=args.db,
        database_access="read_only_knowledge_edge_shadow_report",
        local_sqlite_read=True,
        local_sqlite_changed=False,
        output_kind="file",
        output_file=str(output_path),
        safe_next_actions=(
            "Review the shadow report; Session 2 approves final thresholds, this "
            "report does not.",
        ),
    )
    _emit_report(report, json_output=args.json)
    return 0
