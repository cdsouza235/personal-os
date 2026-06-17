import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from personalos.pre_live_readiness import (
    EXECUTION_MODES,
    LIVE_RAILS,
    ExecutionMode,
    GateStatus,
    LiveRail,
    LiveRailConfig,
    LiveRailStatus,
    PreLiveReadinessConfig,
    ReadinessGate,
    ReadinessStatus,
    default_live_rail_statuses,
    evaluate_pre_live_readiness,
    readiness_report_to_summary,
)


class PreLiveReadinessDefaultsTest(unittest.TestCase):
    def test_missing_config_is_not_ready_and_live_rails_default_disabled(self) -> None:
        report = evaluate_pre_live_readiness()

        self.assertEqual(report.status, ReadinessStatus.NOT_READY)
        self.assertIn("Missing readiness config fails closed.", report.reasons)
        for rail in report.rails:
            with self.subTest(rail=rail.rail):
                self.assertEqual(rail.status, LiveRailStatus.DISABLED)
                self.assertFalse(rail.active)

    def test_default_config_is_not_ready_with_missing_required_gates(self) -> None:
        report = evaluate_pre_live_readiness(PreLiveReadinessConfig())
        gates = _gates_by_name(report)

        self.assertEqual(report.status, ReadinessStatus.NOT_READY)
        self.assertEqual(gates[ReadinessGate.CONFIG_PROVIDED].status, GateStatus.SATISFIED)
        self.assertEqual(
            gates[ReadinessGate.CHRIS_APPROVAL_RECORDED].status,
            GateStatus.MISSING,
        )
        self.assertEqual(
            gates[ReadinessGate.GLOBAL_KILL_SWITCH_DEFINED].status,
            GateStatus.MISSING,
        )

    def test_all_live_rails_are_represented_as_disabled_by_default(self) -> None:
        rails = default_live_rail_statuses()

        self.assertEqual({rail.rail for rail in rails}, set(LIVE_RAILS))
        for rail in rails:
            with self.subTest(rail=rail.rail):
                self.assertEqual(rail.status, LiveRailStatus.DISABLED)
                self.assertFalse(rail.active)
                self.assertIn("disabled", rail.reason.lower())

    def test_no_live_rail_is_considered_active_by_default(self) -> None:
        report = evaluate_pre_live_readiness(PreLiveReadinessConfig())

        self.assertFalse(any(rail.active for rail in report.rails))
        self.assertFalse(report.scheduler_activated)
        self.assertFalse(report.openclaw_called)
        self.assertFalse(report.external_services_contacted)

    def test_dry_run_apply_and_live_terms_remain_distinct(self) -> None:
        mode_values = [mode.value for mode in EXECUTION_MODES]
        report = evaluate_pre_live_readiness(PreLiveReadinessConfig())

        self.assertEqual(len(mode_values), len(set(mode_values)))
        self.assertEqual(ExecutionMode.DRY_RUN.value, "dry_run")
        self.assertEqual(ExecutionMode.INTERNAL_APPLY.value, "internal_apply")
        self.assertEqual(ExecutionMode.LIVE_WRITE.value, "live_write")
        self.assertIn("dry_run", report.to_dict()["execution_modes"])
        self.assertIn("internal_apply", report.to_dict()["execution_modes"])
        self.assertIn("live_write", report.to_dict()["execution_modes"])


class PreLiveReadinessSafetyTest(unittest.TestCase):
    def test_live_rail_activation_request_is_blocked_without_marking_it_active(self) -> None:
        config = replace(
            _fully_satisfied_config(),
            rails={
                LiveRail.GMAIL: LiveRailConfig(
                    status=LiveRailStatus.ACTIVE,
                    active=True,
                )
            },
        )

        report = evaluate_pre_live_readiness(config)
        rails = _rails_by_name(report)

        self.assertEqual(report.status, ReadinessStatus.BLOCKED)
        self.assertEqual(rails[LiveRail.GMAIL].status, LiveRailStatus.BLOCKED)
        self.assertFalse(rails[LiveRail.GMAIL].active)
        self.assertFalse(report.external_services_contacted)

    def test_invalid_or_unknown_live_rail_config_fails_closed(self) -> None:
        config = replace(
            _fully_satisfied_config(),
            rails={
                LiveRail.TODOIST: {"status": "unexpected_live_status"},
                "future_live_rail": {"status": LiveRailStatus.DISABLED},
            },
        )

        report = evaluate_pre_live_readiness(config)
        gates = _gates_by_name(report)
        rails = _rails_by_name(report)

        self.assertEqual(report.status, ReadinessStatus.BLOCKED)
        self.assertEqual(rails[LiveRail.TODOIST].status, LiveRailStatus.BLOCKED)
        self.assertEqual(
            gates[ReadinessGate.LIVE_PERMISSIONS_DISABLED_BY_DEFAULT].status,
            GateStatus.BLOCKED,
        )

    def test_invalid_or_unknown_live_rail_config_fails_closed_in_summary_surface(self) -> None:
        config = replace(
            _fully_satisfied_config(),
            rails={
                LiveRail.TODOIST: {"status": "unexpected_live_status"},
                "future_live_rail": {"status": LiveRailStatus.DISABLED},
            },
        )

        summary = readiness_report_to_summary(evaluate_pre_live_readiness(config))

        self.assertEqual(summary["status"], "blocked")
        self.assertTrue(summary["inert_report_only"])
        self.assertFalse(summary["live_rails_activated"])
        self.assertGreater(summary["blocked_or_non_disabled_rail_count"], 0)
        self.assertTrue(
            any(
                rail["rail"] == "todoist" and rail["status"] == "blocked"
                for rail in summary["rails"]
            )
        )

    def test_production_db_path_is_not_active_by_default(self) -> None:
        report = evaluate_pre_live_readiness(PreLiveReadinessConfig())
        gates = _gates_by_name(report)
        rails = _rails_by_name(report)

        self.assertFalse(report.production_db_path_active)
        self.assertEqual(
            gates[ReadinessGate.PRODUCTION_DB_PATH_INACTIVE_BY_DEFAULT].status,
            GateStatus.SATISFIED,
        )
        self.assertEqual(rails[LiveRail.PRODUCTION_SQLITE].status, LiveRailStatus.DISABLED)
        self.assertFalse(rails[LiveRail.PRODUCTION_SQLITE].active)

    def test_credentials_are_not_loaded_or_read(self) -> None:
        report = evaluate_pre_live_readiness(PreLiveReadinessConfig())
        gates = _gates_by_name(report)

        self.assertFalse(report.credentials_loaded)
        self.assertFalse(report.credentials_read)
        self.assertEqual(gates[ReadinessGate.CREDENTIALS_NOT_LOADED].status, GateStatus.SATISFIED)

    def test_credentials_loaded_marker_blocks_readiness(self) -> None:
        report = evaluate_pre_live_readiness(
            replace(_fully_satisfied_config(), credentials_loaded=True)
        )
        gates = _gates_by_name(report)

        self.assertEqual(report.status, ReadinessStatus.BLOCKED)
        self.assertEqual(
            gates[ReadinessGate.CREDENTIALS_POLICY_ACKNOWLEDGED].status,
            GateStatus.BLOCKED,
        )
        self.assertEqual(gates[ReadinessGate.CREDENTIALS_NOT_LOADED].status, GateStatus.BLOCKED)

    def test_readiness_evaluation_is_read_only_and_inert(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            before = sorted(temp_root.iterdir())

            report = evaluate_pre_live_readiness(
                replace(
                    _fully_satisfied_config(),
                    production_db_path=temp_root / "approved-runtime.sqlite3",
                )
            )
            after = sorted(temp_root.iterdir())

        self.assertEqual(report.status, ReadinessStatus.READY)
        self.assertEqual(before, after)
        self.assertFalse(report.files_created)
        self.assertFalse(report.runtime_state_mutated)
        self.assertFalse(report.scheduler_activated)
        self.assertFalse(report.openclaw_called)

    def test_protected_paths_remain_blocked(self) -> None:
        protected_path = Path.home() / "PersonalOS" / "runtime.sqlite3"

        report = evaluate_pre_live_readiness(
            replace(_fully_satisfied_config(), production_db_path=protected_path)
        )
        gates = _gates_by_name(report)

        self.assertEqual(report.status, ReadinessStatus.BLOCKED)
        self.assertEqual(
            gates[ReadinessGate.PRODUCTION_DB_PATH_APPROVED].status,
            GateStatus.BLOCKED,
        )
        self.assertIn("protected PersonalOS path", gates[ReadinessGate.PRODUCTION_DB_PATH_APPROVED].reason)


class PreLiveReadinessRequiredGateTest(unittest.TestCase):
    def test_fully_satisfied_config_can_report_ready_without_activating_live_rails(self) -> None:
        report = evaluate_pre_live_readiness(_fully_satisfied_config())

        self.assertEqual(report.status, ReadinessStatus.READY)
        self.assertFalse(report.production_db_path_active)
        self.assertFalse(report.production_migration_active)
        for rail in report.rails:
            with self.subTest(rail=rail.rail):
                self.assertEqual(rail.status, LiveRailStatus.DISABLED)
                self.assertFalse(rail.active)

    def test_readiness_cannot_pass_without_chris_approval_marker(self) -> None:
        report = evaluate_pre_live_readiness(
            replace(
                _fully_satisfied_config(),
                chris_approval_recorded=False,
                chris_approval_reference=None,
            )
        )
        gates = _gates_by_name(report)

        self.assertEqual(report.status, ReadinessStatus.NOT_READY)
        self.assertEqual(gates[ReadinessGate.CHRIS_APPROVAL_RECORDED].status, GateStatus.MISSING)

    def test_readiness_cannot_pass_without_global_kill_switch(self) -> None:
        report = evaluate_pre_live_readiness(
            replace(
                _fully_satisfied_config(),
                global_kill_switch_defined=False,
                global_kill_switch_reference=None,
            )
        )
        gates = _gates_by_name(report)

        self.assertEqual(report.status, ReadinessStatus.NOT_READY)
        self.assertEqual(
            gates[ReadinessGate.GLOBAL_KILL_SWITCH_DEFINED].status,
            GateStatus.MISSING,
        )

    def test_readiness_cannot_pass_without_idempotency_ledger_or_completion_report(self) -> None:
        checks = (
            ("idempotency_policy_approved", ReadinessGate.IDEMPOTENCY_POLICY_APPROVED),
            ("side_effect_ledger_policy_approved", ReadinessGate.SIDE_EFFECT_LEDGER_APPROVED),
            ("completion_report_policy_approved", ReadinessGate.COMPLETION_REPORT_APPROVED),
        )

        for attribute, gate in checks:
            with self.subTest(attribute=attribute):
                report = evaluate_pre_live_readiness(
                    replace(_fully_satisfied_config(), **{attribute: False})
                )
                gates = _gates_by_name(report)

                self.assertEqual(report.status, ReadinessStatus.NOT_READY)
                self.assertEqual(gates[gate].status, GateStatus.MISSING)

    def test_readiness_cannot_pass_without_first_live_pilot_scope(self) -> None:
        report = evaluate_pre_live_readiness(
            replace(
                _fully_satisfied_config(),
                first_live_pilot_approved=False,
                first_live_pilot_scope=None,
            )
        )
        gates = _gates_by_name(report)

        self.assertEqual(report.status, ReadinessStatus.NOT_READY)
        self.assertEqual(gates[ReadinessGate.FIRST_LIVE_PILOT_APPROVED].status, GateStatus.MISSING)


def _fully_satisfied_config() -> PreLiveReadinessConfig:
    return PreLiveReadinessConfig(
        mode_separation_confirmed=True,
        credentials_policy_acknowledged=True,
        production_db_path=Path(tempfile.gettempdir()) / "personalos-readiness-approved.sqlite3",
        production_db_path_approved=True,
        production_migration_policy_approved=True,
        backup_restore_verified=True,
        idempotency_policy_approved=True,
        side_effect_ledger_policy_approved=True,
        completion_report_policy_approved=True,
        rollback_recovery_policy_approved=True,
        global_kill_switch_defined=True,
        global_kill_switch_reference="pre-live-global-disable",
        scheduler_activation_requirement_approved=True,
        operator_handoff_approved=True,
        first_live_pilot_approved=True,
        first_live_pilot_scope="one rail, one operator, one bounded operation",
        tests_and_docs_current=True,
        chris_approval_recorded=True,
        chris_approval_reference="chris-explicit-pre-live-approval-marker",
    )


def _gates_by_name(report: object) -> dict[ReadinessGate, object]:
    return {gate.gate: gate for gate in report.gates}


def _rails_by_name(report: object) -> dict[LiveRail, object]:
    return {rail.rail: rail for rail in report.rails}
