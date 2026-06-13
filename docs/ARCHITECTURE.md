# Architecture

## Purpose

Personal OS is a modular, local-first system for productivity, routines, priorities, and execution. It separates strategic reasoning, code development, local runtime operation, durable memory, and external execution systems.

## Roles

### ChatGPT

ChatGPT is the strategy and synthesis layer. It produces PRDs, architecture proposals, acceptance criteria, plans, retrospectives, and audits. It does not directly operate the local runtime.

### Codex

Codex is the software development layer. Codex edits this repository, creates tests, proposes implementation details, and documents behavior. Codex must follow the safety policy before any interaction with live systems.

### OpenClaw

OpenClaw is the local runtime and operator. It is responsible for approved local workflows on the Mac Mini after explicit gates are passed. OpenClaw runtime configuration is production state and must not be mutated by Codex without explicit approval.

### Mac Mini

The Mac Mini is the runtime and deployment host. It is expected to run approved local workflows, store runtime artifacts, and provide access to local-first state once the project reaches the correct phase.

### GitHub

GitHub is the source of truth for code. Repository changes should be reviewed and committed through standard development workflows before they influence runtime behavior.

### PersonalOS, Obsidian, and Markdown

Markdown and Obsidian hold durable memory and human-readable operating records, including:

- Clarity Notes
- Follow-Up Notes
- Logs
- Protocols
- Decision records
- Evidence summaries

These documents complement, but do not replace, structured runtime state.

## State Model

SQLite will be used for structured runtime state after the project enters an approved implementation phase. Production SQLite state is protected and must not be inspected or changed during Phase -1.

Markdown will be used for durable narrative state, protocols, logs, and reviewable records.

## Module Boundaries

```text
app/dashboard/            Future local dashboard surface.
app/api/                  Future API surface.
personalos/routines/      Routine modeling and orchestration code.
personalos/priorities/    Priority modeling and review code.
personalos/composer/      Drafting and synthesis helpers.
personalos/todoist/       Todoist integration boundary.
personalos/calendar/      Calendar integration boundary.
personalos/gmail/         Gmail integration boundary.
