# Roadmap

## Phase -1: Codex Setup and Repo Foundation

Status: complete.

Scope:

- Create the initial private repo scaffold.
- Add README and core docs.
- Establish the safety boundary.
- Add inert placeholders for future modules.

Exit criteria:

- Scaffold committed at `04d51891c2778971f7657eda6076a8cd80b11129`.
- No live-system inventory performed.
- No production state inspected or mutated.

## Phase 0: Read-Only Inventory

Status: next recommended phase.

Scope:

- Inventory approved local project surfaces.
- Map existing repo, state, and runtime boundaries.
- Produce evidence-backed notes.
- Keep all interactions read-only.

Gate:

- Requires explicit approval before starting.
- Read-only only.
- May inspect specified live paths only after explicit approval for that inventory scope.

Proposed read-only paths:

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

Required outputs:

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

## Phase 1: Runtime Stabilization

Scope:

- Define safe runtime boundaries.
- Confirm OpenClaw operator responsibilities.
- Establish logs and system event conventions.
- Prepare non-mutating checks around runtime readiness.
- Build no-send scheduler and email infrastructure only; no Gmail access or send behavior.

## Phase 2: Dashboard and State Store

Scope:

- Build the local dashboard shell.
- Add Today View, Settings/Permissions, System Status/Logs, and module navigation.
- Define and migrate SQLite runtime state.
- Keep the dashboard local-network only with no public internet exposure.
- Keep no login or password for V1 by choice, while documenting local-network risks and future options such as password, device allowlist, Tailscale/VPN, or local-only binding.
- Keep dev/test SQLite files repo-local; require backup before any future production migration.

## Phase 3: Routine Engine

Scope:

- Build the data-driven routine engine.
- Add routine editor support for add, edit, disable, and delete.
- Implement cadence rules and missed behavior options.
- Add defaults for cleaning, reading, prayer/meditation, Grease-the-Groove, fitness shell, and shutdown/review.

## Phase 4: Priority Engine

Scope:

- Build the priority registry.
- Add project and follow-up structures.
- Support ChatGPT synthesis imports.
- Connect priorities to briefings and review tasks.

## Phase 5: Todoist and Calendar Modules

Scope:

- Add validated Todoist write module for low-risk routine tasks and high-value review/follow-up tasks.
- Add validated Calendar write module for approved self-only blocks.
- Keep high-stakes actions, messages to other people, and external calendar events behind approval.
- Remove completed Todoist tasks from later briefings.
- Treat a module as validated only after schema, tests, dry-run/no-send mode, dedupe where applicable, permissions tests, logging/completion report, and one controlled live test for side-effecting modules.
- Keep Gmail send out of Codex development responsibility; Gmail send remains OpenClaw runtime responsibility after ledger, idempotency, and permission gates.

## Phase 6: Composer Model Integration

Scope:

- Define Composer Packet generation.
- Integrate composer_model with no broad filesystem access.
- Require structured JSON plus readable text.
- Enforce output sections for email_briefs, todoist_tasks, calendar_blocks, followups, and warnings.
- Include first-pass Composer Packet fields for date, timezone, briefing_window, routines_due, routines_completed, missed_routines, active_priorities, followups, calendar_summary, todoist_summary, routine_rules, permissions, model_instructions, and excluded_sensitive_context_note.

## Phase 7: Weekly Chart Pack and Report Jobs

Scope:

- Add weekly chart pack workflow hook.
- Add report job shell and coded jobs.
- Track week-over-week chart review changes.
- Support jobs such as macro calendar, earnings calendar, TradingView alert digest, priority status report, routine adherence report, Todoist completion report, and calendar utilization report.

## Phase 8: Fitness Integration

Scope:

- Preserve the existing CSV-based local fitness tracker.
- Add a V1 shell, link, and status.
- Later integrate routine prompts and recovery/training state.
