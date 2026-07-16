import os
import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.permissions import PermissionMode
from personalos.runtime_bootstrap import (
    RUNTIME_BOOTSTRAP_READ_PERMISSION,
    RUNTIME_BOOTSTRAP_RUN_PERMISSION,
    RUNTIME_BOOTSTRAP_WRITE_PERMISSION,
    bootstrap_runtime_database,
    create_runtime_status_report,
    evaluate_runtime_bootstrap_permission,
    plan_runtime_bootstrap,
    preview_runtime_bootstrap,
    require_runtime_bootstrap_permission,
    seed_runtime_profile,
    validate_runtime_bootstrap_profile,
)
from personalos.state import get_permission_setting, upsert_permission_setting


REPO_ROOT = Path(__file__).resolve().parents[1]


class RuntimeBootstrapProfileValidationTest(unittest.TestCase):
    def test_runtime_profile_validation_accepts_explicit_temp_dev_runtime_db_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            profile = validate_runtime_bootstrap_profile(_profile(Path(temp_dir)))

        self.assertEqual(profile.runtime_mode, "local_runtime_preview")
        self.assertTrue(profile.db_path.is_absolute())
        self.assertTrue(profile.no_external_writes)
        self.assertTrue(profile.no_send_mode)

    def test_runtime_profile_validation_rejects_protected_personalos_path(self) -> None:
        profile = _profile(
            Path(tempfile.gettempdir()),
            db_path=Path("/Users/coldstake/PersonalOS/runtime.sqlite3"),
        )

        with self.assertRaises(ValueError):
            validate_runtime_bootstrap_profile(profile)

    def test_runtime_profile_validation_rejects_protected_openclaw_path(self) -> None:
        profile = _profile(
            Path(tempfile.gettempdir()),
            db_path=Path("/Users/coldstake/.openclaw/runtime.sqlite3"),
        )

        with self.assertRaises(ValueError):
            validate_runtime_bootstrap_profile(profile)

    def test_runtime_profile_validation_rejects_missing_no_external_writes_true(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            profile = _profile(Path(temp_dir))
            profile["no_external_writes"] = False

            with self.assertRaises(ValueError):
                validate_runtime_bootstrap_profile(profile)

    def test_runtime_profile_validation_rejects_missing_no_send_mode_true(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            profile = _profile(Path(temp_dir))
            profile["no_send_mode"] = False

            with self.assertRaises(ValueError):
                validate_runtime_bootstrap_profile(profile)


class RuntimeBootstrapPreviewTest(unittest.TestCase):
    def test_bootstrap_preview_does_not_create_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            profile = _profile(Path(temp_dir))
            db_path = Path(profile["db_path"])

            plan = plan_runtime_bootstrap(profile)

            self.assertEqual(plan["status"], "planned")
            self.assertFalse(plan["database_write"])
            self.assertFalse(db_path.exists())
            self.assertFalse(db_path.parent.exists())

    def test_bootstrap_preview_reports_migrations_and_safety_flags(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plan = plan_runtime_bootstrap(_profile(Path(temp_dir)))

        self.assertIn(
            "0008",
            [migration["version"] for migration in plan["migrations_that_would_apply"]],
        )
        self.assertEqual(plan["seed_profile_name"], "mvp_preview_safe_seed")
        self.assertEqual(
            plan["safety_flags"],
            {
                "no_external_writes": True,
                "no_send_mode": True,
                "no_live_systems_touched": True,
            },
        )


class RuntimeBootstrapExecutionTest(unittest.TestCase):
    def test_bootstrap_creates_temp_db_and_applies_migrations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            profile = _profile(temp_path)
            with _authorized_connection(temp_path) as permission_connection:
                result = bootstrap_runtime_database(
                    profile,
                    permission_connection=permission_connection,
                )

            db_path = Path(profile["db_path"])
            self.assertEqual(result["status"], "completed")
            self.assertTrue(db_path.exists())
            self.assertEqual(
                [migration["version"] for migration in result["migrations_applied"]],
                [
                    "0001",
                    "0002",
                    "0003",
                    "0004",
                    "0005",
                    "0006",
                    "0007",
                    "0008",
                    "0009",
                    "00010",
                    "00011",
                    "00012",
                    "00013",
                    "00014",
                    "00015",
                    "00016",
                    "00017",
                    "00018",
                    "00019",
                    "00020",
                    "00021",
                    "00022",
                ],
            )

            with _sqlite_connection(db_path) as connection:
                rows = connection.execute("SELECT version FROM schema_migrations").fetchall()
                table = connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table' AND name = ?
                    """,
                    ("runtime_bootstrap_runs",),
                ).fetchone()

                self.assertEqual(len(rows), 22)
            self.assertIsNotNone(table)

    def test_bootstrap_enables_sqlite_foreign_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            with _authorized_connection(temp_path) as permission_connection:
                result = bootstrap_runtime_database(
                    _profile(temp_path),
                    permission_connection=permission_connection,
                )

        self.assertTrue(result["foreign_keys_enabled"])

    def test_bootstrap_creates_backup_before_migrating_existing_db(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            backup_dir = temp_path / "backups"
            profile = _profile(temp_path, backup_dir=backup_dir)
            db_path = Path(profile["db_path"])
            db_path.parent.mkdir(parents=True)
            with _sqlite_connection(db_path) as connection:
                connection.execute("CREATE TABLE marker (id TEXT PRIMARY KEY)")
                connection.execute("INSERT INTO marker (id) VALUES ('before')")
                connection.commit()

            with _authorized_connection(temp_path) as permission_connection:
                result = bootstrap_runtime_database(
                    profile,
                    permission_connection=permission_connection,
                )

            backup_path = Path(result["backup_path"])
            self.assertEqual(result["status"], "completed")
            self.assertTrue(result["backup_created"])
            self.assertTrue(backup_path.exists())
            self.assertEqual(backup_path.parent.resolve(), backup_dir.resolve())
            with _sqlite_connection(backup_path) as connection:
                marker = connection.execute("SELECT id FROM marker").fetchone()["id"]
            self.assertEqual(marker, "before")

    def test_repeated_bootstrap_backups_are_distinct_and_do_not_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            backup_dir = temp_path / "backups"
            profile = _profile(temp_path, backup_dir=backup_dir)
            db_path = Path(profile["db_path"])
            db_path.parent.mkdir(parents=True)
            with _sqlite_connection(db_path) as connection:
                connection.execute("CREATE TABLE marker (id TEXT PRIMARY KEY)")
                connection.execute("INSERT INTO marker (id) VALUES ('first')")
                connection.commit()

            with _authorized_connection(temp_path) as permission_connection:
                first_result = bootstrap_runtime_database(
                    profile,
                    permission_connection=permission_connection,
                )

                with _sqlite_connection(db_path) as connection:
                    connection.execute("UPDATE marker SET id = 'second'")
                    connection.commit()

                second_result = bootstrap_runtime_database(
                    profile,
                    permission_connection=permission_connection,
                )

            first_backup_path = Path(first_result["backup_path"])
            second_backup_path = Path(second_result["backup_path"])

            self.assertEqual(first_result["status"], "completed")
            self.assertEqual(second_result["status"], "completed")
            self.assertTrue(first_result["backup_created"])
            self.assertTrue(second_result["backup_created"])
            self.assertNotEqual(first_backup_path, second_backup_path)
            self.assertTrue(first_backup_path.exists())
            self.assertTrue(second_backup_path.exists())

            with _sqlite_connection(first_backup_path) as connection:
                first_marker = connection.execute("SELECT id FROM marker").fetchone()["id"]
            with _sqlite_connection(second_backup_path) as connection:
                second_marker = connection.execute("SELECT id FROM marker").fetchone()["id"]

            self.assertEqual(first_marker, "first")
            self.assertEqual(second_marker, "second")

    def test_bootstrap_does_not_create_backup_for_brand_new_db(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            backup_dir = temp_path / "backups"
            with _authorized_connection(temp_path) as permission_connection:
                result = bootstrap_runtime_database(
                    _profile(temp_path, backup_dir=backup_dir),
                    permission_connection=permission_connection,
                )

            self.assertEqual(result["status"], "completed")
            self.assertFalse(result["backup_created"])
            self.assertFalse(backup_dir.exists())

    def test_seed_profile_creates_safe_local_only_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            profile = _profile(temp_path)
            with _authorized_connection(temp_path) as permission_connection:
                result = bootstrap_runtime_database(
                    profile,
                    permission_connection=permission_connection,
                )
            db_path = Path(profile["db_path"])

            with _sqlite_connection(db_path) as connection:
                routine_rows = connection.execute(
                    "SELECT status, enabled FROM routines ORDER BY routine_id"
                ).fetchall()
                priority = connection.execute(
                    """
                    SELECT status, metadata_json
                    FROM priorities
                    WHERE priority_id = ?
                    """,
                    ("seed-priority-local-preview",),
                ).fetchone()
                briefing_rows = connection.execute(
                    """
                    SELECT name, delivery_mode, status
                    FROM briefing_windows
                    ORDER BY scheduled_time
                    """
                ).fetchall()
                blocked_calendar = get_permission_setting(connection, "self_calendar_blocks")

        self.assertEqual(result["seed_profile_name"], "mvp_preview_safe_seed")
        self.assertEqual([row["status"] for row in routine_rows], ["paused", "paused"])
        self.assertEqual([row["enabled"] for row in routine_rows], [0, 0])
        self.assertEqual(priority["status"], "paused")
        self.assertIn('"fake":true', priority["metadata_json"])
        self.assertEqual(
            [row["name"] for row in briefing_rows],
            ["morning", "midday", "afternoon", "evening"],
        )
        self.assertTrue(all(row["delivery_mode"] == "no_send" for row in briefing_rows))
        self.assertTrue(all(row["status"] == "draft" for row in briefing_rows))
        self.assertEqual(blocked_calendar["mode"], PermissionMode.DISABLED.value)

    def test_seed_profile_does_not_create_live_todoist_calendar_gmail_or_model_permissions(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            profile = _profile(temp_path)
            with _authorized_connection(temp_path) as permission_connection:
                bootstrap_runtime_database(
                    profile,
                    permission_connection=permission_connection,
                )
            db_path = Path(profile["db_path"])

            with _sqlite_connection(db_path) as connection:
                rows = connection.execute(
                    "SELECT category, mode FROM permission_settings ORDER BY category"
                ).fetchall()

        categories = {row["category"]: row["mode"] for row in rows}
        forbidden_markers = ("live", "gmail", "model_api", "openai", "openrouter")
        self.assertFalse(
            [
                category
                for category in categories
                if any(marker in category for marker in forbidden_markers)
            ]
        )
        self.assertEqual(categories["todoist_module_dev_test_write"], "disabled")
        self.assertEqual(categories["calendar_module_dev_test_write"], "disabled")
        self.assertEqual(categories["composer_module_dev_test_run"], "disabled")
        self.assertEqual(categories["synthesis_import_dev_test_read"], "disabled")
        self.assertEqual(categories["synthesis_import_dev_test_write"], "disabled")
        self.assertEqual(categories["synthesis_import_dev_test_preview"], "disabled")
        self.assertEqual(categories["side_effect_ledger_dev_test_read"], "disabled")
        self.assertEqual(categories["side_effect_ledger_dev_test_write"], "disabled")
        self.assertEqual(categories["side_effect_ledger_dev_test_record_attempt"], "disabled")
        self.assertEqual(categories["scheduler_dev_test_read"], "disabled")
        self.assertEqual(categories["scheduler_dev_test_write"], "disabled")
        self.assertEqual(categories["scheduler_dev_test_run"], "disabled")

    def test_seed_profile_does_not_silently_enable_dangerous_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            profile = _profile(temp_path)
            with _authorized_connection(temp_path) as permission_connection:
                bootstrap_runtime_database(
                    profile,
                    permission_connection=permission_connection,
                )
            db_path = Path(profile["db_path"])

            with _sqlite_connection(db_path) as connection:
                rows = connection.execute(
                    "SELECT category, mode FROM permission_settings ORDER BY category"
                ).fetchall()

        categories = {row["category"]: row["mode"] for row in rows}
        auto_enabled = {
            category
            for category, mode in categories.items()
            if mode == PermissionMode.AUTO_WRITE.value
        }
        dangerous_markers = ("_write", "_run", "_apply", "_attempt", "_simulated")
        self.assertEqual(auto_enabled, {RUNTIME_BOOTSTRAP_READ_PERMISSION})
        self.assertFalse(
            [
                category
                for category in auto_enabled
                if any(marker in category for marker in dangerous_markers)
            ]
        )

    def test_runtime_status_report_includes_table_counts_and_safety_flags(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            profile = _profile(temp_path)
            with _authorized_connection(temp_path) as permission_connection:
                result = bootstrap_runtime_database(
                    profile,
                    permission_connection=permission_connection,
                )
            db_path = Path(profile["db_path"])
            with _sqlite_connection(db_path) as connection:
                report = create_runtime_status_report(
                    connection,
                    profile=profile,
                    bootstrap_output=result,
                )

        self.assertEqual(report["db_path_label"], "temp-runtime-preview")
        self.assertEqual(report["table_counts"]["briefing_windows"], 4)
        self.assertEqual(report["table_counts"]["runtime_bootstrap_runs"], 1)
        self.assertGreaterEqual(report["table_counts"]["permission_settings"], 1)
        self.assertTrue(report["no_external_writes"])
        self.assertTrue(report["no_send_mode"])
        self.assertTrue(report["no_live_systems_touched"])


class RuntimeBootstrapPermissionTest(unittest.TestCase):
    def test_runtime_permissions_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            profile = _profile(temp_path)
            with _migrated_connection(temp_path / "auth-runtime") as connection:
                permission = evaluate_runtime_bootstrap_permission(
                    connection,
                    category=RUNTIME_BOOTSTRAP_WRITE_PERMISSION,
                )
                preview = preview_runtime_bootstrap(profile)
                bootstrap = bootstrap_runtime_database(
                    profile,
                    permission_connection=connection,
                )

        self.assertFalse(permission["allowed"])
        self.assertEqual(preview["status"], "blocked")
        self.assertEqual(bootstrap["status"], "blocked")
        self.assertFalse(Path(profile["db_path"]).exists())

    def test_permission_gated_preview_write_and_run_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            profile = _profile(temp_path)
            with _migrated_connection(temp_path / "auth-runtime") as connection:
                _set_permission(connection, RUNTIME_BOOTSTRAP_READ_PERMISSION)
                preview = preview_runtime_bootstrap(profile, permission_connection=connection)
                write_blocked = bootstrap_runtime_database(
                    profile,
                    permission_connection=connection,
                )

                _set_permission(connection, RUNTIME_BOOTSTRAP_WRITE_PERMISSION)
                run_blocked = bootstrap_runtime_database(
                    profile,
                    permission_connection=connection,
                )

                _set_permission(connection, RUNTIME_BOOTSTRAP_RUN_PERMISSION)
                require_result = require_runtime_bootstrap_permission(
                    connection,
                    category=RUNTIME_BOOTSTRAP_RUN_PERMISSION,
                )
                completed = bootstrap_runtime_database(
                    profile,
                    permission_connection=connection,
                )

        self.assertEqual(preview["status"], "planned")
        self.assertEqual(write_blocked["status"], "blocked")
        self.assertIn(RUNTIME_BOOTSTRAP_WRITE_PERMISSION, write_blocked["reason"])
        self.assertEqual(run_blocked["status"], "blocked")
        self.assertIn(RUNTIME_BOOTSTRAP_RUN_PERMISSION, run_blocked["reason"])
        self.assertTrue(require_result["allowed"])
        self.assertEqual(completed["status"], "completed")

    def test_seed_profile_requires_write_and_run_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            profile = _profile(temp_path)
            with _migrated_connection(temp_path / "target-runtime") as target_connection:
                result = seed_runtime_profile(target_connection, profile)
                count = target_connection.execute(
                    "SELECT COUNT(*) FROM permission_settings"
                ).fetchone()[0]

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(count, 0)


class RuntimeBootstrapSafetyTest(unittest.TestCase):

    def test_source_code_does_not_reference_protected_absolute_paths(self) -> None:
        protected_fragments = (
            "/Users/coldstake/PersonalOS",
            "/Users/coldstake/.openclaw",
        )
        # P-SCHED-02 (D-PO-011, HI-09) sanctions exactly one occurrence of exactly one
        # fragment: config.py's PRODUCTION_DB_PATH constant, the one approved production
        # database location. Nothing else in src/ may reference either protected path;
        # test_config_py_is_the_only_sanctioned_protected_path_reference below double-
        # checks that this one exception is narrow (single occurrence, exact constant,
        # no OpenClaw reference at all).
        sanctioned_exceptions = {
            Path("src/personalos/config.py"): {"/Users/coldstake/PersonalOS"},
        }
        matches = []
        for directory, directories, filenames in os.walk(REPO_ROOT / "src"):
            directories[:] = [item for item in directories if item != "__pycache__"]
            for filename in filenames:
                path = Path(directory) / filename
                if path.suffix != ".py":
                    continue
                text = path.read_text(encoding="utf-8")
                relative_path = path.relative_to(REPO_ROOT)
                allowed_fragments = sanctioned_exceptions.get(relative_path, set())
                for fragment in protected_fragments:
                    if fragment in text and fragment not in allowed_fragments:
                        matches.append(str(relative_path))

        self.assertEqual(matches, [])

    def test_config_py_is_the_only_sanctioned_protected_path_reference(self) -> None:
        text = (REPO_ROOT / "src" / "personalos" / "config.py").read_text(encoding="utf-8")
        self.assertNotIn("/Users/coldstake/.openclaw", text)
        self.assertEqual(text.count("/Users/coldstake/PersonalOS"), 1)
        self.assertIn(
            'PRODUCTION_DB_PATH = Path("/Users/coldstake/PersonalOS/personal_os.db")',
            text,
        )

    def test_repo_artifact_safety_has_no_var_or_database_artifacts_outside_git(self) -> None:
        db_artifacts: list[Path] = []
        var_dirs: list[Path] = []
        for directory, directories, filenames in os.walk(REPO_ROOT):
            current = Path(directory)
            if ".git" in current.parts:
                directories[:] = []
                continue
            directories[:] = [item for item in directories if item != ".git"]
            for dirname in directories:
                if dirname == "var":
                    var_dirs.append(current / dirname)
            for filename in filenames:
                path = current / filename
                is_named_db_artifact = filename in {".sqlite", ".sqlite3"}
                is_db_suffix = path.suffix in {".sqlite", ".sqlite3", ".db"}
                if is_named_db_artifact or is_db_suffix:
                    db_artifacts.append(path)

        self.assertEqual(db_artifacts, [])
        self.assertEqual(var_dirs, [])


def _profile(
    temp_path: Path,
    *,
    db_path: Path | None = None,
    backup_dir: Path | None = None,
) -> dict[str, object]:
    return {
        "profile_name": "phase-9b-preview",
        "runtime_mode": "local_runtime_preview",
        "db_path_label": "temp-runtime-preview",
        "db_path": str(db_path or temp_path / "runtime" / "preview" / "personalos.sqlite3"),
        "backup_enabled": True,
        "backup_dir": str(backup_dir) if backup_dir is not None else None,
        "no_external_writes": True,
        "no_send_mode": True,
        "seed_profile_name": "mvp_preview_safe_seed",
        "created_by": "tests",
    }


@contextmanager
def _authorized_connection(temp_path: Path) -> Iterator[sqlite3.Connection]:
    with _migrated_connection(temp_path / "auth-runtime") as connection:
        _set_permission(connection, RUNTIME_BOOTSTRAP_READ_PERMISSION)
        _set_permission(connection, RUNTIME_BOOTSTRAP_WRITE_PERMISSION)
        _set_permission(connection, RUNTIME_BOOTSTRAP_RUN_PERMISSION)
        yield connection


@contextmanager
def _migrated_connection(runtime_dir: Path) -> Iterator[sqlite3.Connection]:
    config = PersonalOSConfig(
        environment=Environment.TEST,
        timezone=DEFAULT_TIMEZONE,
        database_path=runtime_dir / "test" / "personalos.sqlite3",
    )
    connection = connect_sqlite(config, runtime_dir=runtime_dir)
    apply_migrations(connection)
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def _sqlite_connection(db_path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def _set_permission(connection: sqlite3.Connection, category: str) -> None:
    upsert_permission_setting(
        connection,
        category=category,
        mode=PermissionMode.AUTO_WRITE.value,
        metadata={"source": "tests"},
        updated_by="tests",
        updated_at_utc="2026-06-15T10:00:00+00:00",
    )
