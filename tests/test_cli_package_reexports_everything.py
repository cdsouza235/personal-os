"""Regression guard for the cli.py -> cli/ package split (P-DEBT-02b).

Records the FULL original namespace of the former single-file
``personalos/cli.py`` module -- public AND private names, plus every name
that module-level imports (stdlib and personalos.*) incidentally bound as a
``cli.<name>`` attribute -- and asserts the new ``personalos.cli`` package
re-exports every one of those names unchanged. Unlike the state.py split
(P-DEBT-02a), private names are included deliberately: tests such as
tests/test_path_safety.py reach directly into ``cli._connect_read_write``,
and this file's surface is private-by-convention rather than a clean public
API, so "public names only" is not a safe re-export contract here.
"""

import unittest

import personalos.cli as cli

# Recorded from the original personalos/cli.py (pre-split), via
# `dir(personalos.cli)` on the single-file module before the split, minus
# dunder attributes. Do not add to this list casually -- if the API of
# personalos.cli legitimately grows, add the new name here deliberately.
ORIGINAL_NAMES = {
    "ALLOWED_SOURCE_TYPES",
    "Any",
    "BRIEFING_WINDOWS",
    "CliError",
    "DEFAULT_TIMEZONE",
    "Iterable",
    "Mapping",
    "PRIORITY_STATUSES",
    "Path",
    "PersonalOSArgumentParser",
    "PriorityEnginePermissionDenied",
    "REPORT_SAFETY_FLAGS",
    "ROUTINE_STATUSES",
    "RoutineEnginePermissionDenied",
    "SAFE_LOCAL_WORKFLOW_SPECS",
    "SAFE_NO_SEND_SEED_PROFILE",
    "SIMULATED_JOB_TYPES",
    "Sequence",
    "SynthesisApplyValidationError",
    "SynthesisImportValidationError",
    "ZoneInfo",
    "ZoneInfoNotFoundError",
    "_add_date_timezone_args",
    "_add_db_arg",
    "_add_json_arg",
    "_append_candidate_or_ledger_summary",
    "_append_rail_state_lines",
    "_append_workflow_catalog_lines",
    "_append_workflow_completion_lines",
    "_blocked_actions_for_report",
    "_command_briefing_export",
    "_command_briefing_preview",
    "_command_dashboard_render",
    "_command_demo_no_send_e2e",
    "_command_dispatch_morning",
    "_command_knowledge_edge_flag_false_positive",
    "_command_knowledge_edge_queue_show",
    "_command_knowledge_edge_scan",
    "_command_priorities_create",
    "_command_priorities_list",
    "_command_priorities_update",
    "_command_routines_create",
    "_command_routines_list",
    "_command_routines_update",
    "_command_run_morning",
    "_command_scheduler_jobs",
    "_command_scheduler_preview",
    "_command_scheduler_run",
    "_command_scheduler_seed_dev",
    "_command_side_effects_record_dry_run",
    "_command_side_effects_summary",
    "_command_status",
    "_command_synthesis_apply",
    "_command_synthesis_preview",
    "_command_today",
    "_command_workflows",
    "_connect_read_only",
    "_connect_read_write",
    "_database_target_report",
    "_database_target_text",
    "_emit_report",
    "_format_cli_error",
    "_format_scalar",
    "_has_text",
    "_human_report",
    "_load_json_object",
    "_loads_json_object",
    "_local_sqlite_changes_text",
    "_merge_synthesis_source_type",
    "_output_target_report",
    "_output_target_text",
    "_parse_json_object_arg",
    "_safety_flags_from_report",
    "_synthesis_rejected_result",
    "_today_iso",
    "_with_workflow_context",
    "_yes_no_unavailable",
    "annotations",
    "apply_synthesis_import_preview",
    "argparse",
    "build_parser",
    "closing",
    "create_external_write_intent_and_record_dry_run",
    "create_priority_flow",
    "create_rail_state_report",
    "create_routine_record",
    "create_status_summary",
    "create_synthesis_import_preview_record",
    "create_today_view_summary",
    "datetime",
    "generate_no_send_briefing_preview",
    "is_under_repo",
    "is_under_temp",
    "json",
    "list_scheduler_jobs",
    "main",
    "os",
    "preview_scheduler_jobs",
    "quote",
    "read_briefing_output",
    "read_priorities",
    "read_routines",
    "render_today_view_html_from_connection",
    "run_scheduler_job_simulated",
    "seed_dev_scheduler_jobs",
    "sqlite3",
    "stable_approval_source_hash",
    "summarize_side_effect_ledgers",
    "sys",
    "update_priority_flow",
    "update_routine_record",
    "validate_existing_input_file_path",
    "validate_existing_sqlite_path",
    "validate_output_file_path",
}


class CliPackageReexportsEverythingTest(unittest.TestCase):
    def test_every_original_name_is_still_importable(self) -> None:
        for name in sorted(ORIGINAL_NAMES):
            self.assertTrue(
                hasattr(cli, name), f"personalos.cli lost name: {name}"
            )

    def test_connect_read_write_is_directly_accessible(self) -> None:
        # tests/test_path_safety.py depends on this exact attribute path.
        self.assertTrue(callable(cli._connect_read_write))

    def test_full_surface_matches_exactly_module_attrs_only(self) -> None:
        # dir() on a package also exposes its own submodules as attributes
        # (e.g. `cli.today`), which is an unavoidable side effect of the
        # module -> package conversion and not part of the original API
        # surface. Note this is distinct from stdlib modules the original
        # single-file module imported directly (json, os, sqlite3, sys,
        # argparse) -- those WERE part of the original namespace and must
        # stay, so we exclude only the new cli/ submodules by name.
        new_submodules = {
            "briefing",
            "db",
            "dispatch",
            "errors",
            "knowledge_edge",
            "parser",
            "priorities",
            "reporting",
            "routines",
            "scheduler",
            "side_effects",
            "synthesis",
            "today",
            "workflows",
        }
        surface = {
            name
            for name in dir(cli)
            if not (name.startswith("__") and name.endswith("__"))
            and name not in new_submodules
        }
        self.assertEqual(surface, ORIGINAL_NAMES)


if __name__ == "__main__":
    unittest.main()
