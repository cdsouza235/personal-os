import os
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class Phase8DocsAndSafetyTest(unittest.TestCase):
    def test_docs_describe_phase_8_scope_and_non_goals(self) -> None:
        docs_text = "\n".join(
            [
                (REPO_ROOT / "README.md").read_text(encoding="utf-8"),
                (REPO_ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8"),
                (REPO_ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8"),
                (REPO_ROOT / "docs" / "SAFETY_POLICY.md").read_text(encoding="utf-8"),
            ]
        ).lower()

        required_phrases = (
            "phase 8 fitness integration foundation",
            "existing csv-based local fitness tracker is preserved",
            "no notion dependency",
            "no live personalos csv reads or writes",
            "no apple health or wearable api integration",
            "no workout recommendation engine",
            "no todoist/calendar/gmail writes",
            "no scheduler or launchagents",
            "no production sqlite/runtime state",
            "no dashboard ui yet",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, docs_text)

    def test_repo_contains_no_runtime_database_or_var_artifacts_outside_git(self) -> None:
        db_artifacts: list[Path] = []
        var_dirs: list[Path] = []
        for directory, directories, filenames in os.walk(REPO_ROOT):
            current = Path(directory)
            if ".git" in current.parts:
                directories[:] = []
                continue
            directories[:] = [item for item in directories if item != ".git"]
            for dirname in directories:
                if dirname == "var":
                    var_dirs.append(current / dirname)
            for filename in filenames:
                path = current / filename
                is_named_db_artifact = filename in {".sqlite", ".sqlite3"}
                is_db_suffix = path.suffix in {".sqlite", ".sqlite3", ".db"}
                if is_named_db_artifact or is_db_suffix:
                    db_artifacts.append(path)

        self.assertEqual(db_artifacts, [])
        self.assertEqual(var_dirs, [])
