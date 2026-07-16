"""P-KE-1A: media item / scheduled event state -- dedupe uniqueness, canonical
grouping, entity matches (confidence/reason/false-positive), the 90-day rolling
appearance-history window, and the three-track (content_status / decision_state /
queue_visibility_state) transition rules (amendment §8.4, §11.3, §11.4, §13.1-13.3).
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import personalos.knowledge_edge.state as ke
from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations


def _seed_source(connection: sqlite3.Connection, source_id: str = "src-1") -> None:
    ke.create_source(
        connection,
        source_id=source_id,
        source_type="podcast_feed",
        lane="curated_podcasts",
        name="Test Podcast",
    )


class MediaItemDedupeTest(unittest.TestCase):
    def test_dedupe_key_is_unique(self) -> None:
        with _migrated_connection() as connection:
            _seed_source(connection)
            ke.create_media_item(
                connection,
                media_item_id="media-1",
                source_id="src-1",
                source_specific_id="ep-1",
                canonical_url="https://example.com/ep-1",
                title="Episode 1",
                source_precedence="official",
                media_type="podcast_episode",
                dedupe_key="dedupe-ep-1",
            )
            with self.assertRaises(sqlite3.IntegrityError):
                ke.create_media_item(
                    connection,
                    media_item_id="media-2",
                    source_id="src-1",
                    source_specific_id="ep-2",
                    canonical_url="https://example.com/ep-2",
                    title="Episode 1 (duplicate)",
                    source_precedence="official",
                    media_type="podcast_episode",
                    dedupe_key="dedupe-ep-1",
                )

    def test_get_media_item_by_dedupe_key(self) -> None:
        with _migrated_connection() as connection:
            _seed_source(connection)
            created = ke.create_media_item(
                connection,
                media_item_id="media-1",
                source_id="src-1",
                source_specific_id="ep-1",
                canonical_url="https://example.com/ep-1",
                title="Episode 1",
                source_precedence="official",
                media_type="podcast_episode",
                dedupe_key="dedupe-ep-1",
            )
            fetched = ke.get_media_item_by_dedupe_key(connection, "dedupe-ep-1")
        self.assertEqual(created["media_item_id"], fetched["media_item_id"])

    def test_source_specific_id_is_unique_per_source(self) -> None:
        with _migrated_connection() as connection:
            _seed_source(connection)
            ke.create_media_item(
                connection,
                media_item_id="media-1",
                source_id="src-1",
                source_specific_id="ep-1",
                canonical_url="https://example.com/ep-1",
                title="Episode 1",
                source_precedence="official",
                media_type="podcast_episode",
                dedupe_key="dedupe-a",
            )
            with self.assertRaises(sqlite3.IntegrityError):
                ke.create_media_item(
                    connection,
                    media_item_id="media-2",
                    source_id="src-1",
                    source_specific_id="ep-1",
                    canonical_url="https://example.com/ep-1-alt",
                    title="Episode 1 (repost)",
                    source_precedence="official",
                    media_type="podcast_episode",
                    dedupe_key="dedupe-b",
                )


class CanonicalGroupingTest(unittest.TestCase):
    def test_canonical_group_members_round_trip(self) -> None:
        with _migrated_connection() as connection:
            _seed_source(connection)
            group = ke.create_canonical_group(
                connection, canonical_group_id="group-1", dedupe_rule="live_and_official_replay"
            )
            ke.create_media_item(
                connection,
                media_item_id="media-live",
                source_id="src-1",
                source_specific_id="live-1",
                canonical_url="https://example.com/live",
                title="Live",
                source_precedence="official",
                media_type="video_interview",
                dedupe_key="dedupe-live",
                canonical_group_id=group["canonical_group_id"],
                is_canonical=True,
            )
            ke.create_media_item(
                connection,
                media_item_id="media-replay",
                source_id="src-1",
                source_specific_id="replay-1",
                canonical_url="https://example.com/replay",
                title="Replay",
                source_precedence="official",
                media_type="video_interview",
                dedupe_key="dedupe-replay",
                canonical_group_id=group["canonical_group_id"],
                is_canonical=False,
            )
            members = ke.list_canonical_group_members(
                connection, canonical_group_id="group-1"
            )
        self.assertEqual(len(members), 2)
        self.assertTrue(members[0]["is_canonical"])


class EntityMatchAndAppearanceHistoryTest(unittest.TestCase):
    def _seed_media_item(
        self, connection: sqlite3.Connection, media_item_id: str, discovered_at: str
    ) -> None:
        if ke.get_source(connection, "src-1") is None:
            _seed_source(connection)
        ke.create_media_item(
            connection,
            media_item_id=media_item_id,
            source_id="src-1",
            source_specific_id=media_item_id,
            canonical_url=f"https://example.com/{media_item_id}",
            title=media_item_id,
            source_precedence="official",
            media_type="podcast_episode",
            dedupe_key=f"dedupe-{media_item_id}",
            discovered_at=discovered_at,
        )

    def test_entity_match_confidence_reason_and_false_positive_flag(self) -> None:
        with _migrated_connection() as connection:
            self._seed_media_item(connection, "media-1", "2026-07-10T00:00:00+00:00")
            match = ke.create_entity_match(
                connection,
                entity_match_id="match-1",
                target_type="media_item",
                target_id="media-1",
                matched_entity_type="person",
                matched_entity_id="ke-person-kevin-warsh",
                match_method="exact_alias",
                confidence=0.95,
                reason="Exact alias match on 'Kevin Warsh'",
            )
            self.assertFalse(match["is_false_positive"])
            self.assertIsNone(match["flagged_at"])

            flagged = ke.flag_entity_match_false_positive(connection, entity_match_id="match-1")
        self.assertTrue(flagged["is_false_positive"])
        self.assertIsNotNone(flagged["flagged_at"])

    def test_appearance_history_within_90_day_window(self) -> None:
        as_of = "2026-07-16"
        with _migrated_connection() as connection:
            self._seed_media_item(connection, "media-recent", "2026-07-01T00:00:00+00:00")
            self._seed_media_item(connection, "media-old", "2026-03-01T00:00:00+00:00")
            ke.create_entity_match(
                connection,
                entity_match_id="match-recent",
                target_type="media_item",
                target_id="media-recent",
                matched_entity_type="person",
                matched_entity_id="ke-person-kevin-warsh",
                match_method="exact_alias",
                confidence=0.9,
                reason="Within window",
            )
            ke.create_entity_match(
                connection,
                entity_match_id="match-old",
                target_type="media_item",
                target_id="media-old",
                matched_entity_type="person",
                matched_entity_id="ke-person-kevin-warsh",
                match_method="exact_alias",
                confidence=0.9,
                reason="Outside window",
            )
            history = ke.list_entity_appearance_history(
                connection,
                matched_entity_type="person",
                matched_entity_id="ke-person-kevin-warsh",
                as_of_date=as_of,
                window_days=90,
            )
        media_item_ids = {item["media_item_id"] for item in history}
        self.assertIn("media-recent", media_item_ids)
        self.assertNotIn("media-old", media_item_ids)

    def test_appearance_history_excludes_false_positives_by_default(self) -> None:
        with _migrated_connection() as connection:
            self._seed_media_item(connection, "media-1", "2026-07-10T00:00:00+00:00")
            ke.create_entity_match(
                connection,
                entity_match_id="match-1",
                target_type="media_item",
                target_id="media-1",
                matched_entity_type="person",
                matched_entity_id="ke-person-kevin-warsh",
                match_method="exact_alias",
                confidence=0.9,
                reason="Later flagged bad",
            )
            ke.flag_entity_match_false_positive(connection, entity_match_id="match-1")

            excluding = ke.list_entity_appearance_history(
                connection,
                matched_entity_type="person",
                matched_entity_id="ke-person-kevin-warsh",
                as_of_date="2026-07-16",
            )
            including = ke.list_entity_appearance_history(
                connection,
                matched_entity_type="person",
                matched_entity_id="ke-person-kevin-warsh",
                as_of_date="2026-07-16",
                include_false_positives=True,
            )
        self.assertEqual(excluding, [])
        self.assertEqual(len(including), 1)

    def test_entity_match_confidence_bounds_are_enforced(self) -> None:
        with _migrated_connection() as connection:
            self._seed_media_item(connection, "media-1", "2026-07-10T00:00:00+00:00")
            with self.assertRaises(ValueError):
                ke.create_entity_match(
                    connection,
                    entity_match_id="match-bad",
                    target_type="media_item",
                    target_id="media-1",
                    matched_entity_type="person",
                    matched_entity_id="ke-person-kevin-warsh",
                    match_method="exact_alias",
                    confidence=1.5,
                    reason="Out of bounds",
                )


class MediaThreeTrackTransitionTest(unittest.TestCase):
    def _create_media_item(self, connection: sqlite3.Connection) -> None:
        _seed_source(connection)
        ke.create_media_item(
            connection,
            media_item_id="media-1",
            source_id="src-1",
            source_specific_id="ep-1",
            canonical_url="https://example.com/ep-1",
            title="Episode 1",
            source_precedence="official",
            media_type="podcast_episode",
            dedupe_key="dedupe-1",
        )

    def test_content_status_valid_transition_succeeds(self) -> None:
        with _migrated_connection() as connection:
            self._create_media_item(connection)
            updated = ke.update_media_content_status(
                connection, media_item_id="media-1", content_status="normalized"
            )
        self.assertEqual(updated["content_status"], "normalized")

    def test_content_status_invalid_transition_raises(self) -> None:
        with _migrated_connection() as connection:
            self._create_media_item(connection)
            with self.assertRaises(ke.InvalidTransitionError):
                ke.update_media_content_status(
                    connection, media_item_id="media-1", content_status="archived"
                )

    def test_decision_state_watched_is_terminal(self) -> None:
        with _migrated_connection() as connection:
            self._create_media_item(connection)
            ke.update_media_decision_state(
                connection, media_item_id="media-1", decision_state="watch"
            )
            ke.update_media_decision_state(
                connection, media_item_id="media-1", decision_state="watched"
            )
            with self.assertRaises(ke.InvalidTransitionError):
                ke.update_media_decision_state(
                    connection, media_item_id="media-1", decision_state="skip"
                )

    def test_queue_visibility_transition_sequence(self) -> None:
        with _migrated_connection() as connection:
            self._create_media_item(connection)
            ke.update_media_queue_visibility(
                connection, media_item_id="media-1", queue_visibility_state="queued"
            )
            updated = ke.update_media_queue_visibility(
                connection, media_item_id="media-1", queue_visibility_state="suppressed"
            )
        self.assertEqual(updated["queue_visibility_state"], "suppressed")

    def test_watched_skipped_expired_never_appear_in_content_status_track(self) -> None:
        self.assertNotIn("watched", ke.MEDIA_CONTENT_STATUSES)
        self.assertNotIn("skipped", ke.MEDIA_CONTENT_STATUSES)
        self.assertNotIn("expired", ke.MEDIA_CONTENT_STATUSES)


class ScheduledEventTest(unittest.TestCase):
    def _seed_company(self, connection: sqlite3.Connection) -> None:
        ke.create_company(
            connection,
            company_id="company-1",
            legal_name="Test Co",
            display_name="Test Co",
            roster_group="nasdaq100_top10",
            roster_status="confirmed",
        )

    def test_scheduled_event_round_trip_and_filing_urls(self) -> None:
        with _migrated_connection() as connection:
            self._seed_company(connection)
            created = ke.create_scheduled_event(
                connection,
                event_id="event-1",
                company_id="company-1",
                event_type="quarterly_earnings",
                scheduled_date="2026-08-01",
                filing_urls=["https://sec.gov/filing-1", "https://sec.gov/filing-2"],
            )
        self.assertEqual(created["filing_urls"], [
            "https://sec.gov/filing-1", "https://sec.gov/filing-2",
        ])
        self.assertEqual(created["event_status"], "discovered")

    def test_event_status_transition_from_pre_event_to_cancelled(self) -> None:
        with _migrated_connection() as connection:
            self._seed_company(connection)
            ke.create_scheduled_event(
                connection,
                event_id="event-1",
                company_id="company-1",
                event_type="quarterly_earnings",
                scheduled_date="2026-08-01",
            )
            updated = ke.update_event_status(
                connection, event_id="event-1", event_status="cancelled"
            )
        self.assertEqual(updated["event_status"], "cancelled")

    def test_event_status_terminal_state_rejects_further_transitions(self) -> None:
        with _migrated_connection() as connection:
            self._seed_company(connection)
            ke.create_scheduled_event(
                connection,
                event_id="event-1",
                company_id="company-1",
                event_type="quarterly_earnings",
                scheduled_date="2026-08-01",
            )
            ke.update_event_status(connection, event_id="event-1", event_status="cancelled")
            with self.assertRaises(ke.InvalidTransitionError):
                ke.update_event_status(
                    connection, event_id="event-1", event_status="confirmed"
                )

    def test_unique_constraint_on_company_fiscal_period_event_type(self) -> None:
        with _migrated_connection() as connection:
            self._seed_company(connection)
            ke.create_scheduled_event(
                connection,
                event_id="event-1",
                company_id="company-1",
                event_type="quarterly_earnings",
                scheduled_date="2026-08-01",
                fiscal_period="2026-Q2",
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO ke_scheduled_events (
                        event_id, company_id, fiscal_period, event_type, scheduled_date,
                        time_precision, source_timezone, schedule_confidence,
                        schedule_source, filing_urls_json, event_status, decision_state,
                        queue_visibility_state, pinned, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "event-2", "company-1", "2026-Q2", "quarterly_earnings",
                        "2026-08-15", "date_only", "UTC", "unknown", "", "[]",
                        "discovered", "undecided", "candidate", 0,
                        "2026-07-16T00:00:00+00:00", "2026-07-16T00:00:00+00:00",
                    ),
                )


def _config_for(runtime_dir: Path, environment: Environment) -> PersonalOSConfig:
    directory_name = "dev" if environment is Environment.DEVELOPMENT else "test"
    return PersonalOSConfig(
        environment=environment,
        timezone=DEFAULT_TIMEZONE,
        database_path=runtime_dir / directory_name / "personalos.sqlite3",
    )


@contextmanager
def _connected_sqlite(
    config: PersonalOSConfig,
    *,
    runtime_dir: Path,
) -> Iterator[sqlite3.Connection]:
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


if __name__ == "__main__":
    unittest.main()
