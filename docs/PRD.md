# Product Requirements Document

## Product

Personal OS is a modular, local-first productivity, routine, priority, and execution operating system.

## Problem

Personal productivity systems often scatter priorities, routines, follow-ups, calendar obligations, tasks, email, and reflective notes across disconnected tools. Personal OS aims to create a coherent operating layer while preserving explicit human approval for systems that affect live execution.

## Goals

- Maintain durable clarity around priorities, routines, and follow-ups.
- Provide structured state for runtime workflows through SQLite in later phases.
- Preserve reviewable narrative records in Markdown and Obsidian.
- Keep code versioned in GitHub.
- Keep runtime operation delegated to OpenClaw after approval gates.
- Integrate with Todoist, Calendar, and Gmail only behind explicit safety boundaries.

## Non-Goals for Phase -1

- No live-system inventory.
- No Gmail, Todoist, Calendar, LaunchAgent, production ledger, credential, or runtime mutation.
- No production SQLite inspection or mutation.
- No OpenClaw runtime configuration inspection or mutation.
- No scripts that execute live workflows.

## User Roles

- ChatGPT: strategy, synthesis, PRD, architecture, acceptance criteria, and audit.
- Codex: software development layer.
- OpenClaw: local runtime and operator on the Mac Mini.
- PersonalOS, Obsidian, and Markdown: durable memory, logs, protocols, and notes.
- Todoist, Calendar, and Gmail: external execution systems behind explicit gates.

## Initial Acceptance Criteria

Phase -1 is complete when:

- The initial repository scaffold exists.
- Core documentation files describe the architecture and safety boundaries.
- Empty module directories are represented by inert placeholders.
- No live runtime, credential, external execution, or production state path has been inspected or mutated.
- No live workflow script has been created.

## Future Capabilities

Future phases may add:
