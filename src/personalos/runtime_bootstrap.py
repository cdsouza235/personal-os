"""Local/dev-preview runtime SQLite bootstrap foundation."""

from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from personalos.config import DEFAULT_TIMEZONE, REPO_ROOT
from personalos.db.migrations import MIGRATION_METADATA_TABLE, apply_migrations, discover_migrations
from personalos.permissions import PermissionMode
from personalos.state import (
    create_priority,
    create_routine,
    get_permission_setting,
    get_priority,
    get_routine,
    upsert_permission_setting,
)

RUNTIME_BOOTSTRAP_READ_PERMISSION = "runtime_bootstrap_dev_test_read"
RUNTIME_BOOTSTRAP_WRITE_PERMISSION = "runtime_bootstrap_dev_test_write"
RUNTIME_BOOTSTRAP_RUN_PERMISSION = "runtime_bootstrap_dev_test_run"

ALLOWED_RUNTIME_MODES = ("dev_runtime", "local_runtime_preview")
ALLOWED_SEED_PROFILES = ("mvp_preview_safe_seed", "none")
SAFE_SEED_PROFILE_NAME = "mvp_preview_safe_seed"
BOOTSTRAP_RUN_STATUSES = ("planned", "completed", "failed")
BACKUP_PATH_ATTEMPTS = 100

_DATABASE_SUFFIXES = {".sqlite", ".sqlite3", ".db"}
_PRODUCTION_MARKERS = {"prod", "production", "live"}
_SENSITIVE_PATH_MARKERS = (
    "credential",
    "credentials",
    "client" + "_" + "sec" + "ret",
    "token" + ".json",
    "api" + "_" + "key",
    "o" + "auth",
    "pass" + "word",
    "sec" + "ret",
)
_LIVE_PERMISSION_MARKERS = (
    "live",
    "gmail",
    "model_api",
)


class RuntimeBootstrapPermissionDenied(PermissionError):
    """Raised when runtime bootstrap permission settings do not allow the action."""


@dataclass(frozen=True)
class RuntimeBootstrapProfile:
    profile_name: str
    runtime_mode: str
    db_path_label: str
    db_path: Path
    backup_enabled: bool
    backup_dir: Path | None
    no_external_writes: bool
    no_send_mode: bool
    seed_profile_name: str
    created_by: str


def validate_runtime_bootstrap_profile(
    profile: RuntimeBootstrapProfile | Mapping[str, Any],
) -> RuntimeBootstrapProfile:
    profile_map = _profile_to_mapping(profile)
    normalized = RuntimeBootstrapProfile(
        profile_name=_validate_required_text("profile_name", profile_map.get("profile_name")),
        runtime_mode=_validate_runtime_mode(profile_map.get("runtime_mode")),
        db_path_label=_validate_required_text("db_path_label", profile_map.get("db_path_label")),
        db_path=_validate_database_path(profile_map.get("db_path")),
        backup_enabled=_validate_true("backup_enabled", profile_map.get("backup_enabled")),
        backup_dir=_validate_backup_dir(profile_map.get("backup_dir")),
        no_external_writes=_validate_true(
            "no_external_writes",
            profile_map.get("no_external_writes"),
        ),
        no_send_mode=_validate_true("no_send_mode", profile_map.get("no_send_mode")),
        seed_profile_name=_validate_seed_profile(profile_map.get("seed_profile_name")),
        created_by=_validate_required_text("created_by", profile_map.get("created_by")),
    )
    _ensure_allowed_runtime_path(normalized.db_path)
    if normalized.backup_dir is not None:
        _ensure_allowed_runtime_path(normalized.backup_dir, require_database_suffix=False)
    return normalized


def plan_runtime_bootstrap(
    profile: RuntimeBootstrapProfile | Mapping[str, Any],
) -> dict[str, Any]:
    validated = validate_runtime_bootstrap_profile(profile)
    migrations_that_would_apply = _pending_migration_summaries(validated.db_path)
    return {
        "status": "planned",
        "dry_run": True,
        "database_write": False,
        "target_db_path": str(validated.db_path),
        "db_path_label": validated.db_path_label,
        "backup_path": str(_backup_path_for(validated)) if validated.db_path.exists() else None,
        "migrations_that_would_apply": migrations_that_would_apply,
        "seed_profile_name": validated.seed_profile_name,
        "safety_flags": _safety_flags(validated),
        "warnings": _path_warnings(validated),
    }


def preview_runtime_bootstrap(
    profile: RuntimeBootstrapProfile | Mapping[str, Any],
    *,
    permission_connection: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    if permission_connection is None:
        permission = _missing_permission_decision(RUNTIME_BOOTSTRAP_READ_PERMISSION)
        return _blocked_result("Missing runtime bootstrap permission connection.", True, permission)

    permission = evaluate_runtime_bootstrap_permission(
        permission_connection,
        category=RUNTIME_BOOTSTRAP_READ_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(permission["reason"], True, permission)

    plan = plan_runtime_bootstrap(profile)
    plan["permission"] = permission
    return plan


def bootstrap_runtime_database(
    profile: RuntimeBootstrapProfile | Mapping[str, Any],
    *,
    permission_connection: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    validated = validate_runtime_bootstrap_profile(profile)
    permissions = _evaluate_mutation_permissions(permission_connection)
    denied = next((permission for permission in permissions if not permission["allowed"]), None)
    if denied is not None:
        return _blocked_result(denied["reason"], False, denied)

    db_existed = validated.db_path.exists()
    backup_path: Path | None = None
    migrations_applied: list[dict[str, Any]] = []
    seeded_objects: dict[str, list[dict[str, Any]]] = {}
    run_id = str(uuid4())
    started_at = _utc_now()

    try:
        validated.db_path.parent.mkdir(parents=True, exist_ok=True)
        if db_existed:
            backup_path = _create_backup(validated)

        connection = _connect_sqlite(validated.db_path)
        try:
            applied = apply_migrations(connection)
            migrations_applied = [_migration_to_summary(migration) for migration in applied]
            seeded_objects = _seed_runtime_profile_unchecked(
                connection,
                validated,
                created_at=started_at,
            )
            foreign_keys_enabled = _foreign_keys_enabled(connection)
            output = {
                "status": "completed",
                "dry_run": False,
                "database_write": True,
                "target_db_path": str(validated.db_path),
                "db_path_label": validated.db_path_label,
                "backup_created": backup_path is not None,
                "backup_path": str(backup_path) if backup_path is not None else None,
                "migrations_applied": migrations_applied,
                "seed_profile_name": validated.seed_profile_name,
                "seeded_objects": seeded_objects,
                "foreign_keys_enabled": foreign_keys_enabled,
                "safety_flags": _safety_flags(validated),
                "warnings": _path_warnings(validated),
            }
            _record_bootstrap_run(
                connection,
                run_id=run_id,
                profile=validated,
                dry_run=False,
                status="completed",
                input_payload=_profile_to_jsonable(validated),
                output_payload=output,
                error_message=None,
                created_at=started_at,
                completed_at=_utc_now(),
            )
            status_report = create_runtime_status_report(
                connection,
                profile=validated,
                bootstrap_output=output,
            )
            output["runtime_status_report"] = status_report
            output["run_id"] = run_id
            return output
        finally:
            connection.close()
    except Exception as error:
        return {
            "status": "failed",
            "reason": str(error),
            "dry_run": False,
            "database_write": db_existed or validated.db_path.exists(),
            "target_db_path": str(validated.db_path),
            "db_path_label": validated.db_path_label,
            "backup_created": backup_path is not None,
            "backup_path": str(backup_path) if backup_path is not None else None,
            "migrations_applied": migrations_applied,
            "seeded_objects": seeded_objects,
            "permissions": permissions,
            **_safety_flags(validated),
        }


def seed_runtime_profile(
    connection: sqlite3.Connection,
    profile: RuntimeBootstrapProfile | Mapping[str, Any],
    *,
    permission_connection: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    validated = validate_runtime_bootstrap_profile(profile)
    permissions = _evaluate_mutation_permissions(permission_connection)
    denied = next((permission for permission in permissions if not permission["allowed"]), None)
    if denied is not None:
        return _blocked_result(denied["reason"], False, denied)

    seeded_objects = _seed_runtime_profile_unchecked(
        connection,
        validated,
        created_at=_utc_now(),
    )
    return {
        "status": "seeded",
        "dry_run": False,
        "database_write": True,
        "seed_profile_name": validated.seed_profile_name,
        "seeded_objects": seeded_objects,
        "permissions": permissions,
        **_safety_flags(validated),
    }


def create_runtime_status_report(
    connection: sqlite3.Connection,
    *,
    profile: RuntimeBootstrapProfile | Mapping[str, Any],
    bootstrap_output: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    validated = validate_runtime_bootstrap_profile(profile)
    return {
        "db_path_label": validated.db_path_label,
        "migrations_applied": _applied_migration_summaries(connection),
        "table_counts": _table_counts(connection),
        "permission_summary": _permission_summary(connection),
        "seeded_objects": dict(bootstrap_output.get("seeded_objects", {}))
        if bootstrap_output is not None
        else _seeded_object_summary(connection),
        "backup_created": bool(bootstrap_output.get("backup_created", False))
        if bootstrap_output is not None
        else False,
        "no_external_writes": True,
        "no_send_mode": True,
        "no_live_systems_touched": True,
        "warnings": _path_warnings(validated),
    }


def require_runtime_bootstrap_permission(
    connection: sqlite3.Connection,
    *,
    category: str,
) -> dict[str, Any]:
    decision = evaluate_runtime_bootstrap_permission(connection, category=category)
    if not decision["allowed"]:
        raise RuntimeBootstrapPermissionDenied(decision["reason"])
    return decision


def evaluate_runtime_bootstrap_permission(
    connection: sqlite3.Connection,
    *,
    category: str,
) -> dict[str, Any]:
    category = _validate_required_text("category", category)
    setting = get_permission_setting(connection, category)
    if setting is None:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=None,
            reason=f"Missing runtime bootstrap permission setting: {category}",
            setting=None,
        )

    try:
        mode = PermissionMode(setting["mode"])
    except ValueError:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=setting["mode"],
            reason=f"Invalid runtime bootstrap permission mode: {setting['mode']}",
            setting=setting,
        )

    if mode is PermissionMode.DISABLED:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=mode.value,
            reason=f"Runtime bootstrap permission is disabled: {category}",
            setting=setting,
        )
    if mode is not PermissionMode.AUTO_WRITE:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=mode.value,
            reason=f"Runtime bootstrap permission is not enabled for dev/test use: {category}",
            setting=setting,
        )

    return _permission_decision(
        allowed=True,
        category=category,
        mode=mode.value,
        reason="Runtime bootstrap permission is explicitly enabled for dev/test use.",
        setting=setting,
    )


def _seed_runtime_profile_unchecked(
    connection: sqlite3.Connection,
    profile: RuntimeBootstrapProfile,
    *,
    created_at: str,
) -> dict[str, list[dict[str, Any]]]:
    if profile.seed_profile_name == "none":
        return {
            "permission_settings": [],
            "routines": [],
            "priorities": [],
            "briefing_windows": [],
        }
    if profile.seed_profile_name != SAFE_SEED_PROFILE_NAME:
        raise ValueError(f"Unsupported seed profile: {profile.seed_profile_name}")

    return {
        "permission_settings": _seed_permission_settings(connection, created_at=created_at),
        "routines": _seed_routines(connection, created_at=created_at),
        "priorities": _seed_priorities(connection, created_at=created_at),
        "briefing_windows": _seed_briefing_windows(connection, created_at=created_at),
    }


def _seed_permission_settings(
    connection: sqlite3.Connection,
    *,
    created_at: str,
) -> list[dict[str, Any]]:
    categories = {
        RUNTIME_BOOTSTRAP_READ_PERMISSION: PermissionMode.AUTO_WRITE.value,
        RUNTIME_BOOTSTRAP_WRITE_PERMISSION: PermissionMode.AUTO_WRITE.value,
        RUNTIME_BOOTSTRAP_RUN_PERMISSION: PermissionMode.AUTO_WRITE.value,
        "routine_todoist_tasks": PermissionMode.DISABLED.value,
        "self_calendar_blocks": PermissionMode.DISABLED.value,
        "high_value_review_tasks": PermissionMode.DISABLED.value,
        "high_value_execution_actions": PermissionMode.DISABLED.value,
        "messages_to_other_people": PermissionMode.DISABLED.value,
        "external_calendar_events": PermissionMode.DISABLED.value,
        "todoist_module_dev_test_read": PermissionMode.DISABLED.value,
        "todoist_module_dev_test_write": PermissionMode.DISABLED.value,
        "todoist_module_dev_test_simulated_write": PermissionMode.DISABLED.value,
        "calendar_module_dev_test_read": PermissionMode.DISABLED.value,
        "calendar_module_dev_test_write": PermissionMode.DISABLED.value,
        "calendar_module_dev_test_simulated_write": PermissionMode.DISABLED.value,
        "composer_module_dev_test_read": PermissionMode.DISABLED.value,
        "composer_module_dev_test_write": PermissionMode.DISABLED.value,
        "composer_module_dev_test_run": PermissionMode.DISABLED.value,
        "synthesis_import_dev_test_read": PermissionMode.DISABLED.value,
        "synthesis_import_dev_test_write": PermissionMode.DISABLED.value,
        "synthesis_import_dev_test_preview": PermissionMode.DISABLED.value,
        "report_jobs_dev_test_read": PermissionMode.DISABLED.value,
        "report_jobs_dev_test_write": PermissionMode.DISABLED.value,
        "report_jobs_dev_test_run": PermissionMode.DISABLED.value,
        "chart_pack_reviews_dev_test_read": PermissionMode.DISABLED.value,
        "chart_pack_reviews_dev_test_write": PermissionMode.DISABLED.value,
        "fitness_integration_dev_test_read": PermissionMode.DISABLED.value,
        "fitness_integration_dev_test_write": PermissionMode.DISABLED.value,
        "fitness_integration_dev_test_validate": PermissionMode.DISABLED.value,
    }
    seeded = []
    for category, mode in sorted(categories.items()):
        seeded.append(
            upsert_permission_setting(
                connection,
                category=category,
                mode=mode,
                metadata={
                    "seed_profile": SAFE_SEED_PROFILE_NAME,
                    "no_external_writes": True,
                    "no_send_mode": True,
                    "live_permission": False,
                },
                updated_by="personalos.runtime_bootstrap",
                updated_at_utc=created_at,
            )
        )
    return seeded


def _seed_routines(
    connection: sqlite3.Connection,
    *,
    created_at: str,
) -> list[dict[str, Any]]:
    routine_inputs = (
        {
            "routine_id": "seed-routine-morning-review",
            "name": "MVP preview morning review",
            "status": "paused",
            "enabled": False,
            "settings": {"cadence": "manual_only", "seed_profile": SAFE_SEED_PROFILE_NAME},
            "notes": "Local preview seed only; no scheduler is active.",
        },
        {
            "routine_id": "seed-routine-evening-shutdown",
            "name": "MVP preview evening shutdown",
            "status": "paused",
            "enabled": False,
            "settings": {"cadence": "manual_only", "seed_profile": SAFE_SEED_PROFILE_NAME},
            "notes": "Local preview seed only; no notification or send path is active.",
        },
    )
    routines = []
    for routine_input in routine_inputs:
        routine = get_routine(connection, routine_input["routine_id"])
        if routine is None:
            routine = create_routine(
                connection,
                **routine_input,
                created_at_utc=created_at,
                updated_at_utc=created_at,
            )
        routines.append(routine)
    return routines


def _seed_priorities(
    connection: sqlite3.Connection,
    *,
    created_at: str,
) -> list[dict[str, Any]]:
    priority_input = {
        "priority_id": "seed-priority-local-preview",
        "title": "MVP preview: review local Today View shell",
        "status": "paused",
        "metadata": {
            "seed_profile": SAFE_SEED_PROFILE_NAME,
            "fake": True,
            "local_only": True,
        },
        "notes": "Fake local preview priority; not routed to Todoist, Calendar, Gmail, or models.",
    }
    priority = get_priority(connection, priority_input["priority_id"])
    if priority is None:
        priority = create_priority(
            connection,
            **priority_input,
            created_at_utc=created_at,
            updated_at_utc=created_at,
        )
    return [priority]


def _seed_briefing_windows(
    connection: sqlite3.Connection,
    *,
    created_at: str,
) -> list[dict[str, Any]]:
    windows = (
        ("briefing-window-morning", "morning", "08:00"),
        ("briefing-window-midday", "midday", "12:00"),
        ("briefing-window-afternoon", "afternoon", "16:00"),
        ("briefing-window-evening", "evening", "20:00"),
    )
    with connection:
        for window_id, name, scheduled_time in windows:
            connection.execute(
                """
                INSERT INTO briefing_windows (
                    id,
                    name,
                    scheduled_time,
                    timezone,
                    delivery_mode,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    scheduled_time = excluded.scheduled_time,
                    timezone = excluded.timezone,
                    delivery_mode = excluded.delivery_mode,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                (
                    window_id,
                    name,
                    scheduled_time,
                    DEFAULT_TIMEZONE,
                    "no_send",
                    "draft",
                    created_at,
                    created_at,
                ),
            )
    return _list_briefing_windows(connection)


def _record_bootstrap_run(
    connection: sqlite3.Connection,
    *,
    run_id: str,
    profile: RuntimeBootstrapProfile,
    dry_run: bool,
    status: str,
    input_payload: Mapping[str, Any],
    output_payload: Mapping[str, Any],
    error_message: str | None,
    created_at: str,
    completed_at: str | None,
) -> None:
    if status not in BOOTSTRAP_RUN_STATUSES:
        raise ValueError(f"runtime bootstrap status must be one of: {BOOTSTRAP_RUN_STATUSES}")
    with connection:
        connection.execute(
            """
            INSERT INTO runtime_bootstrap_runs (
                id,
                profile_name,
                runtime_mode,
                db_path_label,
                dry_run,
                status,
                input_json,
                output_json,
                error_message,
                created_at,
                completed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                profile.profile_name,
                profile.runtime_mode,
                profile.db_path_label,
                int(dry_run),
                status,
                _json_dumps(input_payload),
                _json_dumps(output_payload),
                error_message,
                created_at,
                completed_at,
            ),
        )


def _evaluate_mutation_permissions(
    permission_connection: sqlite3.Connection | None,
) -> list[dict[str, Any]]:
    if permission_connection is None:
        return [
            _missing_permission_decision(RUNTIME_BOOTSTRAP_WRITE_PERMISSION),
            _missing_permission_decision(RUNTIME_BOOTSTRAP_RUN_PERMISSION),
        ]
    return [
        evaluate_runtime_bootstrap_permission(
            permission_connection,
            category=RUNTIME_BOOTSTRAP_WRITE_PERMISSION,
        ),
        evaluate_runtime_bootstrap_permission(
            permission_connection,
            category=RUNTIME_BOOTSTRAP_RUN_PERMISSION,
        ),
    ]


def _pending_migration_summaries(db_path: Path) -> list[dict[str, str]]:
    migrations = discover_migrations()
    if not db_path.exists():
        return [_migration_to_summary(migration) for migration in migrations]

    connection = _connect_sqlite_read_only(db_path)
    try:
        applied_versions = _applied_migration_versions_if_available(connection)
    finally:
        connection.close()
    return [
        _migration_to_summary(migration)
        for migration in migrations
        if migration.version not in applied_versions
    ]


def _applied_migration_summaries(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        f"""
        SELECT version, name, checksum, applied_at
        FROM {MIGRATION_METADATA_TABLE}
        ORDER BY version
        """
    ).fetchall()
    return [
        {
            "version": row["version"],
            "name": row["name"],
            "checksum": row["checksum"],
            "applied_at": row["applied_at"],
        }
        for row in rows
    ]


def _applied_migration_versions_if_available(connection: sqlite3.Connection) -> set[str]:
    table_exists = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (MIGRATION_METADATA_TABLE,),
    ).fetchone()
    if table_exists is None:
        return set()
    rows = connection.execute(f"SELECT version FROM {MIGRATION_METADATA_TABLE}").fetchall()
    return {row["version"] for row in rows}


def _table_counts(connection: sqlite3.Connection) -> dict[str, int]:
    table_names = _table_names(connection)
    counts: dict[str, int] = {}
    for table_name in sorted(table_names):
        if table_name.startswith("sqlite_"):
            continue
        counts[table_name] = int(
            connection.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
        )
    return counts


def _permission_summary(connection: sqlite3.Connection) -> dict[str, Any]:
    rows = connection.execute(
        """
        SELECT category, mode
        FROM permission_settings
        ORDER BY category
        """
    ).fetchall()
    categories = {row["category"]: row["mode"] for row in rows}
    live_like = [
        category
        for category in categories
        if any(marker in category for marker in _LIVE_PERMISSION_MARKERS)
    ]
    return {
        "count": len(categories),
        "categories": categories,
        "runtime_bootstrap_permissions": {
            key: categories.get(key)
            for key in (
                RUNTIME_BOOTSTRAP_READ_PERMISSION,
                RUNTIME_BOOTSTRAP_WRITE_PERMISSION,
                RUNTIME_BOOTSTRAP_RUN_PERMISSION,
            )
        },
        "live_like_permission_categories": live_like,
        "live_like_permission_count": len(live_like),
    }


def _seeded_object_summary(connection: sqlite3.Connection) -> dict[str, Any]:
    return {
        "permission_settings": [
            row["category"]
            for row in connection.execute(
                """
                SELECT category
                FROM permission_settings
                WHERE updated_by = ?
                ORDER BY category
                """,
                ("personalos.runtime_bootstrap",),
            ).fetchall()
        ],
        "routines": [
            row["routine_id"]
            for row in connection.execute(
                """
                SELECT routine_id
                FROM routines
                WHERE routine_id LIKE 'seed-routine-%'
                ORDER BY routine_id
                """
            ).fetchall()
        ],
        "priorities": [
            row["priority_id"]
            for row in connection.execute(
                """
                SELECT priority_id
                FROM priorities
                WHERE priority_id LIKE 'seed-priority-%'
                ORDER BY priority_id
                """
            ).fetchall()
        ],
        "briefing_windows": [
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM briefing_windows
                ORDER BY scheduled_time
                """
            ).fetchall()
        ],
    }


def _list_briefing_windows(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, name, scheduled_time, timezone, delivery_mode, status, created_at, updated_at
        FROM briefing_windows
        ORDER BY scheduled_time, name
        """
    ).fetchall()
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "scheduled_time": row["scheduled_time"],
            "timezone": row["timezone"],
            "delivery_mode": row["delivery_mode"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def _create_backup(profile: RuntimeBootstrapProfile) -> Path:
    backup_dir = profile.backup_dir or profile.db_path.parent
    backup_dir.mkdir(parents=True, exist_ok=True)
    for _ in range(BACKUP_PATH_ATTEMPTS):
        backup_path = _backup_path_for(profile)
        try:
            with profile.db_path.open("rb") as source, backup_path.open("xb") as target:
                shutil.copyfileobj(source, target)
            shutil.copystat(profile.db_path, backup_path)
            return backup_path
        except FileExistsError:
            continue
    raise RuntimeError("Could not create a unique runtime backup path.")


def _backup_path_for(profile: RuntimeBootstrapProfile) -> Path:
    backup_dir = profile.backup_dir or profile.db_path.parent
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    suffix = uuid4().hex[:8]
    return backup_dir / f"{profile.db_path.name}.backup.{timestamp}.{suffix}"


def _connect_sqlite(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    _enable_foreign_keys(connection)
    return connection


def _connect_sqlite_read_only(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _enable_foreign_keys(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    if not _foreign_keys_enabled(connection):
        raise RuntimeError("SQLite foreign key enforcement could not be enabled.")


def _foreign_keys_enabled(connection: sqlite3.Connection) -> bool:
    return int(connection.execute("PRAGMA foreign_keys").fetchone()[0]) == 1


def _profile_to_mapping(profile: RuntimeBootstrapProfile | Mapping[str, Any]) -> Mapping[str, Any]:
    if isinstance(profile, RuntimeBootstrapProfile):
        return {
            "profile_name": profile.profile_name,
            "runtime_mode": profile.runtime_mode,
            "db_path_label": profile.db_path_label,
            "db_path": profile.db_path,
            "backup_enabled": profile.backup_enabled,
            "backup_dir": profile.backup_dir,
            "no_external_writes": profile.no_external_writes,
            "no_send_mode": profile.no_send_mode,
            "seed_profile_name": profile.seed_profile_name,
            "created_by": profile.created_by,
        }
    return profile


def _profile_to_jsonable(profile: RuntimeBootstrapProfile) -> dict[str, Any]:
    return {
        "profile_name": profile.profile_name,
        "runtime_mode": profile.runtime_mode,
        "db_path_label": profile.db_path_label,
        "db_path": str(profile.db_path),
        "backup_enabled": profile.backup_enabled,
        "backup_dir": str(profile.backup_dir) if profile.backup_dir is not None else None,
        "no_external_writes": profile.no_external_writes,
        "no_send_mode": profile.no_send_mode,
        "seed_profile_name": profile.seed_profile_name,
        "created_by": profile.created_by,
    }


def _validate_required_text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _validate_runtime_mode(value: Any) -> str:
    runtime_mode = _validate_required_text("runtime_mode", value)
    if runtime_mode not in ALLOWED_RUNTIME_MODES:
        allowed = ", ".join(ALLOWED_RUNTIME_MODES)
        raise ValueError(f"runtime_mode must be one of: {allowed}")
    return runtime_mode


def _validate_seed_profile(value: Any) -> str:
    seed_profile = _validate_required_text("seed_profile_name", value)
    if seed_profile not in ALLOWED_SEED_PROFILES:
        allowed = ", ".join(ALLOWED_SEED_PROFILES)
        raise ValueError(f"seed_profile_name must be one of: {allowed}")
    return seed_profile


def _validate_true(name: str, value: Any) -> bool:
    if value is not True:
        raise ValueError(f"{name} must be true for Phase 9B runtime bootstrap")
    return True


def _validate_database_path(value: Any) -> Path:
    if value is None:
        raise ValueError("db_path must be explicit")
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError("db_path must be an explicit absolute path")
    if path.suffix not in _DATABASE_SUFFIXES:
        allowed = ", ".join(sorted(_DATABASE_SUFFIXES))
        raise ValueError(f"db_path suffix must be one of: {allowed}")
    return path.resolve()


def _validate_backup_dir(value: Any) -> Path | None:
    if value in (None, ""):
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError("backup_dir must be an explicit absolute path when provided")
    return path.resolve()


def _ensure_allowed_runtime_path(path: Path, *, require_database_suffix: bool = True) -> None:
    resolved = path.resolve()
    _reject_protected_path(resolved)
    _reject_sensitive_path(resolved)
    _reject_production_path(resolved)
    if require_database_suffix and resolved.suffix not in _DATABASE_SUFFIXES:
        raise ValueError("runtime database path must use a SQLite file suffix")
    if _is_under_repo(resolved) or _is_under_temp(resolved):
        return
    raise ValueError("runtime bootstrap paths must stay in explicit temp or repo-local dev paths")


def _reject_protected_path(path: Path) -> None:
    parts = path.parts
    home = Path.home().resolve()
    protected_personalos = home / "PersonalOS"
    protected_openclaw = home / ".openclaw"
    try:
        path.relative_to(protected_personalos)
    except ValueError:
        pass
    else:
        raise ValueError("runtime bootstrap path points at a protected PersonalOS path")
    try:
        path.relative_to(protected_openclaw)
    except ValueError:
        pass
    else:
        raise ValueError("runtime bootstrap path points at a protected OpenClaw path")
    if ".openclaw" in parts:
        raise ValueError("runtime bootstrap path points at a protected OpenClaw path")
    if "LaunchAgents" in parts:
        raise ValueError("runtime bootstrap path points at a protected LaunchAgents path")


def _reject_sensitive_path(path: Path) -> None:
    lowered = str(path).lower()
    if any(marker in lowered for marker in _SENSITIVE_PATH_MARKERS):
        raise ValueError("runtime bootstrap path looks like a credential or authorization path")


def _reject_production_path(path: Path) -> None:
    parts = {part.lower() for part in path.parts}
    stem_markers = {part.lower() for part in path.stem.replace("-", "_").split("_")}
    if parts & _PRODUCTION_MARKERS or stem_markers & _PRODUCTION_MARKERS:
        raise ValueError("production-looking runtime paths are blocked in Phase 9B")


def _is_under_repo(path: Path) -> bool:
    try:
        path.relative_to(REPO_ROOT.resolve())
    except ValueError:
        return False
    return True


def _is_under_temp(path: Path) -> bool:
    temp_root = Path(tempfile.gettempdir()).resolve()
    allowed_temp_roots = {
        temp_root,
        Path("/tmp").resolve(),
        Path("/private/tmp").resolve(),
        Path("/var/folders").resolve(),
        Path("/private/var/folders").resolve(),
    }
    for root in allowed_temp_roots:
        try:
            path.relative_to(root)
        except ValueError:
            continue
        return True
    return False


def _path_warnings(profile: RuntimeBootstrapProfile) -> list[str]:
    warnings = [
        "Phase 9B bootstrap is local/dev-preview only; production runtime activation is blocked.",
        (
            "No scheduler, LaunchAgent, Gmail send, live Todoist/Calendar write, "
            "or live model/API call is configured."
        ),
    ]
    if _is_under_repo(profile.db_path):
        warnings.append("Repo-local runtime databases are allowed only for explicit dev/test use.")
    return warnings


def _safety_flags(profile: RuntimeBootstrapProfile) -> dict[str, bool]:
    return {
        "no_external_writes": profile.no_external_writes,
        "no_send_mode": profile.no_send_mode,
        "no_live_systems_touched": True,
    }


def _permission_decision(
    *,
    allowed: bool,
    category: str,
    mode: str | None,
    reason: str,
    setting: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "allowed": allowed,
        "category": category,
        "mode": mode,
        "reason": reason,
        "setting": setting,
    }


def _missing_permission_decision(category: str) -> dict[str, Any]:
    return _permission_decision(
        allowed=False,
        category=category,
        mode=None,
        reason=f"Missing runtime bootstrap permission setting: {category}",
        setting=None,
    )


def _blocked_result(
    reason: str,
    dry_run: bool,
    permission: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": reason,
        "dry_run": dry_run,
        "database_write": False,
        "external_mutation": False,
        "sent": False,
        "no_external_writes": True,
        "no_send_mode": True,
        "no_live_systems_touched": True,
        "permission": dict(permission),
    }


def _migration_to_summary(migration: Any) -> dict[str, str]:
    return {
        "version": migration.version,
        "name": migration.name,
        "checksum": migration.checksum,
    }


def _table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        """
    ).fetchall()
    return {row["name"] for row in rows}


def _json_dumps(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, allow_nan=False, separators=(",", ":"), sort_keys=True)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
