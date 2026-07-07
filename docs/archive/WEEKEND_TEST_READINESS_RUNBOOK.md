# Weekend Test Readiness Runbook

This document records the repo-local, inert readiness runbook for a future
weekend testing pass. It is implemented as a report-only contract in
`src/personalos/weekend_test_readiness.py`.

This runbook does not start weekend testing, does not authorize live-service
testing, does not approve Phase 14-C, does not approve a candidate, does not
authorize a candidate, does not activate or run a candidate, does not
authorize live-service access, does not handle credentials, does not activate
production DB, does not activate scheduler/background behavior, does not
invoke OpenClaw, does not touch protected paths, does not implement dynamic
cleaning, does not adopt Watch Tower, does not add `.agent`, does not add
`CLAUDE.md`, and does not add runtime/operator scaffolding.

## Source Contract

The source module exposes:

- `build_weekend_test_readiness_report`
- `validate_weekend_test_readiness_report_contract`
- `WEEKEND_TEST_READINESS_SCHEMA_VERSION`
- `WEEKEND_TEST_READINESS_STATUS`
- `WEEKEND_TEST_READINESS_TOP_LEVEL_FIELDS`
- `SOURCE_DOCUMENTS`
- `MANUAL_TEST_CATEGORIES`
- `EVIDENCE_TEMPLATES`
- `NO_GO_CRITERIA`
- `ROLLBACK_REHEARSAL_TEMPLATES`
- `NON_AUTHORIZATION_FALSE_FIELDS`

The builder accepts no caller input. The report defaults to:

- `status=test_plan_recorded_not_live`
- `weekend_testing_started=false`
- `live_testing_authorized=false`
- `live_mvp_ready=false`
- `human_gates_remaining=true`
- `inert_report_only=true`
- `readiness.status=not_ready`
- `inert_report_only=true`
- `live_rails_activated=false`

The validator returns only `report_matches_inert_contract=true` or
`report_matches_inert_contract=false`. It never emits ready, approved,
authorized, activated, executed, or live status.

## Source Documents

The weekend test readiness report is anchored to these repo-local documents:

- [PRE_LIVE_READINESS.md](PRE_LIVE_READINESS.md)
- [ACTIVATION_CHECKLIST.md](ACTIVATION_CHECKLIST.md)
- [FIRST_LIVE_PILOT_PROTOCOL.md](FIRST_LIVE_PILOT_PROTOCOL.md)
- [LIVE_RAIL_ACTIVATION_POLICY.md](LIVE_RAIL_ACTIVATION_POLICY.md)
- [OPERATOR_HANDOFF_CONTRACT.md](OPERATOR_HANDOFF_CONTRACT.md)
- [NON_HUMAN_CLOSURE_PLAN.md](NON_HUMAN_CLOSURE_PLAN.md)

Those documents remain policy and planning surfaces. Linking them here does
not complete the activation checklist, select a live pilot, approve a live
rail, approve a production DB path, approve credential handling, approve
OpenClaw handoff, or approve a go/no-go launch decision.

## Manual Test Categories

The report records these future manual test categories:

1. Repo validation capture.
2. Readiness status capture.
3. Activation checklist review.
4. First-live pilot protocol review.
5. Live rail policy review.
6. Operator handoff boundary review.
7. No-go and halt review.
8. Rollback tabletop review.

Every manual test category has:

- `evidence_required=true`
- `contains_human_decision=false`
- `contains_live_access=false`
- `credentials_required=false`
- `production_db_required=false`
- `scheduler_required=false`
- `openclaw_required=false`

The categories are evidence-preparation categories only. They do not record
human approval, perform live-service tests, inspect credentials, activate
production DB, start schedulers, call OpenClaw, or touch protected paths.

## Evidence Templates

The report records templates for:

- Validation evidence.
- Readiness evidence.
- Dry-run preview evidence.
- Rollback tabletop evidence.

Each evidence template requires fixed field labels only. The templates require:

- `captures_secret_values=false`
- `records_live_object_ids=false`
- `authorizes_live_access=false`

Future evidence may reference labels, commands, status values, and redacted
artifacts, but must not include raw credentials, OAuth tokens, API keys,
secret values, or broad protected content.

## No-Go Criteria

The report records no-go criteria for the future testing pass. The pass must
stop before live work if any of these conditions appear:

- `readiness.status` is anything other than `not_ready` before explicit live
  approval.
- Any live rail reports activated before approval.
- Any credential, OAuth token, API key, or secret handling is required.
- Any production DB path is needed or inferred.
- Any scheduler, LaunchAgent, crontab, daemon, watcher, or background loop is
  needed.
- OpenClaw handoff or invocation is requested without a separate approved
  handoff.
- Protected path access is needed.
- Dry-run evidence is missing, stale, or uses different input than the
  proposed pilot.
- Rollback or recovery behavior is ambiguous.
- Go/no-go launch approval is missing.

## Rollback Tabletop Templates

The rollback section is rehearsal-only. It records tabletop templates for:

- Todoist rollback.
- Google Calendar rollback.
- Gmail draft recovery.
- Production DB restore.

Every rollback template has:

- `rehearsal_only=true`
- `live_action_authorized=false`

The templates prepare questions and evidence labels. They do not delete,
close, reopen, annotate, cancel, update, restore, migrate, or otherwise mutate
any live system.

## Human Gates

The weekend test readiness track keeps the human gates from
[NON_HUMAN_CLOSURE_PLAN.md](NON_HUMAN_CLOSURE_PLAN.md) explicit:

- candidate approval remains a separate human decision
- Phase 14-C authorization remains a separate human decision
- live-service access remains a separate human decision
- credential/auth handling remains a separate human decision
- production DB activation remains a separate human decision
- scheduler/background activation remains a separate human decision
- OpenClaw handoff or invocation remains a separate human decision
- actual live-service testing remains a separate human-gated activity
- go/no-go launch approval remains a separate human decision

Those gates are not completed by this runbook.

## Non-Authorization

The report includes:

- `weekend_runbook_is_not_live_testing_authorization=true`
- `repo_merge_is_not_live_authorization=true`

Every `NON_AUTHORIZATION_FALSE_FIELDS` entry must remain false, including
Phase 14-C authorization, candidate approval, candidate authorization,
candidate activation, candidate run, live testing authorization, live-service
access, credential reads, production DB activation, scheduler/background
activation, OpenClaw calls, external services, external mutation, protected
paths, live model/API calls, dynamic cleaning, Watch Tower adoption, `.agent`,
`CLAUDE.md`, and runtime/operator scaffolding.

## Validation Coverage

`tests/test_weekend_test_readiness.py` verifies:

- the report builder accepts no caller input
- the default report is inert and `test_plan_recorded_not_live`
- the non-human closure plan is composed without authorizing live work
- source documents, manual test categories, evidence templates, no-go
  criteria, rollback templates, human gates, blocked rails, and
  non-authorization fields match the static contract
- drifted reports fail closed without echoing caller-controlled values
- boolean-lookalike values are rejected for safety flags

`tests/test_weekend_test_readiness_docs.py` verifies that this document is
linked from the primary project docs and preserves the non-live, non-secret,
non-authorization, human-gate, no-go, and rollback-tabletop boundaries.

The follow-on non-human packet is
[DRY_RUN_EVIDENCE_BUNDLE.md](DRY_RUN_EVIDENCE_BUNDLE.md), which records the
temp-only no-send evidence contract and completion-report validator without
starting weekend testing or authorizing live access.
