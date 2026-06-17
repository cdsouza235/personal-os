import json
import tempfile
import unittest
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from personalos.config import (
    DEFAULT_TIMEZONE,
    Environment,
    PersonalOSConfig,
    ProductionConfigUnavailable,
)
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.events import (
    EventType,
    create_system_event,
    record_system_event,
    serialize_metadata,
)


class SystemEventTest(unittest.TestCase):
    def test_events_can_be_recorded_to_isolated_test_db(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with closing(connect_sqlite(config, runtime_dir=runtime_dir)) as connection:
                apply_migrations(connection)
                event = create_system_event(
                    source="tests.system_events",
                    event_type=EventType.INFO,
                    message="test event recorded",
                    metadata={"safe": True, "count": 1},
                )
                record_system_event(connection, event)
                row = connection.execute(
                    """
                    SELECT event_id, timestamp_utc, source, event_type, message, metadata_json
                    FROM system_events
                    WHERE event_id = ?
                    """,
                    (event.event_id,),
                ).fetchone()

            self.assertEqual(row["event_id"], event.event_id)
            self.assertEqual(row["source"], "tests.system_events")
            self.assertEqual(row["event_type"], EventType.INFO.value)
            self.assertEqual(row["message"], "test event recorded")
            self.assertEqual(json.loads(row["metadata_json"]), {"count": 1, "safe": True})

    def test_event_timestamp_is_utc_iso_formatted(self) -> None:
        event = create_system_event(
            source="tests.system_events",
            event_type=EventType.WARNING,
            message="timestamp check",
        )

        parsed_timestamp = datetime.fromisoformat(event.timestamp_utc)

        self.assertEqual(parsed_timestamp.tzinfo, UTC)
        self.assertTrue(event.timestamp_utc.endswith("+00:00"))

    def test_metadata_is_serialized_safely(self) -> None:
        metadata_json = serialize_metadata({"z": "last", "a": "first", "unicode": "check"})

        self.assertEqual(metadata_json, '{"a":"first","unicode":"check","z":"last"}')
        self.assertEqual(json.loads(metadata_json)["unicode"], "check")

    def test_event_ids_are_unique(self) -> None:
        first_event = create_system_event(
            source="tests.system_events",
            event_type=EventType.INFO,
            message="first",
        )
        second_event = create_system_event(
            source="tests.system_events",
            event_type=EventType.INFO,
            message="second",
        )

        self.assertNotEqual(first_event.event_id, second_event.event_id)

    def test_production_database_access_remains_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            production_config = PersonalOSConfig(
                environment=Environment.PRODUCTION,
                timezone=DEFAULT_TIMEZONE,
                database_path=runtime_dir / "production" / "blocked.sqlite3",
            )

            with self.assertRaises(ProductionConfigUnavailable):
                connect_sqlite(production_config, runtime_dir=runtime_dir)

            self.assertFalse(production_config.database_path.exists())


def _config_for(runtime_dir: Path, environment: Environment) -> PersonalOSConfig:
    directory_name = "dev" if environment is Environment.DEVELOPMENT else "test"
    return PersonalOSConfig(
        environment=environment,
        timezone=DEFAULT_TIMEZONE,
        database_path=runtime_dir / directory_name / "personalos.sqlite3",
    )
