# Phase 14-C Candidate Decision Support

Last updated: 2026-06-25

## Purpose

This document is a repo-local, docs/test-only decision-support artifact for
future human review of the currently recorded Phase 14-C candidate. It makes a
future approve/reject/defer decision easier to inspect without making that
decision.

This document is inert and unfilled. It does not authorize execution, does not
authorize live service access, and does not authorize runtime behavior.
Future explicit human approval required before any movement beyond
candidate-review tracking only.

## Current Candidate Context

- Candidate: `Clean Kitchen Countertops and Stovetop`
- Weekday: `Monday`
- Area: `Kitchen`
- Candidate type: household cleaning routine task
- Status: candidate-review tracking only
- Candidate selected for live execution: no
- Candidate approved: no
- Candidate authorized: no
- Candidate activated or run: no
- Phase 14-C remains blocked
- `readiness.status=not_ready`
- `inert_report_only=true`
- `live_rails_activated=false`

The candidate exists only so Chris can review one concrete future option. It is
not a Todoist task creation request and not a live pilot approval.

## Current Blocked Posture

Personal OS remains inert, no-send, and report-only. Phase 14-C remains
blocked. The current state is candidate-review tracking only.

The repo may document evidence requirements, decision options, and
false-default templates. It must not approve, authorize, activate, run,
schedule, import, synchronize, mutate, or execute anything.

## What Candidate-Review Tracking Only Means

Candidate-review tracking only means:

- one future candidate has been recorded for later human review;
- the candidate context can be referenced in repo docs and tests;
- review checklists and evidence requirements can be documented;
- false-default decision templates can be prepared;
- Chris still has not made a product, execution, live-service, or runtime
  decision.

Candidate-review tracking only does not approve Phase 14-C, approve the
candidate, authorize the candidate, activate or run the candidate, authorize
Todoist/Gmail/Calendar access, or authorize live service access.

## What This Document Does Not Authorize

This document does not authorize:

- Phase 14-C approval;
- candidate approval;
- candidate authorization;
- candidate activation or execution;
- Todoist access or writes;
- Gmail access or writes;
- Calendar access or writes;
- OpenClaw handoff or invocation;
- credentials/auth handling;
- production DB activation;
- scheduler/background activation;
- LaunchAgent, crontab, daemon, watcher, or service activation;
- protected path access;
- external PersonalOS runtime writes;
- external writes;
- live model/API calls;
- dynamic cleaning implementation;
- 15-task cleaning import;
- skip/push/bump behavior;
- automatic rescheduling;
- Watch Tower adoption;
- `.agent/`;
- `CLAUDE.md`;
- runtime/operator scaffolding.

## Decision Options For Future Human Review

This document does not select any option. A future human decision may choose
one of these options:

- Approve for a later bounded repo-local prep packet. This would allow only
  the exact repo-local docs/tests/fake/dry-run scope Chris names later.
  It would not authorize execution or live service access.
- Reject candidate. This would record that `Clean Kitchen Countertops and
  Stovetop` should not continue as the Phase 14-C candidate under review.
- Defer / keep blocked. This would keep the candidate-review tracking record
  while preserving the blocked posture.

Any future approval must be explicit, narrow, and separate from approval to
merge this documentation.

## Candidate Review Checklist

Review all of the following before any future decision:

- Scope clarity: the candidate remains a single, self-only, low-risk household
  cleaning routine task with no external recipient.
- Household usefulness: the task remains useful enough to justify later
  bounded prep, manual validation, or rejection.
- Safety boundaries: no Todoist/Gmail/Calendar access or writes are needed for
  the review itself.
- Ambiguity risks: the task title, weekday, area, recurrence expectation, and
  success criteria are clear enough for a later bounded packet.
- Expected manual validation: Chris can manually confirm the candidate,
  wording, recurrence assumptions, stop conditions, and rollback expectations.
- Before future approval: the repo must still report `readiness.status=not_ready`,
  `inert_report_only=true`, and `live_rails_activated=false`, and tests must
  preserve the non-authorization invariants.
- Separately gated even after approval: live rails, credential/auth handling,
  production DB paths, protected paths, scheduler/background behavior,
  OpenClaw, live model/API calls, dynamic cleaning, Watch Tower artifacts, and
  runtime/operator scaffolding remain separate gates.

Missing, ambiguous, or unsafe evidence means defer / keep blocked.

## Failure-Mode / Risk Checklist

Stop and keep Phase 14-C blocked if any of these appear:

- wording can be read as Phase 14-C approved;
- wording can be read as candidate approved;
- wording can be read as candidate authorized;
- wording can be read as candidate activated or run;
- wording can be read as live access authorized;
- a future packet would need Todoist/Gmail/Calendar access;
- a future packet would need OpenClaw;
- a future packet would need credentials/auth material;
- a future packet would need production DB activation;
- a future packet would need scheduler/background activation;
- a future packet would need protected path access;
- a future packet would need external writes;
- a future packet would need live model/API calls;
- a future packet would implement dynamic cleaning;
- a future packet would import the 15-task cleaning list;
- a future packet would implement skip/push/bump behavior;
- a future packet would implement automatic rescheduling;
- a future packet would adopt Watch Tower, add `.agent/`, add `CLAUDE.md`, or
  add runtime/operator scaffolding.

## Required Future Approval Wording

Any future approval must state all of the following in plain language:

- Decision option: approve for a later bounded repo-local prep packet, reject
  candidate, defer / keep blocked, or open a separate live authorization review.
- Candidate: `Clean Kitchen Countertops and Stovetop`.
- Allowed next packet: exact scope only.
- Allowed files or rails: none unless Chris explicitly names them.
- Evidence reviewed: exact docs, tests, readiness output, dry-run output, and
  rollback/stop evidence reviewed.
- Still blocked: every live rail, credential/auth path, production DB,
  protected path, scheduler/background behavior, OpenClaw path, live model/API
  path, dynamic cleaning behavior, Watch Tower artifact, and runtime/operator
  scaffold not explicitly named.

Approval to merge this decision-support artifact only adds documentation and
tests. It does not authorize Phase 14-C, approve the candidate, authorize
candidate execution, authorize Todoist/Gmail/Calendar access, invoke OpenClaw,
handle credentials/auth, activate production DB, activate
schedulers/background loops, implement dynamic cleaning, adopt Watch Tower,
add `.agent/`, add `CLAUDE.md`, or add runtime/operator scaffolding.

## Inert Validator Behavior

`src/personalos/phase14c_candidate_decision_support.py` validates only the
unfilled false-default decision-support record. It is a repo-local report
helper, not a runtime path.

- `blank_phase14c_candidate_decision_support_record` returns the unfilled
  false-default decision-record template with `readiness.status=not_ready`.
- `validate_phase14c_candidate_decision_record` accepts only the unfilled
  template shape as `decision_needed`; it blocks any selected decision option,
  human decision marker, approval flag, authorization flag, activation flag,
  live-service flag, credential/secret field, live object ID, unknown schema
  field, candidate drift, dynamic cleaning flag, Watch Tower flag, `.agent/`
  flag, `CLAUDE.md` flag, or runtime/operator scaffolding flag.
- `build_phase14c_candidate_decision_support_report` returns an inert report
  with `phase14_c_blocked=true`, `candidate_review_tracking_only=true`,
  `readiness.status=not_ready`, `inert_report_only=true`, and
  `live_rails_activated=false`.
- `render_phase14c_candidate_decision_support_checklist` renders the same
  non-authorization boundary for review.

The validator has no Todoist, Gmail, Calendar, OpenClaw, credential,
production DB, scheduler/background, protected-path, external-write, live
model/API, Watch Tower, `.agent/`, `CLAUDE.md`, dynamic cleaning, or
runtime/operator path. The decision-record schema is strict: an extra
top-level key or unknown container blocks the record instead of treating it as
accepted. A nested payload under a known fillable field, such as `notes`, is
also blocked because filling any decision-record field would record a human
decision outside this packet. Table-driven invariant coverage verifies that
every fillable decision field blocks when filled, every required false field
blocks when truthy, the known schema fields match the false-default template,
and validator statuses remain limited to `decision_needed` or `blocked`.
Report-level coverage verifies that blocked reports do not echo unsafe input
values and that default report timestamps remain deterministic unless
explicitly overridden. Report shape contract coverage keeps top-level report
fields and validation payload fields explicit, including checks that raw
decision-record echo fields are absent. Missing-field matrix coverage verifies
that every required text default and every required false field fails closed as
`decision_needed` when absent. Blocked-reason sanitization keeps
caller-supplied decision and drift values out of blocked report JSON while
still reporting the blocked field names. Unknown schema key-name sanitization
keeps caller-supplied unknown keys out of blocked report JSON while still
failing closed on unknown schema fields. Blocked report sanitization matrix
coverage verifies representative unknown-schema, decision-selection,
candidate-drift, and nested-fillable payload inputs do not echo
caller-controlled tokens. Nested prohibited-field coverage verifies that
caller-controlled nested live/API and credential/secret values stay out of
blocked report JSON. Strict required-false-field coverage verifies that
non-boolean false-like values are blocked instead of accepted as the unfilled
false-default template. Strict required-text-default coverage verifies that
case/spacing variants are blocked instead of accepted as the unfilled
template.
Strict readiness.status coverage verifies that case/spacing variants are
blocked instead of accepted as `readiness.status=not_ready`, and that
caller-controlled readiness drift values stay out of blocked report JSON.
Required readiness.status coverage verifies that the false-default template
contains `readiness.status=not_ready` and that a missing readiness status
fails closed as `decision_needed`.

## Stop Conditions

Stop and report back instead of continuing if:

- the starting checkpoint is not clean;
- `main` and `origin/main` do not match before a bounded packet starts;
- any open PR appears when the packet requires none;
- the work appears to require runtime code changes;
- the work appears to require a real candidate approval, rejection, or defer
  decision;
- any wording could be interpreted as approval, authorization, activation,
  execution, or live service access;
- any test failure requires architectural, product, safety, or workflow
  judgment;
- any path suggests credentials/auth, protected paths, production DB,
  OpenClaw, scheduler/background behavior, Todoist/Gmail/Calendar, live
  model/API behavior, external writes, Watch Tower adoption, `.agent/`,
  `CLAUDE.md`, or runtime/operator scaffolding.

## Related Decision Gate

The controlling decision-gate artifact remains
[PHASE_14C_DECISION_GATE.md](PHASE_14C_DECISION_GATE.md). This document adds a
review checklist and an unfilled decision-record template for the same
non-authorizing boundary.

## Unfilled Decision-Record Template

This template is inert and unfilled by default. It does not approve anything,
authorize anything, activate anything, or run anything. Do not fill it in
unless Chris gives future explicit human approval required for the exact
decision being recorded.

```yaml
schema_version: phase14c_candidate_decision_support.v1
decision_status: unfilled
decision_option: unselected
decision_date:
decision_maker:
candidate: Clean Kitchen Countertops and Stovetop
weekday: Monday
area: Kitchen
current_status: candidate-review tracking only
readiness.status: not_ready
approval_wording_provided: false
evidence_review_complete: false
manual_validation_complete: false
phase14_c_approved: false
candidate_approved: false
candidate_authorized: false
candidate_activated: false
candidate_run: false
candidate_execution_authorized: false
live_rails_activated: false
todoist_access_authorized: false
todoist_write_authorized: false
gmail_access_authorized: false
gmail_write_authorized: false
calendar_access_authorized: false
calendar_write_authorized: false
openclaw_authorized: false
credentials_auth_handling_authorized: false
production_db_activation_authorized: false
scheduler_background_activation_authorized: false
protected_path_access_authorized: false
external_writes_authorized: false
live_model_api_calls_authorized: false
dynamic_cleaning_authorized: false
fifteen_task_import_authorized: false
skip_push_bump_behavior_authorized: false
automatic_rescheduling_authorized: false
watch_tower_adoption_authorized: false
agent_directory_authorized: false
claude_md_authorized: false
runtime_operator_scaffolding_authorized: false
future_packet_scope:
manual_validation_expected:
remaining_separate_gates:
stop_conditions_reviewed:
notes:
```
