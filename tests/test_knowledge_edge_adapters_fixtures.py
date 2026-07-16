"""P-KE-1B: adapter contracts + fixture implementations."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime

from personalos.knowledge_edge.adapters.contracts import DiscoveredEvent, DiscoveredMediaItem
from personalos.knowledge_edge.adapters.fixtures import (
    FIXTURE_FAILURE_SUMMARY,
    FixtureChannelVideoAdapter,
    FixtureEarningsEventAdapter,
    FixturePodcastFeedAdapter,
    FixtureFilingsAdapter,
)

NOW = datetime(2026, 7, 16, tzinfo=UTC)


def _episode(cursor_value: str) -> DiscoveredMediaItem:
    return DiscoveredMediaItem(
        source_id="src-podcast-1",
        source_specific_id=f"ep-{cursor_value}",
        canonical_url=f"https://example.com/ep-{cursor_value}",
        title=f"Episode {cursor_value}",
        media_type="podcast_episode",
        source_precedence="official",
        format_hint="original_podcast_guest",
        cursor_value=cursor_value,
    )


class FixturePodcastFeedAdapterTest(unittest.TestCase):
    def test_fetch_without_cursor_returns_all_records_sorted(self) -> None:
        adapter = FixturePodcastFeedAdapter({"src-podcast-1": (_episode("0003"), _episode("0001"), _episode("0002"))})
        result = adapter.fetch_episodes(source_id="src-podcast-1", cursor=None, now=NOW)
        self.assertTrue(result.healthy)
        self.assertEqual([item.cursor_value for item in result.items], ["0001", "0002", "0003"])
        self.assertEqual(result.next_cursor_value, "0003")

    def test_fetch_with_cursor_returns_only_due_records(self) -> None:
        adapter = FixturePodcastFeedAdapter({"src-podcast-1": (_episode("0001"), _episode("0002"), _episode("0003"))})
        result = adapter.fetch_episodes(source_id="src-podcast-1", cursor="0001", now=NOW)
        self.assertEqual([item.cursor_value for item in result.items], ["0002", "0003"])

    def test_fetch_with_cursor_beyond_all_records_returns_empty_and_preserves_cursor(self) -> None:
        adapter = FixturePodcastFeedAdapter({"src-podcast-1": (_episode("0001"),)})
        result = adapter.fetch_episodes(source_id="src-podcast-1", cursor="0001", now=NOW)
        self.assertEqual(result.items, ())
        self.assertEqual(result.next_cursor_value, "0001")

    def test_unknown_source_returns_empty_healthy_result(self) -> None:
        adapter = FixturePodcastFeedAdapter({})
        result = adapter.fetch_episodes(source_id="src-unknown", cursor=None, now=NOW)
        self.assertTrue(result.healthy)
        self.assertEqual(result.items, ())

    def test_failing_source_returns_unhealthy_result_and_preserves_cursor(self) -> None:
        adapter = FixturePodcastFeedAdapter(
            {"src-podcast-1": (_episode("0001"),)}, failing_sources=frozenset({"src-podcast-1"})
        )
        result = adapter.fetch_episodes(source_id="src-podcast-1", cursor="0000", now=NOW)
        self.assertFalse(result.healthy)
        self.assertEqual(result.error_summary, FIXTURE_FAILURE_SUMMARY)
        self.assertEqual(result.items, ())
        self.assertEqual(result.next_cursor_value, "0000")


class FixtureChannelVideoAdapterTest(unittest.TestCase):
    def test_fetch_uploads_basic(self) -> None:
        video = DiscoveredMediaItem(
            source_id="src-yt-1",
            source_specific_id="vid-1",
            canonical_url="https://youtube.com/watch?v=vid-1",
            title="An Interview",
            media_type="video_interview",
            source_precedence="official",
            format_hint="original_long_form_interview",
            cursor_value="2026-07-16T00:00:00+00:00",
        )
        adapter = FixtureChannelVideoAdapter({"src-yt-1": (video,)})
        result = adapter.fetch_uploads(source_id="src-yt-1", cursor=None, now=NOW)
        self.assertTrue(result.healthy)
        self.assertEqual(len(result.items), 1)


class FixtureEarningsEventAdapterTest(unittest.TestCase):
    def test_fetch_events_basic(self) -> None:
        event = DiscoveredEvent(
            source_id="src-cal-1",
            company_id="ke-company-nvda",
            event_id_hint="2026-q3",
            event_type="quarterly_earnings",
            scheduled_date="2026-08-20",
            time_precision="date_only",
            schedule_confidence="estimated",
            schedule_source="fixture",
            cursor_value="0001",
        )
        adapter = FixtureEarningsEventAdapter({"src-cal-1": (event,)})
        result = adapter.fetch_events(source_id="src-cal-1", cursor=None, now=NOW)
        self.assertTrue(result.healthy)
        self.assertEqual(result.items[0].company_id, "ke-company-nvda")


class FixtureFilingsAdapterTest(unittest.TestCase):
    def test_fetch_filings_healthy_source_unaffected_by_other_failing_sources(self) -> None:
        adapter = FixtureFilingsAdapter({}, failing_sources=frozenset({"other-source"}))
        result = adapter.fetch_filings(source_id="src-edgar-1", cursor=None, now=NOW)
        self.assertTrue(result.healthy)
        self.assertEqual(result.items, ())


if __name__ == "__main__":
    unittest.main()
