# Phase 14-A/B First Live Pilot Preparation

Last updated: 2026-06-20

## Purpose

This document records the Phase 14-A/B preparation packet for a possible first
live pilot. It designs the pilot envelope and adds inert fail-closed
scaffolding only.

This packet does not authorize, activate, execute, schedule, or run a live
pilot. It does not configure credentials, read OAuth material, create Todoist
tasks, touch Gmail, touch Calendar, write PersonalOS Markdown, activate
production SQLite, start a scheduler or background process, call OpenClaw, call
live model/API providers, contact external services, or perform external
writes.

## Pilot Envelope

- Pilot name: Phase 14-A/B first live pilot preparation.
- Pilot phase label: Phase 14-A/B first live pilot preparation.
- Intended future rail: Todoist.
- Intended future operation: create one routine-oriented Todoist task.
- Intended future mode: one explicit foreground command or operator action
  only.
- Intended future scope: self-only, low-risk, future-only, one task maximum.
- Current approval state: proposed only, not authorized, not approved, not run.
- Stop boundary: stop before live activation.

## Candidate Handling

Phase 13G recommends Todoist routine-task creation as the lowest-risk first
possible live rail shape. The current repo snapshot does not contain exactly
one clear, concrete, validated Phase 13G Todoist candidate that can be selected
for a future pilot.

No candidate is selected by this packet.

The Phase 13E-D synthetic Todoist preview candidate is not selected because it
is a Phase 13E-D no-send fixture, not a validated Phase 13G candidate. It also
belongs to a synthetic demo preview path, not a future live pilot approval
packet.

Because no concrete candidate is selected, this packet does not claim that a
specific candidate is low-risk, self-only, foreground-only, or future-only.
Those candidate-specific facts must be established by a future human-selected
Phase 13G-compatible candidate before any live pilot can proceed.

## Required Candidate Criteria

A future candidate must satisfy all of these criteria before it can be proposed
for approval:

- Source phase is Phase 13G.
- Validation status is validated.
- Exactly one candidate is selected.
- Rail is Todoist.
- Operation is one routine-task creation.
- Risk level is low.
- Candidate is self-only.
- Candidate is foreground-only.
- Candidate is future-only.
- Candidate is routine-task oriented.
- Candidate is not already marked approved.
- Candidate has no live Todoist task ID or external object ID.
- Candidate does not require credential inspection by Codex/Fable.
- Candidate does not require scheduler, OpenClaw, Gmail, Calendar, PersonalOS
  Markdown, production DB, live model/API, or protected-path access.

If any criterion is missing, ambiguous, or unsafe, the preparation output must
be an inert decision-needed or blocked report, not a live action.

## Phase 14-A Design Result

The proposed first live pilot shape remains:

Create one self-only, low-risk, future-only Todoist routine task from exactly
one already validated Phase 13G candidate, using foreground-only execution,
after a later explicit human approval packet names the candidate, rail,
operation, operator, host, commit, credential label if any, stop condition, and
undo plan.

Current result:

- Candidate selected: none.
- Human decision needed: select exactly one validated Phase 13G Todoist
  routine-task candidate or decide that Phase 14 cannot proceed yet.
- Live pilot authorization: absent.
- Live pilot execution: not attempted.
- Todoist task creation or mutation: not attempted.

## Phase 14-B Scaffolding Result

`src/personalos/phase14_pilot_prep.py` adds inert preparation helpers:

- `build_phase14_ab_pilot_preparation` builds a proposed-only readiness
  artifact.
- `validate_phase13g_todoist_candidate` accepts only already validated Phase
  13G Todoist routine-task candidates and fails closed otherwise.
- `guard_phase14_ab_live_execution` returns a blocked inert report for any
  attempted live execution from the preparation artifact.
- `render_phase14_ab_preflight_checklist` renders the stop boundary and
  blockers for human review.

The scaffolding has no Todoist client, no credential plumbing, no API call path,
no scheduler hook, no background execution, no OpenClaw handoff, and no
production DB integration.

## Activation Blockers

Activation remains blocked because:

- No exact validated Phase 13G candidate is selected.
- Pilot is proposed only and is not authorized.
- `readiness.status=not_ready`.
- `inert_report_only=true`.
- Live rails remain disabled.
- Chris approval for a selected pilot is missing.
- Credential label and scopes are not approved.
- No live Todoist client or API path exists in this packet.
- Side-effect ledger, idempotency, duplicate prevention, completion report, and
  rollback evidence are not approved for a live attempt.
- Stop before live activation.

## Rollback And Abort Criteria

Abort before live activation if any of these occur:

- Candidate selection is missing, ambiguous, not Phase 13G, or not validated.
- More than one candidate would require selection.
- The candidate is not low-risk, self-only, foreground-only, future-only, and
  routine-task oriented.
- Any live rail, credential, production DB, scheduler, OpenClaw, protected
  path, live model/API, or external runtime write boundary is required.
- `readiness.status` remains `not_ready`.
- Chris approval is missing, stale, general, or not specific to the selected
  pilot.
- Exact dry-run evidence, ledger intent, idempotency key, duplicate check,
  completion report target, or rollback plan is missing.

Future Todoist rollback options must be named before activation: delete, close,
reopen, annotate, or create a corrective task. This packet does not authorize
using any of those options live.

## Evidence Required Before Any Live Attempt

Before any future live attempt, a later approved packet must provide:

- Exactly one validated Phase 13G Todoist routine-task candidate.
- Exact candidate preview generated from the same input.
- Explicit Chris approval naming rail, operation, operator, host, commit,
  input, credential label if any, stop condition, and undo plan.
- Completed readiness and activation checklist evidence for the selected
  pilot.
- Idempotency key and payload fingerprint.
- Ledger intent before any live attempt.
- Duplicate-prevention result.
- Completion report target and required fields.
- Rollback or undo plan.
- Proof that non-selected rails remain disabled.

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

Stop before live activation.

This packet does not approve Phase 14-C, a live Todoist write, credentials,
production DB activation, scheduler/background work, OpenClaw runtime work,
external runtime writes, protected-path access, or merge.
