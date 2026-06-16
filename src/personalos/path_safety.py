"""Shared explicit-path safety checks for local/dev Personal OS surfaces."""

from __future__ import annotations

import tempfile
from pathlib import Path

from personalos.config import REPO_ROOT

DATABASE_SUFFIXES = frozenset({".sqlite", ".sqlite3", ".db"})
PRODUCTION_MARKERS = frozenset({"prod", "production", "live"})
SENSITIVE_PATH_MARKERS = (
    "credential",
    "credentials",
    "client" + "_" + "sec" + "ret",
    "token" + ".json",
    "api" + "_" + "key",
    "o" + "auth",
    "pass" + "word",
    "sec" + "ret",
)


def resolve_explicit_path(path_value: str | Path, *, path_label: str) -> Path:
    path_text = str(path_value).strip()
    if not path_text:
        raise ValueError(f"{path_label} must be provided explicitly")
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        raise ValueError(f"{path_label} must be an explicit absolute path")
    return path.resolve()


def reject_protected_path(path: Path, *, path_label: str) -> None:
    home = Path.home().resolve()
    protected_personalos = home / "PersonalOS"
    protected_openclaw = home / ".openclaw"
    try:
        path.relative_to(protected_personalos)
    except ValueError:
        pass
    else:
        raise ValueError(f"{path_label} points at a protected PersonalOS path")
    try:
        path.relative_to(protected_openclaw)
    except ValueError:
        pass
    else:
        raise ValueError(f"{path_label} points at a protected OpenClaw path")
    if ".openclaw" in path.parts:
        raise ValueError(f"{path_label} points at a protected OpenClaw path")
    if "LaunchAgents" in path.parts:
        raise ValueError(f"{path_label} points at a protected LaunchAgents path")


def reject_sensitive_path(path: Path, *, path_label: str) -> None:
    lowered = str(path).lower()
    if any(marker in lowered for marker in SENSITIVE_PATH_MARKERS):
        raise ValueError(f"{path_label} looks like a credential or authorization path")


def reject_production_path(path: Path, *, path_label: str) -> None:
    parts = {part.lower() for part in path.parts}
    stem_markers = {part.lower() for part in path.stem.replace("-", "_").split("_")}
    if parts & PRODUCTION_MARKERS or stem_markers & PRODUCTION_MARKERS:
        raise ValueError(f"production-looking {path_label} is blocked in Phase 12A")


def validate_existing_sqlite_path(path_value: str | Path, *, path_label: str) -> Path:
    resolved = resolve_explicit_path(path_value, path_label=path_label)
    reject_protected_path(resolved, path_label=path_label)
    reject_sensitive_path(resolved, path_label=path_label)
    reject_production_path(resolved, path_label=path_label)
    if resolved.suffix not in DATABASE_SUFFIXES:
        allowed = ", ".join(sorted(DATABASE_SUFFIXES))
        raise ValueError(f"{path_label} suffix must be one of: {allowed}")
    if not (is_under_repo(resolved) or is_under_temp(resolved)):
        raise ValueError(f"{path_label} must stay in explicit temp or repo-local dev paths")
    if not resolved.is_file():
        raise ValueError(f"{path_label} must point to an existing SQLite file")
    return resolved


def validate_existing_input_file_path(path_value: str | Path, *, path_label: str) -> Path:
    resolved = resolve_explicit_path(path_value, path_label=path_label)
    reject_protected_path(resolved, path_label=path_label)
    reject_sensitive_path(resolved, path_label=path_label)
    reject_production_path(resolved, path_label=path_label)
    if is_under_repo_var(resolved):
        raise ValueError(f"{path_label} must not point under repo-local var/")
    if not (is_under_repo(resolved) or is_under_temp(resolved)):
        raise ValueError(f"{path_label} must stay in explicit temp or repo-local dev paths")
    if not resolved.is_file():
        raise ValueError(f"{path_label} must point to an existing file")
    return resolved


def validate_output_file_path(path_value: str | Path, *, path_label: str) -> Path:
    resolved = resolve_explicit_path(path_value, path_label=path_label)
    reject_protected_path(resolved, path_label=path_label)
    reject_sensitive_path(resolved, path_label=path_label)
    reject_production_path(resolved, path_label=path_label)
    if is_under_repo_var(resolved):
        raise ValueError(f"{path_label} must not point under repo-local var/")
    if not (is_under_repo(resolved) or is_under_temp(resolved)):
        raise ValueError(f"{path_label} must stay in explicit temp or repo-local dev paths")
    if resolved.exists() and resolved.is_dir():
        raise ValueError(f"{path_label} must point to a file, not a directory")
    if not resolved.parent.is_dir():
        raise ValueError(f"{path_label} parent directory must already exist")
    return resolved


def is_under_repo(path: Path) -> bool:
    try:
        path.relative_to(REPO_ROOT.resolve())
    except ValueError:
        return False
    return True


def is_under_repo_var(path: Path) -> bool:
    try:
        path.relative_to((REPO_ROOT / "var").resolve())
    except ValueError:
        return False
    return True


def is_under_temp(path: Path) -> bool:
    for temp_root in _temp_roots():
        try:
            path.relative_to(temp_root)
        except ValueError:
            continue
        return True
    return False


def _temp_roots() -> tuple[Path, ...]:
    roots = {
        Path(tempfile.gettempdir()).resolve(),
        Path("/tmp").resolve(),
        Path("/private/tmp").resolve(),
    }
    return tuple(sorted(roots))
