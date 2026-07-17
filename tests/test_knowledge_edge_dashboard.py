"""P-KE-1C: knowledge_edge/dashboard.py rendering + composition unit tests.

Covers: four-lane + demoted/ambiguous composition, priority-tier rendering, the
Sec8.4 link hierarchy including the "Link pending (unknown vendor)" quarantine
display, Sec10.5 coverage-gap honesty, the Sec12.3 empty-state wording, and the
disabled/fixture feature-mode gate itself (amendment Sec14.4 -- this phase supports
disabled/fixture only).
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import personalos.knowledge_edge.state as ke
from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.knowledge_edge.adapters.contracts import (
    DiscoveredEvent,
    DiscoveredMediaItem,
)
from personalos.knowledge_edge.adapters.fixtures import (
    FixtureChannelVideoAdapter,
    FixtureEarningsEventAdapter,
    FixtureFilingsAdapter,
    FixturePodcastFeedAdapter,
)
from personalos.knowledge_edge.dashboard import (
    KNOWLEDGE_EDGE_FEATURE_MODES,
    _resolve_event_best_link,
    build_knowledge_edge_queue_summary,
    render_knowledge_edge_queue_html,
    validate_knowledge_edge_feature_mode,
)
from personalos.knowledge_edge.scan_orchestrator import run_scan

NOW = datetime(2026, 7, 16, 21, 0, 0, tzinfo=UTC)
QUEUE_DATE = "2026-07-16"


def _config_for(runtime_dir: Path, environment: Environment) -> PersonalOSConfig:
    directory_name = "dev" if environment is Environment.DEVELOPMENT else "test"
    return PersonalOSConfig(
        environment=environment,
        timezone=DEFAULT_TIMEZONE,
        database_path=runtime_dir / directory_name / "personalos.sqlite3",
    )


@contextmanager
def _connected_sqlite(config: PersonalOSConfig, *, runtime_dir: Path) -> Iterator[sqlite3.Connection]:
    connection = connect_sqlite(config, runtime_dir=runtime_dir)
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def _migrated_connection() -> Iterator[sqlite3.Connection]:
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir) / "runtime"
        config = _config_for(runtime_dir, Environment.TEST)
        with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
            apply_migrations(connection)
            yield connection


def _seed_registries(connection: sqlite3.Connection) -> None:
    ke.create_source(
        connection, source_id="src-dwarkesh", source_type="podcast_feed", lane="curated_podcasts", name="Dwarkesh Podcast"
    )
    ke.create_source(
        connection, source_id="src-cnbc", source_type="youtube_channel", lane="market_voices", name="CNBC Television"
    )
    ke.create_source(
        connection,
        source_id="src-frontier-ai",
        source_type="youtube_channel",
        lane="consequential_leaders",
        name="Official Frontier AI Lab Channel",
    )
    ke.create_source(
        connection, source_id="src-calendar", source_type="calendar_provider", lane="earnings_events", name="Earnings Calendar"
    )
    ke.create_person(connection, person_id="ke-person-tom-lee", display_name="Tom Lee", category="market_voice")
    ke.create_person(
        connection, person_id="ke-person-jensen-huang", display_name="Jensen Huang", category="consequential_leader"
    )
    # 'ke-company-nvda' is already seeded by migration 00017 (PHASE0_ROSTER.md
    # §3.1's launch roster) -- no create_company call needed here.


def _run_four_lane_scan(connection: sqlite3.Connection, *, extra_frontier_items=()) -> None:
    podcast_adapter = FixturePodcastFeedAdapter(
        {
            "src-dwarkesh": (
                DiscoveredMediaItem(
                    source_id="src-dwarkesh",
                    source_specific_id="ep-100",
                    canonical_url="https://dwarkesh.com/ep-100",
                    title="Episode 100: A Long Conversation",
                    media_type="podcast_episode",
                    source_precedence="official",
                    format_hint="original_podcast_guest",
                    feed_guid="dwarkesh-guid-100",
                    published_at="2026-07-16T18:00:00+00:00",
                    duration_seconds=5400,
                    cursor_value="2026-07-16T18:00:00+00:00",
                ),
            ),
        }
    )
    frontier_items = (
        DiscoveredMediaItem(
            source_id="src-frontier-ai",
            source_specific_id="vid-jensen-1",
            canonical_url="https://example.com/watch?v=jensen-1",
            title="Jensen Huang: The Future of Compute",
            media_type="video_interview",
            source_precedence="official",
            format_hint="original_long_form_interview",
            underlying_id="jensen-interview-1",
            matched_person_id="ke-person-jensen-huang",
            matched_company_id="ke-company-nvda",
            published_at="2026-07-16T12:00:00+00:00",
            duration_seconds=3600,
            cursor_value="2026-07-16T12:00:00+00:00",
        ),
        *extra_frontier_items,
    )
    channel_adapter = FixtureChannelVideoAdapter(
        {
            "src-frontier-ai": frontier_items,
            "src-cnbc": (
                DiscoveredMediaItem(
                    source_id="src-cnbc",
                    source_specific_id="vid-tomlee-1",
                    canonical_url="https://example.com/watch?v=tomlee-1",
                    title="Tom Lee on Bitcoin and Market Outlook",
                    media_type="video_interview",
                    source_precedence="official",
                    format_hint="financial_media_segment",
                    matched_person_id="ke-person-tom-lee",
                    published_at="2026-07-16T14:00:00+00:00",
                    duration_seconds=900,
                    cursor_value="2026-07-16T14:00:00+00:00",
                ),
            ),
        }
    )
    earnings_adapter = FixtureEarningsEventAdapter(
        {
            "src-calendar": (
                DiscoveredEvent(
                    source_id="src-calendar",
                    company_id="ke-company-nvda",
                    event_id_hint="2026-q2",
                    event_type="quarterly_earnings",
                    scheduled_date="2026-08-19",
                    fiscal_period="2026-Q2",
                    time_precision="date_only",
                    schedule_confidence="confirmed_secondary",
                    schedule_source="fixture calendar provider",
                    cursor_value="0001",
                ),
            ),
        }
    )
    run_scan(
        connection,
        scan_run_id="run-1",
        run_type="full_scan",
        triggered_by="scheduler",
        now=NOW,
        queue_date=QUEUE_DATE,
        podcast_adapter=podcast_adapter,
        channel_adapter=channel_adapter,
        earnings_adapter=earnings_adapter,
        filings_adapter=FixtureFilingsAdapter({}),
    )


class FeatureModeValidationTest(unittest.TestCase):
    def test_disabled_fixture_and_shadow_live_are_the_only_allowed_modes(self) -> None:
        self.assertEqual(KNOWLEDGE_EDGE_FEATURE_MODES, ("disabled", "fixture", "shadow_live"))
        for mode in ("active_read_only", "active_with_obsidian_handoff", "live", "bogus"):
            with self.subTest(mode=mode):
                with self.assertRaises(ValueError):
                    validate_knowledge_edge_feature_mode(mode)

    def test_shadow_live_mode_is_accepted_and_echoed_back(self) -> None:
        with _migrated_connection() as connection:
            _seed_registries(connection)
            _run_four_lane_scan(connection)
            summary = build_knowledge_edge_queue_summary(
                connection, queue_date=QUEUE_DATE, feature_mode="shadow_live"
            )
        self.assertTrue(summary["available"])
        self.assertEqual(summary["feature_mode"], "shadow_live")
        html = render_knowledge_edge_queue_html(summary)
        self.assertIn("shadow_live", html)
        self.assertIn("no production notification", html)

    def test_disabled_mode_returns_unavailable_without_reading_state(self) -> None:
        with _migrated_connection() as connection:
            summary = build_knowledge_edge_queue_summary(
                connection, queue_date=QUEUE_DATE, feature_mode="disabled"
            )
        self.assertEqual(summary, {"feature_mode": "disabled", "available": False, "queue_date": QUEUE_DATE})
        self.assertEqual(render_knowledge_edge_queue_html(summary), "")


class QueueSummaryCompositionTest(unittest.TestCase):
    def test_four_lane_summary_hydrates_all_sections(self) -> None:
        with _migrated_connection() as connection:
            _seed_registries(connection)
            _run_four_lane_scan(connection)
            summary = build_knowledge_edge_queue_summary(
                connection, queue_date=QUEUE_DATE, feature_mode="fixture"
            )

        self.assertTrue(summary["available"])
        self.assertEqual(len(summary["sections"]["p0_consequential_leaders"]), 1)
        self.assertEqual(len(summary["sections"]["p1_core_podcasts"]), 1)
        self.assertEqual(len(summary["sections"]["p2_market_voices"]), 1)
        self.assertEqual(len(summary["sections"]["tomorrow_earnings_events"]), 1)
        self.assertEqual(summary["sections"]["saved_to_reconsider"], [])
        self.assertEqual(summary["demoted_ambiguous"], [])
        self.assertIsNone(summary["empty_state"])

        p0_card = summary["sections"]["p0_consequential_leaders"][0]
        self.assertEqual(p0_card["title"], "Jensen Huang: The Future of Compute")
        self.assertIn("Jensen Huang", p0_card["matched_people"])
        self.assertIn("NVIDIA", p0_card["matched_companies"])
        self.assertFalse(p0_card["false_positive_flagged"])
        self.assertTrue(p0_card["why_surfaced"])

        earnings_card = summary["sections"]["tomorrow_earnings_events"][0]
        self.assertEqual(earnings_card["company_display_name"], "NVIDIA")
        self.assertEqual(earnings_card["link"]["label"], "Link pending")

    def test_empty_queue_produces_coverage_qualified_empty_state(self) -> None:
        with _migrated_connection() as connection:
            _seed_registries(connection)
            run_scan(
                connection,
                scan_run_id="run-empty",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW,
                queue_date=QUEUE_DATE,
                podcast_adapter=FixturePodcastFeedAdapter({}),
                channel_adapter=FixtureChannelVideoAdapter({}),
                earnings_adapter=FixtureEarningsEventAdapter({}),
                filings_adapter=FixtureFilingsAdapter({}),
            )
            summary = build_knowledge_edge_queue_summary(
                connection, queue_date=QUEUE_DATE, feature_mode="fixture"
            )

        self.assertIsNotNone(summary["empty_state"])
        self.assertIn("No qualifying item was found among the sources successfully checked", summary["empty_state"])
        self.assertIn("of", summary["empty_state"])
        self.assertNotIn("no appearance occurred", summary["empty_state"])  # empty-state text itself, not the honesty caption

    def test_ambiguous_item_surfaces_demoted_with_label_not_in_any_priority_section(self) -> None:
        ambiguous_item = DiscoveredMediaItem(
            source_id="src-frontier-ai",
            source_specific_id="vid-ambiguous-1",
            canonical_url="https://example.com/watch?v=ambiguous-1",
            title="Jensen Huang Segment (duration unknown)",
            media_type="video_interview",
            source_precedence="reputable_secondary",
            format_hint="financial_media_segment",
            matched_person_id="ke-person-jensen-huang",
            duration_seconds=None,
            published_at="2026-07-16T10:00:00+00:00",
            cursor_value="0002",
        )
        with _migrated_connection() as connection:
            _seed_registries(connection)
            _run_four_lane_scan(connection, extra_frontier_items=(ambiguous_item,))
            summary = build_knowledge_edge_queue_summary(
                connection, queue_date=QUEUE_DATE, feature_mode="fixture"
            )

        self.assertEqual(len(summary["demoted_ambiguous"]), 1)
        demoted = summary["demoted_ambiguous"][0]
        self.assertEqual(demoted["title"], "Jensen Huang Segment (duration unknown)")
        self.assertIn("ambiguous_unknown_duration_demoted", demoted["why_surfaced"])
        p0_titles = [card["title"] for card in summary["sections"]["p0_consequential_leaders"]]
        self.assertNotIn("Jensen Huang Segment (duration unknown)", p0_titles)

        html = render_knowledge_edge_queue_html(summary)
        self.assertIn("Demoted / Ambiguous", html)
        self.assertIn("Jensen Huang Segment (duration unknown)", html)
        self.assertIn("ambiguous_unknown_duration_demoted", html)

    def test_false_positive_flag_surfaces_in_hydrated_card(self) -> None:
        with _migrated_connection() as connection:
            _seed_registries(connection)
            _run_four_lane_scan(connection)
            p0_before = build_knowledge_edge_queue_summary(
                connection, queue_date=QUEUE_DATE, feature_mode="fixture"
            )["sections"]["p0_consequential_leaders"][0]
            self.assertFalse(p0_before["false_positive_flagged"])
            entity_match_id = p0_before["entity_match_ids"][0]

            ke.flag_entity_match_false_positive(connection, entity_match_id=entity_match_id)

            summary_after = build_knowledge_edge_queue_summary(
                connection, queue_date=QUEUE_DATE, feature_mode="fixture"
            )
            p0_after = summary_after["sections"]["p0_consequential_leaders"][0]

        self.assertTrue(p0_after["false_positive_flagged"])
        html = render_knowledge_edge_queue_html(summary_after)
        self.assertIn("flagged", html)


class EventLinkHierarchyTest(unittest.TestCase):
    def test_live_webcast_from_unapproved_domain_is_quarantined(self) -> None:
        event = {
            "live_webcast_url": "https://unknown-vendor.example.com/stream",
            "official_event_page_url": "https://nvidia.com/ir/events/q2",
            "replay_url": None,
        }
        link = _resolve_event_best_link(event, approved_webcast_vendor_domains=frozenset())
        self.assertTrue(link["quarantined"])
        self.assertEqual(link["label"], "Link pending (unknown vendor)")
        self.assertIsNone(link["url"])
        self.assertEqual(link["official_event_page_url"], "https://nvidia.com/ir/events/q2")

    def test_live_webcast_from_approved_domain_is_verified(self) -> None:
        event = {
            "live_webcast_url": "https://ir.nvidia.com/webcast/q2",
            "official_event_page_url": "https://nvidia.com/ir/events/q2",
            "replay_url": None,
        }
        link = _resolve_event_best_link(
            event, approved_webcast_vendor_domains=frozenset({"ir.nvidia.com"})
        )
        self.assertFalse(link["quarantined"])
        self.assertEqual(link["label"], "official company live webcast URL")
        self.assertEqual(link["url"], "https://ir.nvidia.com/webcast/q2")

    def test_falls_back_to_event_page_then_replay_then_link_pending(self) -> None:
        no_webcast_event = {
            "live_webcast_url": None,
            "official_event_page_url": "https://nvidia.com/ir/events/q2",
            "replay_url": None,
        }
        link = _resolve_event_best_link(no_webcast_event, approved_webcast_vendor_domains=frozenset())
        self.assertEqual(link["label"], "official company event detail page")
        self.assertEqual(link["url"], "https://nvidia.com/ir/events/q2")

        replay_only_event = {"live_webcast_url": None, "official_event_page_url": None, "replay_url": "https://nvidia.com/replay/q2"}
        link = _resolve_event_best_link(replay_only_event, approved_webcast_vendor_domains=frozenset())
        self.assertEqual(link["label"], "official company replay URL")
        self.assertEqual(link["url"], "https://nvidia.com/replay/q2")

        nothing_event = {"live_webcast_url": None, "official_event_page_url": None, "replay_url": None}
        link = _resolve_event_best_link(nothing_event, approved_webcast_vendor_domains=frozenset())
        self.assertEqual(link["label"], "Link pending")
        self.assertIsNone(link["url"])


class CoverageHonestyTest(unittest.TestCase):
    def test_coverage_section_reports_per_adapter_health_and_never_asserts_absence(self) -> None:
        with _migrated_connection() as connection:
            _seed_registries(connection)
            _run_four_lane_scan(connection)
            summary = build_knowledge_edge_queue_summary(
                connection, queue_date=QUEUE_DATE, feature_mode="fixture"
            )

        coverage = summary["coverage"]
        self.assertIn("healthy", coverage["overall_summary"])
        self.assertTrue(coverage["per_adapter_lines"])
        for line in coverage["per_adapter_lines"]:
            self.assertIn("healthy", line)
        self.assertIn("absence of a result is never proof that no appearance occurred", coverage["honesty_note"])

        html = render_knowledge_edge_queue_html(summary)
        self.assertIn("Coverage &amp; Source Health", html)
        self.assertIn("absence of a result is never proof that no appearance occurred", html)


if __name__ == "__main__":
    unittest.main()
