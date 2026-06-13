"""Safe SQLite connection helpers for development and test databases."""

import sqlite3
from pathlib import Path

from personalos.config import (
    Environment,
    PersonalOSConfig,
    ProductionConfigUnavailable,
    RUNTIME_DIR,
)


def connect_sqlite(
    config: PersonalOSConfig,
    *,
    runtime_dir: Path = RUNTIME_DIR,
) -> sqlite3.Connection:
    """Open a SQLite connection for a development or test database."""
    if config.environment is Environment.PRODUCTION:
        raise ProductionConfigUnavailable(
            "Production database access is not available in the Phase 1 dev/test boundary."
        )

    database_path = config.database_path
    _ensure_runtime_path(database_path, runtime_dir)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def _ensure_runtime_path(database_path: Path, runtime_dir: Path) -> None:
    database_path.resolve().relative_to(runtime_dir.resolve())
