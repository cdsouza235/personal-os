# Phase 14-C Connectivity Readiness

Date: 2026-06-29

Baseline:

- `main` at `16ad60e288d1c83049dbd28f210cb7824fd48ab2`
- PR #90 already merged
- Google Calendar smoke event already exists:
  `memu6fhql6stl71auv05e1a6d0`
- Calendar duplicate creation is not authorized by this packet

## Capability Inventory

| Capability | Status | Evidence / blocker |
| --- | --- | --- |
| Git repo read/write | available | local clean `main`; `origin/HEAD` matches baseline; branch push succeeded |
| GitHub PR via `gh` | available | PR metadata query succeeded; `gh auth status` still reports invalid stored host tokens |
| Google Calendar connector | available | bounded readback found exactly one matching event |
| Gmail connector/client | missing | `gmail_not_run_missing_connector_or_client` |
| Todoist connector/client | repo-local gated client path prepared | `personalos phase14c todoist-inbox-smoke` defaults to no-execution/report-only; live path requires token config plus explicit approval |
| OpenClaw local/test/sandbox harness | available and passed | `openclaw_local_harness_passed` |
| OpenClaw model provider/client | repo-local OpenRouter gated client path prepared | `personalos phase14c openrouter-model-smoke` defaults to no-execution/report-only; live path requires OpenRouter config plus explicit approval |

Safe Calendar account identity observed from the connector:

- `c***@gmail.com`

## Rails Run

Google Calendar:

- No new event was created.
- The existing event was read back by ID and by a bounded July 6, 2026
  search window.
- The search returned exactly one matching event.

OpenClaw local/test/sandbox:

- Ran once through `run_phase14c_openclaw_local_sandbox_smoke`.
- Result: `openclaw_local_harness_passed`.
- Mode: `local_test_sandbox`.
- Invocation name: `phase14c_smoke_test`.
- No protected OpenClaw runtime call, protected path access, scheduler
  activation, production DB activation, broad runtime handoff, credential
  exposure, or external mutation occurred.

## Rails Not Run

Gmail:

- Result: `gmail_not_run_missing_connector_or_client`.
- No email was drafted or sent.
- Required next-run setup names:
  - `PERSONALOS_PHASE14C_GMAIL_CREDENTIAL`
  - `PHASE14C_GMAIL_CONTROLLED_RECIPIENT`

Todoist:

- Result: not run live in this packet.
- No task was created.
- Default gate status without live execution:
  `todoist_not_run_missing_execute_live_flag`.
- Required next-run setup name:
  - `PERSONALOS_PHASE14C_TODOIST_TOKEN`
- Future live command, after separate explicit approval:
  `personalos phase14c todoist-inbox-smoke --execute-live --approval-reference <ref> --json`
- The live path creates at most one Inbox/default task, omits `project_id` for
  Inbox/default, and does not set recurrence, subtasks, labels, comments,
  attachments, edits, deletes, skip/push/bump behavior, or automatic
  rescheduling.

OpenClaw model smoke:

- Result: not run live in this packet.
- No model provider call was made.
- Default gate status is
  `openclaw_model_smoke_not_run_missing_provider_config` when required config
  names are missing, or
  `openclaw_model_smoke_not_run_missing_execute_live_flag` when config names
  are present but live execution is not explicitly requested.
- Required next-run setup names:
  - `PERSONALOS_OPENCLAW_MODEL_PROVIDER`
  - `PERSONALOS_OPENCLAW_MODEL_API_KEY`
  - `PERSONALOS_OPENCLAW_NEMOTRON_SUPER_MODEL`
  - `PERSONALOS_OPENCLAW_GLM_5_2_MODEL`
- Future live command, after separate explicit approval:
  `personalos phase14c openrouter-model-smoke --execute-live --approval-reference <ref> --json`
- The live path uses a stdlib HTTP OpenRouter client, calls Nemotron Super at
  most once, and calls GLM 5.2 at most once only if the primary validation
  fails. It does not use a provider SDK, log credential values, log full
  prompts, log raw provider responses, execute tools, or invoke OpenClaw
  runtime.

Phase 14-C live-rail config preflight also reports these missing names:

- `PERSONALOS_PHASE14C_TODOIST_TOKEN`
- `PERSONALOS_PHASE14C_GOOGLE_CALENDAR_CREDENTIAL`
- `PERSONALOS_PHASE14C_GMAIL_CREDENTIAL`
- `PERSONALOS_PHASE14C_OPENCLAW_TEST_MODE`

## Mobile Continuity Commands

Local setup script:

```bash
scripts/phase14c_connectivity_setup.sh
```

The script refuses to overwrite an existing `.env.local`, prompts without
echoing token/API-key values, writes through a temporary file before moving
the completed file to `.env.local`, and leaves `.env.local` gitignored. It
must not be committed or pasted into chat.

Names-only setup verification:

```bash
set -a; source .env.local; set +a; PYTHONPATH=src python3 -m personalos.cli phase14c connectivity-setup --json
```

Repo readiness:

```bash
PYTHONPATH=src python3 -m personalos.cli readiness status --json
```

Phase 14-C live-rail config-name preflight:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c supervised-smoke-credential-preflight --json
```

OpenClaw model provider readiness:

```bash
set -a; source .env.local; set +a; PYTHONPATH=src python3 -m personalos.cli phase14c openclaw-model-readiness --json
```

Todoist no-execution gate:

```bash
set -a; source .env.local; set +a; PYTHONPATH=src python3 -m personalos.cli phase14c todoist-inbox-smoke --json
```

OpenRouter no-execution gate:

```bash
set -a; source .env.local; set +a; PYTHONPATH=src python3 -m personalos.cli phase14c openrouter-model-smoke --json
```

OpenClaw local/test/sandbox harness:

```bash
PYTHONPATH=src python3 -c 'import json; from personalos.phase14c_supervised_smoke import run_phase14c_openclaw_local_sandbox_smoke; print(json.dumps(run_phase14c_openclaw_local_sandbox_smoke(), sort_keys=True, indent=2))'
```

## Safety Assertions

- No credential values, tokens, OAuth material, or environment dumps were
  printed or committed.
- `.env.local` is gitignored; `.env.example` contains placeholders only.
- No Gmail email was drafted or sent.
- No Todoist task was created.
- No OpenRouter model provider call was made.
- No duplicate Calendar event was created.
- No protected path was accessed.
- No scheduler, LaunchAgent, crontab, daemon, watcher, or background loop was
  activated.
- No production DB path was activated.
- No dynamic cleaning was implemented.
- No broad OpenClaw runtime handoff occurred.
- `readiness.status` remains `not_ready`.
- `inert_report_only` remains `true`.
