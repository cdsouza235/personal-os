import tempfile
import unittest
from pathlib import Path

from personalos.config import (
    DEFAULT_TIMEZONE,
    Environment,
    PersonalOSConfig,
    ProductionConfigUnavailable,
)
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import (
    MIGRATION_METADATA_TABLE,
    MigrationChecksumMismatch,
    apply_migrations,
    discover_migrations,
)


class SQLiteFoundationTest(unittest.TestCase):
    def test_dev_and_test_connections_open_safely(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"

            for environment in (Environment.DEVELOPMENT, Environment.TEST):
                with self.subTest(environment=environment):
                    config = _config_for(runtime_dir, environment)

                    with connect_sqlite(config, runtime_dir=runtime_dir) as connection:
                        result = connection.execute("SELECT 1").fetchone()[0]

                    self.assertEqual(result, 1)

    def test_parent_directories_are_created_only_for_dev_and_test(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            dev_config = _config_for(runtime_dir, Environment.DEVELOPMENT)
            production_config = PersonalOSConfig(
                environment=Environment.PRODUCTION,
                timezone=DEFAULT_TIMEZONE,
                database_path=runtime_dir / "production" / "blocked.sqlite3",
            )

            self.assertFalse(dev_config.database_path.parent.exists())
            with connect_sqlite(dev_config, runtime_dir=runtime_dir) as connection:
                connection.execute("SELECT 1")
            self.assertTrue(dev_config.database_path.parent.exists())

            with self.assertRaises(ProductionConfigUnavailable):
                connect_sqlite(production_config, runtime_dir=runtime_dir)
            self.assertFalse(production_config.database_path.parent.exists())

    def test_database_paths_outside_runtime_area_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runtime_dir = temp_path / "runtime"
            outside_config = PersonalOSConfig(
                environment=Environment.TEST,
                timezone=DEFAULT_TIMEZONE,
                database_path=temp_path / "outside.sqlite3",
            )

            with self.assertRaises(ValueError):
                connect_sqlite(outside_config, runtime_dir=runtime_dir)

            self.assertFalse(outside_config.database_path.exists())

    def test_production_database_access_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            production_config = PersonalOSConfig(
                environment=Environment.PRODUCTION,
                timezone=DEFAULT_TIMEZONE,
                database_path=runtime_dir / "production" / "blocked.sqlite3",
            )

            with self.assertRaises(ProductionConfigUnavailable):
                connect_sqlite(production_config, runtime_dir=runtime_dir)

    def test_migration_application_is_idempotent_and_records_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with connect_sqlite(config, runtime_dir=runtime_dir) as connection:
                first_applied = apply_migrations(connection)
                second_applied = apply_migrations(connection)

                rows = connection.execute(
                    f"SELECT version, name, checksum FROM {MIGRATION_METADATA_TABLE}"
                ).fetchall()

            self.assertEqual([migration.version for migration in first_applied], ["0001", "0002"])
            self.assertEqual(second_applied, [])
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["version"], "0001")
            self.assertEqual(rows[0]["name"], "bootstrap")
            self.assertTrue(rows[0]["checksum"])

    def test_migration_checksum_drift_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runtime_dir = temp_path / "runtime"
            migrations_dir = temp_path / "migrations"
            migrations_dir.mkdir()
            migration_path = migrations_dir / "0001_bootstrap.sql"
            migration_path.write_text("SELECT 1;\n", encoding="utf-8")
            config = _config_for(runtime_dir, Environment.TEST)

            with connect_sqlite(config, runtime_dir=runtime_dir) as connection:
                first_applied = apply_migrations(connection, migrations_dir=migrations_dir)
                second_applied = apply_migrations(connection, migrations_dir=migrations_dir)
                recorded_checksum = connection.execute(
                    f"SELECT checksum FROM {MIGRATION_METADATA_TABLE} WHERE version = ?",
                    ("0001",),
                ).fetchone()["checksum"]

                migration_path.write_text("SELECT 2;\n", encoding="utf-8")

                with self.assertRaises(MigrationChecksumMismatch) as context:
                    apply_migrations(connection, migrations_dir=migrations_dir)

            self.assertEqual([migration.version for migration in first_applied], ["0001"])
            self.assertEqual(second_applied, [])
            self.assertEqual(context.exception.version, "0001")
            self.assertEqual(context.exception.recorded_checksum, recorded_checksum)
            self.assertNotEqual(context.exception.current_checksum, recorded_checksum)

    def test_migration_discovery_finds_foundation_migrations(self) -> None:
        migrations = discover_migrations()

        self.assertEqual([migration.version for migration in migrations], ["0001", "0002"])
        self.assertEqual([migration.name for migration in migrations], ["bootstrap", "system_events"])


def _config_for(runtime_dir: Path, environment: Environment) -> PersonalOSConfig:
    directory_name = "dev" if environment is Environment.DEVELOPMENT else "test"
    return PersonalOSConfig(
        environment=environment,
        timezone=DEFAULT_TIMEZONE,
        database_path=runtime_dir / directory_name / "personalos.sqlite3",
    )
