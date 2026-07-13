"""Wires tests/calendar_kill_drill.py into the automated suite (P-RAIL-CAL-02).

The drill script is the artifact a human runs by hand during a real incident to verify
the kill procedure still works; this test just makes sure it stays green on every
run of the suite, so a regression in any of the five kill mechanisms is caught before it
ever matters. Loaded by file path (not package import) since it's a standalone script, not
a module of the `tests` package -- same pattern as `tests/test_gmail_kill_drill.py`.
"""

import importlib.util
import sys
import unittest
from pathlib import Path

_SCRIPT_PATH = Path(__file__).resolve().parent / "calendar_kill_drill.py"
_SPEC = importlib.util.spec_from_file_location("calendar_kill_drill", _SCRIPT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
calendar_kill_drill = importlib.util.module_from_spec(_SPEC)
# dataclass field resolution needs the module registered in sys.modules before exec.
sys.modules[_SPEC.name] = calendar_kill_drill
_SPEC.loader.exec_module(calendar_kill_drill)


class CalendarKillDrillTest(unittest.TestCase):
    def test_rail_state_flip_kill_mechanism_blocks_next_create(self) -> None:
        result = calendar_kill_drill.run_rail_state_kill_drill()
        self.assertTrue(result.passed, msg="\n".join(result.details))

    def test_client_id_removal_kill_mechanism_blocks_next_create(self) -> None:
        result = calendar_kill_drill.run_client_id_removal_kill_drill()
        self.assertTrue(result.passed, msg="\n".join(result.details))

    def test_client_secret_removal_kill_mechanism_blocks_next_create(self) -> None:
        result = calendar_kill_drill.run_client_secret_removal_kill_drill()
        self.assertTrue(result.passed, msg="\n".join(result.details))

    def test_refresh_token_removal_kill_mechanism_blocks_next_create(self) -> None:
        result = calendar_kill_drill.run_refresh_token_removal_kill_drill()
        self.assertTrue(result.passed, msg="\n".join(result.details))

    def test_controlled_calendar_id_removal_kill_mechanism_blocks_next_create(self) -> None:
        result = calendar_kill_drill.run_controlled_calendar_id_removal_kill_drill()
        self.assertTrue(result.passed, msg="\n".join(result.details))


if __name__ == "__main__":
    unittest.main()
