"""Wires tests/gmail_kill_drill.py into the automated suite (P-RAIL-GM-02).

The drill script is the artifact a human runs by hand during a real incident to verify
the kill procedure still works; this test just makes sure it stays green on every
run of the suite, so a regression in any of the three kill mechanisms is caught before it
ever matters. Loaded by file path (not package import) since it's a standalone script, not
a module of the `tests` package -- same pattern as `tests/test_todoist_kill_drill.py`.
"""

import importlib.util
import sys
import unittest
from pathlib import Path

_SCRIPT_PATH = Path(__file__).resolve().parent / "gmail_kill_drill.py"
_SPEC = importlib.util.spec_from_file_location("gmail_kill_drill", _SCRIPT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
gmail_kill_drill = importlib.util.module_from_spec(_SPEC)
# dataclass field resolution needs the module registered in sys.modules before exec.
sys.modules[_SPEC.name] = gmail_kill_drill
_SPEC.loader.exec_module(gmail_kill_drill)


class GmailKillDrillTest(unittest.TestCase):
    def test_rail_state_flip_kill_mechanism_blocks_next_send(self) -> None:
        result = gmail_kill_drill.run_rail_state_kill_drill()
        self.assertTrue(result.passed, msg="\n".join(result.details))

    def test_sender_credential_removal_kill_mechanism_blocks_next_send(self) -> None:
        result = gmail_kill_drill.run_sender_credential_removal_kill_drill()
        self.assertTrue(result.passed, msg="\n".join(result.details))

    def test_app_password_removal_kill_mechanism_blocks_next_send(self) -> None:
        result = gmail_kill_drill.run_app_password_removal_kill_drill()
        self.assertTrue(result.passed, msg="\n".join(result.details))

    def test_controlled_recipient_removal_kill_mechanism_blocks_next_send(self) -> None:
        result = gmail_kill_drill.run_controlled_recipient_removal_kill_drill()
        self.assertTrue(result.passed, msg="\n".join(result.details))


if __name__ == "__main__":
    unittest.main()
