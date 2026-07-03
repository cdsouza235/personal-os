# Non-Human Closure Plan

This document records the accelerated Codex/Fable + Claude Code operating plan
for closing the remaining repo-local, non-human Personal OS work.

The plan is implemented as an inert report contract in
`src/personalos/nonhuman_closure.py`. It is a planning and audit surface only.
It does not approve Phase 14-C, does not approve a candidate, does not
authorize a candidate, does not activate or run a candidate, does not
authorize live-service access, does not handle credentials, does not activate
production DB, does not activate scheduler/background behavior, does not invoke
OpenClaw, does not touch protected paths, does not implement dynamic cleaning,
does not adopt Watch Tower, does not add `.agent/`, does not add `CLAUDE.md`,
and does not add runtime/operator scaffolding.

## Source Contract

The source module exposes:

- `build_nonhuman_closure_plan_report`
- `validate_nonhuman_closure_plan_report_contract`
- `NONHUMAN_CLOSURE_SCHEMA_VERSION`
- `NONHUMAN_CLOSURE_STATUS`
- `NONHUMAN_CLOSURE_TOP_LEVEL_FIELDS`
- `NONHUMAN_CLOSURE_PACKET_PLAN`
- `HUMAN_REQUIRED_GATES`
- `BLOCKED_LIVE_RAILS`
- `NON_AUTHORIZATION_FALSE_FIELDS`

The builder accepts no caller input. The report defaults to:

- `status=blocked_by_human_gates`
- `nonhuman_closure_complete=false`
- `live_mvp_ready=false`
- `human_gates_remaining=true`
- `accelerated_packet_model_recorded=true`
- `readiness.status=not_ready`
- `inert_report_only=true`
- `live_rails_activated=false`

The report also composes the MVP readiness gap report, including the current
Phase 14-C wide-net readiness summary. That nested MVP summary keeps:

- `wide_net_rollup_contract_valid=true`
- `wide_net_ready_for_live_execution=false`
- `wide_net_live_run_authorized_by_this_report=false`
- `wide_net_calendar_cli_connector_wiring_present=false`
- `wide_net_credential_values_read=false`
- `wide_net_external_mutation=false`
- `wide_net_readiness_status=not_ready`
- `wide_net_live_rails_activated=false`

Those fields are status evidence only. They do not authorize the future
wide-net live run, Calendar app connector use, credential handling, or
external mutation.

The validator returns only `report_matches_inert_contract=true` or
`report_matches_inert_contract=false`. It never emits ready, approved,
authorized, activated, executed, or live status.

## Accelerated Packet Model

For the current long-run loop, Codex/Fable should aim to finish the remaining
safe non-human repo-local work in three to five large packets, each followed by
Claude Code read-only audit before delegated merge conditions are evaluated.

The packet unit is intentionally larger than a micro-invariant. Each packet may
combine adjacent repo-local source, tests, docs, status updates, validator
hardening, runbooks, fake/local fixtures, dry-run evidence, and audit bundle
work while the work remains inert, deterministic, testable, non-live, and
inside the approved envelope.

## Packet Plan

The current report records five packet slots:

1. MVP readiness gap report: merged on `main` after Claude Code audit.
2. Non-human closure plan: merged on `main` after Claude Code audit.
3. [Weekend test readiness runbook](WEEKEND_TEST_READINESS_RUNBOOK.md):
   merged on `main` after Claude Code audit, covering manual
   test plan, no-go criteria, rollback checklist, and evidence templates.
4. [Dry-run evidence bundle](DRY_RUN_EVIDENCE_BUNDLE.md): merged on `main`
   after Claude Code audit, covering local no-send smoke commands, fake/local
   fixtures, and report validators.
5. [Final non-human handoff](FINAL_NONHUMAN_HANDOFF.md): merged on `main`
   after Claude Code audit, covering final non-human closure report, the
   wide-net blocked gate summary, and exact human gate checklist.

Every packet in this plan has:

- `claude_code_audit_required=true`
- `contains_human_decision=false`
- `contains_live_access=false`

## Human Gates

The non-human closure track does not remove human gates. It makes them more
explicit.

The report records these gates as human-required:

- candidate approval remains a separate human decision
- Phase 14-C authorization remains a separate human decision
- live-service access remains a separate human decision
- credential/auth handling remains a separate human decision
- production DB activation remains a separate human decision
- scheduler/background activation remains a separate human decision
- OpenClaw handoff or invocation remains a separate human decision
- actual live-service testing remains a separate human-gated activity
- go/no-go launch approval remains a separate human decision

Those gates are the work for Chris + ChatGPT/Codex after the non-human
repo-local packets are complete. They are not inside the non-human packet
track.

## Blocked Live Rails

The non-human closure report keeps these rails blocked:

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

## Non-Authorization

The report includes:

- `repo_merge_is_not_live_authorization=true`
- `nonhuman_closure_is_not_product_approval=true`

Every `NON_AUTHORIZATION_FALSE_FIELDS` entry must remain false, including
Phase 14-C authorization, candidate approval, candidate authorization,
candidate activation, candidate run, live-service access, credential reads,
production DB activation, scheduler/background activation, OpenClaw calls,
external services, external mutation, protected paths, live model/API calls,
dynamic cleaning, Watch Tower adoption, `.agent`, `CLAUDE.md`, and
runtime/operator scaffolding.

## Validation Coverage

`tests/test_nonhuman_closure.py` verifies:

- the report builder accepts no caller input
- the default report is inert and `blocked_by_human_gates`
- the MVP readiness gap report remains composed and valid
- the nested MVP wide-net readiness gates remain blocked
- the packet plan has five safe audited packet slots
- human gates and blocked live rails are explicit
- non-authorization flags remain false
- drifted reports fail closed without echoing caller-controlled values

`tests/test_nonhuman_closure_docs.py` verifies that this document is linked
from the primary project docs and preserves the accelerated packet model,
human-gate separation, blocked rails, and non-authorization wording.
