# Codex Workflow

## Role

Codex/Fable is the software development layer for Personal OS. It edits repository code, tests, and documentation after phase gates. It does not act as the production operator.

OpenClaw remains the production and runtime operator.

## Current Work Type

This update is documentation-only. Codex may update README and docs, but must not inspect or mutate protected runtime paths, external systems, credentials, production ledgers, production SQLite state, or production state.

## Phase Rules

Phase -1 is complete and committed. Phase 0 must be read-only inventory first and requires explicit approval before starting.

After Phase 0, Codex may edit code, tests, and docs in repo branches according to the approved plan.

## Allowed Codex Work

Codex may:

- Read repository-local files.
- Edit documentation in this repository.
- Edit code and tests after the correct phase gate.
- Produce diff summaries and implementation notes.
- Run local tests for repository code.
- Document assumptions, acceptance criteria, and safety boundaries.

## Prohibited Codex Work

Codex may not:

- Send email.
- Write Todoist.
- Write Calendar.
- Load or modify LaunchAgents.
- Modify production ledgers.
- Mutate production SQLite state.
- Run live OpenClaw workflows.
- Inspect `/Users/coldstake/PersonalOS`.
- Inspect `/Users/coldstake/.openclaw`.
- Touch credentials.
- Touch runtime or production state.
- Create scripts that run live workflows.

## Development Evidence Standard

For development work, Codex should return:

- Files changed.
- Diff summary.
- Test logs or command output when applicable.
- Unit or integration output when applicable.
- Brief implementation note.
- Assumptions and recommended next step.

## Runtime Evidence Standard

Runtime and live operations are owned by OpenClaw after approval gates. Evidence should include:

- Persisted completion report.
- Ledger or log snapshot.
- Safety flags.

Forensic bundles are reserved for incidents, production activation, high-stakes operations, or duplicate/mutation anomalies.

## Branch and Commit Guidance

Documentation-only changes may be made directly in the repo when requested. Code changes after Phase 0 should usually happen in branches with focused commits and tests.

Do not commit unless the user explicitly asks for a commit.

## Model Boundary

Codex uses the repository as its working surface. It must not give a composer model broad filesystem access or unrestricted production context. Composer integrations must use dedicated Composer Packets and structured JSON outputs before execution.
