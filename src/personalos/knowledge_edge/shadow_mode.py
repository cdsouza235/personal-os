"""P-KE-2C: `shadow_live` feature-mode admission fence (amendment §14.4).

§14.4 defines `shadow_live` as "live discovery and persistence, no production
notification or Obsidian write." This module is the one place that fence is
enforced as code, mirroring the house convention already set by
`rails/knowledge_edge/podcasts.py`/`youtube.py`'s `_evaluate_gates`: one ordered,
honest refusal function per surface, never a scattered ad hoc check duplicated at
each call site.

What `shadow_live` may touch, structurally, per this module:
    - the shadow SQLite database at `SHADOW_DB_PATH` -- the ONLY writable DB;
    - live discovery adapters, already independently gated per-source by their own
      verified-active check (`podcasts.py`/`youtube.py` `_evaluate_gates`).

What `shadow_live` may never touch, enforced here:
    - any database path other than `SHADOW_DB_PATH` (most importantly, the one
      approved production location);
    - notification delivery;
    - Obsidian writes;
    - scheduler/LaunchAgent/background activation.

`SHADOW_DB_PATH` mirrors `PHASE0_ARCHITECTURE_DECISIONS.md` AD-4's admitted shadow
path exactly: originally `config.SHADOW_DB_PATH` = `var/shadow/personalos-shadow.sqlite3`
(repo-local; Packet 1A), **amended by P-KE-2E (2026-07-17)** to
`~/.personalos/shadow/personalos-shadow.sqlite3` -- the harness wipes untracked repo
files on every packet run, which destroyed the repo-local shadow DB between runs and
cannot coexist with the required 14-day accumulation (see
`audits/knowledge-edge/2026-07-17-packet-2c-first-shadow-run-transcript.md`
"COLLISION"). The fence's CLASS logic here is unchanged by that amendment -- exactly
one admitted shadow path, dev/test/production still refused -- only the admitted value
moved outside the repo tree.

The constant itself now lives in `path_safety.SHADOW_DB_PATH` (imported here, not
redefined) rather than in `src/personalos/config.py` -- AD-4's own originally-suggested
location -- because `config.py` sits outside this packet's declared `allowed_paths`
(`src/personalos/knowledge_edge/**`, `src/personalos/cli/**`, `rails/knowledge_edge/**`,
`docs/knowledge_edge/**`, `tests/**`, `migrations/**`), same as at Packet 1A. Landing
this constant in `config.py` itself remains a required follow-up for whichever future
packet next legitimately touches `config.py`, mirroring `PHASE0_PLAN.md` §3's "required
follow-up this packet cannot execute" pattern -- not invented as a fait accompli here.
Because the new path sits outside the repo, `path_safety.validate_existing_sqlite_path`
now needs (and has, as of P-KE-2E) a dedicated exact-match admission branch
(`path_safety.is_admitted_shadow_path`) -- the old repo-local path's free ride on the
generic `is_under_repo` branch no longer applies; see `path_safety.py`'s own
`SHADOW_DB_PATH` module comment for the admission analysis.
"""

from __future__ import annotations

from pathlib import Path

from personalos import config
from personalos.path_safety import SHADOW_DB_PATH

SHADOW_LIVE_MODE = "shadow_live"


class ShadowModeViolation(RuntimeError):
    """Raised when an operation would cross the §14.4 `shadow_live` fence."""


def require_shadow_database_path(database_path: str | Path) -> Path:
    """The one admitted writable DB for a `shadow_live` operation: resolves
    ``database_path`` and requires an exact match against `SHADOW_DB_PATH`. Every
    shadow-mode entrypoint (bootstrap, shadow scan, sample freeze, report
    generation) calls this before doing anything else.
    """
    resolved = Path(database_path).expanduser().resolve()
    expected = SHADOW_DB_PATH.resolve()
    if resolved != expected:
        raise ShadowModeViolation(
            f"shadow_live mode requires the shadow database path exactly "
            f"({expected}); got {resolved}"
        )
    return resolved


def refuse_if_shadow_live(feature_mode: str, *, surface: str) -> None:
    """Structural refusal for any surface `shadow_live` may never reach --
    notifications, Obsidian, scheduler activation. A no-op for every other feature
    mode: this function only ever narrows what `shadow_live` may do, it is never a
    general-purpose feature-mode gate for other modes.
    """
    if feature_mode == SHADOW_LIVE_MODE:
        raise ShadowModeViolation(
            f"{surface} is refused in shadow_live mode (amendment §14.4: shadow_live "
            "is live discovery and persistence only -- no production notification, "
            "no Obsidian write, no scheduler activation, no production database)"
        )


def refuse_notification_send(feature_mode: str) -> None:
    refuse_if_shadow_live(feature_mode, surface="notification send")


def refuse_obsidian_write(feature_mode: str) -> None:
    refuse_if_shadow_live(feature_mode, surface="Obsidian write")


def refuse_scheduler_activation(feature_mode: str) -> None:
    refuse_if_shadow_live(feature_mode, surface="scheduler/LaunchAgent activation")


def refuse_production_database(feature_mode: str, database_path: str | Path) -> None:
    """Refuses when `feature_mode` is `shadow_live` AND `database_path` resolves to
    the one approved production location (`config.PRODUCTION_DB_PATH`) --
    `shadow_live` may only ever write its own shadow DB, never production,
    regardless of what a caller passes. Reads `config.PRODUCTION_DB_PATH` at call
    time (not captured at import), matching `config._ensure_production_runtime_path`'s
    own discipline, so tests can monkeypatch it to a temp stand-in.
    """
    if feature_mode != SHADOW_LIVE_MODE:
        return
    resolved = Path(database_path).expanduser().resolve()
    if resolved == config.PRODUCTION_DB_PATH.resolve():
        raise ShadowModeViolation(
            "production database path is refused in shadow_live mode (amendment §14.4)"
        )


def validate_shadow_admission(*, feature_mode: str, database_path: str | Path) -> None:
    """The one entrypoint every shadow-mode CLI command runs before doing anything
    else: a no-op for any mode other than `shadow_live`; for `shadow_live`, refuses
    the production path first (the more specific, more dangerous mismatch) and then
    requires an exact match against `SHADOW_DB_PATH`.
    """
    if feature_mode != SHADOW_LIVE_MODE:
        return
    refuse_production_database(feature_mode, database_path)
    require_shadow_database_path(database_path)
