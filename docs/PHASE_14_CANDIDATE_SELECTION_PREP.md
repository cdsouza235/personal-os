# Pre-Phase-14-C Candidate-Selection Preparation

Last updated: 2026-06-20

## Purpose

This document records an inert pre-Phase-14-C candidate-selection preparation
packet. It prepares the repo for a later human decision where Chris can select
exactly one future, foreground-only, self-only, low-risk Todoist routine-task
candidate, or decide that no candidate is suitable yet.

This packet does not select, approve, authorize, schedule, activate, execute,
or run a live pilot. It does not configure credentials, read OAuth material,
create Todoist tasks, touch Gmail, touch Calendar, write PersonalOS Markdown,
activate production SQLite, start a scheduler or background process, call
OpenClaw, call live model/API providers, contact external services, or perform
external writes.

## Current Decision State

- Candidate selected: none.
- Candidate approved: no.
- Live pilot authorized: no.
- Live pilot run: no.
- Phase 14-C: blocked.
- Phase 13E-D synthetic Todoist fixture: rejected as a live-pilot candidate.
- Required human decision: Chris must later select exactly one candidate or
  decide that no candidate is suitable.

Candidate selection and live activation are separate decisions. Selecting a
candidate in a later packet would not authorize a live Todoist write. Live
activation requires a later explicit packet with readiness, approval,
credential-label, idempotency, ledger, completion-report, stop-condition, and
rollback evidence.

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
- Exactly one well-formed inert candidate: `proposed_only`, not selected, not
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
