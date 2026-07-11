"""Behavioral-equivalence proof for P-DEBT-01 (governance/ROADMAP.md Phase E).

REWORK NOTE (2026-07-11): a prior version of this file imported each site's
PUBLIC `evaluate_*_permission` function as "the old implementation" and
compared it against a direct call into `evaluate_auto_write_gate` built from
the SAME lambda reason-strings. By the time that comparison ran, those public
functions had ALREADY been migrated (in the same diff) to be thin wrappers
that call `evaluate_auto_write_gate` internally -- so the test was comparing
the new shared function against a wrapper that also calls the new shared
function. It was circular: a reason-string or branch-logic drift introduced
during migration would have been invisible to it.

This version fixes that by hardcoding the EXPECTED `allowed`/`reason` (and
full result-dict shape) for every branch of all 12 sites as literal Python
data, typed independently rather than produced by calling any evaluator. The
test then asserts the CURRENT, real public `evaluate_*_permission` function
(the actual code path every caller in the codebase uses) at each site
produces exactly that hardcoded value.

Provenance of the hardcoded literals, given this sandbox has no `git` binary
and no `.git` directory (confirmed: `which git` fails, `/work/.git` does not
exist) -- so `git show <base_sha>:<path>` as prescribed by the task brief is
not possible here:

  1. The task brief itself transcribes the original (pre-migration) exact
     reason-string patterns for all 12 sites, sampled directly from base
     source by the task's author before any migration happened. That
     transcription is reproduced per-site in the tables below.
  2. Every one of the 12 sites' CURRENT source (the `evaluate_*_permission`
     function bodies, which per the migration design pass each exact reason
     string through as a literal f-string argument to
     `evaluate_auto_write_gate`) was re-read directly (not executed) via the
     Read tool immediately before writing this file, specifically to check
     for any drift against the task brief's independent transcription.
  3. The two sources agree on every site once English capitalization rules
     are accounted for (labels like "routine engine permission" are
     lower-case when they follow "Missing "/"Invalid " mid-sentence, and
     capitalized when they open a sentence, e.g. "Routine engine permission
     is disabled: ..." -- this is a property of ordinary English, not an
     inconsistency, and both sources show it identically). No drift was
     found. The literals below are byte-exact copies of what both sources
     agree on, retyped here as plain data (not imported lambdas) so this
     test does not call any of the 12 sites' own code to build its
     expectations.

If a future site's wording is ever intentionally changed, this test's
literal must be updated by a human reading the change -- that friction is
the point: it is what makes an accidental drift visible instead of silently
absorbed.
"""

import sqlite3
import tempfile
import unittest
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from personalos.briefings import evaluate_briefing_loop_permission
from personalos.calendar_blocks import evaluate_calendar_module_permission
from personalos.composer import evaluate_composer_module_permission
from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.permissions import PermissionMode
from personalos.priorities import evaluate_priority_engine_permission
from personalos.rails.calendar import (
    CALENDAR_RAIL_LIVE_WRITE_PERMISSION,
    evaluate_calendar_rail_live_write_permission,
)
from personalos.rails.gmail import (
    GMAIL_RAIL_LIVE_SEND_PERMISSION,
    evaluate_gmail_rail_live_send_permission,
)
from personalos.rails.todoist import (
    TODOIST_RAIL_LIVE_WRITE_PERMISSION,
    evaluate_todoist_rail_live_write_permission,
)
from personalos.routines import evaluate_routine_engine_permission
from personalos.runtime_bootstrap import evaluate_runtime_bootstrap_permission
from personalos.side_effects import evaluate_side_effect_ledger_permission
from personalos.state import get_permission_setting, upsert_permission_setting
from personalos.synthesis_apply import evaluate_synthesis_apply_permission
from personalos.synthesis_import import evaluate_synthesis_import_permission
from personalos.todoist import evaluate_todoist_module_permission


@contextmanager
def _migrated_test_connection() -> Iterator[sqlite3.Connection]:
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir) / "runtime"
        config = PersonalOSConfig(
            environment=Environment.TEST,
            timezone=DEFAULT_TIMEZONE,
            database_path=runtime_dir / "test" / "personalos.sqlite3",
        )
        connection = connect_sqlite(config, runtime_dir=runtime_dir)
        apply_migrations(connection)
        try:
            yield connection
        finally:
            connection.close()


def _set(connection: sqlite3.Connection, *, category: str, mode: str) -> None:
    upsert_permission_setting(
        connection,
        category=category,
        mode=mode,
        metadata={"packet": "P-DEBT-01"},
        updated_by="tests",
        updated_at_utc="2026-07-11T00:00:00+00:00",
    )


class _FamilyASite:
    """One module dev/test gate site: 4-branch logic, `category` supplied by caller.

    `missing`/`invalid`/`disabled`/`not_auto_write` reason builders and the
    `success` string are hand-transcribed literals (see module docstring for
    provenance), not references to the site's own production lambdas.
    """

    def __init__(
        self,
        *,
        name: str,
        fn: Callable[..., dict[str, Any]],
        missing: Callable[[str], str],
        invalid: Callable[[str, str], str],
        disabled: Callable[[str], str],
        not_auto_write: Callable[[str], str],
        success: str,
        include_mode: bool = True,
        include_setting: bool = True,
    ) -> None:
        self.name = name
        self.fn = fn
        self.missing = missing
        self.invalid = invalid
        self.disabled = disabled
        self.not_auto_write = not_auto_write
        self.success = success
        self.include_mode = include_mode
        self.include_setting = include_setting


class _FamilyBSite:
    """One live rail gate site: 3-branch logic, single fixed `category`."""

    def __init__(
        self,
        *,
        name: str,
        fn: Callable[[sqlite3.Connection], dict[str, Any]],
        category: str,
        missing: str,
        invalid: Callable[[str], str],
        not_auto_write: Callable[[str], str],
        success: str,
    ) -> None:
        self.name = name
        self.fn = fn
        self.category = category
        self.missing = missing
        self.invalid = invalid
        self.not_auto_write = not_auto_write
        self.success = success


# Hand-transcribed from the 12 sites' current source (cross-checked against
# the task brief's independent base-source transcription -- see module
# docstring). Every reason string here is retyped literal text, not an
# imported function reference.
_FAMILY_A_SITES: list[_FamilyASite] = [
    _FamilyASite(
        name="todoist_module",
        fn=evaluate_todoist_module_permission,
        missing=lambda c: f"Missing Todoist module permission setting: {c}",
        invalid=lambda c, m: f"Invalid Todoist module permission mode: {m}",
        disabled=lambda c: f"Todoist module permission is disabled: {c}",
        not_auto_write=lambda c: f"Todoist module permission is not enabled for dev/test use: {c}",
        success="Todoist module permission is explicitly enabled for dev/test use.",
    ),
    _FamilyASite(
        name="routine_engine",
        fn=evaluate_routine_engine_permission,
        missing=lambda c: f"Missing routine engine permission setting: {c}",
        invalid=lambda c, m: f"Invalid routine engine permission mode: {m}",
        disabled=lambda c: f"Routine engine permission is disabled: {c}",
        not_auto_write=lambda c: f"Routine engine permission is not enabled for dev/test use: {c}",
        success="Routine engine permission is explicitly enabled for dev/test use.",
    ),
    _FamilyASite(
        name="priority_engine",
        fn=evaluate_priority_engine_permission,
        missing=lambda c: f"Missing priority engine permission setting: {c}",
        invalid=lambda c, m: f"Invalid priority engine permission mode: {m}",
        disabled=lambda c: f"Priority engine permission is disabled: {c}",
        not_auto_write=lambda c: f"Priority engine permission is not enabled for dev/test use: {c}",
        success="Priority engine permission is explicitly enabled for dev/test use.",
    ),
    _FamilyASite(
        name="calendar_module",
        fn=evaluate_calendar_module_permission,
        missing=lambda c: f"Missing Calendar module permission setting: {c}",
        invalid=lambda c, m: f"Invalid Calendar module permission mode: {m}",
        disabled=lambda c: f"Calendar module permission is disabled: {c}",
        not_auto_write=lambda c: f"Calendar module permission is not enabled for dev/test use: {c}",
        success="Calendar module permission is explicitly enabled for dev/test use.",
    ),
    _FamilyASite(
        name="composer_module",
        fn=evaluate_composer_module_permission,
        missing=lambda c: f"Missing Composer module permission setting: {c}",
        invalid=lambda c, m: f"Invalid Composer module permission mode: {m}",
        disabled=lambda c: f"Composer module permission is disabled: {c}",
        not_auto_write=lambda c: f"Composer module permission is not enabled for dev/test use: {c}",
        success="Composer module permission is explicitly enabled for dev/test use.",
    ),
    _FamilyASite(
        name="briefing_loop",
        fn=evaluate_briefing_loop_permission,
        missing=lambda c: f"Missing briefing loop permission setting: {c}",
        invalid=lambda c, m: f"Invalid briefing loop permission mode: {m}",
        disabled=lambda c: f"Briefing loop permission is disabled: {c}",
        not_auto_write=lambda c: f"Briefing loop permission is not enabled for dev/test use: {c}",
        success="Briefing loop permission is explicitly enabled for dev/test use.",
    ),
    _FamilyASite(
        name="synthesis_import",
        fn=evaluate_synthesis_import_permission,
        missing=lambda c: f"Missing synthesis import permission setting: {c}",
        invalid=lambda c, m: f"Invalid synthesis import permission mode: {m}",
        disabled=lambda c: f"Synthesis import permission is disabled: {c}",
        not_auto_write=lambda c: f"Synthesis import permission is not enabled for dev/test use: {c}",
        success="Synthesis import permission is explicitly enabled for dev/test use.",
    ),
    _FamilyASite(
        name="synthesis_apply",
        fn=evaluate_synthesis_apply_permission,
        missing=lambda c: f"Missing synthesis apply permission setting: {c}",
        invalid=lambda c, m: f"Invalid synthesis apply permission mode: {m}",
        disabled=lambda c: f"Synthesis apply permission is disabled: {c}",
        not_auto_write=lambda c: f"Synthesis apply permission is not enabled for dev/test use: {c}",
        success="Synthesis apply permission is explicitly enabled for dev/test use.",
    ),
    _FamilyASite(
        name="side_effect_ledger",
        fn=evaluate_side_effect_ledger_permission,
        missing=lambda c: f"Missing side-effect ledger permission setting: {c}",
        invalid=lambda c, m: f"Invalid side-effect ledger permission mode: {m}",
        disabled=lambda c: f"Side-effect ledger permission is disabled: {c}",
        not_auto_write=lambda c: f"Side-effect ledger permission is not enabled for dev/test use: {c}",
        success="Side-effect ledger permission is explicitly enabled for dev/test use.",
        include_mode=False,
        include_setting=False,
    ),
    _FamilyASite(
        name="runtime_bootstrap",
        fn=evaluate_runtime_bootstrap_permission,
        missing=lambda c: f"Missing runtime bootstrap permission setting: {c}",
        invalid=lambda c, m: f"Invalid runtime bootstrap permission mode: {m}",
        disabled=lambda c: f"Runtime bootstrap permission is disabled: {c}",
        not_auto_write=lambda c: f"Runtime bootstrap permission is not enabled for dev/test use: {c}",
        success="Runtime bootstrap permission is explicitly enabled for dev/test use.",
    ),
]

_FAMILY_B_SITES: list[_FamilyBSite] = [
    _FamilyBSite(
        name="todoist_rail_live_write",
        fn=evaluate_todoist_rail_live_write_permission,
        category=TODOIST_RAIL_LIVE_WRITE_PERMISSION,
        missing=f"Missing permission setting: {TODOIST_RAIL_LIVE_WRITE_PERMISSION}",
        invalid=lambda m: f"Invalid permission mode: {m}",
        not_auto_write=lambda m: (
            "Todoist live-write rail permission is not auto_write "
            "(this dev/test simulated-write permission being enabled does not "
            f"count): {m}"
        ),
        success="Todoist live-write rail permission is explicitly set to auto_write.",
    ),
    _FamilyBSite(
        name="calendar_rail_live_write",
        fn=evaluate_calendar_rail_live_write_permission,
        category=CALENDAR_RAIL_LIVE_WRITE_PERMISSION,
        missing=f"Missing permission setting: {CALENDAR_RAIL_LIVE_WRITE_PERMISSION}",
        invalid=lambda m: f"Invalid permission mode: {m}",
        not_auto_write=lambda m: (
            "Calendar live-write rail permission is not auto_write "
            "(any other rail's or module's permission being enabled does not "
            f"count): {m}"
        ),
        success="Calendar live-write rail permission is explicitly set to auto_write.",
    ),
    _FamilyBSite(
        name="gmail_rail_live_send",
        fn=evaluate_gmail_rail_live_send_permission,
        category=GMAIL_RAIL_LIVE_SEND_PERMISSION,
        missing=f"Missing permission setting: {GMAIL_RAIL_LIVE_SEND_PERMISSION}",
        invalid=lambda m: f"Invalid permission mode: {m}",
        not_auto_write=lambda m: (
            "Gmail live-send rail permission is not auto_write "
            "(any other rail's or module's permission being enabled does not "
            f"count): {m}"
        ),
        success="Gmail live-send rail permission is explicitly set to auto_write.",
    ),
]


class PermissionEvaluatorEquivalenceTest(unittest.TestCase):
    """Asserts the current, real (post-migration) evaluators match hardcoded,
    independently-transcribed expected values for every branch of all 12
    sites -- see module docstring for why this is non-circular."""

    def _expected(
        self,
        *,
        allowed: bool,
        reason: str,
        category: str | None,
        mode: str | None,
        setting: dict[str, Any] | None,
        include_category: bool,
        include_mode: bool,
        include_setting: bool,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {"allowed": allowed}
        if include_category:
            result["category"] = category
        if include_mode:
            result["mode"] = mode
        result["reason"] = reason
        if include_setting:
            result["setting"] = setting
        return result

    def test_family_a_sites_across_full_branch_space(self) -> None:
        for site in _FAMILY_A_SITES:
            with self.subTest(site=site.name):
                with _migrated_test_connection() as connection:
                    category = f"{site.name}_equivalence_category"

                    # 1. missing setting
                    actual = site.fn(connection, category=category)
                    expected = self._expected(
                        allowed=False,
                        reason=site.missing(category),
                        category=category,
                        mode=None,
                        setting=None,
                        include_category=True,
                        include_mode=site.include_mode,
                        include_setting=site.include_setting,
                    )
                    self.assertEqual(expected, actual)

                    # 2. invalid mode string
                    _set(connection, category=category, mode="not_a_real_mode")
                    setting = get_permission_setting(connection, category)
                    actual = site.fn(connection, category=category)
                    expected = self._expected(
                        allowed=False,
                        reason=site.invalid(category, "not_a_real_mode"),
                        category=category,
                        mode="not_a_real_mode",
                        setting=setting,
                        include_category=True,
                        include_mode=site.include_mode,
                        include_setting=site.include_setting,
                    )
                    self.assertEqual(expected, actual)

                    # 3. disabled
                    _set(connection, category=category, mode=PermissionMode.DISABLED.value)
                    setting = get_permission_setting(connection, category)
                    actual = site.fn(connection, category=category)
                    expected = self._expected(
                        allowed=False,
                        reason=site.disabled(category),
                        category=category,
                        mode=PermissionMode.DISABLED.value,
                        setting=setting,
                        include_category=True,
                        include_mode=site.include_mode,
                        include_setting=site.include_setting,
                    )
                    self.assertEqual(expected, actual)

                    # 4. approval_required
                    _set(connection, category=category, mode=PermissionMode.APPROVAL_REQUIRED.value)
                    setting = get_permission_setting(connection, category)
                    actual = site.fn(connection, category=category)
                    expected = self._expected(
                        allowed=False,
                        reason=site.not_auto_write(category),
                        category=category,
                        mode=PermissionMode.APPROVAL_REQUIRED.value,
                        setting=setting,
                        include_category=True,
                        include_mode=site.include_mode,
                        include_setting=site.include_setting,
                    )
                    self.assertEqual(expected, actual)

                    # 5. auto_write
                    _set(connection, category=category, mode=PermissionMode.AUTO_WRITE.value)
                    setting = get_permission_setting(connection, category)
                    actual = site.fn(connection, category=category)
                    expected = self._expected(
                        allowed=True,
                        reason=site.success,
                        category=category,
                        mode=PermissionMode.AUTO_WRITE.value,
                        setting=setting,
                        include_category=True,
                        include_mode=site.include_mode,
                        include_setting=site.include_setting,
                    )
                    self.assertEqual(expected, actual)

    def test_family_b_sites_across_full_branch_space(self) -> None:
        for site in _FAMILY_B_SITES:
            with self.subTest(site=site.name):
                with _migrated_test_connection() as connection:
                    # 1. missing setting
                    actual = site.fn(connection)
                    expected = self._expected(
                        allowed=False,
                        reason=site.missing,
                        category=site.category,
                        mode=None,
                        setting=None,
                        include_category=True,
                        include_mode=True,
                        include_setting=True,
                    )
                    self.assertEqual(expected, actual)

                    # 2. invalid mode string
                    _set(connection, category=site.category, mode="not_a_real_mode")
                    setting = get_permission_setting(connection, site.category)
                    actual = site.fn(connection)
                    expected = self._expected(
                        allowed=False,
                        reason=site.invalid("not_a_real_mode"),
                        category=site.category,
                        mode="not_a_real_mode",
                        setting=setting,
                        include_category=True,
                        include_mode=True,
                        include_setting=True,
                    )
                    self.assertEqual(expected, actual)

                    # 3. disabled -- no separate branch; folds into not-auto-write
                    _set(connection, category=site.category, mode=PermissionMode.DISABLED.value)
                    setting = get_permission_setting(connection, site.category)
                    actual = site.fn(connection)
                    expected = self._expected(
                        allowed=False,
                        reason=site.not_auto_write(PermissionMode.DISABLED.value),
                        category=site.category,
                        mode=PermissionMode.DISABLED.value,
                        setting=setting,
                        include_category=True,
                        include_mode=True,
                        include_setting=True,
                    )
                    self.assertEqual(expected, actual)

                    # 4. approval_required -- also folds into not-auto-write
                    _set(connection, category=site.category, mode=PermissionMode.APPROVAL_REQUIRED.value)
                    setting = get_permission_setting(connection, site.category)
                    actual = site.fn(connection)
                    expected = self._expected(
                        allowed=False,
                        reason=site.not_auto_write(PermissionMode.APPROVAL_REQUIRED.value),
                        category=site.category,
                        mode=PermissionMode.APPROVAL_REQUIRED.value,
                        setting=setting,
                        include_category=True,
                        include_mode=True,
                        include_setting=True,
                    )
                    self.assertEqual(expected, actual)

                    # 5. auto_write
                    _set(connection, category=site.category, mode=PermissionMode.AUTO_WRITE.value)
                    setting = get_permission_setting(connection, site.category)
                    actual = site.fn(connection)
                    expected = self._expected(
                        allowed=True,
                        reason=site.success,
                        category=site.category,
                        mode=PermissionMode.AUTO_WRITE.value,
                        setting=setting,
                        include_category=True,
                        include_mode=True,
                        include_setting=True,
                    )
                    self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
