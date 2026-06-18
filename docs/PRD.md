# Personal OS PRD v0.2

Last updated: 2026-06-18

## Product Definition

Personal OS is a modular, local-first productivity, routine, priority,
briefing, reporting, and execution operating system. It helps Chris maintain
routines, reason about priorities, generate no-send briefings, review
candidate actions, preserve durable notes later, and eventually operate gated
execution rails through approved runtime paths.

## Product Principles

- Chris remains the owner, final approver, and source of judgment.
- GitHub is the source of truth for repo code, tests, migrations, and docs.
- SQLite is the structured runtime state store.
- ChatGPT is the strategy, synthesis, PRD, architecture, and audit layer.
- Codex/Fable is the repository implementation layer.
- OpenClaw is the approved runtime/operator layer only.
- Todoist, Google Calendar, Gmail, and Markdown are future gated rails.
- Safety should be explicit in architecture and low-friction in local use.

## Current State

The canonical current project snapshot is [../STATUS.md](../STATUS.md).

As of 2026-06-18, the repo has completed through Phase 13E-C plus Phase 13F-D
policy/readiness docs. The current/next phase is Phase 13E-D: a synthetic
end-to-end no-send demo. Phase 14 has not started. Live rails remain disabled.

Current validated posture:

- `readiness.status=not_ready`
- `inert_report_only=true`
- `live_rails_activated=false`
- no credentials loaded or read
- no production DB active
- no scheduler active
- no external writes
- no OpenClaw call

## V1 Product Scope

V1 remains a local-first operating shell with explicit safety and review
boundaries:

- Local dashboard and CLI status surfaces.
- Today view.
- Routine and priority foundations.
- ChatGPT synthesis import preview and approved local apply into dev/test
  SQLite only.
- No-send briefing previews.
- Todoist and Calendar candidate previews.
- Side-effect and idempotency ledgers.
- Scheduler simulation records only.
- Report/jobs and chart-pack foundations.
- Fitness integration contract foundations.
- System status, safety evidence, and completion reports.

Future gated rails may include Todoist writes, Calendar writes, Gmail
briefings, PersonalOS Markdown durable notes, live model/API calls, production
SQLite activation, scheduler activation, and OpenClaw runtime operation. None
of those rails are currently active.

## Role Boundaries

### Chris

Chris owns priorities, approves high-stakes decisions, and decides when phase
gates may advance.

### ChatGPT

ChatGPT is the thought partner, synthesis layer, strategy layer, PRD writer,
architect, and auditor. It may produce structured plans and reviews. It does
not mutate live systems.

### Codex/Fable

Codex/Fable may edit repository code, tests, migrations, and documentation
inside approved phase scope. They may run repo-local validation. They must not
operate production workflows, inspect protected personal/runtime paths, load
credentials, activate live rails, or perform external writes.

### OpenClaw

OpenClaw is the approved runtime/operator layer only. It is not the repo
implementation layer and must not be involved in Codex/Fable repo work unless
Chris explicitly approves a narrow runtime/operator task.

## Source Boundaries

- Code/docs source of truth: GitHub repo.
- Structured runtime state: SQLite.
- Durable notes later: PersonalOS/Obsidian/Markdown.
- Execution rails later: Todoist, Google Calendar, Gmail, OpenClaw.

Execution rails are gated by readiness policies, activation checklists, pilot
protocols, and explicit Chris approval.

## Dashboard And CLI Requirements

Dashboard and CLI surfaces must remain local, inert, no-send, and
evidence-oriented until a later approved phase changes that posture. They may
show readiness status, safe local actions, blocked live actions, completion
reports, and no-live evidence. They must not expose activation controls,
credential setup, live send/write controls, scheduler activation, production DB
activation, or OpenClaw calls.

## High-Stakes Domains

Legal, tax, medical, health, investment, portfolio, crypto, relationship,
family-sensitive, external-message, external-meeting, and large-financial
commitment items require explicit review or manual handling. They must not be
auto-executed or treated as low-risk rails.

## Current Non-Goals

- No Phase 14 work.
- No live Gmail, Todoist, Google Calendar, PersonalOS Markdown, or OpenClaw
  execution.
- No credential loading or reading.
- No production DB activation.
- No scheduler, LaunchAgent, crontab, daemon, or background-loop activation.
- No external writes.
- No protected path inspection or mutation.

## Phase 13E-D Product Target

Phase 13E-D should demonstrate the existing no-send pipeline end to end using
synthetic local inputs and explicit safe output paths. Its canonical future
target is defined in
[PHASE_13E_D_SYNTHETIC_NO_SEND_DEMO.md](PHASE_13E_D_SYNTHETIC_NO_SEND_DEMO.md).
That document is a planning artifact only until implementation is explicitly
approved.
