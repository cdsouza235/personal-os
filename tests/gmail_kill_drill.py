#!/usr/bin/env python3
"""Gmail rail kill-drill (P-RAIL-GM-02).

Proves, by actually exercising the code paths, that all THREE kill mechanisms documented
in docs/GMAIL_KILL_PROCEDURE.md (which supplements the generic kill-procedure section in
governance/RUNBOOK.md) really do stop a live Gmail send. Gmail has one more independent
kill mechanism than Todoist (`tests/todoist_kill_drill.py` proves two): the controlled-
recipient env var is a fifth safety gate unique to this rail (see the "Recipient scoping"
section of `src/personalos/rails/gmail.py`'s module docstring), and removing/changing it
alone blocks the next send just as surely as the other two do.

  1. Flipping the rail state away from "live" (`status._RAIL_STATES["gmail"]`).
  2. Removing EITHER credential from the environment (sender address OR app password --
     `PERSONALOS_RAIL_GMAIL_SENDER_ADDRESS` / `PERSONALOS_RAIL_GMAIL_APP_PASSWORD`); this
     drill proves both independently since either one alone is sufficient.
  3. Removing (or changing) the controlled-recipient env var
     (`PERSONALOS_RAIL_GMAIL_CONTROLLED_RECIPIENT`) -- unique to Gmail, no Todoist
     equivalent.

Safe to run any time, including by a human under incident pressure: it never touches the
network (a fake client stands in for `GmailSmtpClient`), never reads or requires a real
Gmail credential or real email address (fixed placeholder strings are used throughout),
and never touches a real database (a throwaway sqlite file in a temp directory, deleted
on exit). It does not require the caller to have set PYTHONPATH -- it locates `src/` from
its own path.

Usage:
    python3 tests/gmail_kill_drill.py

Exit code 0 means all three kill mechanisms were proven to work; exit code 1 means at
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
from personalos.rails.gmail import (  # noqa: E402
    GMAIL_RAIL_APP_PASSWORD_ENV_VAR,
    GMAIL_RAIL_CONTROLLED_RECIPIENT_ENV_VAR,
    GMAIL_RAIL_LIVE_SEND_PERMISSION,
    GMAIL_RAIL_SENDER_ADDRESS_ENV_VAR,
    STATUS_BLOCKED_CREDENTIAL_MISSING,
    STATUS_BLOCKED_RAIL_STATE,
    STATUS_BLOCKED_RECIPIENT_NOT_CONTROLLED,
    STATUS_CLIENT_CALL_PASSED,
    send_live_gmail_message,
)
from personalos.state import upsert_permission_setting  # noqa: E402

# Never real credentials or a real email address -- fixed, obviously-fake placeholders,
# exactly like tests/test_rails_gmail.py's FAKE_SENDER_ADDRESS / FAKE_APP_PASSWORD /
# FAKE_CONTROLLED_RECIPIENT.
FAKE_SENDER_ADDRESS = "fake.kill-drill.sender@example.com"
FAKE_APP_PASSWORD = "fake-kill-drill-app-password-never-real"  # noqa: S105 - drill fixture, not a real credential
FAKE_CONTROLLED_RECIPIENT = "fake.kill-drill.recipient@example.com"

_FAKE_CREDENTIAL_ENV = {
    GMAIL_RAIL_SENDER_ADDRESS_ENV_VAR: FAKE_SENDER_ADDRESS,
    GMAIL_RAIL_APP_PASSWORD_ENV_VAR: FAKE_APP_PASSWORD,
    GMAIL_RAIL_CONTROLLED_RECIPIENT_ENV_VAR: FAKE_CONTROLLED_RECIPIENT,
}


class _FakeClient:
    """Stands in for GmailSmtpClient: no smtplib, no network, ever."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def send_message(self, *, sender, to_address, subject, body):
        self.calls.append(
            {"sender": sender, "to_address": to_address, "subject": subject, "body": body}
        )
        return {
            "status": STATUS_CLIENT_CALL_PASSED,
            "network_called": True,
            "external_mutation": True,
        }


@dataclass
class DrillResult:
    mechanism: str
    passed: bool
    details: list[str] = field(default_factory=list)


def _message_input(source_id: str) -> dict[str, object]:
    return {
        "source_type": "kill_drill",
        "source_id": source_id,
        "subject": f"Kill drill probe ({source_id})",
        "body": "Kill drill probe body -- never a real briefing.",
        "to_address": FAKE_CONTROLLED_RECIPIENT,
    }


def _set_auto_write_permission(connection: sqlite3.Connection) -> None:
    upsert_permission_setting(
        connection,
        category=GMAIL_RAIL_LIVE_SEND_PERMISSION,
        mode=PermissionMode.AUTO_WRITE.value,
        metadata={"packet": "P-RAIL-GM-02", "purpose": "kill_drill"},
        updated_by="gmail_kill_drill",
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
    """Kill mechanism 1: flip `status._RAIL_STATES["gmail"]` away from "live"."""
    details: list[str] = []
    with _drill_connection() as connection:
        _set_auto_write_permission(connection)
        client = _FakeClient()

        with mock.patch.dict(status._RAIL_STATES, {"gmail": "live"}):
            with mock.patch.dict(os.environ, _FAKE_CREDENTIAL_ENV):
                baseline = send_live_gmail_message(
                    connection, client=client, **_message_input("rail-state-baseline")
                )
                baseline_ok = baseline["status"] == STATUS_CLIENT_CALL_PASSED
                details.append(
                    f"baseline (rail=live, credentials+recipient present): "
                    f"status={baseline['status']!r} "
                    f"({'reached fake client' if baseline_ok else 'DID NOT reach fake client'})"
                )

                # Kill mechanism 1, applied mid-scenario, exactly as a human would do it by
                # hand: flip the rail's state key back off "live".
                status._RAIL_STATES["gmail"] = "inert"

                killed = send_live_gmail_message(
                    connection, client=client, **_message_input("rail-state-after-kill")
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


def run_sender_credential_removal_kill_drill() -> DrillResult:
    """Kill mechanism 2a: unset `PERSONALOS_RAIL_GMAIL_SENDER_ADDRESS`."""
    details: list[str] = []
    with _drill_connection() as connection:
        _set_auto_write_permission(connection)
        client = _FakeClient()

        with mock.patch.dict(status._RAIL_STATES, {"gmail": "live"}):
            with mock.patch.dict(os.environ, _FAKE_CREDENTIAL_ENV):
                baseline = send_live_gmail_message(
                    connection, client=client, **_message_input("sender-credential-baseline")
                )
                baseline_ok = baseline["status"] == STATUS_CLIENT_CALL_PASSED
                details.append(
                    f"baseline (rail=live, credentials+recipient present): "
                    f"status={baseline['status']!r} "
                    f"({'reached fake client' if baseline_ok else 'DID NOT reach fake client'})"
                )

                # Kill mechanism 2a, applied mid-scenario: remove ONLY the sender-address
                # credential from the environment, leave the app password in place, to
                # prove either credential alone is sufficient to kill the rail.
                os.environ.pop(GMAIL_RAIL_SENDER_ADDRESS_ENV_VAR, None)

                killed = send_live_gmail_message(
                    connection, client=client, **_message_input("sender-credential-after-kill")
                )
                killed_ok = killed["status"] == STATUS_BLOCKED_CREDENTIAL_MISSING
                details.append(
                    f"after kill (sender-address env var unset, app password still set): "
                    f"status={killed['status']!r} "
                    f"({'blocked as expected' if killed_ok else 'NOT BLOCKED -- kill failed'})"
                )

        calls_ok = len(client.calls) == 1
        details.append(
            f"fake client invocation count after kill attempt: {len(client.calls)} (expected 1)"
        )

    passed = baseline_ok and killed_ok and calls_ok
    return DrillResult(mechanism="sender_credential_removal", passed=passed, details=details)


def run_app_password_removal_kill_drill() -> DrillResult:
    """Kill mechanism 2b: unset `PERSONALOS_RAIL_GMAIL_APP_PASSWORD`."""
    details: list[str] = []
    with _drill_connection() as connection:
        _set_auto_write_permission(connection)
        client = _FakeClient()

        with mock.patch.dict(status._RAIL_STATES, {"gmail": "live"}):
            with mock.patch.dict(os.environ, _FAKE_CREDENTIAL_ENV):
                baseline = send_live_gmail_message(
                    connection, client=client, **_message_input("app-password-baseline")
                )
                baseline_ok = baseline["status"] == STATUS_CLIENT_CALL_PASSED
                details.append(
                    f"baseline (rail=live, credentials+recipient present): "
                    f"status={baseline['status']!r} "
                    f"({'reached fake client' if baseline_ok else 'DID NOT reach fake client'})"
                )

                # Kill mechanism 2b, applied mid-scenario: remove ONLY the app-password
                # credential, leave the sender address in place, to prove either
                # credential alone is sufficient to kill the rail.
                os.environ.pop(GMAIL_RAIL_APP_PASSWORD_ENV_VAR, None)

                killed = send_live_gmail_message(
                    connection, client=client, **_message_input("app-password-after-kill")
                )
                killed_ok = killed["status"] == STATUS_BLOCKED_CREDENTIAL_MISSING
                details.append(
                    f"after kill (app-password env var unset, sender address still set): "
                    f"status={killed['status']!r} "
                    f"({'blocked as expected' if killed_ok else 'NOT BLOCKED -- kill failed'})"
                )

        calls_ok = len(client.calls) == 1
        details.append(
            f"fake client invocation count after kill attempt: {len(client.calls)} (expected 1)"
        )

    passed = baseline_ok and killed_ok and calls_ok
    return DrillResult(mechanism="app_password_removal", passed=passed, details=details)


def run_controlled_recipient_removal_kill_drill() -> DrillResult:
    """Kill mechanism 3: unset (or change) `PERSONALOS_RAIL_GMAIL_CONTROLLED_RECIPIENT`.

    Unique to Gmail -- Todoist has no equivalent recipient-scoping gate. Proven here as
    its own independent mechanism because a human with access to only this one env var
    (e.g. via a secrets store that doesn't expose the other two) must still be able to
    kill the rail unilaterally.
    """
    details: list[str] = []
    with _drill_connection() as connection:
        _set_auto_write_permission(connection)
        client = _FakeClient()

        with mock.patch.dict(status._RAIL_STATES, {"gmail": "live"}):
            with mock.patch.dict(os.environ, _FAKE_CREDENTIAL_ENV):
                baseline = send_live_gmail_message(
                    connection, client=client, **_message_input("controlled-recipient-baseline")
                )
                baseline_ok = baseline["status"] == STATUS_CLIENT_CALL_PASSED
                details.append(
                    f"baseline (rail=live, credentials+recipient present): "
                    f"status={baseline['status']!r} "
                    f"({'reached fake client' if baseline_ok else 'DID NOT reach fake client'})"
                )

                # Kill mechanism 3, applied mid-scenario, exactly as a human would do it by
                # hand: remove the controlled-recipient env var from the environment.
                os.environ.pop(GMAIL_RAIL_CONTROLLED_RECIPIENT_ENV_VAR, None)

                killed = send_live_gmail_message(
                    connection,
                    client=client,
                    **_message_input("controlled-recipient-after-kill"),
                )
                killed_ok = killed["status"] == STATUS_BLOCKED_RECIPIENT_NOT_CONTROLLED
                details.append(
                    f"after kill (controlled-recipient env var unset): "
                    f"status={killed['status']!r} "
                    f"({'blocked as expected' if killed_ok else 'NOT BLOCKED -- kill failed'})"
                )

        calls_ok = len(client.calls) == 1
        details.append(
            f"fake client invocation count after kill attempt: {len(client.calls)} (expected 1)"
        )

    passed = baseline_ok and killed_ok and calls_ok
    return DrillResult(
        mechanism="controlled_recipient_removal", passed=passed, details=details
    )


def run_all_drills() -> list[DrillResult]:
    return [
        run_rail_state_kill_drill(),
        run_sender_credential_removal_kill_drill(),
        run_app_password_removal_kill_drill(),
        run_controlled_recipient_removal_kill_drill(),
    ]


def _print_report(results: list[DrillResult]) -> bool:
    print("Gmail rail kill-drill (P-RAIL-GM-02)")
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
            "PASS -- all four kill-drill scenarios (three independent mechanisms, with "
            "the credential mechanism proven for both env vars) blocked the next send "
            "attempt."
        )
    else:
        print(
            "FAIL -- at least one kill mechanism did NOT block the next send attempt. "
            "Do not rely on the RUNBOOK kill procedure until this is fixed."
        )
    return all_passed


def main() -> int:
    results = run_all_drills()
    all_passed = _print_report(results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
