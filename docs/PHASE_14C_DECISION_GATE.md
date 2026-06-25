# Phase 14-C Candidate Decision Gate

Last updated: 2026-06-25

## Purpose

This document is a repo-local, docs/test-only decision gate for future
Phase 14-C candidate review. It records what is already known, what remains
blocked, what evidence must be reviewed before any future decision, and what
exact human approval would be required before moving beyond
candidate-review tracking only.

This gate does not approve Phase 14-C, does not approve the candidate, does
not authorize execution, does not authorize live service access, and does not
activate any runtime behavior.

The companion decision-support artifact is
[PHASE_14C_CANDIDATE_DECISION_SUPPORT.md](PHASE_14C_CANDIDATE_DECISION_SUPPORT.md).
It adds an inert review checklist and unfilled decision-record template for
the same blocked candidate posture. The companion inert validator lives in
`src/personalos/phase14c_candidate_decision_support.py` and validates only the
unfilled false-default template/report state; it does not record a decision.
Its contract manifest is structured inert audit metadata only and does not
approve, authorize, activate, execute, or grant live-service access. The
inert report embeds that same static manifest for auditability without
echoing unsafe caller-controlled input. Its report-contract validator checks
in-memory reports against that static contract and fails closed on tampering
without echoing unsafe report keys or values. Matrix coverage keeps absent
reports, shape drift, inert flag drift, raw-echo fields, and validation
payload mismatch fail-closed.

## Current Recorded Candidate

- Candidate: `Clean Kitchen Countertops and Stovetop`
- Weekday: `Monday`
- Area: `Kitchen`
- Candidate type: household cleaning routine task
- Status: candidate-review tracking only
- Candidate selected for live execution: no
- Candidate is not approved.
- Candidate is not authorized.
- Candidate is not activated or run.
- Phase 14-C remains blocked.
- `readiness.status=not_ready`
- `inert_report_only=true`
- `live_rails_activated=false`

The candidate was recorded so Chris can review one concrete future option
later. The record is not a live pilot approval and is not a Todoist task
creation request.

## Current Posture

Personal OS remains inert, no-send, and report-only. Phase 14-C remains
blocked. Candidate-review tracking only is the current state.

The repo may contain documentation, tests, inert templates, and fail-closed
validators that preserve the review boundary. It must not contain wording or
behavior that can reasonably be read as approval, authorization, activation,
execution, live service access, or dynamic cleaning implementation. A
decision-support validator may block filled decision records, approval flags,
authorization flags, live-service fields, credentials/secrets, live IDs,
unknown schema fields, candidate drift, dynamic cleaning flags, Watch Tower
flags, `.agent/`, `CLAUDE.md`, and runtime/operator scaffolding flags.

## What Candidate-Review Tracking Means

Candidate-review tracking only means:

- one future candidate has been recorded for later human review;
- the candidate context can be referenced in repo docs and tests;
- the repo can define future evidence requirements and decision templates;
- the repo can preserve fail-closed language and invariant tests;
- Chris still has not made a product or execution decision.

Candidate-review tracking only does not create, schedule, activate, run,
approve, authorize, import, synchronize, or mutate anything.

## What This Does Not Authorize

This decision gate does not authorize:

- Phase 14-C;
- candidate execution;
- candidate approval;
- candidate authorization;
- candidate activation;
- live Todoist access or writes;
- Gmail access;
- Calendar access;
- OpenClaw handoff or invocation;
- credential, secret, OAuth, API-key, token, or auth handling;
- production DB activation;
- scheduler/background behavior;
- LaunchAgent, crontab, daemon, watcher, or service activation;
- protected path access;
- external PersonalOS runtime writes;
- live model/API calls;
- dynamic cleaning implementation;
- 15-task cleaning import;
- skip/push/bump behavior;
- automatic rescheduling;
- Watch Tower adoption;
- `.agent/`;
- `CLAUDE.md`;
- runtime/operator scaffolding.

Summary boundary: no Todoist/Gmail/Calendar/OpenClaw access, no credentials,
no production DB, no scheduler/background/daemon/service activation, no
dynamic cleaning implementation, no 15-task cleaning import, no skip/push/bump
behavior, no automatic rescheduling, no Watch Tower adoption, no `.agent/`,
no `CLAUDE.md`, and no runtime/operator scaffolding.

## Future Human Decision Options

Chris may later choose one of these options. This document does not select any
option.

- Approve for a later bounded repo-local prep packet. This would allow only
  the exact repo-local docs/tests/fake/dry-run scope Chris names. It would not
  authorize live Todoist access or writes.
- Reject candidate. This would record that `Clean Kitchen Countertops and
  Stovetop` is not suitable for Phase 14-C consideration.
- Defer / keep blocked. This would keep the candidate-review tracking record
  without approving any next packet.

Any later movement beyond candidate-review tracking requires future explicit
human approval from Chris for the exact next action. Approval must name the
candidate, the allowed packet type, the allowed files or rails, the evidence
reviewed, and the still-blocked boundaries.

## Required Pre-Approval Checklist

Before Chris decides whether to move beyond candidate-review tracking, review
all of the following evidence:

- `STATUS.md` still reports `readiness.status=not_ready`.
- `STATUS.md` still reports `inert_report_only=true`.
- `STATUS.md` still reports `live_rails_activated=false`.
- `docs/PHASE_14_CANDIDATE_SELECTION_PREP.md` still records the candidate as
  candidate-review tracking only.
- This decision gate still says Phase 14-C remains blocked.
- The candidate is not approved, not authorized, and not activated or run.
- The proposed next packet is explicitly described as repo-local prep,
  rejection, deferment, or a separate live authorization review.
- Any future live authorization review has separate readiness, idempotency,
  ledger, completion-report, stop-condition, and rollback evidence.
- No Todoist/Gmail/Calendar/OpenClaw access is needed for the decision itself.
- No credentials, secrets, OAuth, API keys, tokens, or auth material are
  requested, inspected, loaded, configured, printed, or handled.
- No production DB path, protected path, scheduler, background loop,
  LaunchAgent, crontab, daemon, watcher, or service is needed.
- No dynamic cleaning implementation, 15-task cleaning import,
  skip/push/bump behavior, or automatic rescheduling is included.
- No Watch Tower adoption, `.agent/`, `CLAUDE.md`, or runtime/operator
  scaffolding is included.
- Validation passes with the repo's canonical `PYTHONPATH=src` test commands.

Missing, ambiguous, or unsafe evidence means defer / keep blocked.

## Required Approval Wording

Any future approval must be explicit and narrow. It must include all of these
fields in plain language:

- Decision: approve for later bounded repo-local prep packet, reject candidate,
  defer / keep blocked, or approve a separate Phase 14-C live authorization
  packet.
- Candidate: `Clean Kitchen Countertops and Stovetop`.
- Allowed scope: exact next packet only.
- Allowed rail access: none unless Chris separately names the rail and exact
  live operation.
- Evidence reviewed: exact docs, tests, readiness output, dry-run output, and
  rollback/stop evidence reviewed.
- Still blocked: every live rail, credential/auth path, production DB,
  protected path, scheduler/background behavior, OpenClaw path, dynamic
  cleaning behavior, Watch Tower artifact, and runtime/operator scaffold not
  explicitly named.

Approval to merge a decision-gate PR only memorializes this gate. It does not
approve Phase 14-C, approve the candidate, authorize execution, authorize
Todoist/Gmail/Calendar access, invoke OpenClaw, handle credentials/auth,
activate production DB, activate schedulers/background loops, implement
dynamic cleaning, adopt Watch Tower, add `.agent/`, add `CLAUDE.md`, or add
runtime/operator scaffolding.

## Stop Conditions

Stop and report back instead of continuing if:

- the starting checkpoint is not clean;
- `main` and `origin/main` do not match before a bounded packet starts;
- any open PR appears when the packet requires none;
- the work appears to require runtime code changes;
- the work appears to require safety-policy judgment beyond documenting a
  gate;
- any wording could be interpreted as approval, authorization, activation, or
  execution;
- any test failure requires architectural, product, safety, or workflow
  judgment;
- any path suggests credentials/auth, protected paths, production DB,
  OpenClaw, scheduler/background behavior, Todoist/Gmail/Calendar, live
  model/API behavior, Watch Tower adoption, `.agent/`, `CLAUDE.md`, or
  runtime/operator scaffolding.

## Safety Boundaries

These safety fields must remain true unless Chris explicitly approves a later
packet that changes them:

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

## Decision Record Template

This template is inert and unfilled by default. It does not approve anything.
Do not fill it in unless Chris gives explicit future approval for the exact
decision being recorded.

```yaml
schema_version: phase14c_candidate_decision_gate.v1
decision_status: unfilled
decision_date:
decision_maker:
candidate: Clean Kitchen Countertops and Stovetop
weekday: Monday
area: Kitchen
current_status: candidate-review tracking only
decision_option: unselected
allowed_next_packet: none
evidence_reviewed: []
phase14_c_approved: false
candidate_approved: false
candidate_authorized: false
candidate_activated_or_run: false
candidate_execution_authorized: false
todoist_access_authorized: false
todoist_write_authorized: false
gmail_access_authorized: false
calendar_access_authorized: false
openclaw_handoff_or_invocation_authorized: false
credentials_auth_handling_authorized: false
production_db_activation_authorized: false
scheduler_background_behavior_authorized: false
dynamic_cleaning_implementation_authorized: false
fifteen_task_cleaning_import_authorized: false
skip_push_bump_behavior_authorized: false
automatic_rescheduling_authorized: false
watch_tower_adoption_authorized: false
agent_directory_authorized: false
claude_md_authorized: false
runtime_operator_scaffolding_authorized: false
rollback_or_stop_conditions:
notes:
```
