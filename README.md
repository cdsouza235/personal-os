# Personal OS

Personal OS is a modular, local-first productivity, routine, priority, and execution operating system. It helps Chris think clearly, maintain routines, manage high-value priorities, generate briefings, create Todoist tasks, schedule Calendar blocks, preserve durable notes, and run reports through OpenClaw on the Mac Mini.

This repository is the private code source of truth for Personal OS. It is documentation-first right now: no live workflow scripts, runtime mutations, or production integrations are enabled from this repo yet.

## Operating Roles

- Chris: owner, final approver, source of judgment and priorities.
- ChatGPT: thought partner, synthesis layer, analysis layer, PRD writer, architect, and auditor.
- Codex: primary coding agent and software development layer for repository code, tests, and documentation.
- Fable: optional or future alternate coding agent for long-horizon software development work.
- OpenClaw: local Personal Assistant and runtime operator on the Mac Mini.
- Mac Mini: always-on runtime host, OpenClaw host, SQLite state host, local PersonalOS file host, scheduler, and local repo clone.
- GitHub private repo: source of truth for code.
- SQLite: structured runtime state.
- Markdown, Obsidian, and PersonalOS: Clarity Notes, General Follow-Up Notes, protocols, logs, and reviews.
- Todoist, Calendar, and Gmail: execution rails, only touched by validated runtime modules.

## V1 Scope

- Local dashboard shell.
- Routine editor.
- Today view.
- Priority registry.
- ChatGPT synthesis import box.
- SQLite runtime state store.
- 8am, 12pm, 4pm, and 8pm briefing generation.
- Todoist auto-write for low-risk routine tasks and follow-ups.
- Calendar auto-write for approved self-only blocks.
- Gmail briefings.
- PersonalOS Markdown Clarity Notes and General Follow-Up Notes.
- Configurable permissions.
- System status and logs.
- Reports/jobs module shell.
- Fitness integration hook.
- Weekly chart pack workflow hook.

## Dashboard Requirements

The V1 dashboard is local-network only, with no public internet exposure and no login or password requirement by choice. It should be mobile-friendly for iPhone and usable from Windows or Mac browsers on the local network.

This is a deliberate V1 tradeoff, not an absence of risk. Risks include accidental local network access, stale browser sessions, and exposure from trusted devices on the network. Future security options may include a password, device allowlist, Tailscale/VPN access, or local-only binding.

Planned sections:

- Today View
- Routine Editor
- Priority Editor
- Todoist/Calendar Preview
- System Status/Logs
- Settings/Permissions
- Reports/Jobs shell

## State Architecture

- GitHub private repo: code source of truth.
- SQLite on the Mac Mini: structured runtime state.
- Markdown and Obsidian: Clarity Notes, Follow-Up Notes, logs, and protocols.
- Mac Mini: runtime and deployment host.
- OpenClaw: local runtime operator.
- Codex: primary software developer.
- Fable: optional or future alternate coding agent.

America/Chicago is Chris's operating timezone for briefings and routines. The Mac Mini system timezone may differ, so scheduler code must explicitly use the configured operating timezone and must not assume the host timezone.

Production SQLite state lives on the Mac Mini runtime path. Development and test SQLite files live inside repo-local temporary or test paths. Codex may create and edit dev/test databases in this repository, but may not mutate production SQLite state without explicit approval. Production migrations require a backup first, and production backups should include periodic JSON and SQLite snapshots.

## Safety Boundary

Codex may work on documentation, tests, and repository code after the appropriate phase gate, but OpenClaw remains the production/runtime operator.

Codex must not send email, write Todoist, write Calendar, load LaunchAgents, modify production ledgers, mutate production SQLite state, run live OpenClaw workflows, inspect `/Users/coldstake/PersonalOS`, inspect `/Users/coldstake/.openclaw`, touch credentials, or touch production state without explicit approval.

The first live-system interaction phase is Phase 0 read-only inventory.

## Phase 0 Inventory Charter

Phase 0 requires explicit approval before starting. It is read-only. Phase 0 may inspect specified live paths only after explicit approval for that inventory scope.

Proposed read-only paths may include:

- `/Users/coldstake/PersonalOS`
- `/Users/coldstake/.openclaw`
- `/Users/coldstake/Library/LaunchAgents`
- `/Users/coldstake/dev/personal-os`

Forbidden actions:

- Sending email.
- Executing `gog gmail send`.
- Mutating Todoist.
- Mutating Calendar.
- Loading or unloading LaunchAgents.
- Modifying production ledgers.
- Modifying production SQLite state.
- Reading or printing credentials.

Required Phase 0 outputs:

- Current file/module inventory.
- Inventory report.
- Protected path map.
- Boundary map.
- Current runtime architecture map.
- Config, ledger, and LaunchAgent inventory.
- Risk register.
- Migration recommendations.
- Recommended Phase 1 implementation plan.
- Open questions.

## Repository Layout

Existing repo scaffold paths:

```text
docs/          Product, architecture, safety, roadmap, and Codex workflow docs.
app/           Placeholder for local dashboard and API surfaces.
personalos/    Placeholder for domain modules.
scripts/       Reserved for later inert or approved helper scripts.
tests/         Placeholder for repository tests.
.codex/        Codex-local project guidance and metadata.
```

Planned future modules include routines, priorities, composer, Todoist, Calendar, Gmail, reports, evidence, dashboard views, and local API surfaces.

Protected live runtime paths are outside this repository and must not be inspected or mutated without explicit approval. They include `/Users/coldstake/PersonalOS`, `/Users/coldstake/.openclaw`, LaunchAgents, credentials, production ledgers, production SQLite state, and other production runtime state.

## Current Phase

Phase 3 routine engine foundation is in progress on repository code only. It
remains dev/test-only and does not operate live Personal OS workflows.

## Phase 1 Runtime Foundation

The Phase 1 runtime stabilization foundation adds repository-local Python tooling
and dev/test-only runtime primitives. The foundation currently includes:

- Python package and test scaffold.
- Secret-free sample config and dev/test environment defaults.
- Repo-local dev/test SQLite connection and migration helpers.
- Migration metadata, idempotent application, and checksum drift protection.
- Dev/test system event records.
- Fail-closed permission defaults.
- Dry-run/no-send validation results.
- Inert completion report serialization.

Phase 1 remains dev/test-only. It does not send email, write Todoist, write
Calendar, call OpenClaw, start schedulers, call external APIs, or access
production state.

## Phase 2 Dashboard-State Foundation

Phase 2 added a dev/test-only SQLite state foundation and read-model layer for
future dashboard work. It includes:

- Core state tables for `routines`, `routine_completions`, `priorities`,
  `projects`, `followups`, and `permission_settings`.
- State-store helpers for `permission_settings` get/list/upsert operations.
- Read-only list/count helpers for routines, priorities, projects, and
  followups.
- A local status summary read model with core counts, permission settings,
  recent system events, a generated UTC timestamp, and an optional environment
  label.

Phase 2 is not production-ready. It does not include a dashboard UI, API server,
scheduler, Gmail/Todoist/Calendar integration, OpenClaw wiring, LaunchAgents,
production SQLite access, credentials, external API clients, live runtime
behavior, public internet exposure, or a login/password system.

## Phase 3 Routine Engine Foundation

The current Phase 3 branch adds a safe internal routine engine foundation on
top of the Phase 2 tables. It includes:

- Routine data-access helpers for get/list/count/create and status/enabled
  updates.
- Routine validation for IDs, status values, enabled flags, completion dates,
  JSON-safe metadata, missing routines, disabled routines, and inactive
  routines.
- Routine completion helpers that write only to dev/test SQLite when explicitly
  allowed.
- Permission-gated routine-engine read and write paths backed by
  `permission_settings`.
- A dry-run-safe completion flow that validates intended work and reports what
  would be written without inserting a completion row.
- A non-dry-run dev/test completion flow that records a completion row only in
  the injected dev/test SQLite connection and returns an inert result dict.

Phase 3 permission keys:

- `routine_engine_dev_test_read`
- `routine_engine_dev_test_write`

Both keys fail closed when missing, disabled, invalid, or set to approval-only.
The routine engine allows work only when the relevant key is explicitly set to
`auto_write` in the dev/test database.

Phase 3 is not a scheduler, dashboard UI, API server, OpenClaw integration,
Todoist integration, Gmail integration, Calendar integration, LaunchAgent,
production SQLite path, credential path, external API client, notification
system, or live runtime activation. The Phase 3 PR must stop before merge and
must not start Phase 4.

Local checks:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

`pytest` is configured in `pyproject.toml`, but it is not installed in the
current local environment used for this phase.
