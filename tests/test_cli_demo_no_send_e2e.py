import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from personalos import cli


REPO_ROOT = Path(__file__).resolve().parents[1]
DB_SUFFIXES = {".sqlite", ".sqlite3", ".db"}


class DemoNoSendE2ECliTest(unittest.TestCase):
    def test_demo_no_send_e2e_cli_succeeds_with_safe_temp_output_dir(self) -> None:
        before_artifacts = _repo_db_artifacts()
        self.assertFalse((REPO_ROOT / "var").exists())
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "phase-13e-d-output"
            result = _run_cli(
                [
                    "demo",
                    "no-send-e2e",
                    "--output-dir",
                    str(output_dir),
                    "--json",
                ]
            )

            payload = json.loads(result.stdout)

            self.assertEqual(result.code, 0)
            self.assertEqual(payload["status"], "completed")
            self.assertEqual(
                payload["command_contract"],
                "PYTHONPATH=src python3 -m personalos.cli demo no-send-e2e --output-dir <safe_output_dir> --json",
            )
            self.assertEqual(payload["phase_name"], "Phase 13E-D - synthetic end-to-end no-send demo")
            self.assertEqual(Path(payload["output_dir"]), output_dir.resolve())
            self.assertTrue(Path(payload["generated_db_path"]).is_file())
            Path(payload["generated_db_path"]).relative_to(output_dir.resolve())
            self.assertTrue(payload["safety_assertions"]["all_required_assertions_passed"])
            self.assertFalse(payload["safety_assertions"]["any_rail_live"])
            self.assertEqual(payload["safety_assertions"]["scheduler_state"], "off")
            self.assertTrue(payload["blocked_live_action_summary"]["rails_all_non_live"])
            self.assertFalse(payload["blocked_live_action_summary"]["live_tasks_created"])
            self.assertFalse(payload["blocked_live_action_summary"]["live_calendar_events_created"])
            self.assertFalse(payload["blocked_live_action_summary"]["gmail_sent_or_drafted"])
            self.assertFalse(payload["blocked_live_action_summary"]["markdown_written"])
            for artifact in payload["artifact_list"]:
                with self.subTest(artifact=artifact["name"]):
                    artifact_path = Path(artifact["path"])
                    artifact_path.relative_to(output_dir.resolve())
                    self.assertTrue(artifact_path.exists())

        self.assertFalse((REPO_ROOT / "var").exists())
        self.assertEqual(_repo_db_artifacts(), before_artifacts)

    def test_demo_no_send_e2e_cli_rejects_unsafe_output_dirs_nonzero(self) -> None:
        unsafe_paths = (
            "/Users/coldstake/PersonalOS/demo",
            "/Users/coldstake/.openclaw/demo",
            "/Users/coldstake/Library/LaunchAgents/demo",
            str(REPO_ROOT),
            str(REPO_ROOT / ".git" / "demo"),
            str(REPO_ROOT / "var" / "demo"),
            "/tmp/personalos-production-demo",
            "/tmp/personalos-prod-demo",
            "/tmp/personalos-live-demo",
            "/tmp/personalos-credentials-demo",
            "/tmp/personalos-secret-demo",
            "/tmp/personalos-token-demo",
            "/tmp/personalos-openclaw-demo",
            "/tmp/personalos-scheduler-demo",
            "/tmp/personalos-crontab-demo",
            "/tmp/personalos-daemon-demo",
        )
        for unsafe_path in unsafe_paths:
            with self.subTest(unsafe_path=unsafe_path):
                result = _run_cli(
                    [
                        "demo",
                        "no-send-e2e",
                        "--output-dir",
                        unsafe_path,
                        "--json",
                    ]
                )
                self.assertEqual(result.code, 1)
                self.assertEqual(result.stdout, "")
                self.assertIn("error:", result.stderr)

    def test_demo_no_send_e2e_output_dir_is_required(self) -> None:
        result = _run_cli(["demo", "no-send-e2e", "--json"])

        self.assertEqual(result.code, 2)
        self.assertIn("--output-dir", result.stderr)


class CliResult:
    def __init__(self, *, code: int, stdout: str, stderr: str) -> None:
        self.code = code
        self.stdout = stdout
        self.stderr = stderr


def _run_cli(args: list[str]) -> CliResult:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            code = cli.main(args)
        except SystemExit as error:
            code = int(error.code)
    return CliResult(code=code, stdout=stdout.getvalue(), stderr=stderr.getvalue())


def _repo_db_artifacts() -> list[str]:
    artifacts: list[str] = []
    for path in REPO_ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.is_file() and path.suffix in DB_SUFFIXES:
            artifacts.append(str(path.relative_to(REPO_ROOT)))
    return sorted(artifacts)
