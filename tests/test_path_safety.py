import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from personalos import cli
from personalos import config as config_module
from personalos.db.migrations import apply_migrations
from personalos.path_safety import (
    reject_production_path,
    validate_existing_input_file_path,
    validate_existing_sqlite_path,
    validate_output_file_path,
)


class ProductionSqlitePathExceptionTest(unittest.TestCase):
    """P-SCHED-03: validate_existing_sqlite_path's narrow D-PO-011 exception.

    Every test here uses a temp-directory stand-in for config.PRODUCTION_DB_PATH,
    monkeypatched only for the duration of the test (mirroring tests/test_config.py's
    own pattern for the same constant). None of these tests ever resolve, stat, open,
    or create a file at the real /Users/coldstake/PersonalOS/personal_os.db path.
    """

    def test_approved_production_path_stand_in_passes_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            stand_in_path = Path(temp_dir) / "PersonalOS" / "personal_os.db"
            stand_in_path.parent.mkdir(parents=True)
            stand_in_path.touch()
            with mock.patch.object(config_module, "PRODUCTION_DB_PATH", stand_in_path):
                validated = validate_existing_sqlite_path(
                    str(stand_in_path), path_label="operator db_path"
                )

            self.assertEqual(validated, stand_in_path.resolve())

    def test_cli_connect_read_write_succeeds_for_approved_stand_in(self) -> None:
        # Proves the full path the `run morning` handler takes (_connect_read_write ->
        # validate_existing_sqlite_path -> sqlite3.connect) now succeeds end to end for
        # the approved path, without ever touching the real file.
        with tempfile.TemporaryDirectory() as temp_dir:
            stand_in_path = Path(temp_dir) / "PersonalOS" / "personal_os.db"
            stand_in_path.parent.mkdir(parents=True)
            connection = sqlite3.connect(stand_in_path)
            try:
                apply_migrations(connection)
            finally:
                connection.close()

            with mock.patch.object(config_module, "PRODUCTION_DB_PATH", stand_in_path):
                connection = cli._connect_read_write(str(stand_in_path))
                try:
                    connection.execute("SELECT 1")
                finally:
                    connection.close()

    def test_other_paths_under_personalos_home_are_still_rejected(self) -> None:
        home = Path.home().resolve()
        for filename in ("some_other_file.db", "personal_os.db.bak"):
            candidate = home / "PersonalOS" / filename
            with self.subTest(filename=filename):
                with self.assertRaises(ValueError):
                    validate_existing_sqlite_path(str(candidate), path_label="operator db_path")

    def test_exemption_is_exact_path_not_a_broadened_directory_glob(self) -> None:
        # Patch both Path.home() and PRODUCTION_DB_PATH to a temp stand-in so we can
        # exercise reject_protected_path's real "under ~/PersonalOS" branch without
        # touching the real home directory or the real production path. A sibling file
        # in the very same directory as the approved stand-in must still be rejected.
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_home = Path(temp_dir)
            approved_stand_in = fake_home / "PersonalOS" / "personal_os.db"
            sibling_file = fake_home / "PersonalOS" / "not_the_approved_file.db"
            approved_stand_in.parent.mkdir(parents=True)
            approved_stand_in.touch()
            sibling_file.touch()

            with mock.patch("personalos.path_safety.Path.home", return_value=fake_home):
                with mock.patch.object(config_module, "PRODUCTION_DB_PATH", approved_stand_in):
                    validated = validate_existing_sqlite_path(
                        str(approved_stand_in), path_label="operator db_path"
                    )
                    self.assertEqual(validated, approved_stand_in.resolve())

                    with self.assertRaises(ValueError):
                        validate_existing_sqlite_path(
                            str(sibling_file), path_label="operator db_path"
                        )

    def test_other_validation_functions_still_reject_personalos_home_unconditionally(self) -> None:
        home = Path.home().resolve()
        candidate = home / "PersonalOS" / config_module.PRODUCTION_DB_PATH.name

        with self.assertRaises(ValueError):
            validate_existing_input_file_path(str(candidate), path_label="input path")

        with self.assertRaises(ValueError):
            validate_output_file_path(str(candidate), path_label="output path")

    def test_reject_production_path_still_blocks_production_marker_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            for filename in ("production.db", "prod.db", "live.db"):
                candidate = Path(temp_dir) / filename
                with self.subTest(filename=filename):
                    with self.assertRaises(ValueError):
                        reject_production_path(candidate, path_label="db path")

            # A path with no production marker is unaffected by that guard.
            reject_production_path(Path(temp_dir) / "personal_os.db", path_label="db path")


if __name__ == "__main__":
    unittest.main()
