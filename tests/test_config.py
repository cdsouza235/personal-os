import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from personalos import config as config_module
from personalos.config import (
    DEFAULT_TIMEZONE,
    RUNTIME_DIR,
    Environment,
    ProductionConfigUnavailable,
    bootstrap_production_database,
    load_config,
)


class ConfigBoundaryTest(unittest.TestCase):
    def test_default_environment_is_safe_non_production(self) -> None:
        config = load_config()

        self.assertEqual(config.environment, Environment.DEVELOPMENT)
        self.assertFalse(config.is_production)

    def test_default_timezone_is_america_chicago(self) -> None:
        self.assertEqual(load_config().timezone, DEFAULT_TIMEZONE)
        self.assertEqual(DEFAULT_TIMEZONE, "America/Chicago")

    def test_dev_and_test_database_paths_stay_inside_runtime_area(self) -> None:
        expected_runtime_dirs = {
            Environment.DEVELOPMENT: "dev",
            Environment.TEST: "test",
        }

        for environment in (Environment.DEVELOPMENT, Environment.TEST):
            with self.subTest(environment=environment):
                config = load_config(environment)

                self.assertEqual(config.database_path.suffix, ".sqlite3")
                runtime_relative_path = config.database_path.resolve().relative_to(
                    RUNTIME_DIR.resolve()
                )
                self.assertEqual(runtime_relative_path.parts[0], expected_runtime_dirs[environment])

    def test_production_config_is_not_selected_by_default(self) -> None:
        self.assertNotEqual(load_config().environment, Environment.PRODUCTION)

    def test_production_db_path_constant_matches_the_d_po_011_approved_location(self) -> None:
        # Pure value comparison -- no filesystem access to the real path happens here.
        self.assertEqual(
            config_module.PRODUCTION_DB_PATH,
            Path("/Users/coldstake/PersonalOS/personal_os.db"),
        )

    def test_production_config_resolves_to_the_approved_path_stand_in(self) -> None:
        # Never touches the real production path: PRODUCTION_DB_PATH is monkeypatched to
        # a temp stand-in for the duration of this test only.
        with tempfile.TemporaryDirectory() as temp_dir:
            stand_in_path = Path(temp_dir) / "PersonalOS" / "personal_os.db"
            with mock.patch.object(config_module, "PRODUCTION_DB_PATH", stand_in_path):
                config = load_config(Environment.PRODUCTION)

                self.assertTrue(config.is_production)
                self.assertEqual(config.database_path, stand_in_path.resolve())

    def test_production_path_validation_rejects_any_mismatched_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_stand_in = Path(temp_dir) / "PersonalOS" / "personal_os.db"
            other_path = Path(temp_dir) / "PersonalOS" / "not_the_approved_file.db"
            with mock.patch.object(config_module, "PRODUCTION_DB_PATH", approved_stand_in):
                with self.assertRaises(ProductionConfigUnavailable):
                    config_module._ensure_production_runtime_path(other_path)

                # The exact approved stand-in still passes.
                config_module._ensure_production_runtime_path(approved_stand_in)

    def test_bootstrap_production_database_applies_migrations_to_the_stand_in_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            stand_in_path = Path(temp_dir) / "PersonalOS" / "personal_os.db"
            with mock.patch.object(config_module, "PRODUCTION_DB_PATH", stand_in_path):
                applied = bootstrap_production_database()

                self.assertTrue(stand_in_path.exists())
                self.assertGreater(len(applied), 0)

                connection = sqlite3.connect(stand_in_path)
                try:
                    applied_versions = {
                        row[0]
                        for row in connection.execute(
                            "SELECT version FROM schema_migrations"
                        ).fetchall()
                    }
                finally:
                    connection.close()
                self.assertEqual(applied_versions, {migration["version"] for migration in applied})
