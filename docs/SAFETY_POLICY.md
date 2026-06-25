# Safety Policy

Last updated: 2026-06-25

## Purpose

Personal OS should remain useful locally while making activation boundaries
explicit. This policy defines protected systems, no-send posture, readiness
requirements, and prohibited work.

The canonical current safety snapshot is [../STATUS.md](../STATUS.md).

## Current Required Posture

Until Chris explicitly approves a later phase that changes these facts, the
repo must report:

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

STATUS.md must be updated whenever the validated safety posture changes.

## Protected Systems

Codex/Fable must not inspect or mutate the following without explicit Chris
approval for that exact scope:

- `/Users/coldstake/PersonalOS`
- `/Users/coldstake/.openclaw`
- credential stores, OAuth files, tokens, secrets, or environment secrets
- production SQLite paths
- production ledgers
- Gmail
- Todoist
- Google Calendar
- LaunchAgents
- crontab
- daemon/background-loop configuration
- OpenClaw runtime files or runtime config
- other production runtime state

## Prohibited Actions

Codex/Fable must not:

- send, draft, read, or mutate Gmail
- write or mutate Todoist
- write or mutate Google Calendar
- write PersonalOS Markdown
- load, read, print, or configure credentials
- activate or mutate production DB paths
- activate a scheduler
- install or modify LaunchAgents
- write crontab entries
- start daemons or background loops
- call OpenClaw
- call live external services
- perform external writes
- start Phase 14

## Long-Run Mode Safety Rule

Long-run Codex/Fable work packets never weaken these safety gates. Long-run
mode only changes how long Codex/Fable may continue inside an approved
repo-local inert envelope before stopping.

Prompts may narrow safety rules, add stricter stop conditions, or require
extra validation. Prompts may not weaken this policy, `../AGENTS.md`,
[AGENT_WORK_PACKET_PROTOCOL.md](AGENT_WORK_PACKET_PROTOCOL.md), or
[CODEX_WORKFLOW.md](CODEX_WORKFLOW.md).

Live rails, credentials, production DB paths, protected paths,
scheduler/background work, LaunchAgents, crontab, daemons, OpenClaw runtime,
external runtime writes, live model/API calls, and high-stakes execution still
require explicit Chris approval for the exact scope.

## Readiness And Activation Gates

Before any live-rail work, the repo must satisfy the applicable gates:

- [PRE_LIVE_READINESS.md](PRE_LIVE_READINESS.md)
- [LIVE_RAIL_ACTIVATION_POLICY.md](LIVE_RAIL_ACTIVATION_POLICY.md)
- [ACTIVATION_CHECKLIST.md](ACTIVATION_CHECKLIST.md)
- [FIRST_LIVE_PILOT_PROTOCOL.md](FIRST_LIVE_PILOT_PROTOCOL.md)
- [OPERATOR_HANDOFF_CONTRACT.md](OPERATOR_HANDOFF_CONTRACT.md)
- [PRODUCTION_DB_POLICY.md](PRODUCTION_DB_POLICY.md)

These documents and readiness/status reports are policy and evidence surfaces.
They do not authorize live rails, production DB activation, scheduler
activation, OpenClaw runtime operation, credential loading, or external writes
by themselves.

## Phase 13E-D / 13G Boundary

Phase 13E-D is implemented and post-merge validated. The planning/evidence
document is
[PHASE_13E_D_SYNTHETIC_NO_SEND_DEMO.md](PHASE_13E_D_SYNTHETIC_NO_SEND_DEMO.md).

Phase 13G is a planning/control-plane readiness matrix. It must not start
Phase 14, authorize a live pilot, or activate any live rail.

## Phase 14-A/B Preparation Boundary

Phase 14-A/B preparation may define a proposed first live pilot envelope and
fail-closed repo-local scaffolding only. The planning/evidence document is
[PHASE_14_AB_FIRST_LIVE_PILOT_PREP.md](PHASE_14_AB_FIRST_LIVE_PILOT_PREP.md).

Phase 14-A/B preparation must not authorize, activate, execute, schedule, or
run a live pilot. It must not create a live Todoist task, configure
credentials, activate production SQLite, start schedulers or background
processes, call OpenClaw, call live model/API providers, contact external
services, perform external writes, or inspect protected paths. Phase 14-C or
any live attempt requires a later explicit Chris approval packet.

## Pre-Phase-14-C Candidate-Selection Boundary

Pre-Phase-14-C candidate-selection preparation may define an inert
candidate-selection process, blank candidate template, fail-closed validator,
and candidate-review tracking record only. The planning/evidence document is
[PHASE_14_CANDIDATE_SELECTION_PREP.md](PHASE_14_CANDIDATE_SELECTION_PREP.md).
The future human decision-gate document is
[PHASE_14C_DECISION_GATE.md](PHASE_14C_DECISION_GATE.md).
The companion candidate decision-support document is
[PHASE_14C_CANDIDATE_DECISION_SUPPORT.md](PHASE_14C_CANDIDATE_DECISION_SUPPORT.md).

Candidate-selection preparation may record a human-selected candidate for
candidate-review tracking only. It must not select a candidate for live
execution, approve, authorize, schedule, activate, execute, or run a live
pilot. It must not create a live Todoist task, configure credentials, activate
production SQLite, start schedulers or background processes, call OpenClaw,
call live model/API providers, contact external services, perform external
writes, or inspect protected paths. Candidate-review tracking, candidate
approval for execution, and approving live activation remain separate later
Chris decisions.

The Phase 14-C candidate decision gate may document required future approval
wording, pre-approval evidence, and inert decision-record templates. It must
not approve Phase 14-C, approve or authorize the candidate, authorize
execution, authorize Todoist/Gmail/Calendar access, invoke OpenClaw, handle
credentials/auth, activate production DB paths, activate scheduler/background
behavior, implement dynamic cleaning, import a 15-task cleaning list,
implement skip/push/bump behavior, implement automatic rescheduling, adopt
Watch Tower, add `.agent/`, add `CLAUDE.md`, or add runtime/operator
scaffolding.

The Phase 14-C candidate decision-support artifact may document review
questions, failure modes, stop conditions, future approval wording, and an
unfilled false-default decision-record template. It must preserve
candidate-review tracking only and Phase 14-C remains blocked. Its repo-local
validator may produce inert `decision_needed` or `blocked` reports for the
unfilled template and unsafe filled records, but it must not record approve,
reject, or defer; approve or authorize a candidate; grant live-service access;
handle credentials/auth; activate production DB or scheduler/background
behavior; touch protected paths; call OpenClaw; implement dynamic cleaning;
adopt Watch Tower; add `.agent/`; add `CLAUDE.md`; or add runtime/operator
scaffolding. Unknown decision-record schema fields must fail closed instead of
being accepted as part of the unfilled template. Nested payloads under known
fillable fields must also fail closed because filling any decision-record field
would record a human decision outside the current blocked posture. The
validator tests must also keep table-driven coverage for every fillable
decision field, every required false field, the known schema field set, and
the allowed `decision_needed` / `blocked` status set.

## High-Stakes Domains

Legal, tax, medical, health, investment, portfolio, crypto, relationship,
family-sensitive, external-message, external-meeting, and large-financial
commitment actions require explicit review or manual handling. They must not
be treated as low risk, auto-executed, or routed to live rails without a
separate approved policy and test path.

## Validation Evidence

Safety-sensitive changes should report:

- branch and changed files
- tests run and results
- `git diff --check`
- `git diff --cached --check` when staged files exist
- repo-local `var/` scan
- SQLite/DB artifact scan outside `.git`
- confirmation that protected systems were not touched
- confirmation that live rails, credentials, production DB, schedulers,
  external writes, and OpenClaw remained inactive
