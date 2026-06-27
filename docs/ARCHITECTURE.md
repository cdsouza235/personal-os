# Personal OS Architecture Brief v0.2

Last updated: 2026-06-18

## System Definition

Personal OS is a local-first system that separates strategy, repository
implementation, structured runtime state, durable notes, local no-send
surfaces, and future gated execution rails.

The canonical current-state snapshot is [../STATUS.md](../STATUS.md).

## Control Plane

- Chris: owner and final approver.
- ChatGPT: synthesis/control, strategy, PRD, architecture, and audit.
- Codex/Fable: repo implementation, tests, docs, migrations, and PRs.
- OpenClaw: future approved runtime/operator only.

ChatGPT may synthesize and audit. Codex/Fable may implement inside the repo.
OpenClaw may operate approved runtime workflows later. These roles should not
be collapsed without explicit Chris approval.

## Source And State Topology

- GitHub repo: code, tests, migrations, and Markdown docs source of truth.
- SQLite: structured runtime state.
- Dashboard/CLI: local no-send and inert status/report surfaces.
- PersonalOS/Obsidian/Markdown: durable notes later, behind explicit gates.
- Todoist, Google Calendar, Gmail: gated execution rails, with a bounded
  Phase 14-C supervised smoke-test path for one marked test object per rail.
- OpenClaw: approved runtime/operator layer, with a bounded Phase 14-C
  local/test/sandbox smoke invocation path.

## Repo-Local Surfaces

Current local surfaces may report state, render previews, run deterministic
fake/no-send flows, and write only approved dev/test SQLite or explicit safe
output files. They must keep completion evidence visible:

- readiness status
- inert/report-only mode
- disabled live rails
- credential state
- production DB state
- scheduler state
- OpenClaw call state
- external-write state

Dashboard and CLI surfaces must not add activation controls, credential setup,
OAuth setup, live send/write controls, production DB activation, scheduler
activation, LaunchAgent/crontab/daemon setup, or OpenClaw calls.

## Current Safety Posture

The repo remains inert and no-send:

- `readiness.status=not_ready`
- `inert_report_only=true`
- `live_rails_activated=false`
- credentials not loaded/read
- production DB inactive
- scheduler inactive
- OpenClaw uncalled
- external services not contacted
- external mutation false

Any change to this posture must update [../STATUS.md](../STATUS.md) and pass
the relevant readiness and activation policy gates.

## Gated Rails

The following rails require explicit design and approval:

- Gmail send/draft/read behavior.
- Todoist live writes.
- Google Calendar live writes.
- PersonalOS Markdown writes.
- Live model/API calls.
- Production SQLite activation.
- Scheduler, LaunchAgent, crontab, daemon, or background-loop activation.
- OpenClaw runtime workflows.

Phase 14-C supervised smoke-test prep narrows the immediate next integration
step to Todoist, Google Calendar, Gmail, and OpenClaw under
[PHASE_14C_SUPERVISED_SMOKE_TEST.md](PHASE_14C_SUPERVISED_SMOKE_TEST.md).
That path uses guardrail validation, a fake-client dry-run rehearsal, and
explicit injected clients. It allows at most one marked Todoist task, one
marked Calendar event, one marked Gmail test email to a controlled/self
recipient, and one OpenClaw local/test/sandbox invocation after Chris initiates
the live-test step. Repo prep and fake-client rehearsal do not run those live
actions.

Activation policies live in:

- [PRE_LIVE_READINESS.md](PRE_LIVE_READINESS.md)
- [LIVE_RAIL_ACTIVATION_POLICY.md](LIVE_RAIL_ACTIVATION_POLICY.md)
- [ACTIVATION_CHECKLIST.md](ACTIVATION_CHECKLIST.md)
- [FIRST_LIVE_PILOT_PROTOCOL.md](FIRST_LIVE_PILOT_PROTOCOL.md)
- [PHASE_14_AB_FIRST_LIVE_PILOT_PREP.md](PHASE_14_AB_FIRST_LIVE_PILOT_PREP.md)
- [PHASE_14_CANDIDATE_SELECTION_PREP.md](PHASE_14_CANDIDATE_SELECTION_PREP.md)
- [PHASE_14C_SUPERVISED_SMOKE_TEST.md](PHASE_14C_SUPERVISED_SMOKE_TEST.md)
- [OPERATOR_HANDOFF_CONTRACT.md](OPERATOR_HANDOFF_CONTRACT.md)
- [PRODUCTION_DB_POLICY.md](PRODUCTION_DB_POLICY.md)

These docs define gates only; they do not activate rails.

## State Separation

Development and tests use explicit safe DB paths and local fixtures. Production
SQLite paths, production ledgers, credentials, protected PersonalOS paths,
OpenClaw runtime paths, LaunchAgents, crontab, and other production runtime
state are outside Codex/Fable scope unless Chris explicitly approves a narrow
operation.

## Phase 13E-D / Phase 14-A/B Architecture Boundary

Phase 13E-D is implemented as a synthetic end-to-end no-send demo over
existing local surfaces. It produces a stable evidence bundle from synthetic
inputs and explicit safe output paths.

Phase 14-A/B preparation defines a proposed first-live pilot envelope and
fail-closed scaffolding only. It must not authorize, activate, schedule, or run
a live pilot. It must not activate live rails, touch protected paths, load
credentials, activate production DB, activate schedulers, call OpenClaw,
contact external services, or perform external writes.

Pre-Phase-14-C candidate-selection preparation defines an inert
candidate-selection process, blank template, and fail-closed validator only. It
does not select or approve a Todoist candidate, authorize Phase 14-C, or
activate any live rail.

Phase 14-C supervised smoke-test preparation defines the bounded multi-rail
test runbook, guardrail validator, credential-name-only preflight, read-only
CLI discovery surface, fake-client dry-run rehearsal, and injected-client
execution path. It treats Todoist, Google Calendar, Gmail, and OpenClaw as
acceptable low-blast-radius supervised smoke rails inside that runbook, but it
does not run the live smoke test, activate scheduler/background behavior,
activate production DB, implement dynamic cleaning, touch protected paths, or
broaden OpenClaw runtime scope.
