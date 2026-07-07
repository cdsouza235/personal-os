# MVP Readiness Gap Report

This document describes the inert MVP readiness gap report implemented in
`src/personalos/mvp_readiness.py`.

The report is a repo-local audit surface. It summarizes what has been built,
what remains blocked, and which human decisions are still required before any
live MVP activation path can be considered. It is not a runtime entrypoint and
does not read credentials, inspect protected paths, contact live services,
activate a scheduler, open a production database, call OpenClaw, or write
outside the repo.

## Source Contract

The source module exposes:

- `build_mvp_readiness_gap_report`
- `validate_mvp_readiness_gap_report_contract`
- `MVP_READINESS_SCHEMA_VERSION`
- `MVP_READINESS_STATUS`
- `MVP_READINESS_TOP_LEVEL_FIELDS`
- `COMPLETED_INERT_CAPABILITIES`
- `PENDING_HUMAN_DECISIONS`
- `BLOCKED_LIVE_RAILS`
- `NON_AUTHORIZATION_FALSE_FIELDS`
- `PHASE14C_WIDE_NET_READINESS_PAYLOAD_FIELDS`

The builder accepts no caller input. The report defaults to:

- `readiness.status=not_ready`
- `inert_report_only=true`
- `live_rails_activated=false`
- `live_mvp_ready=false`
- `candidate_review_tracking_only=true`
- `phase14_c_blocked=true`

The contract validator emits only:

- `report_matches_inert_contract=true` when the report exactly matches the
  inert contract.
- `report_matches_inert_contract=false` when the report is absent, tampered,
  malformed, or drifted.

It never emits ready, approved, authorized, activated, or executed status.

## Completed Inert Capabilities

The report records completed repo-local capability groups, including:

- repo-local Python package and tests
- SQLite migrations and local dev/test state surfaces
- routine, priority, today-view, dashboard, report, and briefing foundations
- fake/local Todoist and Calendar preview foundations
- Composer packet and fake model-run foundations
- synthetic no-send end-to-end demo evidence
- pre-live readiness policy and read-only readiness status surfaces
- Phase 14-A/B first live pilot preparation as proposed-only scaffolding
- Phase 14-C candidate-review tracking record
- Phase 14-C decision gate and decision-support report contract
- Phase 14-C supervised smoke and connectivity readiness evidence
- Phase 14-C connected rehearsal gate and live evidence packet
- Phase 14-C wide-net rehearsal plan, fail-closed gate, evidence validators,
  readiness rollup, and contract guardrails

These completed items are evidence of repo-local scaffolding and validation
only. They are not live MVP activation.

## Pending Human Decisions

The report records these pending human decisions:

- candidate approval remains a separate human decision
- Phase 14-C authorization remains a separate human decision
- Phase 14-C wide-net live rehearsal approval remains a separate human decision
- live-service access remains a separate human decision
- Calendar app connector live use remains a separate human decision
- credential/auth handling remains a separate human decision
- production DB activation remains a separate human decision
- scheduler/background activation remains a separate human decision
- OpenClaw handoff or invocation remains a separate human decision

These entries are blockers, not grants.

## Blocked Live Rails

The report records these rails as blocked:

- Gmail
- Todoist
- Google Calendar
- PersonalOS Markdown
- OpenClaw
- credentials
- production DB
- scheduler/background
- live model/API
- protected paths
- dynamic cleaning
- Watch Tower
- `.agent`
- `CLAUDE.md`
- runtime/operator scaffolding

## Phase 14-C Boundary

The report composes the Phase 14-C decision-support report contract. It records
that the decision-support report remains `decision_needed`, validates as the
unfilled false-default decision record, keeps candidate-review tracking only,
and keeps Phase 14-C blocked.

The report records these fields as false:

- `human_decision_recorded`
- `candidate_approved`
- `candidate_authorized`
- `candidate_activated`
- `candidate_run`

The report also composes the Phase 14-C wide-net readiness rollup contract. It
records that the wide-net rollup contract is valid and repo-local, while still
keeping:

- `ready_for_live_execution=false`
- `wide_net_live_run_authorized_by_this_report=false`
- `calendar_cli_connector_wiring_present=false`
- `calendar_connector_readiness_available=true`
- `calendar_connector_readiness_contract_valid=true`
- `calendar_operator_packet_available=true`
- `calendar_operator_packet_contract_valid=true`
- `credential_values_read=false`
- `external_mutation=false`
- `readiness_status=not_ready`
- `inert_report_only=true`
- `live_rails_activated=false`

The wide-net payload is a status summary only. It does not authorize the
future wide-net live run, wire the Calendar app connector, read credentials, or
perform external mutation.

## Non-Authorization

The report includes `approval_to_merge_docs_is_not_live_authorization=true`.
That field means a repo merge is not live authorization.

Every `NON_AUTHORIZATION_FALSE_FIELDS` entry must remain false, including
Phase 14-C authorization, candidate approval, candidate authorization,
candidate activation, candidate run, live-service access, credential reads,
production DB activation, scheduler/background activation, OpenClaw calls,
external services, external mutation, protected paths, live model/API calls,
dynamic cleaning, Watch Tower adoption, `.agent`, `CLAUDE.md`, and
runtime/operator scaffolding.

This packet does not approve Phase 14-C, approve a candidate, authorize a
candidate, activate or run a candidate, authorize live service access, handle
credentials, activate production DB, activate scheduler/background behavior,
invoke OpenClaw, touch protected paths, implement dynamic cleaning, adopt Watch
Tower, add `.agent/`, add `CLAUDE.md`, or add runtime/operator scaffolding.

## Validation Coverage

`tests/test_mvp_readiness.py` verifies:

- the default report is inert and `not_ready`
- the top-level report shape is exact
- the builder accepts no caller input
- the default timestamp is deterministic
- nested readiness, Phase 14-C, and non-authorization payload shapes are exact
- the Phase 14-C wide-net readiness payload composes the rollup contract while
  preserving no-live readiness
- completed inert capabilities, pending human decisions, and blocked live
  rails match the source constants
- non-authorization false fields remain false
- drifted reports fail closed without echoing caller-controlled values in
  validator output

`tests/test_mvp_readiness_docs.py` verifies that this document is linked from
the primary navigation and status documents and that the documented posture
remains inert, not-ready, and non-authorizing.
