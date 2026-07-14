#!/usr/bin/env python3
"""Calendar rail kill-drill (P-RAIL-CAL-02).

Proves, by actually exercising the code paths, that all FIVE kill mechanisms documented
in docs/CALENDAR_KILL_PROCEDURE.md (which supplements the generic kill-procedure section
in governance/RUNBOOK.md) really do stop a live Calendar event create. Calendar has one
more independent kill mechanism than Gmail (`tests/gmail_kill_drill.py` proves three): the
OAuth refresh-token flow needs THREE credential env vars instead of two, each of which
independently gates the call, plus the controlled-calendar-id env var is a fifth safety
gate unique to this rail (see the "Calendar-scoping" section of
`src/personalos/rails/calendar.py`'s module docstring), and removing/changing it alone
blocks the next create just as surely as the others do.

  1. Flipping the rail state away from "live" (`status._RAIL_STATES["calendar"]`).
  2. Removing `PERSONALOS_RAIL_CALENDAR_CLIENT_ID` from the environment (or setting it to
     an empty/whitespace-only value -- both sub-cases proven independently, since the gate
     returns a distinct status for each: `STATUS_BLOCKED_CREDENTIAL_MISSING` vs.
     `STATUS_BLOCKED_CREDENTIAL_EMPTY`).
  3. Removing `PERSONALOS_RAIL_CALENDAR_CLIENT_SECRET` from the environment (or setting it
     to an empty/whitespace-only value -- same two sub-cases as above).
  4. Removing `PERSONALOS_RAIL_CALENDAR_REFRESH_TOKEN` from the environment (or setting it
     to an empty/whitespace-only value -- same two sub-cases as above).
  5. Removing OR changing the controlled-calendar-id env var
     (`PERSONALOS_RAIL_CALENDAR_CONTROLLED_CALENDAR_ID`) -- unique to Calendar and
     Gmail-shaped rails, no Todoist equivalent. Both sub-cases (absence and mismatch) are
     proven independently, since the gate checks exact equality against the
     caller-supplied `calendar_id`, not just presence.

Safe to run any time, including by a human under incident pressure: it never touches the
network (a fake client stands in for `GoogleCalendarClient`), never reads or requires a
real Google OAuth credential or real calendar ID (fixed placeholder strings are used
throughout), and never touches a real database (a throwaway sqlite file in a temp
directory, deleted on exit). It does not require the caller to have set PYTHONPATH -- it
locates `src/` from its own path.

Usage:
    python3 tests/calendar_kill_drill.py

Exit code 0 means all five kill mechanisms were proven to work; exit code 1 means at
least one did not behave as expected and the RUNBOOK kill procedure needs to be
re-examined BEFORE relying on it during a real incident.
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
from personalos.rails.calendar import (  # noqa: E402
    CALENDAR_RAIL_CLIENT_ID_ENV_VAR,
    CALENDAR_RAIL_CLIENT_SECRET_ENV_VAR,
    CALENDAR_RAIL_CONTROLLED_CALENDAR_ID_ENV_VAR,
    CALENDAR_RAIL_LIVE_WRITE_PERMISSION,
    CALENDAR_RAIL_REFRESH_TOKEN_ENV_VAR,
    STATUS_BLOCKED_CALENDAR_NOT_CONTROLLED,
    STATUS_BLOCKED_CREDENTIAL_EMPTY,
    STATUS_BLOCKED_CREDENTIAL_MISSING,
    STATUS_BLOCKED_RAIL_STATE,
    STATUS_EVENT_CREATE_PASSED,
    STATUS_TOKEN_REFRESH_PASSED,
    create_live_calendar_event,
)
from personalos.state import upsert_permission_setting  # noqa: E402

# Never real credentials or a real calendar ID -- fixed, obviously-fake placeholders,
# exactly like tests/test_rails_calendar.py's FAKE_CLIENT_ID / FAKE_CLIENT_SECRET /
# FAKE_REFRESH_TOKEN / FAKE_CONTROLLED_CALENDAR_ID.
FAKE_CLIENT_ID = "fake-kill-drill-client-id-never-real"
FAKE_CLIENT_SECRET = "fake-kill-drill-client-secret-never-real"  # noqa: S105 - drill fixture, not a real credential
FAKE_REFRESH_TOKEN = "fake-kill-drill-refresh-token-never-real"  # noqa: S105 - drill fixture, not a real credential
FAKE_ACCESS_TOKEN = "fake-kill-drill-access-token-never-real"  # noqa: S105 - drill fixture, not a real credential
FAKE_CONTROLLED_CALENDAR_ID = "fake.kill-drill.calendar@group.calendar.google.com"

_FAKE_CREDENTIAL_ENV = {
    CALENDAR_RAIL_CLIENT_ID_ENV_VAR: FAKE_CLIENT_ID,
    CALENDAR_RAIL_CLIENT_SECRET_ENV_VAR: FAKE_CLIENT_SECRET,
    CALENDAR_RAIL_REFRESH_TOKEN_ENV_VAR: FAKE_REFRESH_TOKEN,
    CALENDAR_RAIL_CONTROLLED_CALENDAR_ID_ENV_VAR: FAKE_CONTROLLED_CALENDAR_ID,
}


class _FakeClient:
    """Stands in for GoogleCalendarClient: no urllib, no network, ever."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def refresh_access_token(self):
        return {
            "status": STATUS_TOKEN_REFRESH_PASSED,
            "network_called": True,
            "access_token": FAKE_ACCESS_TOKEN,
            "expires_in": 3599,
        }

    def create_event(self, *, access_token, event):
        self.calls.append({"access_token": access_token, "event": dict(event)})
        return {
            "status": STATUS_EVENT_CREATE_PASSED,
            "external_event_id": "fake-kill-drill-external-event-1",
            "network_called": True,
            "external_mutation": True,
        }


@dataclass
class DrillResult:
    mechanism: str
    passed: bool
    details: list[str] = field(default_factory=list)


def _event_input(source_id: str) -> dict[str, object]:
    return {
        "source_type": "kill_drill",
        "source_id": source_id,
        "summary": f"Kill drill probe ({source_id})",
        "description": "Kill drill probe event -- never a real briefing.",
        "start_time": "2026-07-13T09:00:00+00:00",
        "end_time": "2026-07-13T09:30:00+00:00",
        "calendar_id": FAKE_CONTROLLED_CALENDAR_ID,
    }


def _set_auto_write_permission(connection: sqlite3.Connection) -> None:
    upsert_permission_setting(
        connection,
        category=CALENDAR_RAIL_LIVE_WRITE_PERMISSION,
        mode=PermissionMode.AUTO_WRITE.value,
        metadata={"packet": "P-RAIL-CAL-02", "purpose": "kill_drill"},
        updated_by="calendar_kill_drill",
        updated_at_utc="2026-07-13T00:00:00+00:00",
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
    """Kill mechanism 1: flip `status._RAIL_STATES["calendar"]` away from "live"."""
    details: list[str] = []
    with _drill_connection() as connection:
        _set_auto_write_permission(connection)
        client = _FakeClient()

        with mock.patch.dict(status._RAIL_STATES, {"calendar": "live"}):
            with mock.patch.dict(os.environ, _FAKE_CREDENTIAL_ENV):
                baseline = create_live_calendar_event(
                    connection, client=client, **_event_input("rail-state-baseline")
                )
                baseline_ok = baseline["status"] == STATUS_EVENT_CREATE_PASSED
                details.append(
                    f"baseline (rail=live, credentials+calendar-id present): "
                    f"status={baseline['status']!r} "
                    f"({'reached fake client' if baseline_ok else 'DID NOT reach fake client'})"
                )

                # Kill mechanism 1, applied mid-scenario, exactly as a human would do it by
                # hand: flip the rail's state key back off "live".
                status._RAIL_STATES["calendar"] = "inert"

                killed = create_live_calendar_event(
                    connection, client=client, **_event_input("rail-state-after-kill")
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


def run_client_id_removal_kill_drill() -> DrillResult:
    """Kill mechanism 2: unset `PERSONALOS_RAIL_CALENDAR_CLIENT_ID`."""
    details: list[str] = []
    with _drill_connection() as connection:
        _set_auto_write_permission(connection)
        client = _FakeClient()

        with mock.patch.dict(status._RAIL_STATES, {"calendar": "live"}):
            with mock.patch.dict(os.environ, _FAKE_CREDENTIAL_ENV):
                baseline = create_live_calendar_event(
                    connection, client=client, **_event_input("client-id-baseline")
                )
                baseline_ok = baseline["status"] == STATUS_EVENT_CREATE_PASSED
                details.append(
                    f"baseline (rail=live, credentials+calendar-id present): "
                    f"status={baseline['status']!r} "
                    f"({'reached fake client' if baseline_ok else 'DID NOT reach fake client'})"
                )

                # Kill mechanism 2, applied mid-scenario: remove ONLY the client-id
                # credential from the environment, leave the other two in place, to prove
                # each credential alone is sufficient to kill the rail.
                os.environ.pop(CALENDAR_RAIL_CLIENT_ID_ENV_VAR, None)

                killed = create_live_calendar_event(
                    connection, client=client, **_event_input("client-id-after-kill")
                )
                killed_ok = killed["status"] == STATUS_BLOCKED_CREDENTIAL_MISSING
                details.append(
                    f"after kill (client-id env var unset, other credentials still set): "
                    f"status={killed['status']!r} "
                    f"({'blocked as expected' if killed_ok else 'NOT BLOCKED -- kill failed'})"
                )

        calls_ok = len(client.calls) == 1
        details.append(
            f"fake client invocation count after kill attempt: {len(client.calls)} (expected 1)"
        )

    passed = baseline_ok and killed_ok and calls_ok
    return DrillResult(mechanism="client_id_removal", passed=passed, details=details)


def run_client_secret_removal_kill_drill() -> DrillResult:
    """Kill mechanism 3: unset `PERSONALOS_RAIL_CALENDAR_CLIENT_SECRET`."""
    details: list[str] = []
    with _drill_connection() as connection:
        _set_auto_write_permission(connection)
        client = _FakeClient()

        with mock.patch.dict(status._RAIL_STATES, {"calendar": "live"}):
            with mock.patch.dict(os.environ, _FAKE_CREDENTIAL_ENV):
                baseline = create_live_calendar_event(
                    connection, client=client, **_event_input("client-secret-baseline")
                )
                baseline_ok = baseline["status"] == STATUS_EVENT_CREATE_PASSED
                details.append(
                    f"baseline (rail=live, credentials+calendar-id present): "
                    f"status={baseline['status']!r} "
                    f"({'reached fake client' if baseline_ok else 'DID NOT reach fake client'})"
                )

                # Kill mechanism 3, applied mid-scenario: remove ONLY the client-secret
                # credential, leave the other two in place, to prove each credential alone
                # is sufficient to kill the rail.
                os.environ.pop(CALENDAR_RAIL_CLIENT_SECRET_ENV_VAR, None)

                killed = create_live_calendar_event(
                    connection, client=client, **_event_input("client-secret-after-kill")
                )
                killed_ok = killed["status"] == STATUS_BLOCKED_CREDENTIAL_MISSING
                details.append(
                    f"after kill (client-secret env var unset, other credentials still set): "
                    f"status={killed['status']!r} "
                    f"({'blocked as expected' if killed_ok else 'NOT BLOCKED -- kill failed'})"
                )

        calls_ok = len(client.calls) == 1
        details.append(
            f"fake client invocation count after kill attempt: {len(client.calls)} (expected 1)"
        )

    passed = baseline_ok and killed_ok and calls_ok
    return DrillResult(mechanism="client_secret_removal", passed=passed, details=details)


def run_refresh_token_removal_kill_drill() -> DrillResult:
    """Kill mechanism 4: unset `PERSONALOS_RAIL_CALENDAR_REFRESH_TOKEN`."""
    details: list[str] = []
    with _drill_connection() as connection:
        _set_auto_write_permission(connection)
        client = _FakeClient()

        with mock.patch.dict(status._RAIL_STATES, {"calendar": "live"}):
            with mock.patch.dict(os.environ, _FAKE_CREDENTIAL_ENV):
                baseline = create_live_calendar_event(
                    connection, client=client, **_event_input("refresh-token-baseline")
                )
                baseline_ok = baseline["status"] == STATUS_EVENT_CREATE_PASSED
                details.append(
                    f"baseline (rail=live, credentials+calendar-id present): "
                    f"status={baseline['status']!r} "
                    f"({'reached fake client' if baseline_ok else 'DID NOT reach fake client'})"
                )

                # Kill mechanism 4, applied mid-scenario: remove ONLY the refresh-token
                # credential, leave the other two in place, to prove each credential alone
                # is sufficient to kill the rail.
                os.environ.pop(CALENDAR_RAIL_REFRESH_TOKEN_ENV_VAR, None)

                killed = create_live_calendar_event(
                    connection, client=client, **_event_input("refresh-token-after-kill")
                )
                killed_ok = killed["status"] == STATUS_BLOCKED_CREDENTIAL_MISSING
                details.append(
                    f"after kill (refresh-token env var unset, other credentials still set): "
                    f"status={killed['status']!r} "
                    f"({'blocked as expected' if killed_ok else 'NOT BLOCKED -- kill failed'})"
                )

        calls_ok = len(client.calls) == 1
        details.append(
            f"fake client invocation count after kill attempt: {len(client.calls)} (expected 1)"
        )

    passed = baseline_ok and killed_ok and calls_ok
    return DrillResult(mechanism="refresh_token_removal", passed=passed, details=details)


def run_client_id_empty_value_kill_drill() -> DrillResult:
    """Kill mechanism 2b: set `PERSONALOS_RAIL_CALENDAR_CLIENT_ID` to an
    empty/whitespace-only value rather than removing it.

    Distinct from `run_client_id_removal_kill_drill`, which only proves the env var's
    ABSENCE blocks the write. The gate checks `not value.strip()` separately from
    presence and returns a different status (`STATUS_BLOCKED_CREDENTIAL_EMPTY` instead
    of `STATUS_BLOCKED_CREDENTIAL_MISSING`), so a regression that broke the
    empty-value check specifically (while leaving the missing-value check intact)
    would otherwise pass undetected.
    """
    details: list[str] = []
    empty_env = dict(_FAKE_CREDENTIAL_ENV)
    empty_env[CALENDAR_RAIL_CLIENT_ID_ENV_VAR] = "   "

    with _drill_connection() as connection:
        _set_auto_write_permission(connection)
        client = _FakeClient()

        with mock.patch.dict(status._RAIL_STATES, {"calendar": "live"}):
            with mock.patch.dict(os.environ, _FAKE_CREDENTIAL_ENV):
                baseline = create_live_calendar_event(
                    connection, client=client, **_event_input("client-id-empty-baseline")
                )
                baseline_ok = baseline["status"] == STATUS_EVENT_CREATE_PASSED
                details.append(
                    f"baseline (rail=live, credentials+calendar-id present): "
                    f"status={baseline['status']!r} "
                    f"({'reached fake client' if baseline_ok else 'DID NOT reach fake client'})"
                )

            # Kill mechanism 2b, applied mid-scenario: set the client-id env var to a
            # whitespace-only value rather than removing it, to prove emptiness alone
            # (not just absence) blocks the write.
            with mock.patch.dict(os.environ, empty_env):
                killed = create_live_calendar_event(
                    connection, client=client, **_event_input("client-id-empty-after-kill")
                )
                killed_ok = killed["status"] == STATUS_BLOCKED_CREDENTIAL_EMPTY
                details.append(
                    f"after kill (client-id env var set to whitespace-only value): "
                    f"status={killed['status']!r} "
                    f"({'blocked as expected' if killed_ok else 'NOT BLOCKED -- kill failed'})"
                )

        calls_ok = len(client.calls) == 1
        details.append(
            f"fake client invocation count after kill attempt: {len(client.calls)} (expected 1)"
        )

    passed = baseline_ok and killed_ok and calls_ok
    return DrillResult(mechanism="client_id_empty_value", passed=passed, details=details)


def run_client_secret_empty_value_kill_drill() -> DrillResult:
    """Kill mechanism 3b: set `PERSONALOS_RAIL_CALENDAR_CLIENT_SECRET` to an
    empty/whitespace-only value rather than removing it (same rationale as
    `run_client_id_empty_value_kill_drill`)."""
    details: list[str] = []
    empty_env = dict(_FAKE_CREDENTIAL_ENV)
    empty_env[CALENDAR_RAIL_CLIENT_SECRET_ENV_VAR] = "   "

    with _drill_connection() as connection:
        _set_auto_write_permission(connection)
        client = _FakeClient()

        with mock.patch.dict(status._RAIL_STATES, {"calendar": "live"}):
            with mock.patch.dict(os.environ, _FAKE_CREDENTIAL_ENV):
                baseline = create_live_calendar_event(
                    connection, client=client, **_event_input("client-secret-empty-baseline")
                )
                baseline_ok = baseline["status"] == STATUS_EVENT_CREATE_PASSED
                details.append(
                    f"baseline (rail=live, credentials+calendar-id present): "
                    f"status={baseline['status']!r} "
                    f"({'reached fake client' if baseline_ok else 'DID NOT reach fake client'})"
                )

            # Kill mechanism 3b, applied mid-scenario: set the client-secret env var to
            # a whitespace-only value rather than removing it.
            with mock.patch.dict(os.environ, empty_env):
                killed = create_live_calendar_event(
                    connection, client=client, **_event_input("client-secret-empty-after-kill")
                )
                killed_ok = killed["status"] == STATUS_BLOCKED_CREDENTIAL_EMPTY
                details.append(
                    f"after kill (client-secret env var set to whitespace-only value): "
                    f"status={killed['status']!r} "
                    f"({'blocked as expected' if killed_ok else 'NOT BLOCKED -- kill failed'})"
                )

        calls_ok = len(client.calls) == 1
        details.append(
            f"fake client invocation count after kill attempt: {len(client.calls)} (expected 1)"
        )

    passed = baseline_ok and killed_ok and calls_ok
    return DrillResult(mechanism="client_secret_empty_value", passed=passed, details=details)


def run_refresh_token_empty_value_kill_drill() -> DrillResult:
    """Kill mechanism 4b: set `PERSONALOS_RAIL_CALENDAR_REFRESH_TOKEN` to an
    empty/whitespace-only value rather than removing it (same rationale as
    `run_client_id_empty_value_kill_drill`)."""
    details: list[str] = []
    empty_env = dict(_FAKE_CREDENTIAL_ENV)
    empty_env[CALENDAR_RAIL_REFRESH_TOKEN_ENV_VAR] = "   "

    with _drill_connection() as connection:
        _set_auto_write_permission(connection)
        client = _FakeClient()

        with mock.patch.dict(status._RAIL_STATES, {"calendar": "live"}):
            with mock.patch.dict(os.environ, _FAKE_CREDENTIAL_ENV):
                baseline = create_live_calendar_event(
                    connection, client=client, **_event_input("refresh-token-empty-baseline")
                )
                baseline_ok = baseline["status"] == STATUS_EVENT_CREATE_PASSED
                details.append(
                    f"baseline (rail=live, credentials+calendar-id present): "
                    f"status={baseline['status']!r} "
                    f"({'reached fake client' if baseline_ok else 'DID NOT reach fake client'})"
                )

            # Kill mechanism 4b, applied mid-scenario: set the refresh-token env var to
            # a whitespace-only value rather than removing it.
            with mock.patch.dict(os.environ, empty_env):
                killed = create_live_calendar_event(
                    connection, client=client, **_event_input("refresh-token-empty-after-kill")
                )
                killed_ok = killed["status"] == STATUS_BLOCKED_CREDENTIAL_EMPTY
                details.append(
                    f"after kill (refresh-token env var set to whitespace-only value): "
                    f"status={killed['status']!r} "
                    f"({'blocked as expected' if killed_ok else 'NOT BLOCKED -- kill failed'})"
                )

        calls_ok = len(client.calls) == 1
        details.append(
            f"fake client invocation count after kill attempt: {len(client.calls)} (expected 1)"
        )

    passed = baseline_ok and killed_ok and calls_ok
    return DrillResult(mechanism="refresh_token_empty_value", passed=passed, details=details)


def run_controlled_calendar_id_removal_kill_drill() -> DrillResult:
    """Kill mechanism 5: unset (or change) `PERSONALOS_RAIL_CALENDAR_CONTROLLED_CALENDAR_ID`.

    Unique to Calendar (and Gmail-shaped rails) -- Todoist has no equivalent scoping gate.
    Proven here as its own independent mechanism because a human with access to only this
    one env var (e.g. via a secrets store that doesn't expose the other three) must still
    be able to kill the rail unilaterally.
    """
    details: list[str] = []
    with _drill_connection() as connection:
        _set_auto_write_permission(connection)
        client = _FakeClient()

        with mock.patch.dict(status._RAIL_STATES, {"calendar": "live"}):
            with mock.patch.dict(os.environ, _FAKE_CREDENTIAL_ENV):
                baseline = create_live_calendar_event(
                    connection,
                    client=client,
                    **_event_input("controlled-calendar-id-baseline"),
                )
                baseline_ok = baseline["status"] == STATUS_EVENT_CREATE_PASSED
                details.append(
                    f"baseline (rail=live, credentials+calendar-id present): "
                    f"status={baseline['status']!r} "
                    f"({'reached fake client' if baseline_ok else 'DID NOT reach fake client'})"
                )

                # Kill mechanism 5, applied mid-scenario, exactly as a human would do it by
                # hand: remove the controlled-calendar-id env var from the environment.
                os.environ.pop(CALENDAR_RAIL_CONTROLLED_CALENDAR_ID_ENV_VAR, None)

                killed = create_live_calendar_event(
                    connection,
                    client=client,
                    **_event_input("controlled-calendar-id-after-kill"),
                )
                killed_ok = killed["status"] == STATUS_BLOCKED_CALENDAR_NOT_CONTROLLED
                details.append(
                    f"after kill (controlled-calendar-id env var unset): "
                    f"status={killed['status']!r} "
                    f"({'blocked as expected' if killed_ok else 'NOT BLOCKED -- kill failed'})"
                )

        calls_ok = len(client.calls) == 1
        details.append(
            f"fake client invocation count after kill attempt: {len(client.calls)} (expected 1)"
        )

    passed = baseline_ok and killed_ok and calls_ok
    return DrillResult(
        mechanism="controlled_calendar_id_removal", passed=passed, details=details
    )


def run_controlled_calendar_id_mismatch_kill_drill() -> DrillResult:
    """Kill mechanism 5b: change `PERSONALOS_RAIL_CALENDAR_CONTROLLED_CALENDAR_ID` to a
    value that does not match the caller-supplied `calendar_id`.

    Distinct from `run_controlled_calendar_id_removal_kill_drill`, which only proves the
    env var's ABSENCE blocks the write. The gate checks exact equality against the
    caller-supplied `calendar_id`, not just presence, so a MISMATCH must be proven as its
    own scenario -- a regression that broke the equality check specifically (while leaving
    absence-handling intact) would otherwise pass undetected.
    """
    details: list[str] = []
    mismatched_env = dict(_FAKE_CREDENTIAL_ENV)
    mismatched_env[CALENDAR_RAIL_CONTROLLED_CALENDAR_ID_ENV_VAR] = (
        "uncontrolled.other-calendar@group.calendar.google.com"
    )

    with _drill_connection() as connection:
        _set_auto_write_permission(connection)
        client = _FakeClient()

        with mock.patch.dict(status._RAIL_STATES, {"calendar": "live"}):
            with mock.patch.dict(os.environ, _FAKE_CREDENTIAL_ENV):
                baseline = create_live_calendar_event(
                    connection,
                    client=client,
                    **_event_input("controlled-calendar-id-mismatch-baseline"),
                )
                baseline_ok = baseline["status"] == STATUS_EVENT_CREATE_PASSED
                details.append(
                    f"baseline (rail=live, credentials+calendar-id present and matching): "
                    f"status={baseline['status']!r} "
                    f"({'reached fake client' if baseline_ok else 'DID NOT reach fake client'})"
                )

            # Kill mechanism 5b, applied mid-scenario: change the controlled-calendar-id
            # env var to a DIFFERENT calendar than the one the caller supplies, rather
            # than removing it, to prove mismatch alone (not just absence) blocks the
            # write.
            with mock.patch.dict(os.environ, mismatched_env):
                killed = create_live_calendar_event(
                    connection,
                    client=client,
                    **_event_input("controlled-calendar-id-mismatch-after-kill"),
                )
                killed_ok = killed["status"] == STATUS_BLOCKED_CALENDAR_NOT_CONTROLLED
                details.append(
                    f"after kill (controlled-calendar-id env var set to a different, "
                    f"non-matching calendar): status={killed['status']!r} "
                    f"({'blocked as expected' if killed_ok else 'NOT BLOCKED -- kill failed'})"
                )

        calls_ok = len(client.calls) == 1
        details.append(
            f"fake client invocation count after kill attempt: {len(client.calls)} (expected 1)"
        )

    passed = baseline_ok and killed_ok and calls_ok
    return DrillResult(
        mechanism="controlled_calendar_id_mismatch", passed=passed, details=details
    )


def run_all_drills() -> list[DrillResult]:
    return [
        run_rail_state_kill_drill(),
        run_client_id_removal_kill_drill(),
        run_client_id_empty_value_kill_drill(),
        run_client_secret_removal_kill_drill(),
        run_client_secret_empty_value_kill_drill(),
        run_refresh_token_removal_kill_drill(),
        run_refresh_token_empty_value_kill_drill(),
        run_controlled_calendar_id_removal_kill_drill(),
        run_controlled_calendar_id_mismatch_kill_drill(),
    ]


def _print_report(results: list[DrillResult]) -> bool:
    print("Calendar rail kill-drill (P-RAIL-CAL-02)")
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
        print(
            "PASS -- all nine kill-drill scenarios (five independent mechanisms: rail "
            "state; each of three credentials, proven via both its removal and "
            "empty-value sub-cases; and controlled-calendar-id, proven via both its "
            "removal and mismatch sub-cases) blocked the next create attempt."
        )
    else:
        print(
            "FAIL -- at least one kill mechanism did NOT block the next create attempt. "
            "Do not rely on the RUNBOOK kill procedure until this is fixed."
        )
    return all_passed


def main() -> int:
    results = run_all_drills()
    all_passed = _print_report(results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
