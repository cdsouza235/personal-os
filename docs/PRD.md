# Personal OS Master PRD v0.1

## Product Definition

Personal OS is a modular, local-first productivity, routine, priority, and execution operating system. It helps Chris think clearly, maintain routines, manage high-value priorities, generate briefings, create Todoist tasks, schedule Calendar blocks, preserve durable notes, and run reports through OpenClaw on the Mac Mini.

## Product Principles

- Chris remains the owner, final approver, and source of judgment.
- Todoist and Calendar are execution rails, not the brain.
- Obsidian and Markdown stay minimal and high-signal.
- SQLite holds structured runtime state.
- OpenClaw operates approved local workflows.
- ChatGPT synthesizes and audits.
- Codex/Fable builds repository code.
- Safety should be light in the user experience and explicit in the architecture.

## Operating Roles

- Chris: owner, final approver, source of judgment and priorities.
- ChatGPT: thought partner, synthesis layer, analysis layer, PRD writer, architect, and auditor.
- Codex/Fable: software development layer.
- OpenClaw: local Personal Assistant and runtime operator on the Mac Mini.
- Mac Mini: always-on runtime host, OpenClaw host, SQLite state host, local PersonalOS file host, scheduler, and local repo clone.
- GitHub private repo: source of truth for code.
- SQLite: structured runtime state.
- Markdown, Obsidian, and PersonalOS: Clarity Notes, General Follow-Up Notes, protocols, logs, and reviews.
- Todoist, Calendar, and Gmail: execution rails, only touched by validated runtime modules.

## V1 Scope

V1 should deliver a local-first operating shell and the core routines, priorities, briefings, and integration boundaries needed for daily use.

- Local dashboard shell.
- Routine editor.
- Today view.
- Priority registry.
- ChatGPT synthesis import box.
- SQLite runtime state store.
- 8am Morning Brief, 12pm Midday Reset, 4pm Afternoon Checkpoint, and 8pm Evening Shutdown.
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

The dashboard must be local-network only. It must not be exposed to the public internet. V1 does not require login or password protection.

The dashboard should be mobile-friendly for iPhone and usable from Windows and Mac browsers.

Required sections:

- Today View
- Routine Editor
- Priority Editor
- Todoist/Calendar Preview
- System Status/Logs
- Settings/Permissions
- Reports/Jobs shell

## Routine Defaults

- Cleaning: 1 task/day, Monday-Friday.
- Reading: 4x/week.
- Prayer / Meditation: 2x/week.
- Grease-the-Groove: rotating exercises as needed, target 45 reps per exercise per week.
- Fitness / Strength: separate from Grease-the-Groove; the existing fitness tracker should be preserved and integrated later.
- Shutdown / Review: daily evening.

## Routine Engine Requirements

Routines must be data-driven, not hardcoded. The routine editor must allow add, edit, disable, and delete operations.

Supported cadence rules:

- daily
- weekdays
- x_times_per_week
- weekly
- every_n_days
- specific_days
- rotating_sequence
- manual_only

Supported missed behavior options:

- combine_with_next
- bump_schedule_by_one_day
- carry_forward_within_week
- skip_and_continue
- escalate_to_review

## Todoist Requirements

Todoist is the action rail, not the brain.

- Low-risk routine tasks can auto-write.
- High-value review and follow-up tasks can auto-write.
- High-stakes execution actions require approval.
- Vague thoughts and raw emotional notes must not become Todoist tasks.
- Completed Todoist tasks should be removed from later briefings.

## Calendar Requirements

- Preferred windows should be used first.
- Availability-aware scheduling can be added later.
- Self-only review, deep work, admin, and routine blocks may auto-write once validated.
- Events involving other people or high-stakes appointments require review.

## Briefing Cadence

Timezone: America/Chicago.

- 8am: Morning Brief.
- 12pm: Midday Reset.
- 4pm: Afternoon Checkpoint.
- 8pm: Evening Shutdown.

Daily plan generation happens once in the morning. Each email is generated just-in-time before its window. Todoist and Calendar baseline writes happen in the morning. Later windows adjust based on completed tasks and updated state.

## Notes

Obsidian and PersonalOS should stay minimal.

Clarity Notes are durable, high-signal synthesis after ChatGPT processing. General Follow-Up Notes capture things to revisit, open questions, admin reminders, and project reminders.

Notes become Todoist tasks only if they meet the task schema.

## Weekly Chart Pack Workflow

- Weekend reminder to produce chart packs.
- Chris sends chart packs and TradingView alerts to ChatGPT.
- ChatGPT synthesizes.
- OpenClaw stores synthesis and updates weekly chart review notes.
- The system tracks week-over-week changes.
- OpenClaw does not independently analyze investments.

## Fitness Integration

V1 preserves the existing CSV-based local fitness tracker and adds only a module shell, link, and status surface. V1.5 may add deeper integration with routine prompts and recovery/training state.

## Reports and Jobs

Reports are coded jobs, not a separate analyst persona. Chris and ChatGPT define requirements. Codex builds jobs. OpenClaw runs jobs and delivers outputs.

Example jobs:

- Macro calendar.
- Earnings calendar.
- TradingView alert digest.
- Priority status report.
- Routine adherence report.
- Todoist completion report.
- Calendar utilization report.

## Evidence Standard

Development work should produce a diff summary, test logs, unit or integration output when applicable, and a brief implementation note.

Runtime or live operations should produce a persisted completion report, ledger or log snapshot, and safety flags.

Forensic bundles are reserved for incidents, production activation, high-stakes operations, or duplicate/mutation anomalies.

## Non-Goals for Current Documentation Phase

- No implementation code.
- No live-system inventory.
- No Gmail, Todoist, Calendar, LaunchAgent, production ledger, credential, runtime, or production SQLite mutation.
- No inspection of `/Users/coldstake/PersonalOS`.
- No inspection of `/Users/coldstake/.openclaw`.
- No live workflow scripts.
