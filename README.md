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

Phase -1 scaffold is complete and committed at `04d51891c2778971f7657eda6076a8cd80b11129`.

Next recommended phase: Phase 0 read-only inventory, after explicit approval.
