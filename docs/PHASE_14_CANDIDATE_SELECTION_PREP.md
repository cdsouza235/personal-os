# Pre-Phase-14-C Candidate-Selection Preparation

Last updated: 2026-06-25

## Purpose

This document records an inert pre-Phase-14-C candidate-selection preparation
packet. It prepares the repo for human candidate-review tracking and later
authorization review of exactly one future, foreground-only, self-only,
low-risk Todoist routine-task candidate, or a later decision that no candidate
is suitable yet.

The 2026-06-22 human review outcome records one candidate for
candidate-review tracking only. This packet does not approve, authorize,
schedule, activate, execute, or run a live pilot. It does not configure
credentials, read OAuth material, create Todoist tasks, touch Gmail, touch
Calendar, write PersonalOS Markdown, activate production SQLite, start a
scheduler or background process, call OpenClaw, call live model/API providers,
contact external services, or perform external writes.

## Current Decision State

- Candidate review-tracking record: exactly one.
- Candidate: Clean Kitchen Countertops and Stovetop.
- Task title: Clean Kitchen Countertops and Stovetop.
- Weekday: Monday.
- Area of home: Kitchen.
- Candidate type: household cleaning routine task.
- Scope: one recurring self-only Todoist routine-task candidate.
- Candidate review-tracking status: selected for candidate-review tracking
  only.
- Candidate selected for live execution: no.
- Candidate approved: no.
- Candidate activated: no.
- Live pilot authorized: no.
- Live pilot run: no.
- Phase 14-C: blocked.
- Phase 13E-D synthetic Todoist fixture: rejected as a live-pilot candidate.
- Required future human decision: Chris must later approve or reject this
  candidate for a separate authorization packet, or decide that no candidate is
  suitable.

Candidate selection and live activation are separate decisions. Recording this
candidate for candidate-review tracking does not authorize a live Todoist
write. Live activation requires a later explicit packet with readiness,
approval, credential-label, idempotency, ledger, completion-report,
stop-condition, and rollback evidence.

The follow-on decision-gate document is
[PHASE_14C_DECISION_GATE.md](PHASE_14C_DECISION_GATE.md). It records future
human approval requirements, pre-approval evidence, and inert decision-record
templates. It does not approve Phase 14-C, approve this candidate, authorize
execution, authorize live service access, implement dynamic cleaning, import a
15-task cleaning list, implement skip/push/bump behavior, implement automatic
rescheduling, adopt Watch Tower, add `.agent/`, add `CLAUDE.md`, or add
runtime/operator scaffolding.

The companion decision-support document is
[PHASE_14C_CANDIDATE_DECISION_SUPPORT.md](PHASE_14C_CANDIDATE_DECISION_SUPPORT.md).
It keeps the candidate-review tracking only posture unfilled and false by
default while making a future human approve/reject/defer review easier to
inspect. Its repo-local helper,
`src/personalos/phase14c_candidate_decision_support.py`, validates only the
unfilled false-default decision-support record and blocks any filled decision,
approval, authorization, activation, live-service, credential/secret, live ID,
unknown schema field, dynamic cleaning, Watch Tower, `.agent/`, `CLAUDE.md`,
or runtime/operator scaffolding flag. It also exposes an inert contract
manifest for audit/tests that records schema, status, report, prohibited-field,
and non-authorization contracts without approving or authorizing anything. The
inert report embeds that static manifest and keeps unsafe caller-controlled
input out of blocked report JSON.

## Boundary Assertions

- This is not Phase 14-C.
- This is not live activation.
- This is not Todoist access.
- This is not Todoist write authorization.
- This is not credential, OAuth, API-key, or token handling.
- This is not candidate approval for execution.
- This does not change `readiness.status` to `ready`.
- Phase 14-C remains blocked.
- Candidate selection and live activation remain separate future decisions.

## Future Dynamic Cleaning Context

The recorded candidate represents one task from a possible future dynamic
cleaning system. That concept remains future design context only:

- A weekday household cleaning rotation.
- Roughly 15 total cleaning tasks.
- Tasks organized by area of the home.
- One specific task per day, Monday through Friday.
- Missed-task options may eventually include skip, push to the following day
  and allow two tasks in one day, or push to the following day and bump future
  tasks by one day.

No dynamic cleaning system is implemented here.

## Explicit Exclusions

- No 15-task import.
- No dynamic cleaning rotation implementation.
- No automatic skip/push/bump behavior.
- No automatic rescheduling.
- No OpenClaw access.
- No OpenClaw invocation.
- No Todoist access.
- No Todoist writes.
- No Gmail access.
- No Calendar access.
- No credentials, secrets, OAuth, API keys, or tokens.
- No production DB activation.
- No scheduler/background activation.
- No LaunchAgent, crontab, daemon, watcher, or service changes.
- No protected path access.
- No external PersonalOS runtime writes.
- No live model/API calls.
- No Watch Tower adoption or merge.

## Minimum Candidate Criteria

A future candidate must satisfy all of these criteria before it can be
considered for a later authorization packet:

- Todoist routine-task oriented.
- Self-only.
- Low-risk.
- Future-only.
- Foreground-only.
- No sensitive or high-stakes domain.
- No external dependency.
- No Gmail or Calendar dependency.
- No protected path interaction.
- No credentials, tokens, OAuth material, API keys, or real live Todoist IDs.
- No scheduler or background requirement.
- No OpenClaw requirement.
- Safe to dry-run inertly.

Missing, ambiguous, or unsafe fields produce an inert `decision_needed` or
`blocked` report, not a selected candidate and not a live action.

## Human-Fillable Candidate Template

The template is intentionally blank and fail-closed. It must not include a real
Todoist task ID, credentials, tokens, OAuth material, API keys, or live API
configuration.

```yaml
schema_version: phase14_candidate_selection_prep.v1
packet_name: pre-Phase-14-C candidate-selection preparation
candidate_label:
routine_task_description:
intended_future_window:
self_only_reason:
low_risk_reason:
foreground_only_reason:
future_only_reason:
no_sensitive_domain_confirmation: false
no_external_dependency_confirmation: false
no_gmail_or_calendar_dependency_confirmation: false
no_credentials_or_live_ids_confirmation: false
no_protected_path_interaction_confirmation: false
no_scheduler_background_or_openclaw_confirmation: false
safe_to_dry_run_inertly_confirmation: false
abort_criteria:
evidence_required_before_live_authorization:
selected: false
approved: false
authorized: false
live_pilot_run: false
readiness.status: not_ready
```

## Inert Validator Behavior

`src/personalos/phase14_candidate_selection_prep.py` prepares only inert
reports and templates:

- `blank_phase14_candidate_selection_template` returns the fail-closed blank
  template.
- `phase14_cleaning_candidate_review_tracking_record` returns the inert
  human-selected candidate-review tracking record for Clean Kitchen
  Countertops and Stovetop.
- `validate_phase14_candidate_selection_candidate` validates one human-review
  candidate without selecting or authorizing it.
- `build_phase14_candidate_selection_report` evaluates zero, one, or multiple
  candidate records and returns an inert decision report.
- `render_phase14_candidate_selection_checklist` renders the human-review
  boundary and blockers.

The validator fails closed:

- Zero candidates: `decision_needed`.
- More than one candidate: `decision_needed`.
- Missing required fields: `decision_needed`.
- Live Todoist IDs or live API fields: `blocked`.
- Credential, token, OAuth, API-key, or secret fields: `blocked`.
- Candidate marked selected, approved, authorized, or run: `blocked`.
- Scheduler, background, OpenClaw, protected-path, Gmail, Calendar, or external
  dependency: `blocked`.
- High-stakes or sensitive domain: `blocked`.
- Exactly one well-formed inert candidate: `proposed_only`, recorded for
  candidate-review tracking only, not selected for live execution, not
  approved, not authorized, and not live.

The validator has no Todoist client, no credential plumbing, no API call path,
no scheduler hook, no background execution, no OpenClaw handoff, and no
production DB integration.

## Safety Posture

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

## Stop Boundary

Stop before candidate approval, Phase 14-C authorization, live Todoist access,
credential handling, production DB activation, scheduler/background work,
OpenClaw invocation, protected-path access, external runtime writes, live
model/API calls, or live activation.
