# Phase 13E-D Synthetic End-To-End No-Send Demo

Last updated: 2026-06-18

## Objective

Implement a deterministic synthetic end-to-end demo that exercises existing
local Personal OS no-send surfaces and produces one evidence bundle for review.
The demo uses fixture data only and writes artifacts only under an explicit safe
output directory.

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

## Canonical Command

```bash
PYTHONPATH=src python3 -m personalos.cli demo no-send-e2e --output-dir <safe_output_dir> --json
```

`--output-dir` is required. With `--json`, stdout emits the stable completion
report for audit.

The command creates one dev/test/demo SQLite database at:

```text
<safe_output_dir>/demo.sqlite3
```

The command never defaults to repo-local `var/`, never writes SQLite artifacts
inside the repo, and rejects unsafe output directories before creating or
listing them.

## Safe Output Directory Rules

The demo output directory must be an explicit absolute path under an OS temp
directory. It is rejected when it is or appears to be:

- a protected PersonalOS path
- an OpenClaw path
- a credential, token, secret, OAuth, API-key, or password path
- a production, prod, or live path
- a scheduler, LaunchAgent, crontab, daemon, or background-loop path
- the repo root, under the repo, under `.git`, or under repo-local `var/`

## Synthetic Fixture Coverage

The implemented fixture set includes:

- routines
- priorities
- projects/focus areas
- follow-ups
- Todoist candidates as preview/simulated only
- Calendar candidates as preview/simulated only
- Gmail/no-send briefing export only
- Markdown note candidates as preview/review-only
- blocked/review-only high-stakes candidates for tax, legal/estate,
  portfolio/crypto/investments, health/medical, and relationship messages
- side-effect/idempotency evidence
- scheduler simulation preview evidence without scheduler activation

## Evidence Bundle

The command writes:

- `synthetic_input_manifest.json`
- `demo.sqlite3`
- `safe_path_classification.json`
- `workflow_report.json`
- `status_readiness_report.json`
- `synthesis_payload.synthetic.json`
- `synthesis_preview.json`
- `synthesis_apply_report.json`
- `no_send_briefing_preview.json`
- `no_send_briefing_preview.md`
- `side_effect_ledger_summary.json`
- `idempotency_ledger_summary.json`
- `scheduler_simulation_evidence.json`
- `dashboard_render_evidence.json`
- `dashboard_render.html`
- `safety_assertions.json`
- `artifacts.json`
- `summary.md`
- `completion_report.json`

The completion report includes the demo name, phase name, command contract,
output directory, generated DB path, attempted/completed workflow steps,
artifact list, safety assertions, no-send/export summary, blocked live-action
summary, status/readiness summary, and stable fixture manifest hash.

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
- The command exits nonzero when given protected, credential-looking,
  production/live-looking, OpenClaw-looking, scheduler-looking,
  LaunchAgent-looking, crontab-looking, daemon-looking, repo-root, `.git`, or
  repo-local paths.
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
