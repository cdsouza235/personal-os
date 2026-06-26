import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DRY_RUN_DOC = REPO_ROOT / "docs" / "DRY_RUN_EVIDENCE_BUNDLE.md"


class DryRunEvidenceDocsTest(unittest.TestCase):
    def test_dry_run_doc_records_source_contract(self) -> None:
        text = _normalized_doc_text(DRY_RUN_DOC)

        required_phrases = (
            "src/personalos/dry_run_evidence.py",
            "build_dry_run_evidence_bundle_report",
            "validate_dry_run_evidence_bundle_report_contract",
            "validate_no_send_completion_report_contract",
            "dry_run_evidence_schema_version",
            "dry_run_evidence_status",
            "dry_run_evidence_top_level_fields",
            "no_send_completion_report_fields",
            "no_send_safety_assertion_fields",
            "smoke_command_templates",
            "fake_local_fixture_surfaces",
            "non_authorization_false_fields",
            "the builder accepts no caller input",
            "it never emits ready, approved, authorized, activated, executed, or live status",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_dry_run_doc_records_inert_default_posture(self) -> None:
        text = _normalized_doc_text(DRY_RUN_DOC)
        raw_text = DRY_RUN_DOC.read_text(encoding="utf-8").lower()

        required_phrases = (
            "`status=dry_run_contract_recorded_not_live`",
            "`dry_run_execution_started=false`",
            "`repo_evidence_bundle_written=false`",
            "`temp_only_smoke_supported=true`",
            "`live_mvp_ready=false`",
            "`human_gates_remaining=true`",
            "`readiness.status=not_ready`",
            "`inert_report_only=true`",
            "`live_rails_activated=false`",
            "does not start weekend testing",
            "does not authorize live-service testing",
            "does not approve phase 14-c",
            "does not approve a candidate",
            "does not activate production db",
            "does not activate scheduler/background behavior",
            "does not invoke openclaw",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        self.assertNotIn("dry_run_execution_started=true", raw_text)
        self.assertNotIn("repo_evidence_bundle_written=true", raw_text)
        self.assertNotIn("live_mvp_ready=true", raw_text)

    def test_dry_run_doc_records_no_send_demo_and_fake_surface_boundaries(self) -> None:
        text = _normalized_doc_text(DRY_RUN_DOC)

        required_phrases = (
            "personalos.cli demo no-send-e2e --output-dir <safe_output_dir> --json",
            "`requires_explicit_safe_output_dir=true`",
            "`output_dir_must_be_temp=true`",
            "`repo_local_var_allowed=false`",
            "`repo_local_db_allowed=false`",
            "`writes_repo_files=false`",
            "`external_writes_allowed=false`",
            "phase13e_d_no_send_e2e",
            "readiness_status_json",
            "workflow_catalog_json",
            "`requires_credentials=false`",
            "`uses_production_db=false`",
            "`activates_scheduler=false`",
            "`calls_openclaw=false`",
            "`external_write=false`",
            "todoist simulated write fake client",
            "google calendar simulated write fake client",
            "composer fake model adapter",
            "side-effect dry-run ledger",
            "scheduler simulated preview",
            "`fake_or_preview_only=true`",
            "`live_client_allowed=false`",
            "`credential_required=false`",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_dry_run_doc_records_completion_report_safety_assertions(self) -> None:
        text = _normalized_doc_text(DRY_RUN_DOC)

        required_phrases = (
            "validate_no_send_completion_report_contract",
            "exact top-level completion report field shape",
            "artifact names and artifact path keys",
            "`phase_14_blocked=true`",
            "`deviations=[]`",
            "`readiness.status=not_ready`",
            "`credentials_loaded=false`",
            "`credentials_read=false`",
            "`production_db_path_active=false`",
            "`scheduler_activated=false`",
            "`launch_agent_installed=false`",
            "`crontab_modified=false`",
            "`daemon_started=false`",
            "`openclaw_called=false`",
            "`external_services_contacted=false`",
            "`external_mutation=false`",
            "`gmail_touched=false`",
            "`todoist_touched=false`",
            "`calendar_touched=false`",
            "`personalos_markdown_written=false`",
            "`protected_paths_touched=false`",
            "`scheduler_preview_status=simulated_preview_only`",
            "`operator_status_readiness=not_ready`",
            "`operator_status_live_rails_activated=false`",
            "`all_required_assertions_passed=true`",
            "caller-controlled unsafe report values must not appear",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_dry_run_doc_is_linked_from_core_docs(self) -> None:
        dry_run_link = "DRY_RUN_EVIDENCE_BUNDLE.md"
        related_docs = (
            REPO_ROOT / "README.md",
            REPO_ROOT / "STATUS.md",
            REPO_ROOT / "docs" / "PRD.md",
            REPO_ROOT / "docs" / "ROADMAP.md",
            REPO_ROOT / "docs" / "SAFETY_POLICY.md",
            REPO_ROOT / "docs" / "NON_HUMAN_CLOSURE_PLAN.md",
            REPO_ROOT / "docs" / "WEEKEND_TEST_READINESS_RUNBOOK.md",
        )

        for path in related_docs:
            with self.subTest(path=path.name):
                self.assertIn(dry_run_link, path.read_text(encoding="utf-8"))


def _normalized_doc_text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").lower().split())


if __name__ == "__main__":
    unittest.main()
