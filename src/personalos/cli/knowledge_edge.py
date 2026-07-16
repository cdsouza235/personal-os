"""Knowledge Edge CLI surface (P-KE-1C): fixture scan, queue preview, false-positive flag.

Mirrors ``cli/priorities.py``/``cli/routines.py`` conventions. No network-capable
import appears anywhere in this module -- ``scan`` runs the same fixture-only
``run_scan`` entrypoint Packet 1B's own tests exercise (``adapters/fixtures.py``)
against a small built-in synthetic dataset; it is never a live scan and never
activates a scheduler.
"""

from __future__ import annotations

import argparse
import uuid
from contextlib import closing
from datetime import UTC, datetime

import personalos.knowledge_edge.state as ke
from personalos.cli.db import _connect_read_only, _connect_read_write, _with_workflow_context
from personalos.cli.errors import CliError
from personalos.cli.reporting import _emit_report
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
from personalos.knowledge_edge.scan_orchestrator import run_scan

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
