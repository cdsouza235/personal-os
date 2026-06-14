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

Status: complete.

Scope:

- Build the local dashboard shell.
- Add Today View, Settings/Permissions, System Status/Logs, and module navigation.
- Define and migrate SQLite runtime state.
- Keep the dashboard local-network only with no public internet exposure.
- Keep no login or password for V1 by choice, while documenting local-network risks and future options such as password, device allowlist, Tailscale/VPN, or local-only binding.
- Keep dev/test SQLite files repo-local; require backup before any future production migration.

Current foundation:

- Dev/test-only SQLite tables exist for routines, routine_completions,
  priorities, projects, followups, and permission_settings.
- State-store helpers support permission_settings get/list/upsert operations.
- Read-only list/count helpers exist for routines, priorities, projects, and
  followups.
- A status summary read model exposes core counts, permission settings, recent
  system events, a generated UTC timestamp, and an optional environment label.

Current non-goals:

- No dashboard UI or API server yet.
- No scheduler, live runtime behavior, production SQLite, credentials,
  LaunchAgents, OpenClaw wiring, external API clients, or public internet
  exposure.
- No Gmail, Todoist, or Calendar integration.
- No login/password system.

## Phase 3: Routine Engine

Status: complete.

Scope:

- Build the dev/test-only routine engine foundation on top of the Phase 2
  SQLite tables.
- Add routine helpers for get/list/count/create and status/enabled updates.
- Add routine completion helpers that validate the referenced routine and write
  only to injected dev/test SQLite connections.
- Validate routine status values, enabled flags, completion input shape,
  missing routines, disabled routines, and inactive routines.
- Gate routine-engine read and write paths through explicit
  `permission_settings` keys:
  `routine_engine_dev_test_read` and `routine_engine_dev_test_write`.
- Support a dry-run completion flow that checks permissions and reports the
  intended completion without writing a row.
- Support a non-dry-run dev/test completion flow that writes only a
  `routine_completions` row and returns an inert result.
- Prove through unit tests that missing/disabled permissions deny action and
  enabled dev/test permissions allow the intended routine operations.

Non-goals:

- No scheduler.
- No recurring automation activation.
- No default routine seeding.
- No routine editor UI.
- No dashboard UI or API server.
- No OpenClaw runtime wiring.
- No Gmail, Todoist, or Calendar integration.
- No LaunchAgents, production SQLite, credentials, external API clients,
  public internet exposure, notifications, task creation, email sending, or
  calendar writes.

## Phase 4: Priority Engine

Status: complete.

Scope:

- Build the dev/test-only priority registry foundation on top of the Phase 2
  SQLite `priorities` table.
- Add priority helpers for get/list/count/create, field updates, and status
  transitions.
- Validate priority IDs, titles, allowed status values, JSON-safe metadata,
  notes, and timezone-aware timestamp inputs.
- Gate priority-engine read and write paths through explicit
  `permission_settings` keys:
  `priority_engine_dev_test_read` and `priority_engine_dev_test_write`.
- Support dry-run priority creation, update, and status transition flows that
  report intended writes without mutating SQLite.
- Support non-dry-run dev/test priority writes only when the write permission is
  explicitly enabled.
- Add deterministic read models for active priorities, counts by status, and a
  small priority dashboard summary shape.

Non-goals:

- No autonomous prioritization, semantic scoring, ranking, inference from raw
  notes, or automatic task generation.
- No project/follow-up lifecycle expansion beyond existing Phase 2 tables.
- No ChatGPT synthesis imports or composer integration.
- No dashboard UI or API server.
- No scheduler behavior, recurring automation activation, idempotency/send
  ledger, or runtime wiring.
- No Todoist, Calendar, Gmail, OpenClaw, LaunchAgent, production SQLite,
  credential, external API client, public internet, task creation, email
  sending, or calendar write behavior.

## Phase 5: Todoist and Calendar Modules

Status: in progress.

Scope:

- Add dev/test SQLite tables for Todoist task proposals and Calendar block
  proposals.
- Add validation for required fields, risk levels, approval modes, status
  values, Todoist-like priority values, labels, Calendar start/end windows, and
  Calendar duration consistency.
- Add deterministic module-level dedupe keys and prevent silent duplicate
  creates.
- Add permission-gated read, dev/test write, and simulated-write wrappers.
- Add dry-run preview flows that do not mutate SQLite or call adapters.
- Add fake recording Todoist and Calendar clients for deterministic simulated
  write reports.
- Keep high-risk actions, messages to other people, external meetings,
  family-sensitive events, legal/tax/portfolio execution, and large financial
  commitments behind approval or manual-only paths.

Risk and approval semantics:

- `low`: routine/admin/self-only tasks or blocks.
- `medium`: self-only but sensitive, ambiguous, unusually time-consuming, or
  tied to a larger project.
- `high`: legal, tax, portfolio/crypto/investment execution, health/medical
  decisions, relationship messages, messages to other people, external
  meetings, family-sensitive events, or large financial commitments.
- `auto_allowed` is valid only with `low`.
- `medium` defaults to `approval_required`.
- `high` must be `approval_required` or `manual_only`.
- `manual_only` may be stored or previewed but must not be routed to a write
  client.

Permission keys:

- `todoist_module_dev_test_read`
- `todoist_module_dev_test_write`
- `todoist_module_dev_test_simulated_write`
- `calendar_module_dev_test_read`
- `calendar_module_dev_test_write`
- `calendar_module_dev_test_simulated_write`

Non-goals:

- No live Todoist writes.
- No live Calendar writes.
- No credentials or OAuth.
- No scheduler activation.
- No production SQLite access.
- No Gmail integration.
- No composer/model integration.
- No dashboard UI or API server.
- No LaunchAgents or OpenClaw runtime wiring.
- No public internet exposure or external-user collaboration.
- No autonomous legal, tax, portfolio, crypto, investment, health, medical, or
  relationship-message execution.
- No broader scheduler idempotency/send ledger in Phase 5.
- Post-merge live smoke testing is a separate OpenClaw-approved operation, not
  part of this PR.

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
