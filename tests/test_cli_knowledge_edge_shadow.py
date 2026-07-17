"""P-KE-2C: `personalos knowledge-edge shadow bootstrap|scan|sample-freeze|report`
CLI flows.

`shadow_mode.SHADOW_DB_PATH` is monkeypatched to a temp file for every "admitted"
test so this suite never creates or touches the real repo's `var/shadow/`
directory (QUALITY_GATES' artifact-hygiene check requires no `var/` directory to
exist in the repo tree at all). No live network call is made anywhere in this
suite: `shadow scan` is only ever exercised against a freshly-bootstrapped but
still-`trial`/unverified registry, so `LivePodcastFeedAdapter`'s own gate refuses
before any HTTP client is constructed -- the same "structurally reachable, not
actually reached" pattern `test_rails_knowledge_edge_podcasts.py` already
established.
"""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from personalos import cli
from personalos.knowledge_edge import shadow_mode


class CliRunResult:
    def __init__(self, code: int, stdout: str, stderr: str) -> None:
        self.code = code
        self.stdout = stdout
        self.stderr = stderr


def _run_cli(args: list[str]) -> CliRunResult:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            code = cli.main(args)
        except SystemExit as error:
            code = 0 if error.code is None else int(error.code)
    return CliRunResult(code, stdout.getvalue(), stderr.getvalue())


class ShadowAdmissionFenceTest(unittest.TestCase):
    def test_bootstrap_refuses_a_non_shadow_db_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wrong_path = Path(temp_dir) / "not-shadow.sqlite3"
            result = _run_cli(["knowledge-edge", "shadow", "bootstrap", "--db", str(wrong_path)])
            self.assertEqual(result.code, 1)
            self.assertIn("shadow_live mode requires the shadow database path exactly", result.stderr)
            self.assertFalse(wrong_path.exists())

    def test_scan_refuses_a_non_shadow_db_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wrong_path = Path(temp_dir) / "not-shadow.sqlite3"
            result = _run_cli(
                [
                    "knowledge-edge", "shadow", "scan", "--db", str(wrong_path),
                    "--date", "2026-07-30",
                ]
            )
            self.assertEqual(result.code, 1)
            self.assertIn("shadow_live mode requires", result.stderr)

    def test_sample_freeze_refuses_a_non_shadow_db_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wrong_path = Path(temp_dir) / "not-shadow.sqlite3"
            result = _run_cli(
                [
                    "knowledge-edge", "shadow", "sample-freeze", "--db", str(wrong_path),
                    "--window-start", "2026-07-01", "--window-end", "2026-07-14",
                    "--sample-date", "2026-07-30",
                    "--markdown-output-file", str(Path(temp_dir) / "sample.md"),
                    "--json-output-file", str(Path(temp_dir) / "sample.json"),
                ]
            )
            self.assertEqual(result.code, 1)
            self.assertIn("shadow_live mode requires", result.stderr)

    def test_report_refuses_a_non_shadow_db_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wrong_path = Path(temp_dir) / "not-shadow.sqlite3"
            result = _run_cli(
                [
                    "knowledge-edge", "shadow", "report", "--db", str(wrong_path),
                    "--sample-markdown-file", str(Path(temp_dir) / "sample.md"),
                    "--sample-json-file", str(Path(temp_dir) / "sample.json"),
                    "--grades-json-file", str(Path(temp_dir) / "grades.json"),
                    "--report-date", "2026-07-31",
                    "--output-file", str(Path(temp_dir) / "report.md"),
                ]
            )
            self.assertEqual(result.code, 1)
            self.assertIn("shadow_live mode requires", result.stderr)


class ShadowBootstrapCommandTest(unittest.TestCase):
    def test_bootstrap_creates_and_flips_the_shadow_db(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            shadow_path = Path(temp_dir) / "personalos-shadow.sqlite3"
            with mock.patch.object(shadow_mode, "SHADOW_DB_PATH", shadow_path):
                result = _run_cli(
                    ["knowledge-edge", "shadow", "bootstrap", "--db", str(shadow_path), "--json"]
                )
                self.assertEqual(result.code, 0, result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual(len(payload["sources_flipped_to_active"]), 9)
                self.assertTrue(shadow_path.exists())

                # Idempotent: a second bootstrap makes no further flips.
                second = _run_cli(
                    ["knowledge-edge", "shadow", "bootstrap", "--db", str(shadow_path), "--json"]
                )
                self.assertEqual(second.code, 0, second.stderr)
                second_payload = json.loads(second.stdout)
                self.assertEqual(second_payload["sources_flipped_to_active"], [])
                self.assertEqual(len(second_payload["already_bootstrapped"]), 9)


class ShadowScanCommandTest(unittest.TestCase):
    def test_scan_against_bootstrapped_db_refuses_at_credential_gate_no_network(self) -> None:
        """`shadow bootstrap` leaves all 9 Lane A sources active+verified -- the
        state this scan needs. With the podcast rail's credential env var absent,
        `LivePodcastFeedAdapter._evaluate_gates` refuses every source at the
        credential-presence check (the gate immediately before the one live HTTP
        call would happen), proving the wiring is reachable without ever
        constructing an HTTP client.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            shadow_path = Path(temp_dir) / "personalos-shadow.sqlite3"
            with mock.patch.object(shadow_mode, "SHADOW_DB_PATH", shadow_path):
                bootstrap_result = _run_cli(
                    ["knowledge-edge", "shadow", "bootstrap", "--db", str(shadow_path), "--json"]
                )
                self.assertEqual(bootstrap_result.code, 0)

                with mock.patch.dict("os.environ", {}, clear=False):
                    import os

                    os.environ.pop("PERSONALOS_RAIL_KE_PODCAST_USER_AGENT", None)
                    result = _run_cli(
                        [
                            "knowledge-edge", "shadow", "scan", "--db", str(shadow_path),
                            "--date", "2026-07-30", "--now", "2026-07-30T12:00:00+00:00", "--json",
                        ]
                    )
                # A fully-failed scan is still "partially_completed" (matches the
                # existing `scan` command's own status convention), so exit is 0 --
                # what matters here is that zero sources succeeded and nothing
                # touched the network.
                self.assertEqual(result.code, 0, result.stdout)
                payload = json.loads(result.stdout)
                self.assertEqual(payload["status"], "partially_completed")
                self.assertEqual(payload["sources_healthy"], 0)
                self.assertEqual(payload["sources_failed"], 9)
                self.assertEqual(payload["feature_mode"], "shadow_live")


class ShadowSampleFreezeAndReportCommandTest(unittest.TestCase):
    def test_freeze_then_report_refuses_before_acknowledgment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            shadow_path = Path(temp_dir) / "personalos-shadow.sqlite3"
            with mock.patch.object(shadow_mode, "SHADOW_DB_PATH", shadow_path):
                bootstrap_result = _run_cli(
                    ["knowledge-edge", "shadow", "bootstrap", "--db", str(shadow_path), "--json"]
                )
                self.assertEqual(bootstrap_result.code, 0)

                markdown_path = Path(temp_dir) / "GROUND_TRUTH_SAMPLE_2026-07-30.md"
                json_path = Path(temp_dir) / "GROUND_TRUTH_SAMPLE_2026-07-30.json"
                freeze_result = _run_cli(
                    [
                        "knowledge-edge", "shadow", "sample-freeze", "--db", str(shadow_path),
                        "--window-start", "2026-07-01", "--window-end", "2026-07-14",
                        "--sample-date", "2026-07-30",
                        "--markdown-output-file", str(markdown_path),
                        "--json-output-file", str(json_path),
                        "--coverage-gap", "no §10.3 channels seeded yet",
                        "--json",
                    ]
                )
                self.assertEqual(freeze_result.code, 0, freeze_result.stderr)
                self.assertTrue(markdown_path.exists())
                self.assertTrue(json_path.exists())
                self.assertIn("PENDING CONDUCTOR ACKNOWLEDGMENT", markdown_path.read_text())

                # Acknowledgment is checked before the grades file is ever read, so
                # a not-yet-existing grades path is fine here -- this proves the
                # STOP-before-grading order, not grades-file validation.
                report_path = Path(temp_dir) / "SHADOW_REPORT_2026-07-31.md"
                report_result = _run_cli(
                    [
                        "knowledge-edge", "shadow", "report", "--db", str(shadow_path),
                        "--sample-markdown-file", str(markdown_path),
                        "--sample-json-file", str(json_path),
                        "--grades-json-file", str(Path(temp_dir) / "does-not-exist-yet.json"),
                        "--report-date", "2026-07-31",
                        "--output-file", str(report_path),
                    ]
                )
                self.assertEqual(report_result.code, 1)
                self.assertIn("not yet Conductor-acknowledged", report_result.stderr)
                self.assertFalse(report_path.exists())

    def _bootstrap_freeze_and_acknowledge(self, temp_dir: str, shadow_path: Path) -> tuple[Path, Path]:
        _run_cli(["knowledge-edge", "shadow", "bootstrap", "--db", str(shadow_path)])

        markdown_path = Path(temp_dir) / "GROUND_TRUTH_SAMPLE_2026-07-30.md"
        json_path = Path(temp_dir) / "GROUND_TRUTH_SAMPLE_2026-07-30.json"
        freeze_result = _run_cli(
            [
                "knowledge-edge", "shadow", "sample-freeze", "--db", str(shadow_path),
                "--window-start", "2026-07-01", "--window-end", "2026-07-14",
                "--sample-date", "2026-07-30",
                "--markdown-output-file", str(markdown_path),
                "--json-output-file", str(json_path),
            ]
        )
        self.assertEqual(freeze_result.code, 0, freeze_result.stderr)

        acknowledged_text = markdown_path.read_text().replace(
            'status: "PENDING CONDUCTOR ACKNOWLEDGMENT (R3-04)"',
            'status: "ACKNOWLEDGED"',
        ).replace('acknowledged_by: ""', 'acknowledged_by: "chris"').replace(
            'acknowledged_at: ""', 'acknowledged_at: "2026-07-31T00:00:00+00:00"'
        )
        markdown_path.write_text(acknowledged_text, encoding="utf-8")
        return markdown_path, json_path

    def test_report_refuses_without_a_paired_grades_file(self) -> None:
        """A grades file grading a DIFFERENT (e.g. re-frozen) sample must be
        refused, not silently accepted just because the markdown header says
        ACKNOWLEDGED -- proves the grades-pairing arm is checked, not just the
        frozen-file acknowledgment arm."""
        with tempfile.TemporaryDirectory() as temp_dir:
            shadow_path = Path(temp_dir) / "personalos-shadow.sqlite3"
            with mock.patch.object(shadow_mode, "SHADOW_DB_PATH", shadow_path):
                markdown_path, json_path = self._bootstrap_freeze_and_acknowledge(temp_dir, shadow_path)

                grades_path = Path(temp_dir) / "grades.json"
                grades_path.write_text(
                    json.dumps({"frozen_checksum_sha256": "0" * 64, "precision_verdicts": {}}),
                    encoding="utf-8",
                )

                report_path = Path(temp_dir) / "SHADOW_REPORT_2026-07-31.md"
                report_result = _run_cli(
                    [
                        "knowledge-edge", "shadow", "report", "--db", str(shadow_path),
                        "--sample-markdown-file", str(markdown_path),
                        "--sample-json-file", str(json_path),
                        "--grades-json-file", str(grades_path),
                        "--report-date", "2026-07-31",
                        "--output-file", str(report_path),
                    ]
                )
                self.assertEqual(report_result.code, 1)
                self.assertIn("frozen checksum", report_result.stderr)
                self.assertFalse(report_path.exists())

    def test_report_succeeds_once_sample_is_acknowledged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            shadow_path = Path(temp_dir) / "personalos-shadow.sqlite3"
            with mock.patch.object(shadow_mode, "SHADOW_DB_PATH", shadow_path):
                markdown_path, json_path = self._bootstrap_freeze_and_acknowledge(temp_dir, shadow_path)

                grades_path = Path(temp_dir) / "grades.json"
                grade_init_result = _run_cli(
                    [
                        "knowledge-edge", "shadow", "grade-init",
                        "--sample-markdown-file", str(markdown_path),
                        "--sample-json-file", str(json_path),
                        "--output-file", str(grades_path),
                    ]
                )
                self.assertEqual(grade_init_result.code, 0, grade_init_result.stderr)

                report_path = Path(temp_dir) / "SHADOW_REPORT_2026-07-31.md"
                report_result = _run_cli(
                    [
                        "knowledge-edge", "shadow", "report", "--db", str(shadow_path),
                        "--sample-markdown-file", str(markdown_path),
                        "--sample-json-file", str(json_path),
                        "--grades-json-file", str(grades_path),
                        "--report-date", "2026-07-31",
                        "--person-search-calls-made", "42",
                        "--output-file", str(report_path),
                        "--json",
                    ]
                )
                self.assertEqual(report_result.code, 0, report_result.stderr)
                self.assertTrue(report_path.exists())
                report_text = report_path.read_text()
                self.assertIn("Shadow Report", report_text)
                self.assertIn("§10.3", report_text)
                self.assertIn("42/174 calls used", report_text)


class ShadowGradeInitCommandTest(unittest.TestCase):
    def _bootstrap_and_freeze(self, temp_dir: str, shadow_path: Path) -> tuple[Path, Path]:
        _run_cli(["knowledge-edge", "shadow", "bootstrap", "--db", str(shadow_path)])
        markdown_path = Path(temp_dir) / "GROUND_TRUTH_SAMPLE_2026-07-30.md"
        json_path = Path(temp_dir) / "GROUND_TRUTH_SAMPLE_2026-07-30.json"
        freeze_result = _run_cli(
            [
                "knowledge-edge", "shadow", "sample-freeze", "--db", str(shadow_path),
                "--window-start", "2026-07-01", "--window-end", "2026-07-14",
                "--sample-date", "2026-07-30",
                "--markdown-output-file", str(markdown_path),
                "--json-output-file", str(json_path),
            ]
        )
        self.assertEqual(freeze_result.code, 0, freeze_result.stderr)
        return markdown_path, json_path

    def test_grade_init_refuses_an_unacknowledged_sample(self) -> None:
        """Gate order (R3-04): freeze -> CONDUCTOR ACK -> grade-init -> grading ->
        report. A freshly-frozen, still-PENDING sample must never be able to
        acquire a grades file at all -- grade-init refuses before writing anything,
        same acknowledgment check `shadow report` performs, applied one step
        earlier."""
        with tempfile.TemporaryDirectory() as temp_dir:
            shadow_path = Path(temp_dir) / "personalos-shadow.sqlite3"
            with mock.patch.object(shadow_mode, "SHADOW_DB_PATH", shadow_path):
                markdown_path, json_path = self._bootstrap_and_freeze(temp_dir, shadow_path)

            self.assertIn("PENDING CONDUCTOR ACKNOWLEDGMENT", markdown_path.read_text())

            grades_path = Path(temp_dir) / "grades.json"
            grade_init_result = _run_cli(
                [
                    "knowledge-edge", "shadow", "grade-init",
                    "--sample-markdown-file", str(markdown_path),
                    "--sample-json-file", str(json_path),
                    "--output-file", str(grades_path),
                ]
            )
            self.assertEqual(grade_init_result.code, 1)
            self.assertIn("not yet Conductor-acknowledged", grade_init_result.stderr)
            self.assertFalse(grades_path.exists())

    def test_grade_init_produces_a_pairable_blank_grades_file(self) -> None:
        """No --db is passed at all -- grade-init is a pure file transform and
        needs none, proving it never touches the shadow admission fence because
        there is nothing DB-shaped for that fence to guard here. Requires an
        ACKNOWLEDGED sample (R3-04 gate order) before it will proceed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            shadow_path = Path(temp_dir) / "personalos-shadow.sqlite3"
            with mock.patch.object(shadow_mode, "SHADOW_DB_PATH", shadow_path):
                markdown_path, json_path = self._bootstrap_and_freeze(temp_dir, shadow_path)

            acknowledged_text = markdown_path.read_text().replace(
                'status: "PENDING CONDUCTOR ACKNOWLEDGMENT (R3-04)"',
                'status: "ACKNOWLEDGED"',
            ).replace('acknowledged_by: ""', 'acknowledged_by: "chris"').replace(
                'acknowledged_at: ""', 'acknowledged_at: "2026-07-31T00:00:00+00:00"'
            )
            markdown_path.write_text(acknowledged_text, encoding="utf-8")

            grades_path = Path(temp_dir) / "grades.json"
            grade_init_result = _run_cli(
                [
                    "knowledge-edge", "shadow", "grade-init",
                    "--sample-markdown-file", str(markdown_path),
                    "--sample-json-file", str(json_path),
                    "--output-file", str(grades_path),
                    "--json",
                ]
            )
            self.assertEqual(grade_init_result.code, 0, grade_init_result.stderr)
            grades = json.loads(grades_path.read_text())
            self.assertIn("precision_verdicts", grades)
            self.assertIn("frozen_checksum_sha256", grades)


if __name__ == "__main__":
    unittest.main()
