"""Safe configuration defaults for development and tests."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

DEFAULT_TIMEZONE = "America/Chicago"
REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = REPO_ROOT / "var"
DEV_DB_PATH = RUNTIME_DIR / "dev" / "personalos-dev.sqlite3"
TEST_DB_PATH = RUNTIME_DIR / "test" / "personalos-test.sqlite3"


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class ProductionConfigUnavailable(RuntimeError):
    """Raised when production config is requested before a future approval gate."""


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

    if selected_environment is Environment.PRODUCTION:
        raise ProductionConfigUnavailable(
            "Production configuration is not available in the Phase 1 dev/test boundary."
        )

    database_path = _database_path_for(selected_environment)
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
    raise ProductionConfigUnavailable(
        "Production database paths are intentionally undefined for Phase 1."
    )


def _ensure_repo_local_runtime_path(path: Path) -> None:
    path.resolve().relative_to(RUNTIME_DIR.resolve())
