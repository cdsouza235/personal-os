"""Regression guard for the state.py -> state/ package split (P-DEBT-02a).

Records the full public API surface of the former single-file
``personalos/state.py`` module and asserts the new ``personalos.state``
package re-exports every one of those names unchanged. This is the packet's
own proof that the split is a pure reorganization with no API loss.
"""

import types
import unittest

import personalos.state as state

# Recorded from the original personalos/state.py (pre-split), via an AST scan
# of every top-level function/class/constant whose name does not start with
# an underscore. Do not add to this list casually -- if the public API of
# personalos.state legitimately grows, add the new name here deliberately.
ORIGINAL_PUBLIC_NAMES = {
    "BRIEFING_LOOP_STATE_TABLES",
    "BRIEFING_OUTPUT_DELIVERY_MODES",
    "BRIEFING_OUTPUT_STATUSES",
    "BRIEFING_OUTPUT_WINDOWS",
    "CHART_PACK_REVIEW_SOURCE_TYPES",
    "CHART_PACK_REVIEW_STATUSES",
    "COMPOSER_BRIEFING_WINDOWS",
    "COMPOSER_OUTPUT_STATUSES",
    "COMPOSER_OUTPUT_VALIDATION_STATUSES",
    "COMPOSER_PACKET_STATUSES",
    "COMPOSER_PACKET_TYPES",
    "COMPOSER_STATE_TABLES",
    "CORE_STATE_TABLES",
    "COUNTABLE_STATE_TABLES",
    "DAILY_PLAN_STATUSES",
    "EXECUTION_RAIL_STATE_TABLES",
    "FITNESS_FILE_CONTRACT_STATUSES",
    "FITNESS_FILE_ROLES",
    "FITNESS_INTEGRATION_STATUSES",
    "FITNESS_INTEGRATION_TYPES",
    "FITNESS_STATE_TABLES",
    "FITNESS_VALIDATION_RUN_STATUSES",
    "FITNESS_VALIDATION_RUN_TYPES",
    "FOLLOWUP_STATUSES",
    "MODEL_RUN_ADAPTERS",
    "MODEL_RUN_ROLES",
    "MODEL_RUN_STATUSES",
    "PRIORITY_STATUSES",
    "PROJECT_STATUSES",
    "REPORT_JOB_CADENCES",
    "REPORT_JOB_STATUSES",
    "REPORT_JOB_TYPES",
    "REPORT_RUN_STATUSES",
    "REPORT_RUN_TYPES",
    "REPORT_STATE_TABLES",
    "ROUTINE_CADENCE_TYPES",
    "ROUTINE_COMPLETION_TABLE",
    "ROUTINE_MISSED_BEHAVIOR_TYPES",
    "ROUTINE_STATUSES",
    "SYNTHESIS_IMPORT_INPUT_FORMATS",
    "SYNTHESIS_IMPORT_PREVIEW_STATUSES",
    "SYNTHESIS_IMPORT_PREVIEW_TABLES",
    "SYNTHESIS_IMPORT_RAW_EXCERPT_MAX_CHARS",
    "SYNTHESIS_IMPORT_SOURCE_TYPES",
    "build_calendar_block_record",
    "build_todoist_task_record",
    "count_briefing_outputs",
    "count_calendar_blocks",
    "count_chart_pack_reviews",
    "count_composer_outputs",
    "count_composer_packets",
    "count_daily_plans",
    "count_fitness_file_contracts",
    "count_fitness_integration_states",
    "count_fitness_validation_runs",
    "count_followups",
    "count_model_runs",
    "count_priorities",
    "count_priorities_by_status",
    "count_projects",
    "count_report_jobs",
    "count_report_runs",
    "count_routine_completions",
    "count_routines",
    "count_synthesis_import_previews",
    "count_todoist_tasks",
    "create_briefing_output",
    "create_calendar_block",
    "create_chart_pack_review",
    "create_composer_output",
    "create_composer_packet",
    "create_daily_plan",
    "create_fitness_file_contract",
    "create_fitness_integration_state",
    "create_fitness_validation_run",
    "create_followup",
    "create_model_run",
    "create_priority",
    "create_project",
    "create_report_job",
    "create_report_run",
    "create_routine",
    "create_synthesis_import_preview",
    "create_todoist_task",
    "get_briefing_output",
    "get_calendar_block",
    "get_calendar_block_by_dedupe_key",
    "get_chart_pack_review",
    "get_composer_output",
    "get_composer_packet",
    "get_daily_plan",
    "get_fitness_file_contract",
    "get_fitness_integration_state",
    "get_fitness_validation_run",
    "get_followup",
    "get_model_run",
    "get_permission_setting",
    "get_priority",
    "get_project",
    "get_report_job",
    "get_report_run",
    "get_routine",
    "get_routine_completion",
    "get_synthesis_import_preview",
    "get_todoist_task",
    "get_todoist_task_by_dedupe_key",
    "list_active_priorities",
    "list_briefing_outputs",
    "list_calendar_blocks",
    "list_chart_pack_reviews",
    "list_composer_outputs",
    "list_composer_packets",
    "list_daily_plans",
    "list_fitness_file_contracts",
    "list_fitness_integration_states",
    "list_fitness_validation_runs",
    "list_followups",
    "list_model_runs",
    "list_permission_settings",
    "list_priorities",
    "list_projects",
    "list_report_jobs",
    "list_report_runs",
    "list_routine_completions",
    "list_routines",
    "list_synthesis_import_previews",
    "list_todoist_tasks",
    "record_routine_completion",
    "summarize_priorities",
    "update_calendar_block_status",
    "update_chart_pack_review",
    "update_composer_packet_status",
    "update_daily_plan_status",
    "update_fitness_file_contract",
    "update_fitness_integration_state",
    "update_fitness_validation_run",
    "update_priority",
    "update_priority_status",
    "update_report_job",
    "update_report_run",
    "update_routine",
    "update_routine_status_enabled",
    "update_synthesis_import_preview_status",
    "update_todoist_task_status",
    "upsert_permission_setting",
    "validate_briefing_output_delivery_mode",
    "validate_briefing_output_status",
    "validate_briefing_output_window",
    "validate_chart_pack_review_source_type",
    "validate_chart_pack_review_status",
    "validate_composer_briefing_window",
    "validate_composer_output_status",
    "validate_composer_output_validation_status",
    "validate_composer_packet_status",
    "validate_composer_packet_type",
    "validate_daily_plan_status",
    "validate_fitness_file_contract_status",
    "validate_fitness_file_role",
    "validate_fitness_integration_status",
    "validate_fitness_integration_type",
    "validate_fitness_validation_run_status",
    "validate_fitness_validation_run_type",
    "validate_followup_status",
    "validate_model_run_adapter",
    "validate_model_run_role",
    "validate_model_run_status",
    "validate_priority_status",
    "validate_project_status",
    "validate_report_job_cadence",
    "validate_report_job_status",
    "validate_report_job_type",
    "validate_report_run_status",
    "validate_report_run_type",
    "validate_routine_cadence_type",
    "validate_routine_enabled",
    "validate_routine_missed_behavior",
    "validate_routine_status",
    "validate_synthesis_import_input_format",
    "validate_synthesis_import_preview_status",
    "validate_synthesis_import_source_type",
}


class StatePackageReexportsEverythingTest(unittest.TestCase):
    def test_every_original_public_name_is_still_importable(self) -> None:
        for name in sorted(ORIGINAL_PUBLIC_NAMES):
            self.assertTrue(
                hasattr(state, name), f"personalos.state lost public name: {name}"
            )

    def test_public_surface_matches_exactly_module_attrs_only(self) -> None:
        # dir() on a package also exposes its submodules as attributes (e.g.
        # `state.routines`), which is an unavoidable side effect of the
        # module -> package conversion and not part of the original API
        # surface. Exclude module objects before comparing.
        # `annotations` is bound by `from __future__ import annotations` and
        # was present in the original single-file module's namespace too.
        ignored_attrs = {"annotations"}
        public_attrs = {
            name
            for name in dir(state)
            if not name.startswith("_")
            and name not in ignored_attrs
            and not isinstance(getattr(state, name), types.ModuleType)
        }
        self.assertEqual(public_attrs, ORIGINAL_PUBLIC_NAMES)


if __name__ == "__main__":
    unittest.main()
