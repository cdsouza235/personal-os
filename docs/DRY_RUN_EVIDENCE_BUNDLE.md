# Dry-Run Evidence Bundle

This document records the repo-local, inert dry-run evidence contract for the
non-human closure loop. It is implemented as a report-only contract in
`src/personalos/dry_run_evidence.py`.

This bundle does not start weekend testing, does not authorize live-service
testing, does not approve Phase 14-C, does not approve a candidate, does not
authorize a candidate, does not activate or run a candidate, does not
authorize live-service access, does not handle credentials, does not activate
production DB, does not activate scheduler/background behavior, does not
invoke OpenClaw, does not touch protected paths, does not implement dynamic
cleaning, does not adopt Watch Tower, does not add `.agent`, does not add
`CLAUDE.md`, and does not add runtime/operator scaffolding.

## Source Contract

The source module exposes:

- `build_dry_run_evidence_bundle_report`
- `validate_dry_run_evidence_bundle_report_contract`
- `validate_no_send_completion_report_contract`
- `DRY_RUN_EVIDENCE_SCHEMA_VERSION`
- `DRY_RUN_EVIDENCE_STATUS`
- `DRY_RUN_EVIDENCE_TOP_LEVEL_FIELDS`
- `NO_SEND_COMPLETION_REPORT_FIELDS`
- `NO_SEND_SAFETY_ASSERTION_FIELDS`
- `SMOKE_COMMAND_TEMPLATES`
- `FAKE_LOCAL_FIXTURE_SURFACES`
- `NON_AUTHORIZATION_FALSE_FIELDS`

The builder accepts no caller input. The report defaults to:

- `status=dry_run_contract_recorded_not_live`
- `dry_run_execution_started=false`
- `repo_evidence_bundle_written=false`
- `temp_only_smoke_supported=true`
- `live_mvp_ready=false`
- `human_gates_remaining=true`
- `readiness.status=not_ready`
- `inert_report_only=true`
- `live_rails_activated=false`

The validator returns only `report_matches_inert_contract=true` or
`report_matches_inert_contract=false`. It never emits ready, approved,
authorized, activated, executed, or live status.

## No-Send Demo Contract

The dry-run evidence bundle records the existing Phase 13E-D no-send demo
contract:

```bash
PYTHONPATH=src python3 -m personalos.cli demo no-send-e2e --output-dir <safe_output_dir> --json
```

The command must use an explicit safe temp output directory. The evidence DB
is named `demo.sqlite3` and must stay under the safe output directory. The
contract keeps:

- `requires_explicit_safe_output_dir=true`
- `output_dir_must_be_temp=true`
- `repo_local_var_allowed=false`
- `repo_local_db_allowed=false`
- `writes_repo_files=false`
- `external_writes_allowed=false`

The source contract imports the existing artifact-name contract from
`src/personalos/demo/no_send_e2e.py` so drift in the no-send evidence bundle
surface is visible to tests.

## Smoke Command Templates

The report records only non-live command templates:

- `phase13e_d_no_send_e2e`
- `readiness_status_json`
- `workflow_catalog_json`

Every smoke command template has:

- `requires_credentials=false`
- `uses_production_db=false`
- `activates_scheduler=false`
- `calls_openclaw=false`
- `external_write=false`

The no-send demo template is allowed to write only inside the explicit safe
temp output directory. Readiness and workflow catalog templates are
report-only.

## Fake And Local Fixture Surfaces

The report records the fake/local surfaces used as evidence anchors:

- Todoist simulated write fake client.
- Google Calendar simulated write fake client.
- Composer fake model adapter.
- Synthetic ChatGPT synthesis fixture.
- Side-effect dry-run ledger.
- Scheduler simulated preview.

Every fake/local fixture surface has:

- `fake_or_preview_only=true`
- `live_client_allowed=false`
- `credential_required=false`
- `external_write=false`

These surfaces are not live clients and do not authorize live rails.

## Completion Report Validator

`validate_no_send_completion_report_contract` validates a completion report
from the existing no-send demo without reading artifact files. It checks:

- exact top-level completion report field shape
- demo name, phase name, command contract, completed status, and summary status
- artifact names and artifact path keys
- safety assertion field shape and values
- no-send export summary
- blocked live-action summary
- `phase_14_blocked=true`
- `deviations=[]`

The completion report validator requires:

- `readiness.status=not_ready`
- `inert_report_only=true`
- `live_rails_activated=false`
- `credentials_loaded=false`
- `credentials_read=false`
- `production_db_path_active=false`
- `scheduler_activated=false`
- `launch_agent_installed=false`
- `crontab_modified=false`
- `daemon_started=false`
- `openclaw_called=false`
- `external_services_contacted=false`
- `external_mutation=false`
- `gmail_touched=false`
- `todoist_touched=false`
- `calendar_touched=false`
- `personalos_markdown_written=false`
- `protected_paths_touched=false`
- `scheduler_preview_status=simulated_preview_only`
- `operator_status_readiness=not_ready`
- `operator_status_live_rails_activated=false`
- `all_required_assertions_passed=true`

The validator is non-echoing: caller-controlled unsafe report values must not
appear in serialized validation output.

## Human Gates

The dry-run evidence track keeps the human gates explicit:

- candidate approval remains a separate human decision
- Phase 14-C authorization remains a separate human decision
- live-service access remains a separate human decision
- credential/auth handling remains a separate human decision
- production DB activation remains a separate human decision
- scheduler/background activation remains a separate human decision
- OpenClaw handoff or invocation remains a separate human decision
- actual live-service testing remains a separate human-gated activity
- go/no-go launch approval remains a separate human decision

Those gates are not completed by this bundle.

## Non-Authorization

The report includes:

- `dry_run_bundle_is_not_live_testing_authorization=true`
- `repo_merge_is_not_live_authorization=true`

Every `NON_AUTHORIZATION_FALSE_FIELDS` entry must remain false, including
Phase 14-C authorization, candidate approval, candidate authorization,
candidate activation, candidate run, live testing authorization, live-service
access, credential reads, production DB activation, scheduler/background
activation, OpenClaw calls, external services, external mutation, protected
paths, live model/API calls, dynamic cleaning, Watch Tower adoption, `.agent`,
`CLAUDE.md`, and runtime/operator scaffolding.

## Validation Coverage

`tests/test_dry_run_evidence.py` verifies:

- the report builder accepts no caller input
- the default report is inert and `dry_run_contract_recorded_not_live`
- the weekend test readiness contract is composed without starting testing
- the no-send demo contract matches existing artifact names
- smoke command templates are non-live and credential-free
- fake/local fixture surfaces are preview-only
- completion report contract fields and safety assertions are non-authorizing
- drifted reports fail closed without echoing caller-controlled values
- boolean-lookalike values are rejected for safety flags
- a real temp-only Phase 13E-D no-send demo completion report validates
- tampered no-send completion reports fail closed without echoing unsafe values

`tests/test_dry_run_evidence_docs.py` verifies that this document is linked
from the primary project docs and preserves the non-live, non-secret,
fake/local, no-send, human-gate, completion-report, and non-authorization
boundaries.
