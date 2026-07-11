"""Behavioral-equivalence proof for P-DEBT-01 (governance/ROADMAP.md Phase E).

Drives BOTH the still-present, not-yet-deleted old per-site
`evaluate_*_permission` function AND the new shared
`personalos.permissions.evaluate_auto_write_gate` control flow with
identical inputs across each site's full branch space (missing setting /
invalid mode / disabled [Family A only] / approval_required / auto_write),
and asserts the two decisions match exactly (same `allowed`, `reason`, and
result dict key set/values). This is the proof required by
audits/test-strategy.md Phase E -- "permission-evaluator unification proven
by behavioral equivalence tests (old-vs-new decision matrix) BEFORE
deletion of the copies" -- and it must be green before any of the 12/13
per-site copies are migrated to delegate to the shared function.

There are two families:

Family A -- module dev/test gates (10 sites): 4-branch logic (missing /
invalid / disabled / not-auto-write / auto-write), result dict includes
`category` (except side_effects.py's variant, which also omits `mode` and
`setting`).

Family B -- live rail gates (3 sites): single fixed category (not a
parameter), 3-branch logic (missing / invalid / not-auto-write -- disabled
is not distinguished from approval_required, both fall through to the
"not auto_write" branch), bespoke non-templated reason text per site.
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
from personalos.permissions import PermissionMode, evaluate_auto_write_gate
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
from personalos.state import upsert_permission_setting
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


class _FamilyASiteSpec:
    """One module dev/test gate site: 4-branch logic, `category` supplied by caller."""

    def __init__(
        self,
        *,
        name: str,
        old_fn: Callable[..., dict[str, Any]],
        missing_reason: Callable[[str], str],
        invalid_reason: Callable[[str, str], str],
        disabled_reason: Callable[[str], str],
        not_auto_write_reason: Callable[[str], str],
        success_reason: str,
        include_mode: bool = True,
        include_setting: bool = True,
    ) -> None:
        self.name = name
        self.old_fn = old_fn
        self.missing_reason = missing_reason
        self.invalid_reason = invalid_reason
        self.disabled_reason = disabled_reason
        self.not_auto_write_reason = not_auto_write_reason
        self.success_reason = success_reason
        self.include_mode = include_mode
        self.include_setting = include_setting

    def new_result(self, connection: sqlite3.Connection, *, category: str) -> dict[str, Any]:
        return evaluate_auto_write_gate(
            connection,
            category=category,
            missing_reason=lambda: self.missing_reason(category),
            invalid_reason=lambda raw_mode: self.invalid_reason(category, raw_mode),
            disabled_reason=lambda: self.disabled_reason(category),
            not_auto_write_reason=lambda _mode_value: self.not_auto_write_reason(category),
            success_reason=self.success_reason,
            include_mode=self.include_mode,
            include_setting=self.include_setting,
        )


class _FamilyBSiteSpec:
    """One live rail gate site: 3-branch logic, single fixed `category`."""

    def __init__(
        self,
        *,
        name: str,
        old_fn: Callable[[sqlite3.Connection], dict[str, Any]],
        category: str,
        not_auto_write_reason: Callable[[str], str],
        success_reason: str,
    ) -> None:
        self.name = name
        self.old_fn = old_fn
        self.category = category
        self.not_auto_write_reason = not_auto_write_reason
        self.success_reason = success_reason

    def new_result(self, connection: sqlite3.Connection) -> dict[str, Any]:
        return evaluate_auto_write_gate(
            connection,
            category=self.category,
            missing_reason=lambda: f"Missing permission setting: {self.category}",
            invalid_reason=lambda raw_mode: f"Invalid permission mode: {raw_mode}",
            disabled_reason=None,
            not_auto_write_reason=self.not_auto_write_reason,
            success_reason=self.success_reason,
        )


def _family_a_specs() -> list[_FamilyASiteSpec]:
    return [
        _FamilyASiteSpec(
            name="todoist_module",
            old_fn=evaluate_todoist_module_permission,
            missing_reason=lambda c: f"Missing Todoist module permission setting: {c}",
            invalid_reason=lambda c, m: f"Invalid Todoist module permission mode: {m}",
            disabled_reason=lambda c: f"Todoist module permission is disabled: {c}",
            not_auto_write_reason=lambda c: f"Todoist module permission is not enabled for dev/test use: {c}",
            success_reason="Todoist module permission is explicitly enabled for dev/test use.",
        ),
        _FamilyASiteSpec(
            name="routine_engine",
            old_fn=evaluate_routine_engine_permission,
            missing_reason=lambda c: f"Missing routine engine permission setting: {c}",
            invalid_reason=lambda c, m: f"Invalid routine engine permission mode: {m}",
            disabled_reason=lambda c: f"Routine engine permission is disabled: {c}",
            not_auto_write_reason=lambda c: f"Routine engine permission is not enabled for dev/test use: {c}",
            success_reason="Routine engine permission is explicitly enabled for dev/test use.",
        ),
        _FamilyASiteSpec(
            name="priority_engine",
            old_fn=evaluate_priority_engine_permission,
            missing_reason=lambda c: f"Missing priority engine permission setting: {c}",
            invalid_reason=lambda c, m: f"Invalid priority engine permission mode: {m}",
            disabled_reason=lambda c: f"Priority engine permission is disabled: {c}",
            not_auto_write_reason=lambda c: f"Priority engine permission is not enabled for dev/test use: {c}",
            success_reason="Priority engine permission is explicitly enabled for dev/test use.",
        ),
        _FamilyASiteSpec(
            name="calendar_module",
            old_fn=evaluate_calendar_module_permission,
            missing_reason=lambda c: f"Missing Calendar module permission setting: {c}",
            invalid_reason=lambda c, m: f"Invalid Calendar module permission mode: {m}",
            disabled_reason=lambda c: f"Calendar module permission is disabled: {c}",
            not_auto_write_reason=lambda c: f"Calendar module permission is not enabled for dev/test use: {c}",
            success_reason="Calendar module permission is explicitly enabled for dev/test use.",
        ),
        _FamilyASiteSpec(
            name="composer_module",
            old_fn=evaluate_composer_module_permission,
            missing_reason=lambda c: f"Missing Composer module permission setting: {c}",
            invalid_reason=lambda c, m: f"Invalid Composer module permission mode: {m}",
            disabled_reason=lambda c: f"Composer module permission is disabled: {c}",
            not_auto_write_reason=lambda c: f"Composer module permission is not enabled for dev/test use: {c}",
            success_reason="Composer module permission is explicitly enabled for dev/test use.",
        ),
        _FamilyASiteSpec(
            name="briefing_loop",
            old_fn=evaluate_briefing_loop_permission,
            missing_reason=lambda c: f"Missing briefing loop permission setting: {c}",
            invalid_reason=lambda c, m: f"Invalid briefing loop permission mode: {m}",
            disabled_reason=lambda c: f"Briefing loop permission is disabled: {c}",
            not_auto_write_reason=lambda c: f"Briefing loop permission is not enabled for dev/test use: {c}",
            success_reason="Briefing loop permission is explicitly enabled for dev/test use.",
        ),
        _FamilyASiteSpec(
            name="synthesis_import",
            old_fn=evaluate_synthesis_import_permission,
            missing_reason=lambda c: f"Missing synthesis import permission setting: {c}",
            invalid_reason=lambda c, m: f"Invalid synthesis import permission mode: {m}",
            disabled_reason=lambda c: f"Synthesis import permission is disabled: {c}",
            not_auto_write_reason=lambda c: f"Synthesis import permission is not enabled for dev/test use: {c}",
            success_reason="Synthesis import permission is explicitly enabled for dev/test use.",
        ),
        _FamilyASiteSpec(
            name="synthesis_apply",
            old_fn=evaluate_synthesis_apply_permission,
            missing_reason=lambda c: f"Missing synthesis apply permission setting: {c}",
            invalid_reason=lambda c, m: f"Invalid synthesis apply permission mode: {m}",
            disabled_reason=lambda c: f"Synthesis apply permission is disabled: {c}",
            not_auto_write_reason=lambda c: f"Synthesis apply permission is not enabled for dev/test use: {c}",
            success_reason="Synthesis apply permission is explicitly enabled for dev/test use.",
        ),
        _FamilyASiteSpec(
            name="side_effect_ledger",
            old_fn=evaluate_side_effect_ledger_permission,
            missing_reason=lambda c: f"Missing side-effect ledger permission setting: {c}",
            invalid_reason=lambda c, m: f"Invalid side-effect ledger permission mode: {m}",
            disabled_reason=lambda c: f"Side-effect ledger permission is disabled: {c}",
            not_auto_write_reason=lambda c: f"Side-effect ledger permission is not enabled for dev/test use: {c}",
            success_reason="Side-effect ledger permission is explicitly enabled for dev/test use.",
            include_mode=False,
            include_setting=False,
        ),
        _FamilyASiteSpec(
            name="runtime_bootstrap",
            old_fn=evaluate_runtime_bootstrap_permission,
            missing_reason=lambda c: f"Missing runtime bootstrap permission setting: {c}",
            invalid_reason=lambda c, m: f"Invalid runtime bootstrap permission mode: {m}",
            disabled_reason=lambda c: f"Runtime bootstrap permission is disabled: {c}",
            not_auto_write_reason=lambda c: f"Runtime bootstrap permission is not enabled for dev/test use: {c}",
            success_reason="Runtime bootstrap permission is explicitly enabled for dev/test use.",
        ),
    ]


def _family_b_specs() -> list[_FamilyBSiteSpec]:
    return [
        _FamilyBSiteSpec(
            name="todoist_rail_live_write",
            old_fn=evaluate_todoist_rail_live_write_permission,
            category=TODOIST_RAIL_LIVE_WRITE_PERMISSION,
            not_auto_write_reason=lambda m: (
                "Todoist live-write rail permission is not auto_write "
                "(this dev/test simulated-write permission being enabled does not "
                f"count): {m}"
            ),
            success_reason="Todoist live-write rail permission is explicitly set to auto_write.",
        ),
        _FamilyBSiteSpec(
            name="calendar_rail_live_write",
            old_fn=evaluate_calendar_rail_live_write_permission,
            category=CALENDAR_RAIL_LIVE_WRITE_PERMISSION,
            not_auto_write_reason=lambda m: (
                "Calendar live-write rail permission is not auto_write "
                "(any other rail's or module's permission being enabled does not "
                f"count): {m}"
            ),
            success_reason="Calendar live-write rail permission is explicitly set to auto_write.",
        ),
        _FamilyBSiteSpec(
            name="gmail_rail_live_send",
            old_fn=evaluate_gmail_rail_live_send_permission,
            category=GMAIL_RAIL_LIVE_SEND_PERMISSION,
            not_auto_write_reason=lambda m: (
                "Gmail live-send rail permission is not auto_write "
                "(any other rail's or module's permission being enabled does not "
                f"count): {m}"
            ),
            success_reason="Gmail live-send rail permission is explicitly set to auto_write.",
        ),
    ]


class PermissionEvaluatorEquivalenceTest(unittest.TestCase):
    def _assert_equivalent(self, old_result: dict[str, Any], new_result: dict[str, Any]) -> None:
        self.assertEqual(set(old_result.keys()), set(new_result.keys()))
        self.assertEqual(old_result["allowed"], new_result["allowed"])
        self.assertEqual(old_result["reason"], new_result["reason"])
        if "category" in old_result:
            self.assertEqual(old_result["category"], new_result["category"])
        if "mode" in old_result:
            self.assertEqual(old_result["mode"], new_result["mode"])
        if "setting" in old_result:
            self.assertEqual(old_result["setting"], new_result["setting"])

    def test_family_a_sites_across_full_branch_space(self) -> None:
        for spec in _family_a_specs():
            with self.subTest(site=spec.name):
                with _migrated_test_connection() as connection:
                    category = f"{spec.name}_equivalence_category"

                    old = spec.old_fn(connection, category=category)
                    new = spec.new_result(connection, category=category)
                    self._assert_equivalent(old, new)
                    self.assertFalse(old["allowed"], "missing setting must not be allowed")

                    _set(connection, category=category, mode="not_a_real_mode")
                    old = spec.old_fn(connection, category=category)
                    new = spec.new_result(connection, category=category)
                    self._assert_equivalent(old, new)
                    self.assertFalse(old["allowed"], "invalid mode must not be allowed")

                    _set(connection, category=category, mode=PermissionMode.DISABLED.value)
                    old = spec.old_fn(connection, category=category)
                    new = spec.new_result(connection, category=category)
                    self._assert_equivalent(old, new)
                    self.assertFalse(old["allowed"], "disabled must not be allowed")

                    _set(connection, category=category, mode=PermissionMode.APPROVAL_REQUIRED.value)
                    old = spec.old_fn(connection, category=category)
                    new = spec.new_result(connection, category=category)
                    self._assert_equivalent(old, new)
                    self.assertFalse(old["allowed"], "approval_required must not be allowed")

                    _set(connection, category=category, mode=PermissionMode.AUTO_WRITE.value)
                    old = spec.old_fn(connection, category=category)
                    new = spec.new_result(connection, category=category)
                    self._assert_equivalent(old, new)
                    self.assertTrue(old["allowed"], "auto_write must be allowed")

    def test_family_b_sites_across_full_branch_space(self) -> None:
        for spec in _family_b_specs():
            with self.subTest(site=spec.name):
                with _migrated_test_connection() as connection:
                    old = spec.old_fn(connection)
                    new = spec.new_result(connection)
                    self._assert_equivalent(old, new)
                    self.assertFalse(old["allowed"], "missing setting must not be allowed")

                    _set(connection, category=spec.category, mode="not_a_real_mode")
                    old = spec.old_fn(connection)
                    new = spec.new_result(connection)
                    self._assert_equivalent(old, new)
                    self.assertFalse(old["allowed"], "invalid mode must not be allowed")

                    _set(connection, category=spec.category, mode=PermissionMode.DISABLED.value)
                    old = spec.old_fn(connection)
                    new = spec.new_result(connection)
                    self._assert_equivalent(old, new)
                    self.assertFalse(
                        old["allowed"],
                        "disabled must not be allowed (folded into not-auto-write branch)",
                    )

                    _set(connection, category=spec.category, mode=PermissionMode.APPROVAL_REQUIRED.value)
                    old = spec.old_fn(connection)
                    new = spec.new_result(connection)
                    self._assert_equivalent(old, new)
                    self.assertFalse(old["allowed"], "approval_required must not be allowed")

                    _set(connection, category=spec.category, mode=PermissionMode.AUTO_WRITE.value)
                    old = spec.old_fn(connection)
                    new = spec.new_result(connection)
                    self._assert_equivalent(old, new)
                    self.assertTrue(old["allowed"], "auto_write must be allowed")


if __name__ == "__main__":
    unittest.main()
