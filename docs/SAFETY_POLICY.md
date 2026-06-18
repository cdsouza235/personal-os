# Safety Policy

Last updated: 2026-06-18

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
- `openclaw_called=false`
- `external_services_contacted=false`
- `external_mutation=false`

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

## Phase 13E-D Boundary

Phase 13E-D is the current/next phase: a synthetic end-to-end no-send demo.
The planning document is
[PHASE_13E_D_SYNTHETIC_NO_SEND_DEMO.md](PHASE_13E_D_SYNTHETIC_NO_SEND_DEMO.md).

Phase 13E-D must use synthetic inputs, explicit safe output paths, local
dev/test state, and no-send evidence. It must not start Phase 14 or activate
any live rail.

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
