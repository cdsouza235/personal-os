"""SQLite connection helpers and shared workflow-context report enrichment."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from urllib.parse import quote

from personalos.cli.reporting import _database_target_report, _output_target_report
from personalos.path_safety import validate_existing_sqlite_path
from personalos.status import create_rail_state_report


def _with_workflow_context(
    report: dict[str, Any],
    *,
    workflow_name: str,
    workflow_mode: str,
    database_path: str | Path | None = None,
    database_access: str,
    local_sqlite_read: bool,
    local_sqlite_changed: bool | None,
    output_kind: str,
    output_file: str | Path | None = None,
    safe_next_actions: Sequence[str] = (),
) -> dict[str, Any]:
    database_target = _database_target_report(
        database_path,
        database_access=database_access,
    )
    enriched = {
        **report,
        "workflow_name": workflow_name,
        "workflow_mode": workflow_mode,
        "database_target": database_target,
        "local_sqlite_read": local_sqlite_read,
        "local_sqlite_changed": local_sqlite_changed,
        "external_writes": report.get("external_writes", "none"),
        "credentials": report.get("credentials", "not_loaded"),
        "production_db_active": report.get("production_db_active", False),
        "output_target": _output_target_report(output_kind, output_file=output_file),
        "safe_next_actions": list(safe_next_actions),
    }
    enriched.setdefault("rail_states", create_rail_state_report())
    return enriched


def _connect_read_only(db_path: str) -> sqlite3.Connection:
    validated_path = validate_existing_sqlite_path(db_path, path_label="operator db_path")
    db_uri = f"file:{quote(str(validated_path), safe='/')}?mode=ro"
    connection = sqlite3.connect(db_uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _connect_read_write(
    db_path: str,
    *,
    allow_production_path: bool = False,
) -> sqlite3.Connection:
    validated_path = validate_existing_sqlite_path(
        db_path,
        path_label="operator db_path",
        allow_production_path=allow_production_path,
    )
    connection = sqlite3.connect(validated_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
