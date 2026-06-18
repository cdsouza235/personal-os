# Phase 13E-D Synthetic End-To-End No-Send Demo

Last updated: 2026-06-18

## Objective

Define the next phase: a deterministic synthetic end-to-end demo that exercises
existing local Personal OS no-send surfaces and produces one evidence bundle
for review. This document does not implement the demo.

## In Scope

- Synthetic local inputs only.
- Explicit safe output directory supplied by the caller.
- Existing repo-local no-send CLI/status/dashboard/report surfaces.
- Dev/test SQLite only through explicit safe paths.
- JSON evidence suitable for ChatGPT/Codex audit.
- Human-readable summary suitable for Chris review.
- Assertions that live rails remained disabled.

## Out Of Scope

- Phase 14.
- Live Gmail, Todoist, Google Calendar, PersonalOS Markdown, or OpenClaw work.
- Credential loading, reading, configuration, or OAuth setup.
- Production DB activation or mutation.
- Scheduler, LaunchAgent, crontab, daemon, or background-loop activation.
- Live model/API calls.
- External service calls or external writes.
- Protected path inspection or mutation.

## Canonical Future Command Target

```bash
PYTHONPATH=src python3 -m personalos.cli demo no-send-e2e --output-dir <safe_output_dir> --json
```

The command does not exist yet. Phase 13E-D implementation, when explicitly
approved, should use this target unless Chris changes the contract.

## Required Synthetic Fixture Coverage

The future demo fixture set should include:

- routines
- priorities
- projects/focus areas, if supported
- follow-ups
- Todoist candidates as preview/simulated only
- Calendar candidates as preview/simulated only
- Gmail/no-send briefing export only
- Markdown note candidates as preview/review-only
- blocked high-stakes candidates
- side-effect/idempotency evidence
- scheduler simulation evidence, if used

## Expected Evidence Bundle

The future demo should write only under `<safe_output_dir>` and should produce
evidence comparable to:

- synthetic input manifest
- safe DB path classification
- generated local dev/test DB path
- workflow steps attempted
- workflow steps completed
- status/readiness report
- no-send briefing preview evidence
- synthesis preview/apply evidence if used
- side-effect ledger summary if used
- scheduler simulation evidence if used
- dashboard/static render evidence if used
- JSON completion report
- human-readable summary
- artifact list
- safety assertions

## Safety Assertions

The evidence bundle must assert:

- `readiness.status=not_ready`
- `inert_report_only=true`
- `live_rails_activated=false`
- `credentials_loaded=false`
- `credentials_read=false`
- `production_db_path_active=false`
- `scheduler_activated=false`
- `launch_agent_installed=false`
- `crontab_modified=false`
- `daemon_started=false`
- `openclaw_called=false`
- `external_services_contacted=false`
- `external_mutation=false`
- `gmail_touched=false`
- `todoist_touched=false`
- `calendar_touched=false`
- `personalos_markdown_written=false`
- `protected_paths_touched=false`

## Acceptance Criteria

- The demo is deterministic from synthetic inputs.
- The output directory is explicit and passes safe-path validation.
- No repo-local `var/` directory is created.
- No SQLite/DB artifacts are left in the repo outside `.git`.
- The command exits nonzero when given protected, credential-looking, or
  production-looking paths.
- The JSON output is stable enough for audit.
- Human-readable output identifies safe local actions and blocked live actions.
- Safety assertions prove no live rails, credentials, production DB,
  scheduler/background activation, external writes, OpenClaw calls, or
  protected paths were touched.

## Validation Commands

```bash
git status --short
git diff --check
git diff --cached --check
PYTHONPATH=src python3 -m unittest discover -s tests -p "test_*.py"
PYTHONTRACEMALLOC=10 PYTHONPATH=src python3 -W always::ResourceWarning -m unittest discover -s tests -p "test_*.py" -q
find . -maxdepth 2 -name var -print
find . -path ./.git -prune -o \( -name "*.sqlite" -o -name "*.sqlite3" -o -name "*.db" \) -print
```

## Phase 14 Block

Phase 14 remains blocked. Completing or implementing this demo does not
authorize live rails, credential work, production DB activation, scheduler
activation, OpenClaw runtime work, or external writes.
