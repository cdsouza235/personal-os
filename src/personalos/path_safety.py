"""Shared explicit-path safety checks for local/dev Personal OS surfaces."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from personalos import config
from personalos.config import REPO_ROOT

# The one admitted `shadow_live` database location (`PHASE0_ARCHITECTURE_DECISIONS.md`
# AD-4, amended P-KE-2E, 2026-07-17). Originally `var/shadow/personalos-shadow.sqlite3`
# (repo-local, admitted via the ordinary `is_under_repo` branch below); relocated
# outside the repo because the harness wipes untracked repo files on every packet run,
# which destroyed the shadow DB between runs and cannot coexist with a 14-day
# accumulation (`audits/knowledge-edge/2026-07-17-packet-2c-first-shadow-run-
# transcript.md` "COLLISION"). Lives here, not in `config.py` or
# `knowledge_edge/shadow_mode.py`, so there is exactly one source of truth for the
# admitted value; `shadow_mode.SHADOW_DB_PATH` imports this object directly rather than
# redefining it. Read at call time via `is_admitted_shadow_path` below (never a captured
# copy), the same discipline `config.PRODUCTION_DB_PATH` already gets from this module,
# so tests can monkeypatch it to a temp stand-in.
SHADOW_DB_PATH: Path = Path("~/.personalos/shadow/personalos-shadow.sqlite3").expanduser()

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
DEMO_OUTPUT_DIR_SCHEDULER_MARKERS = frozenset(
    {
        "scheduler",
        "launchagent",
        "launchagents",
        "launch_agent",
        "crontab",
        "daemon",
        "background",
        "background_loop",
        "background-loop",
    }
)
DEMO_OUTPUT_DIR_CREDENTIAL_MARKERS = frozenset(
    {
        "credential",
        "credentials",
        "token",
        "secret",
        "oauth",
        "api",
        "api_key",
        "apikey",
        "client_secret",
        "password",
    }
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
    if any(marker in lowered for marker in SENSITIVE_PATH_MARKERS) or _path_has_marker(
        path,
        DEMO_OUTPUT_DIR_CREDENTIAL_MARKERS,
    ):
        raise ValueError(f"{path_label} looks like a credential or authorization path")


def reject_production_path(path: Path, *, path_label: str) -> None:
    parts = {part.lower() for part in path.parts}
    stem_markers = {part.lower() for part in path.stem.replace("-", "_").split("_")}
    if parts & PRODUCTION_MARKERS or stem_markers & PRODUCTION_MARKERS:
        raise ValueError(f"production-looking {path_label} is blocked in Phase 12A")


def is_admitted_shadow_path(path: Path) -> bool:
    """Exact-match admission for the one `shadow_live` database location -- not a
    general "anything under ~/.personalos" escape hatch, mirroring
    `config.PRODUCTION_DB_PATH`'s own exact-match-only precedent in this module.
    Reads module-level `SHADOW_DB_PATH` at call time (not a captured copy) so tests
    can monkeypatch it to a temp stand-in exactly like `config.PRODUCTION_DB_PATH`
    already is.
    """
    return path == SHADOW_DB_PATH.resolve()


def validate_existing_sqlite_path(
    path_value: str | Path,
    *,
    path_label: str,
    allow_production_path: bool = False,
) -> Path:
    resolved = resolve_explicit_path(path_value, path_label=path_label)
    # D-PO-011 (HI-09) approved exactly one production database location, and
    # P-SCHED-02 (config.py) recorded it as `config.PRODUCTION_DB_PATH` -- the single
    # source of truth for that path, read here at call time (not copied into a
    # module-level name) so tests can monkeypatch `config.PRODUCTION_DB_PATH` to a temp
    # stand-in the same way tests/test_config.py already does, without ever touching the
    # real path. P-SCHED-03 wired this exemption in unconditionally by path-match alone,
    # which meant every CLI command sharing `_connect_read_only`/`_connect_read_write`
    # could target production. P-SCHED-04 narrows it: the exemption only applies when the
    # caller explicitly opts in via `allow_production_path` (threaded from
    # `_connect_read_write`, which only `run morning`'s handler sets). No other path under
    # ~/PersonalOS gets this exemption, and `reject_sensitive_path`/`reject_production_path`
    # still run unconditionally for this path exactly as for any other.
    is_approved_production_path = allow_production_path and (
        resolved == config.PRODUCTION_DB_PATH.resolve()
    )
    # The shadow path (AD-4, amended P-KE-2E) gets no such skip: it goes through
    # reject_protected_path/reject_sensitive_path/reject_production_path unconditionally,
    # like any other path, with no special-casing -- it just happens to pass all three
    # (see the SHADOW_DB_PATH module comment above).
    is_admitted_shadow = is_admitted_shadow_path(resolved)
    if not is_approved_production_path:
        reject_protected_path(resolved, path_label=path_label)
    reject_sensitive_path(resolved, path_label=path_label)
    reject_production_path(resolved, path_label=path_label)
    if resolved.suffix not in DATABASE_SUFFIXES:
        allowed = ", ".join(sorted(DATABASE_SUFFIXES))
        raise ValueError(f"{path_label} suffix must be one of: {allowed}")
    if not (
        is_approved_production_path
        or is_admitted_shadow
        or is_under_repo(resolved)
        or is_under_temp(resolved)
    ):
        raise ValueError(
            f"{path_label} must stay in explicit temp, repo-local dev, or the admitted "
            "shadow path"
        )
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


def validate_demo_output_dir_path(path_value: str | Path, *, path_label: str) -> Path:
    normalized = normalize_explicit_absolute_path_no_stat(path_value, path_label=path_label)
    reject_demo_output_dir_lexical(normalized, path_label=path_label)
    resolved = normalized.resolve(strict=False)
    reject_demo_output_dir_lexical(resolved, path_label=path_label)
    if not is_under_temp(resolved):
        raise ValueError(f"{path_label} must stay under an explicit OS temp directory")
    if resolved.exists() and not resolved.is_dir():
        raise ValueError(f"{path_label} must point to a directory, not a file")
    return resolved


def normalize_explicit_absolute_path_no_stat(
    path_value: str | Path,
    *,
    path_label: str,
) -> Path:
    path_text = str(path_value).strip()
    if not path_text:
        raise ValueError(f"{path_label} must be provided explicitly")
    expanded = Path(path_text).expanduser()
    if not expanded.is_absolute():
        raise ValueError(f"{path_label} must be an explicit absolute path")
    return Path(os.path.normpath(str(expanded)))


def reject_demo_output_dir_lexical(path: Path, *, path_label: str) -> None:
    home = Path.home()
    protected_personalos = home / "PersonalOS"
    protected_openclaw = home / ".openclaw"
    if _is_same_or_under_path(path, protected_personalos):
        raise ValueError(f"{path_label} points at a protected PersonalOS path")
    if _is_same_or_under_path(path, protected_openclaw) or ".openclaw" in path.parts:
        raise ValueError(f"{path_label} points at a protected OpenClaw path")
    if _is_same_or_under_path(path, REPO_ROOT):
        raise ValueError(f"{path_label} must not be inside the repository")
    if ".git" in path.parts:
        raise ValueError(f"{path_label} points at a protected Git metadata path")
    lowered = str(path).lower()
    if "openclaw" in lowered:
        raise ValueError(f"{path_label} looks like a protected OpenClaw path")
    if any(marker in lowered for marker in SENSITIVE_PATH_MARKERS) or _path_has_marker(
        path,
        DEMO_OUTPUT_DIR_CREDENTIAL_MARKERS,
    ):
        raise ValueError(f"{path_label} looks like a credential or authorization path")
    if _path_has_marker(path, PRODUCTION_MARKERS):
        raise ValueError(f"production-looking {path_label} is blocked in Phase 13E-D")
    if _path_has_marker(path, DEMO_OUTPUT_DIR_SCHEDULER_MARKERS):
        raise ValueError(
            f"{path_label} looks like a scheduler, LaunchAgent, crontab, or daemon path"
        )


def is_under_repo(path: Path) -> bool:
    try:
        path.relative_to(REPO_ROOT.resolve())
    except ValueError:
        return False
    return True


def _is_same_or_under_path(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _path_has_marker(path: Path, markers: frozenset[str]) -> bool:
    for part in path.parts:
        tokens = {token for token in re.split(r"[^a-z0-9]+", part.lower()) if token}
        if tokens & markers:
            return True
    return False


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
