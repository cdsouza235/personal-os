"""Structural correctness tests for the P-SCHED-02 LaunchAgent plist
(docs/com.personalos.morning.plist).

This plist is authored only -- nothing in P-SCHED-02 loads it. These tests check the
static content of the file itself: real, run-for-real checks (no mocking needed), since
reading a file's own content requires nothing beyond the file existing on disk.
"""

import plistlib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLIST_PATH = REPO_ROOT / "docs" / "com.personalos.morning.plist"
EXPECTED_LABEL = "com.personalos.morning"


def load_plist() -> dict:
    with PLIST_PATH.open("rb") as handle:
        return plistlib.load(handle)


class SchedulerPlistStructureTest(unittest.TestCase):
    def test_plist_file_exists_and_parses_as_valid_xml_plist(self) -> None:
        self.assertTrue(PLIST_PATH.is_file())
        data = load_plist()
        self.assertIsInstance(data, dict)

    def test_label_is_present_and_matches_the_expected_reverse_dns_id(self) -> None:
        data = load_plist()
        self.assertEqual(data.get("Label"), EXPECTED_LABEL)

    def test_program_arguments_are_absolute_and_invoke_run_morning(self) -> None:
        data = load_plist()
        arguments = data.get("ProgramArguments")
        self.assertIsInstance(arguments, list)
        self.assertGreater(len(arguments), 0)

        interpreter = arguments[0]
        self.assertTrue(Path(interpreter).is_absolute(), msg="interpreter must be absolute")

        self.assertIn("-m", arguments)
        self.assertIn("personalos.cli", arguments)
        self.assertIn("run", arguments)
        self.assertIn("morning", arguments)

        self.assertIn("--db", arguments)
        db_index = arguments.index("--db")
        db_path = arguments[db_index + 1]
        self.assertTrue(Path(db_path).is_absolute(), msg="--db value must be absolute")
        self.assertEqual(db_path, "/Users/coldstake/PersonalOS/personal_os.db")

        # The interpreter itself must be an absolute path too (checked above), and there
        # must be no relative "./something" or bare-filename path arguments anywhere.
        for argument in arguments:
            self.assertFalse(argument.startswith("./"))
            self.assertFalse(argument.startswith("../"))

    def test_working_directory_is_present_and_absolute(self) -> None:
        data = load_plist()
        working_directory = data.get("WorkingDirectory")
        self.assertIsInstance(working_directory, str)
        self.assertTrue(Path(working_directory).is_absolute())

    def test_start_calendar_interval_has_sane_hour_and_minute_not_start_interval(self) -> None:
        data = load_plist()
        self.assertNotIn("StartInterval", data)

        interval = data.get("StartCalendarInterval")
        self.assertIsInstance(interval, dict)
        hour = interval.get("Hour")
        minute = interval.get("Minute")
        self.assertIsInstance(hour, int)
        self.assertIsInstance(minute, int)
        self.assertTrue(0 <= hour <= 23)
        self.assertTrue(0 <= minute <= 59)

    def test_no_run_at_load_and_no_keep_alive(self) -> None:
        data = load_plist()
        self.assertNotIn("RunAtLoad", data)
        self.assertNotIn("KeepAlive", data)

    def test_standard_out_and_error_paths_are_absolute_and_not_under_tmp(self) -> None:
        data = load_plist()
        for key in ("StandardOutPath", "StandardErrorPath"):
            path_value = data.get(key)
            self.assertIsInstance(path_value, str)
            path = Path(path_value)
            self.assertTrue(path.is_absolute())
            self.assertFalse(str(path).startswith("/tmp"))
            self.assertFalse(str(path).startswith("/private/tmp"))


if __name__ == "__main__":
    unittest.main()
