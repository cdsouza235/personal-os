"""Safe configuration defaults for development and tests, plus the one narrow production
database path approved by D-PO-011 (HI-09,
governance/living/agent-writable/DECISIONS.md)."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

DEFAULT_TIMEZONE = "America/Chicago"
REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = REPO_ROOT / "var"
DEV_DB_PATH = RUNTIME_DIR / "dev" / "personalos-dev.sqlite3"
TEST_DB_PATH = RUNTIME_DIR / "test" / "personalos-test.sqlite3"

# The one production database location, approved by D-PO-011 (HI-09, 2026-07-10) and
# reserved as a protected external path in governance/SECURITY.md / RISK_REGISTER.md --
# it is the existing protected path, not a new one. This is intentionally a single,
# hardcoded, exact-match location, not a general "any production path" escape hatch:
# lifting Phase 1's blanket production block must not become a way to point Personal OS
# at an arbitrary host path. P-SCHED-02 adds this constant and the narrow resolver/
# validator below; it deliberately does NOT wire production through
# `db/connection.py` (`connect_sqlite` still independently raises
# `ProductionConfigUnavailable` for `Environment.PRODUCTION`) or through the CLI's
# `--db` path (`path_safety.validate_existing_sqlite_path` still independently rejects
# anything under `~/PersonalOS`). Those are separate, independent guards outside this
# packet's scope; wiring them through to this path is future work.
PRODUCTION_DB_PATH = Path("/Users/coldstake/PersonalOS/personal_os.db")


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class ProductionConfigUnavailable(RuntimeError):
    """Raised when a production database path does not match the one location approved
    by D-PO-011."""


@dataclass(frozen=True)
class PersonalOSConfig:
    environment: Environment
    timezone: str
    database_path: Path

    @property
    def is_production(self) -> bool:
        return self.environment is Environment.PRODUCTION


def default_environment() -> Environment:
    return Environment.DEVELOPMENT


def load_config(environment: Environment | str | None = None) -> PersonalOSConfig:
    selected_environment = _normalize_environment(environment) if environment else default_environment()

    database_path = _database_path_for(selected_environment)
    if selected_environment is Environment.PRODUCTION:
        _ensure_production_runtime_path(database_path)
    else:
        _ensure_repo_local_runtime_path(database_path)

    return PersonalOSConfig(
        environment=selected_environment,
        timezone=DEFAULT_TIMEZONE,
        database_path=database_path,
    )


def _normalize_environment(environment: Environment | str) -> Environment:
    if isinstance(environment, Environment):
        return environment
    return Environment(environment)


def _database_path_for(environment: Environment) -> Path:
    if environment is Environment.DEVELOPMENT:
        return DEV_DB_PATH
    if environment is Environment.TEST:
        return TEST_DB_PATH
    return PRODUCTION_DB_PATH


def _ensure_repo_local_runtime_path(path: Path) -> None:
    path.resolve().relative_to(RUNTIME_DIR.resolve())


def _ensure_production_runtime_path(path: Path) -> None:
    """Fail closed unless `path` resolves to exactly the one approved production
    location. Mirrors `_ensure_repo_local_runtime_path`'s self-check discipline for
    dev/test paths, adapted for one specific real file instead of a whole directory
    tree. `PRODUCTION_DB_PATH` is read at call time (not captured at import) so tests can
    monkeypatch it to a temp stand-in and exercise both the match and mismatch cases
    without ever touching the real path."""
    if path.resolve() != PRODUCTION_DB_PATH.resolve():
        raise ProductionConfigUnavailable(
            "Production database path must match the exact D-PO-011 approved location."
        )


def bootstrap_production_database() -> list[dict[str, str]]:
    """Apply pending schema migrations to the production database (D-PO-011's approved
    path only). Schema-only: no seed data is written -- the dev/test seed profiles in
    `runtime_bootstrap.py` are fake local-preview fixtures and must never land in
    production. This is the "same bootstrap capability" the dev/test path has
    (`apply_migrations`), exposed narrowly for the one production path instead of by
    loosening `runtime_bootstrap.py`'s `ALLOWED_RUNTIME_MODES` guard.

    Nothing in P-SCHED-02 calls this function against the real path; it is exercised in
    tests only against a monkeypatched `PRODUCTION_DB_PATH` pointing at a temp file.
    Running it for real, once HI-10 clears, is a deliberate manual action, not something
    any packet or scheduled job triggers on its own.
    """
    import sqlite3

    from personalos.db.migrations import apply_migrations

    config = load_config(Environment.PRODUCTION)
    database_path = config.database_path
    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        applied = apply_migrations(connection)
        return [
            {"version": migration.version, "name": migration.name, "checksum": migration.checksum}
            for migration in applied
        ]
    finally:
        connection.close()
