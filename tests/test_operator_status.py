import unittest

from personalos.operator_status import create_operator_status_report
from personalos.pre_live_readiness import create_default_pre_live_readiness_report


class OperatorStatusReportTest(unittest.TestCase):
    def test_default_report_shape_is_not_ready_and_inert(self) -> None:
        report = create_operator_status_report(
            generated_at_utc="2026-06-17T00:00:00+00:00"
        )

        self.assertEqual(report["schema_version"], "operator_status.v1")
        self.assertEqual(report["generated_at_utc"], "2026-06-17T00:00:00+00:00")
        self.assertEqual(report["readiness_status"], "not_ready")
        self.assertTrue(report["inert_report_only"])
        self.assertFalse(report["live_rails_activated"])
        self.assertEqual(report["scheduler_status"]["status"], "inactive")
        self.assertEqual(report["production_db_status"]["status"], "not_active")
        self.assertEqual(report["credential_status"]["status"], "not_loaded")
        self.assertFalse(report["credential_status"]["loaded"])
        self.assertFalse(report["credential_status"]["read"])
        self.assertEqual(report["external_write_status"]["status"], "none")
        self.assertTrue(report["external_write_status"]["no_external_writes"])
        self.assertFalse(report["external_write_status"]["write_clients_initialized"])
        self.assertIn("Preview ChatGPT synthesis import", report["safe_local_actions"])
        self.assertIn("Send Gmail", report["blocked_actions"])
        self.assertIn("Call OpenClaw runtime", report["blocked_actions"])
        self.assertIn(
            "Personal OS is not ready for live operation.",
            report["warnings_or_blockers"],
        )

    def test_live_rail_aliases_are_stable_for_audit_json(self) -> None:
        report = create_operator_status_report()

        self.assertEqual(
            set(report["live_rails"]),
            {
                "gmail",
                "todoist",
                "calendar",
                "personalos_markdown",
                "model_api",
                "openclaw",
            },
        )
        for rail in report["live_rails"].values():
            self.assertEqual(rail["status"], "disabled")
            self.assertFalse(rail["active"])

    def test_report_includes_local_ledger_and_scheduler_evidence_when_available(
        self,
    ) -> None:
        readiness = create_default_pre_live_readiness_report()

        report = create_operator_status_report(
            readiness=readiness,
            external_write_ledger_counts={
                "external_write_intents": 2,
                "external_write_attempts": 1,
                "idempotency_records": 3,
            },
            scheduler_counts={
                "scheduler_job_count": 4,
                "scheduler_run_count": 5,
            },
        )

        self.assertEqual(report["external_write_status"]["external_write_intent_count"], 2)
        self.assertEqual(report["external_write_status"]["external_write_attempt_count"], 1)
        self.assertEqual(report["external_write_status"]["idempotency_record_count"], 3)
        self.assertEqual(report["scheduler_status"]["scheduler_job_count"], 4)
        self.assertEqual(report["scheduler_status"]["scheduler_run_count"], 5)
        self.assertEqual(report["evidence"]["readiness_evaluator_result"], "not_ready")
        self.assertTrue(report["evidence"]["live_rails_disabled"])
        self.assertFalse(report["evidence"]["external_write_clients_initialized"])
