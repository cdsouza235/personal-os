"""P-KE-1A: schema + migration behavior for the Knowledge Edge state layer.

Covers migrations 00017-00021 (purely additive CREATE TABLE), applied through the
existing, unmodified ``personalos.db.migrations`` runner (AD-5): table/column
presence, idempotency, checksum-drift detection, and the zero-network-import
posture of the new package.
"""

from __future__ import annotations

import ast
import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import (
    MIGRATION_METADATA_TABLE,
    MigrationChecksumMismatch,
    apply_migrations,
    discover_migrations,
)

NEW_MIGRATION_VERSIONS = (
    "00017", "00018", "00019", "00020", "00021", "00022", "00023", "00024", "00025",
)

EXPECTED_KE_TABLES = {
    "ke_sources",
    "ke_source_endpoints",
    "ke_people",
    "ke_person_aliases",
    "ke_roles",
    "ke_role_occupancies",
    "ke_affiliations",
    "ke_companies",
    "ke_company_identifiers",
    "ke_topics",
    "ke_canonical_groups",
    "ke_media_items",
    "ke_discovery_occurrences",
    "ke_entity_matches",
    "ke_scheduled_events",
    "ke_user_decisions",
    "ke_decision_history",
    "ke_queue_snapshots",
    "ke_queue_snapshot_demoted",
    "ke_scan_runs",
    "ke_scan_cursors",
    "ke_source_health",
    "ke_coverage_reports",
    "ke_roster_change_proposals",
    "ke_synthesis_handoffs",
    "ke_person_search_cache",
}

FORBIDDEN_IMPORT_ROOTS = {
    "urllib",
    "http",
    "http.client",
    "socket",
    "requests",
    "httpx",
    "aiohttp",
    "ftplib",
    "smtplib",
    "telnetlib",
}

# urllib.parse is pure string/URL manipulation -- no socket access -- and is the
# standard-library tool engine/canonicalize.py legitimately needs for §11.2 URL
# canonicalization. It is the one named exception to the otherwise-blanket
# "urllib" root ban; urllib.request (or bare "import urllib") stays forbidden.
# The exception is scoped to that one authorized file (C4, phase-end checkpoint
# 2026-07-16): the Conductor's authorization was "exactly one file", not the whole
# package, so `urllib.parse` planted anywhere else must still fire this guard.
_ALLOWED_NETWORK_IMPORT_EXCEPTIONS: dict[str, frozenset[str]] = {
    "urllib.parse": frozenset({"engine/canonicalize.py"}),
}


def _is_allowed_exception(dotted_name: str, *, relative_name: str) -> bool:
    for exception, allowed_paths in _ALLOWED_NETWORK_IMPORT_EXCEPTIONS.items():
        if dotted_name == exception or dotted_name.startswith(exception + "."):
            return relative_name in allowed_paths
    return False


def _find_network_import_offenders(package_dir: Path) -> list[str]:
    offenders: list[str] = []
    for path in sorted(package_dir.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relative_name = path.relative_to(package_dir).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_allowed_exception(alias.name, relative_name=relative_name):
                        continue
                    root = alias.name.split(".")[0]
                    if root in FORBIDDEN_IMPORT_ROOTS:
                        offenders.append(f"{relative_name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if _is_allowed_exception(module, relative_name=relative_name):
                    continue
                root = module.split(".")[0]
                if root in FORBIDDEN_IMPORT_ROOTS:
                    offenders.append(f"{relative_name}: from {module} import ...")
    return offenders


class KnowledgeEdgeMigrationSchemaTest(unittest.TestCase):
    def test_migrations_00017_through_00021_create_expected_tables(self) -> None:
        with _migrated_connection() as connection:
            table_names = _table_names(connection)

        self.assertTrue(EXPECTED_KE_TABLES <= table_names)

    def test_migration_discovery_includes_new_versions_in_order(self) -> None:
        migrations = discover_migrations()
        versions = [migration.version for migration in migrations]

        for version in NEW_MIGRATION_VERSIONS:
            self.assertIn(version, versions)

        new_indexes = [versions.index(version) for version in NEW_MIGRATION_VERSIONS]
        self.assertEqual(new_indexes, sorted(new_indexes))
        self.assertEqual(versions[-len(NEW_MIGRATION_VERSIONS):], list(NEW_MIGRATION_VERSIONS))

    def test_migrations_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
                first_applied = apply_migrations(connection)
                second_applied = apply_migrations(connection)

                placeholders = ", ".join("?" for _ in NEW_MIGRATION_VERSIONS)
                rows = connection.execute(
                    f"SELECT version, checksum FROM {MIGRATION_METADATA_TABLE} "
                    f"WHERE version IN ({placeholders})",
                    NEW_MIGRATION_VERSIONS,
                ).fetchall()

        applied_new = [m.version for m in first_applied if m.version in NEW_MIGRATION_VERSIONS]
        self.assertEqual(applied_new, list(NEW_MIGRATION_VERSIONS))
        self.assertEqual(second_applied, [])
        self.assertEqual(len(rows), len(NEW_MIGRATION_VERSIONS))
        for row in rows:
            self.assertTrue(row["checksum"])

    def test_migration_checksum_drift_is_blocked_for_ke_migration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runtime_dir = temp_path / "runtime"
            migrations_dir = temp_path / "migrations"
            migrations_dir.mkdir()
            migration_path = migrations_dir / "00017_knowledge_edge_registries.sql"
            migration_path.write_text(
                "CREATE TABLE IF NOT EXISTS ke_sources (source_id TEXT PRIMARY KEY);\n",
                encoding="utf-8",
            )
            config = _config_for(runtime_dir, Environment.TEST)

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection, migrations_dir=migrations_dir)
                recorded_checksum = connection.execute(
                    f"SELECT checksum FROM {MIGRATION_METADATA_TABLE} WHERE version = ?",
                    ("00017",),
                ).fetchone()["checksum"]

                migration_path.write_text(
                    "CREATE TABLE IF NOT EXISTS ke_sources "
                    "(source_id TEXT PRIMARY KEY, extra TEXT);\n",
                    encoding="utf-8",
                )

                with self.assertRaises(MigrationChecksumMismatch) as context:
                    apply_migrations(connection, migrations_dir=migrations_dir)

            self.assertEqual(context.exception.version, "00017")
            self.assertEqual(context.exception.recorded_checksum, recorded_checksum)
            self.assertNotEqual(context.exception.current_checksum, recorded_checksum)

    def test_foreign_keys_reject_orphan_role_occupancy(self) -> None:
        with _migrated_connection() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO ke_role_occupancies (
                        occupancy_id, role_id, person_id, effective_start_date,
                        effective_end_date, date_precision, occupancy_source, notes,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "occ-orphan", "missing-role", "missing-person", None, None,
                        "exact", "test", "", "2026-07-16T00:00:00+00:00",
                        "2026-07-16T00:00:00+00:00",
                    ),
                )

    def test_foreign_keys_reject_orphan_scheduled_event_company(self) -> None:
        with _migrated_connection() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO ke_scheduled_events (
                        event_id, company_id, event_type, scheduled_date, time_precision,
                        source_timezone, schedule_confidence, schedule_source,
                        filing_urls_json, event_status, decision_state,
                        queue_visibility_state, pinned, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "event-orphan", "missing-company", "quarterly_earnings",
                        "2026-08-01", "date_only", "UTC", "unknown", "", "[]",
                        "discovered", "undecided", "candidate", 0,
                        "2026-07-16T00:00:00+00:00", "2026-07-16T00:00:00+00:00",
                    ),
                )


class KnowledgeEdgeNoNetworkImportsTest(unittest.TestCase):
    def test_state_package_has_no_network_capable_imports(self) -> None:
        import personalos.knowledge_edge.state as ke_state

        package_dir = Path(ke_state.__file__).parent
        self.assertEqual(_find_network_import_offenders(package_dir), [])

    def test_knowledge_edge_package_root_has_no_network_capable_imports(self) -> None:
        """Recursive: covers every subpackage (state/, engine/, adapters/) and
        scan_orchestrator.py -- not just the top-level package directory -- so
        Packet 1B's new engine/ and adapters/ modules are in scope too."""
        import personalos.knowledge_edge as ke_package

        package_dir = Path(ke_package.__file__).parent
        self.assertEqual(_find_network_import_offenders(package_dir), [])

    def test_urllib_parse_exception_is_scoped_to_canonicalize_py_only(self) -> None:
        """C4 (phase-end checkpoint 2026-07-16): the authorized carve-out is
        "exactly one file" (engine/canonicalize.py), not the whole package. This
        plants `urllib.parse` in a second, unauthorized file and confirms the
        guard still fires there while staying silent for the one authorized file
        -- reproducing the checkpoint report's gap probe against a synthetic
        package tree (never against the real repo, so nothing needs reverting)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)
            (package_dir / "engine").mkdir()
            (package_dir / "state").mkdir()

            (package_dir / "engine" / "canonicalize.py").write_text(
                "from urllib.parse import urlsplit\n", encoding="utf-8"
            )
            (package_dir / "state" / "evil.py").write_text(
                "import urllib.parse\n", encoding="utf-8"
            )

            offenders = _find_network_import_offenders(package_dir)

        self.assertEqual(offenders, ["state/evil.py: import urllib.parse"])

    def test_urllib_parse_alias_smuggle_still_fires_outside_canonicalize_py(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)
            (package_dir / "state").mkdir()
            (package_dir / "state" / "evil.py").write_text(
                "from urllib import parse as p\n", encoding="utf-8"
            )

            offenders = _find_network_import_offenders(package_dir)

        self.assertEqual(offenders, ["state/evil.py: from urllib import ..."])


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


def _table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {row["name"] for row in rows}


if __name__ == "__main__":
    unittest.main()
