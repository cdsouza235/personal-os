# Personal OS

Personal OS is a modular, local-first productivity, routine, priority, and execution operating system. It helps Chris think clearly, maintain routines, manage high-value priorities, generate briefings, create Todoist tasks, schedule Calendar blocks, preserve durable notes, and run reports through OpenClaw on the Mac Mini.

This repository is the private code source of truth for Personal OS. It is documentation-first right now: no live workflow scripts, runtime mutations, or production integrations are enabled from this repo yet.

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

The V1 dashboard is local-network only, with no public internet exposure and no login or password requirement. It should be mobile-friendly for iPhone and usable from Windows or Mac browsers on the local network.

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
- Codex/Fable: software developer.

## Safety Boundary

Codex may work on documentation, tests, and repository code after the appropriate phase gate, but OpenClaw remains the production/runtime operator.

Codex must not send email, write Todoist, write Calendar, load LaunchAgents, modify production ledgers, mutate production SQLite state, run live OpenClaw workflows, inspect `/Users/coldstake/PersonalOS`, inspect `/Users/coldstake/.openclaw`, touch credentials, or touch production state without explicit approval.

The first live-system interaction phase is Phase 0 read-only inventory.

## Repository Layout

```text
docs/          Product, architecture, safety, roadmap, and Codex workflow docs.
app/           Future local dashboard and API surfaces.
personalos/    Future domain modules for routines, priorities, composer, integrations, reports, and evidence.
scripts/       Reserved for later inert or approved helper scripts; no live workflow scripts in Phase -1.
tests/         Test suites for repository code.
.codex/        Codex-local project guidance and metadata.
```

## Current Phase

Phase -1 scaffold is complete and committed at `04d51891c2778971f7657eda6076a8cd80b11129`.

Next recommended phase: Phase 0 read-only inventory, after explicit approval.
