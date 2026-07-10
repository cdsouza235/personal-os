"""Wires tests/production_scheduler_kill_drill.py into the automated suite (P-SCHED-02).

The drill script is what a human runs by hand to verify the scheduler kill procedure
(governance/RUNBOOK.md's Scheduler kill-procedure line) still works; this test just makes
sure it stays green on every run of the suite. Loaded by file path (not package import)
since it's a standalone script, not a module of the `tests` package -- same pattern as
tests/test_todoist_kill_drill.py.
"""

import importlib.util
import sys
import unittest
from pathlib import Path

_SCRIPT_PATH = Path(__file__).resolve().parent / "production_scheduler_kill_drill.py"
_SPEC = importlib.util.spec_from_file_location("production_scheduler_kill_drill", _SCRIPT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
production_scheduler_kill_drill = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = production_scheduler_kill_drill
_SPEC.loader.exec_module(production_scheduler_kill_drill)


class ProductionSchedulerKillDrillTest(unittest.TestCase):
    def test_detection_logic_reports_job_present(self) -> None:
        result = production_scheduler_kill_drill.run_detection_present_drill()
        self.assertTrue(result.passed, msg="\n".join(result.details))

    def test_detection_logic_reports_job_absent_after_unload(self) -> None:
        result = production_scheduler_kill_drill.run_detection_absent_drill()
        self.assertTrue(result.passed, msg="\n".join(result.details))

    def test_plist_has_no_run_at_load_or_keep_alive(self) -> None:
        result = production_scheduler_kill_drill.run_plist_static_safety_drill()
        self.assertTrue(result.passed, msg="\n".join(result.details))


if __name__ == "__main__":
    unittest.main()
