"""Wires tests/todoist_kill_drill.py into the automated suite (P-RAIL-TD-02).

The drill script is the artifact a human runs by hand during a real incident to verify
the kill procedure still works; this test just makes sure it stays green on every
run of the suite, so a regression in either kill mechanism is caught before it ever
matters. Loaded by file path (not package import) since it's a standalone script, not a
module of the `tests` package.
"""

import importlib.util
import sys
import unittest
from pathlib import Path

_SCRIPT_PATH = Path(__file__).resolve().parent / "todoist_kill_drill.py"
_SPEC = importlib.util.spec_from_file_location("todoist_kill_drill", _SCRIPT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
todoist_kill_drill = importlib.util.module_from_spec(_SPEC)
# dataclass field resolution needs the module registered in sys.modules before exec.
sys.modules[_SPEC.name] = todoist_kill_drill
_SPEC.loader.exec_module(todoist_kill_drill)


class TodoistKillDrillTest(unittest.TestCase):
    def test_rail_state_flip_kill_mechanism_blocks_next_write(self) -> None:
        result = todoist_kill_drill.run_rail_state_kill_drill()
        self.assertTrue(result.passed, msg="\n".join(result.details))

    def test_credential_removal_kill_mechanism_blocks_next_write(self) -> None:
        result = todoist_kill_drill.run_credential_removal_kill_drill()
        self.assertTrue(result.passed, msg="\n".join(result.details))


if __name__ == "__main__":
    unittest.main()
