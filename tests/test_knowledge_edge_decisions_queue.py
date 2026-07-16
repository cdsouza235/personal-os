"""P-KE-1A: user-decision / decision-history / queue-snapshot state (amendment §7.2,
§7.4, §13.4). ``ke_decision_history`` is append-only by construction -- the module
exposes no update/delete for it.
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


def _seed_media_item(connection: sqlite3.Connection, media_item_id: str = "media-1") -> None:
    if ke.get_source(connection, "src-1") is None:
        ke.create_source(
            connection,
            source_id="src-1",
            source_type="podcast_feed",
            lane="curated_podcasts",
            name="Test Podcast",
        )
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
    )


class UserDecisionTest(unittest.TestCase):
    def test_upsert_creates_then_replaces_current_decision(self) -> None:
        with _migrated_connection() as connection:
            _seed_media_item(connection)
            first = ke.upsert_user_decision(
                connection,
                decision_id="decision-1",
                entity_type="media_item",
                entity_id="media-1",
                decision_state="watch",
            )
            second = ke.upsert_user_decision(
                connection,
                decision_id="decision-2",
                entity_type="media_item",
                entity_id="media-1",
                decision_state="watched",
            )
            current = ke.get_user_decision(
                connection, entity_type="media_item", entity_id="media-1"
            )
            decision_count = ke.count_user_decisions(connection)
        self.assertEqual(first["decision_state"], "watch")
        self.assertEqual(second["decision_state"], "watched")
        self.assertEqual(current["decision_state"], "watched")
        # Only one row ever exists per (entity_type, entity_id): the upsert replaces,
        # not appends.
        self.assertEqual(decision_count, 1)

    def test_media_item_decision_state_rejects_event_only_values(self) -> None:
        with _migrated_connection() as connection:
            _seed_media_item(connection)
            with self.assertRaises(ValueError):
                ke.upsert_user_decision(
                    connection,
                    decision_id="decision-bad",
                    entity_type="media_item",
                    entity_id="media-1",
                    decision_state="watch_live",
                )

    def test_scheduled_event_decision_state_rejects_media_only_values(self) -> None:
        with _migrated_connection() as connection:
            ke.create_company(
                connection,
                company_id="company-1",
                legal_name="Test Co",
                display_name="Test Co",
                roster_group="nasdaq100_top10",
                roster_status="confirmed",
            )
            ke.create_scheduled_event(
                connection,
                event_id="event-1",
                company_id="company-1",
                event_type="quarterly_earnings",
                scheduled_date="2026-08-01",
            )
            with self.assertRaises(ValueError):
                ke.upsert_user_decision(
                    connection,
                    decision_id="decision-bad",
                    entity_type="scheduled_event",
                    entity_id="event-1",
                    decision_state="save_for_later",
                )


class DecisionHistoryAppendOnlyTest(unittest.TestCase):
    def test_decision_history_accumulates_rows_without_update_helper(self) -> None:
        with _migrated_connection() as connection:
            _seed_media_item(connection)
            ke.record_decision_history(
                connection,
                history_id="hist-1",
                entity_type="media_item",
                entity_id="media-1",
                track="decision_state",
                from_value="undecided",
                to_value="watch",
                changed_by="user",
            )
            ke.record_decision_history(
                connection,
                history_id="hist-2",
                entity_type="media_item",
                entity_id="media-1",
                track="decision_state",
                from_value="watch",
                to_value="watched",
                changed_by="user",
            )
            history = ke.list_decision_history(
                connection, entity_type="media_item", entity_id="media-1"
            )
            history_count = ke.count_decision_history(connection)
        self.assertEqual(len(history), 2)
        self.assertEqual([row["to_value"] for row in history], ["watch", "watched"])
        self.assertEqual(history_count, 2)

    def test_module_exposes_no_update_or_delete_for_decision_history(self) -> None:
        public_names = {
            name for name in dir(ke) if "decision_history" in name.lower()
        }
        self.assertEqual(
            public_names,
            {"record_decision_history", "list_decision_history", "count_decision_history"},
        )


class QueueSnapshotTest(unittest.TestCase):
    def test_queue_snapshot_round_trip_and_ordering(self) -> None:
        with _migrated_connection() as connection:
            _seed_media_item(connection, "media-1")
            _seed_media_item(connection, "media-2")
            ke.record_queue_snapshot(
                connection,
                snapshot_id="snap-1",
                queue_date="2026-07-16",
                section="p1_core_podcasts",
                entity_type="media_item",
                entity_id="media-2",
                rank_position=2,
            )
            ke.record_queue_snapshot(
                connection,
                snapshot_id="snap-2",
                queue_date="2026-07-16",
                section="p1_core_podcasts",
                entity_type="media_item",
                entity_id="media-1",
                rank_position=1,
            )
            snapshot = ke.list_queue_snapshot(
                connection, queue_date="2026-07-16", section="p1_core_podcasts"
            )
        self.assertEqual([row["entity_id"] for row in snapshot], ["media-1", "media-2"])

    def test_queue_snapshot_unique_per_date_section_entity(self) -> None:
        with _migrated_connection() as connection:
            _seed_media_item(connection, "media-1")
            ke.record_queue_snapshot(
                connection,
                snapshot_id="snap-1",
                queue_date="2026-07-16",
                section="p1_core_podcasts",
                entity_type="media_item",
                entity_id="media-1",
                rank_position=1,
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO ke_queue_snapshots (
                        snapshot_id, queue_date, section, entity_type, entity_id,
                        rank_position, explanation, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "snap-dup", "2026-07-16", "p1_core_podcasts", "media_item",
                        "media-1", 2, "", "2026-07-16T00:00:00+00:00",
                    ),
                )

    def test_invalid_queue_section_is_rejected(self) -> None:
        with _migrated_connection() as connection:
            _seed_media_item(connection, "media-1")
            with self.assertRaises(ValueError):
                ke.record_queue_snapshot(
                    connection,
                    snapshot_id="snap-bad",
                    queue_date="2026-07-16",
                    section="not_a_real_section",
                    entity_type="media_item",
                    entity_id="media-1",
                    rank_position=1,
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
