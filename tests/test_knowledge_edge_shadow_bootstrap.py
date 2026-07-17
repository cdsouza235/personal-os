"""P-KE-2C: shadow-database bootstrap tests
(personalos.knowledge_edge.shadow_bootstrap).

No network-capable import anywhere in this module or the module under test --
`bootstrap_shadow_database` takes the smoke transcript's verification data as
LITERAL config, it never re-fetches anything.
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
from personalos.knowledge_edge.shadow_bootstrap import (
    LANE_A_SHADOW_VERIFICATION_FLIPS,
    ShadowBootstrapError,
    bootstrap_shadow_database,
)


@contextmanager
def _unmigrated_test_connection() -> Iterator[sqlite3.Connection]:
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir) / "runtime"
        config = PersonalOSConfig(
            environment=Environment.TEST,
            timezone=DEFAULT_TIMEZONE,
            database_path=runtime_dir / "test" / "personalos.sqlite3",
        )
        connection = connect_sqlite(config, runtime_dir=runtime_dir)
        try:
            yield connection
        finally:
            connection.close()


class BootstrapShadowDatabaseTest(unittest.TestCase):
    def test_nine_flips_are_declared(self) -> None:
        self.assertEqual(len(LANE_A_SHADOW_VERIFICATION_FLIPS), 9)
        self.assertEqual(
            len({flip.source_id for flip in LANE_A_SHADOW_VERIFICATION_FLIPS}), 9
        )

    def test_first_run_applies_migrations_and_flips_all_nine(self) -> None:
        with _unmigrated_test_connection() as connection:
            result = bootstrap_shadow_database(connection)

            self.assertGreater(len(result.migrations_applied), 0)
            self.assertEqual(len(result.sources_flipped_to_active), 9)
            self.assertEqual(len(result.endpoints_verified), 9)
            self.assertEqual(result.already_bootstrapped, ())

            for flip in LANE_A_SHADOW_VERIFICATION_FLIPS:
                source = ke.get_source(connection, flip.source_id)
                self.assertEqual(source["status"], "active")
                endpoints = ke.list_source_endpoints(connection, source_id=flip.source_id)
                matching = [e for e in endpoints if e["url"] == flip.endpoint_url]
                self.assertEqual(len(matching), 1)
                self.assertEqual(matching[0]["endpoint_verified_at"], flip.verified_at)
                self.assertEqual(matching[0]["verified_by"], flip.verified_by)

    def test_second_run_is_a_no_op_idempotent(self) -> None:
        with _unmigrated_test_connection() as connection:
            bootstrap_shadow_database(connection)
            second = bootstrap_shadow_database(connection)

            self.assertEqual(second.migrations_applied, ())
            self.assertEqual(second.sources_flipped_to_active, ())
            self.assertEqual(second.endpoints_verified, ())
            self.assertEqual(len(second.already_bootstrapped), 9)

    def test_registry_is_byte_equivalent_across_two_independent_bootstraps(self) -> None:
        """Two freshly-bootstrapped shadow connections must end up with identical
        source/endpoint verification state -- the whole point of "literal config, no
        re-fetching" is that this is deterministic, not just idempotent per-connection.
        """
        with _unmigrated_test_connection() as connection_a:
            bootstrap_shadow_database(connection_a)
            sources_a = {
                source["source_id"]: (source["status"])
                for source in ke.list_sources(connection_a)
            }
            endpoints_a = {
                (endpoint["source_id"], endpoint["url"]): (
                    endpoint["endpoint_verified_at"],
                    endpoint["verified_by"],
                )
                for source in ke.list_sources(connection_a)
                for endpoint in ke.list_source_endpoints(connection_a, source_id=source["source_id"])
            }

        with _unmigrated_test_connection() as connection_b:
            bootstrap_shadow_database(connection_b)
            sources_b = {
                source["source_id"]: (source["status"])
                for source in ke.list_sources(connection_b)
            }
            endpoints_b = {
                (endpoint["source_id"], endpoint["url"]): (
                    endpoint["endpoint_verified_at"],
                    endpoint["verified_by"],
                )
                for source in ke.list_sources(connection_b)
                for endpoint in ke.list_source_endpoints(connection_b, source_id=source["source_id"])
            }

        self.assertEqual(sources_a, sources_b)
        self.assertEqual(endpoints_a, endpoints_b)

    def test_missing_source_raises_shadow_bootstrap_error(self) -> None:
        with _unmigrated_test_connection() as connection:
            from personalos.db.migrations import apply_migrations

            apply_migrations(connection)
            connection.execute(
                "DELETE FROM ke_source_endpoints WHERE source_id = 'ke-source-dwarkesh-podcast'"
            )
            connection.execute(
                "DELETE FROM ke_sources WHERE source_id = 'ke-source-dwarkesh-podcast'"
            )
            connection.commit()

            with self.assertRaises(ShadowBootstrapError):
                bootstrap_shadow_database(connection)

    def test_unexpected_source_status_raises_shadow_bootstrap_error(self) -> None:
        with _unmigrated_test_connection() as connection:
            from personalos.db.migrations import apply_migrations

            apply_migrations(connection)
            connection.execute(
                "UPDATE ke_sources SET status = 'retired' WHERE source_id = 'ke-source-dwarkesh-podcast'"
            )
            connection.commit()

            with self.assertRaises(ShadowBootstrapError):
                bootstrap_shadow_database(connection)


if __name__ == "__main__":
    unittest.main()
