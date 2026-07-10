#!/usr/bin/env python3
"""Todoist rail kill-drill (P-RAIL-TD-02).

Proves, by actually exercising the code paths, that BOTH kill mechanisms documented in
docs/TODOIST_KILL_PROCEDURE.md (which supplements the generic kill-procedure section in
governance/RUNBOOK.md) really do stop a live Todoist write:

  1. Flipping the rail state away from "live" (`status._RAIL_STATES["todoist"]`).
  2. Removing the credential from the environment (`PERSONALOS_RAIL_TODOIST_TOKEN`).

Safe to run any time, including by a human under incident pressure: it never touches the
network (a fake client stands in for `TodoistRailClient`), never reads or requires a real
Todoist credential (a fixed placeholder string is used), and never touches a real database
(a throwaway sqlite file in a temp directory, deleted on exit). It does not require the
caller to have set PYTHONPATH -- it locates `src/` from its own path.

Usage:
    python3 tests/todoist_kill_drill.py

Exit code 0 means both kill mechanisms were proven to work; exit code 1 means at least one
did not behave as expected and the RUNBOOK kill procedure needs to be re-examined BEFORE
relying on it during a real incident.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _REPO_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from personalos import status  # noqa: E402
from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig  # noqa: E402
from personalos.db.connection import connect_sqlite  # noqa: E402
from personalos.db.migrations import apply_migrations  # noqa: E402
from personalos.permissions import PermissionMode  # noqa: E402
from personalos.rails.todoist import (  # noqa: E402
    STATUS_BLOCKED_CREDENTIAL_MISSING,
    STATUS_BLOCKED_RAIL_STATE,
    STATUS_CLIENT_CALL_PASSED,
    TODOIST_RAIL_CREDENTIAL_ENV_VAR,
    TODOIST_RAIL_LIVE_WRITE_PERMISSION,
    create_live_todoist_task,
)
from personalos.state import upsert_permission_setting  # noqa: E402

# Never a real credential -- a fixed, obviously-fake placeholder, exactly like
# tests/test_rails_todoist.py's FAKE_TOKEN.
FAKE_TOKEN = "fake-kill-drill-token-never-real"  # noqa: S105 - drill fixture, not a real credential


class _FakeClient:
    """Stands in for TodoistRailClient: no urllib, no network, ever."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create_task(self, payload):
        self.calls.append(dict(payload))
        return {
            "status": STATUS_CLIENT_CALL_PASSED,
            "external_task_id": "fake-kill-drill-external-id",
            "network_called": True,
            "external_mutation": True,
        }


@dataclass
class DrillResult:
    mechanism: str
    passed: bool
    details: list[str] = field(default_factory=list)


def _task_input(source_id: str) -> dict[str, object]:
    return {
        "task_title": f"Kill drill probe ({source_id})",
        "description": "",
        "source_type": "kill_drill",
        "source_id": source_id,
        "project": "Inbox",
        "labels": [],
        "due_date_or_due_string": "",
        "priority": 2,
    }


def _set_auto_write_permission(connection: sqlite3.Connection) -> None:
    upsert_permission_setting(
        connection,
        category=TODOIST_RAIL_LIVE_WRITE_PERMISSION,
        mode=PermissionMode.AUTO_WRITE.value,
        metadata={"packet": "P-RAIL-TD-02", "purpose": "kill_drill"},
        updated_by="todoist_kill_drill",
        updated_at_utc="2026-07-10T00:00:00+00:00",
    )


@contextmanager
def _drill_connection() -> Iterator[sqlite3.Connection]:
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


def run_rail_state_kill_drill() -> DrillResult:
    """Kill mechanism 1: flip `status._RAIL_STATES["todoist"]` away from "live"."""
    details: list[str] = []
    with _drill_connection() as connection:
        _set_auto_write_permission(connection)
        client = _FakeClient()

        with mock.patch.dict(status._RAIL_STATES, {"todoist": "live"}):
            with mock.patch.dict(os.environ, {TODOIST_RAIL_CREDENTIAL_ENV_VAR: FAKE_TOKEN}):
                baseline = create_live_todoist_task(
                    connection, client=client, **_task_input("rail-state-baseline")
                )
                baseline_ok = baseline["status"] == STATUS_CLIENT_CALL_PASSED
                details.append(
                    f"baseline (rail=live, credential=present): status={baseline['status']!r} "
                    f"({'reached fake client' if baseline_ok else 'DID NOT reach fake client'})"
                )

                # Kill mechanism 1, applied mid-scenario, exactly as a human would do it by
                # hand: flip the rail's state key back off "live".
                status._RAIL_STATES["todoist"] = "inert"

                killed = create_live_todoist_task(
                    connection, client=client, **_task_input("rail-state-after-kill")
                )
                killed_ok = killed["status"] == STATUS_BLOCKED_RAIL_STATE
                details.append(
                    f"after kill (rail flipped to 'inert'): status={killed['status']!r} "
                    f"({'blocked as expected' if killed_ok else 'NOT BLOCKED -- kill failed'})"
                )

        calls_ok = len(client.calls) == 1
        details.append(
            f"fake client invocation count after kill attempt: {len(client.calls)} (expected 1)"
        )

    passed = baseline_ok and killed_ok and calls_ok
    return DrillResult(mechanism="rail_state_flip", passed=passed, details=details)


def run_credential_removal_kill_drill() -> DrillResult:
    """Kill mechanism 2: unset `PERSONALOS_RAIL_TODOIST_TOKEN` from the environment."""
    details: list[str] = []
    with _drill_connection() as connection:
        _set_auto_write_permission(connection)
        client = _FakeClient()

        with mock.patch.dict(status._RAIL_STATES, {"todoist": "live"}):
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ[TODOIST_RAIL_CREDENTIAL_ENV_VAR] = FAKE_TOKEN

                baseline = create_live_todoist_task(
                    connection, client=client, **_task_input("credential-baseline")
                )
                baseline_ok = baseline["status"] == STATUS_CLIENT_CALL_PASSED
                details.append(
                    f"baseline (rail=live, credential=present): status={baseline['status']!r} "
                    f"({'reached fake client' if baseline_ok else 'DID NOT reach fake client'})"
                )

                # Kill mechanism 2, applied mid-scenario, exactly as a human would do it by
                # hand: remove the credential from the environment.
                os.environ.pop(TODOIST_RAIL_CREDENTIAL_ENV_VAR, None)

                killed = create_live_todoist_task(
                    connection, client=client, **_task_input("credential-after-kill")
                )
                killed_ok = killed["status"] == STATUS_BLOCKED_CREDENTIAL_MISSING
                details.append(
                    f"after kill (credential env var unset): status={killed['status']!r} "
                    f"({'blocked as expected' if killed_ok else 'NOT BLOCKED -- kill failed'})"
                )

        calls_ok = len(client.calls) == 1
        details.append(
            f"fake client invocation count after kill attempt: {len(client.calls)} (expected 1)"
        )

    passed = baseline_ok and killed_ok and calls_ok
    return DrillResult(mechanism="credential_removal", passed=passed, details=details)


def run_all_drills() -> list[DrillResult]:
    return [run_rail_state_kill_drill(), run_credential_removal_kill_drill()]


def _print_report(results: list[DrillResult]) -> bool:
    print("Todoist rail kill-drill (P-RAIL-TD-02)")
    print("=" * 60)
    all_passed = True
    for result in results:
        verdict = "PASS" if result.passed else "FAIL"
        if not result.passed:
            all_passed = False
        print(f"\n[{verdict}] kill mechanism: {result.mechanism}")
        for line in result.details:
            print(f"    - {line}")
    print("\n" + "=" * 60)
    if all_passed:
        print("PASS -- both kill mechanisms blocked the next write attempt.")
    else:
        print(
            "FAIL -- at least one kill mechanism did NOT block the next write attempt. "
            "Do not rely on the RUNBOOK kill procedure until this is fixed."
        )
    return all_passed


def main() -> int:
    results = run_all_drills()
    all_passed = _print_report(results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
