#!/usr/bin/env python3
"""Scheduler LaunchAgent kill-drill (P-SCHED-02).

Proves two things about the "unload-proof" kill procedure for
`docs/com.personalos.morning.plist` (governance/RUNBOOK.md's Scheduler kill-procedure
line: `launchctl unload` the LaunchAgent, exact label recorded in the activation packet's
sign-off):

  1. Detection logic: given `launchctl list` output, can a human (or a script) correctly
     tell whether the job is currently loaded? Since HI-10 (Mac Mini launchd
     authorization) is still pending, nothing in this packet can load the real
     LaunchAgent to test this against real `launchctl` output -- so this drill proves the
     PARSING/DETECTION LOGIC is correct against fake/mocked `launchctl list` output, for
     both the "job present" and "job absent, cleanly unloaded" scenarios. This is the
     check a human runs for real (via the real `launchctl list` command) once the agent
     is actually loaded; this drill only proves the logic that check depends on.
  2. Static plist safety: the plist file's own content has no `RunAtLoad`/`KeepAlive`
     keys. Unlike (1), this IS a real, run-for-real check -- it just reads the plist file
     on disk, no mocking needed.

Safe to run any time, including by a human under incident pressure: it never touches the
network, never calls `launchctl` for real, never reads or requires a real credential, and
never touches the real production database. It does not require the caller to have set
PYTHONPATH -- it locates `src/` from its own path, exactly like tests/todoist_kill_drill.py.

Usage:
    python3 tests/production_scheduler_kill_drill.py

Exit code 0 means detection logic and plist static safety both check out; exit code 1
means something needs fixing BEFORE relying on this during a real incident.
"""

from __future__ import annotations

import plistlib
import sys
from dataclasses import dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _REPO_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

PLIST_LABEL = "com.personalos.morning"
PLIST_PATH = _REPO_ROOT / "docs" / "com.personalos.morning.plist"

# A realistic sample of `launchctl list` (no arguments) output: a header line, then one
# tab-separated row per loaded job (PID, last-exit-status, label). PID is "-" for a job
# that is loaded but not currently running.
_FAKE_LAUNCHCTL_LIST_HEADER = "PID\tStatus\tLabel"


@dataclass
class DrillResult:
    mechanism: str
    passed: bool
    details: list[str] = field(default_factory=list)


def is_job_loaded(launchctl_list_output: str, *, label: str) -> bool:
    """Parse `launchctl list` (no-argument, tab-separated table) output and report
    whether `label` appears as a loaded job. This is the logic a human runs for real via
    `launchctl list | grep <label>` (or the Python equivalent) once the agent is loaded;
    here it only ever sees fake/mocked output, proven correct on both branches below."""
    for line in launchctl_list_output.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("PID"):
            continue
        columns = line.split("\t")
        if len(columns) < 3:
            continue
        if columns[2].strip() == label:
            return True
    return False


def _fake_launchctl_list_with_job_present() -> str:
    return "\n".join(
        (
            _FAKE_LAUNCHCTL_LIST_HEADER,
            "1234\t0\tcom.apple.something.unrelated",
            f"-\t0\t{PLIST_LABEL}",
            "5678\t0\tcom.apple.another.unrelated",
        )
    )


def _fake_launchctl_list_with_job_absent() -> str:
    return "\n".join(
        (
            _FAKE_LAUNCHCTL_LIST_HEADER,
            "1234\t0\tcom.apple.something.unrelated",
            "5678\t0\tcom.apple.another.unrelated",
        )
    )


def run_detection_present_drill() -> DrillResult:
    """Kill-drill check 1a: the detection logic correctly reports the job as loaded when
    `launchctl list` output contains its label."""
    details: list[str] = []
    fake_output = _fake_launchctl_list_with_job_present()
    detected = is_job_loaded(fake_output, label=PLIST_LABEL)
    details.append(
        f"fake 'launchctl list' output containing {PLIST_LABEL!r}: "
        f"detected={detected} (expected True)"
    )
    return DrillResult(
        mechanism="detection_reports_job_present",
        passed=detected is True,
        details=details,
    )


def run_detection_absent_drill() -> DrillResult:
    """Kill-drill check 1b: the detection logic correctly reports the job as absent
    (cleanly unloaded) once `launchctl list` output no longer contains its label --
    exactly the state a real `launchctl unload` should produce."""
    details: list[str] = []
    fake_output = _fake_launchctl_list_with_job_absent()
    detected = is_job_loaded(fake_output, label=PLIST_LABEL)
    details.append(
        f"fake 'launchctl list' output WITHOUT {PLIST_LABEL!r} (post-unload state): "
        f"detected={detected} (expected False)"
    )
    return DrillResult(
        mechanism="detection_reports_job_absent_after_unload",
        passed=detected is False,
        details=details,
    )


def run_plist_static_safety_drill() -> DrillResult:
    """Kill-drill check 2: a REAL check (no mocking) that the plist file on disk has no
    `RunAtLoad`/`KeepAlive` keys, either of which would fight a clean `launchctl
    unload`."""
    details: list[str] = []
    if not PLIST_PATH.is_file():
        details.append(f"plist file not found at {PLIST_PATH}")
        return DrillResult(mechanism="plist_static_safety", passed=False, details=details)

    with PLIST_PATH.open("rb") as handle:
        data = plistlib.load(handle)

    label_ok = data.get("Label") == PLIST_LABEL
    details.append(f"Label={data.get('Label')!r} (expected {PLIST_LABEL!r}): {label_ok}")

    run_at_load_absent = "RunAtLoad" not in data
    details.append(f"RunAtLoad absent: {run_at_load_absent}")

    keep_alive_absent = "KeepAlive" not in data
    details.append(f"KeepAlive absent: {keep_alive_absent}")

    passed = label_ok and run_at_load_absent and keep_alive_absent
    return DrillResult(mechanism="plist_static_safety", passed=passed, details=details)


def run_all_drills() -> list[DrillResult]:
    return [
        run_detection_present_drill(),
        run_detection_absent_drill(),
        run_plist_static_safety_drill(),
    ]


def _print_report(results: list[DrillResult]) -> bool:
    print("Scheduler LaunchAgent kill-drill (P-SCHED-02)")
    print("=" * 60)
    all_passed = True
    for result in results:
        verdict = "PASS" if result.passed else "FAIL"
        if not result.passed:
            all_passed = False
        print(f"\n[{verdict}] check: {result.mechanism}")
        for line in result.details:
            print(f"    - {line}")
    print("\n" + "=" * 60)
    if all_passed:
        print(
            "PASS -- detection logic is correct on both branches, and the plist has no "
            "RunAtLoad/KeepAlive. This does NOT prove a real `launchctl unload` works "
            "against a real loaded job (HI-10 is still pending; nothing has been loaded "
            "for real). Once the agent is loaded for real, re-verify with the actual "
            "`launchctl list | grep com.personalos.morning` command before and after "
            "`launchctl unload com.personalos.morning`."
        )
    else:
        print("FAIL -- do not rely on this kill procedure until this is fixed.")
    return all_passed


def main() -> int:
    results = run_all_drills()
    all_passed = _print_report(results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
