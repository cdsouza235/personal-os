"""Minimal SQLite migration application for development and test databases."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"
MIGRATION_METADATA_TABLE = "schema_migrations"


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    path: Path
    sql: str
    checksum: str


class MigrationChecksumMismatch(RuntimeError):
    """Raised when an applied migration file no longer matches recorded metadata."""

    def __init__(self, version: str, recorded_checksum: str, current_checksum: str) -> None:
        super().__init__(
            "Migration checksum mismatch for "
            f"{version}: recorded {recorded_checksum}, current {current_checksum}"
        )
        self.version = version
        self.recorded_checksum = recorded_checksum
        self.current_checksum = current_checksum


def discover_migrations(migrations_dir: Path = DEFAULT_MIGRATIONS_DIR) -> list[Migration]:
    migrations: list[Migration] = []

    for path in sorted(migrations_dir.glob("*.sql")):
        version, name = _parse_migration_filename(path)
        sql = path.read_text(encoding="utf-8")
        checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        migrations.append(
            Migration(
                version=version,
                name=name,
                path=path,
                sql=sql,
                checksum=checksum,
            )
        )

    return migrations


def apply_migrations(
    connection: sqlite3.Connection,
    migrations_dir: Path = DEFAULT_MIGRATIONS_DIR,
) -> list[Migration]:
    _ensure_metadata_table(connection)
    applied_checksums = _applied_checksums(connection)
    applied_now: list[Migration] = []

    for migration in discover_migrations(migrations_dir):
        recorded_checksum = applied_checksums.get(migration.version)
        if recorded_checksum:
            if recorded_checksum != migration.checksum:
                raise MigrationChecksumMismatch(
                    migration.version,
                    recorded_checksum,
                    migration.checksum,
                )
            continue

        with connection:
            connection.executescript(migration.sql)
            connection.execute(
                """
                INSERT INTO schema_migrations (version, name, checksum, applied_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    migration.version,
                    migration.name,
                    migration.checksum,
                    datetime.now(UTC).isoformat(),
                ),
            )
        applied_now.append(migration)
        applied_checksums[migration.version] = migration.checksum

    return applied_now


def _ensure_metadata_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )
    connection.commit()


def _applied_checksums(connection: sqlite3.Connection) -> dict[str, str]:
    rows = connection.execute("SELECT version, checksum FROM schema_migrations").fetchall()
    return {row["version"]: row["checksum"] for row in rows}


def _parse_migration_filename(path: Path) -> tuple[str, str]:
    version, separator, name = path.stem.partition("_")
    if not version or not separator or not name:
        raise ValueError(f"Migration filename must be '<version>_<name>.sql': {path.name}")
    return version, name
