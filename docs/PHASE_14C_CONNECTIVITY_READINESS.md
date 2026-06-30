# Phase 14-C Connectivity Readiness

Date: 2026-06-30

Baseline:

- `main` at `b534ca34c9ea17a61d0430e0fea5b8c24739ebc9`
- PR #94 already merged
- Google Calendar smoke event already exists:
  `memu6fhql6stl71auv05e1a6d0`
- Calendar duplicate creation was not authorized or performed by this packet
- Live approval reference:
  `phase14c-2026-06-30-connectivity-live-smoke`

## Capability Inventory

| Capability | Status | Evidence / blocker |
| --- | --- | --- |
| Git repo read/write | available | local clean `main`; `origin/HEAD` matches baseline; branch push succeeded |
| GitHub PR via `gh` | available | PR metadata query succeeded; `gh auth status` still reports invalid stored host tokens |
| Google Calendar connector | available | bounded readback found exactly one matching event |
| Gmail connector/client | available; bounded live smoke passed | `personalos phase14c gmail-smtp-smoke --execute-live --approval-reference phase14c-2026-06-30-connectivity-live-smoke --json` sent one controlled Gmail SMTP test email |
| Todoist connector/client | available; bounded live create attempt unconfirmed | `personalos phase14c todoist-inbox-smoke --execute-live --approval-reference phase14c-2026-06-30-connectivity-live-smoke --json` made one Inbox/default create attempt and could not validate the response |
| OpenClaw local/test/sandbox harness | available and passed | `openclaw_local_harness_passed` |
| OpenClaw model provider/client | available; bounded OpenRouter smoke failed validation | `personalos phase14c openrouter-model-smoke --execute-live --approval-reference phase14c-2026-06-30-connectivity-live-smoke --json` called Nemotron Super once and GLM 5.2 once; both attempts reported sanitized `transport_or_parse_error` |

Safe Calendar account identity observed from the connector:

- `c***@gmail.com`

## Rails Run

Gmail SMTP self-send:

- Result: `gmail_self_send_smoke_passed`.
- One controlled Gmail SMTP email was accepted by Gmail.
- Sender masked: `c***@gmail.com`.
- Recipient masked: `c***@gmail.com`.
- Subject: `[Phase 14-C Test] Clean Kitchen Countertops and Stovetop`.
- Call budget: `email_send_calls=1`, `max_email_sends=1`.
- No CC, BCC, attachments, forwarding, or existing-thread reply.
- No database write, file write, scheduler activation, production DB
  activation, protected-path access, or broad Gmail automation occurred.

Todoist Inbox/default:

- Result: `todoist_inbox_default_task_smoke_failed`.
- Mutation state:
  `unconfirmed_after_task_create_attempt`.
- One Inbox/default task-create request was attempted.
- Title: `[Phase 14-C Test] Clean Kitchen Countertops and Stovetop`.
- Due date: 2026-07-06.
- Call budget: `task_create_calls=1`, `max_task_creates=1`.
- The response could not be validated, so the report intentionally does not
  assert that a task was created or not created.
- Do not rerun this rail without a manual Todoist check or a new explicit
  duplicate-risk approval.
- No recurrence, subtasks, labels, comments, attachments, automatic edits,
  deletes, skip/push/bump behavior, or automatic rescheduling were requested.
- No database write, file write, scheduler activation, production DB
  activation, or protected-path access occurred.

Google Calendar:

- No new event was created.
- The existing event was read back by ID and by a bounded July 6, 2026
  search window.
- The search returned exactly one matching event.

OpenRouter model smoke:

- Result: `openclaw_model_smoke_validation_failed`.
- Primary smoke lane call: `nemotron_super`, one call.
- Fallback smoke lane call: `glm_5_2`, one call, only after primary validation
  failed.
- Call budget: `primary_calls=1`, `fallback_calls=1`,
  `max_primary_calls=1`, `max_fallback_calls=1`.
- Both attempts reported sanitized `transport_or_parse_error` metadata.
- No raw provider response, full prompt, configured model ID, or credential
  value was logged or recorded.
- No tool execution, OpenClaw runtime call, protected-path access, scheduler
  activation, production DB activation, or external mutation occurred.

OpenClaw local/test/sandbox:

- Ran once through `run_phase14c_openclaw_local_sandbox_smoke`.
- Result: `openclaw_local_harness_passed`.
- Mode: `local_test_sandbox`.
- Invocation name: `phase14c_smoke_test`.
- No protected OpenClaw runtime call, protected path access, scheduler
  activation, production DB activation, broad runtime handoff, credential
  exposure, or external mutation occurred.

## Rails Not Run

Protected-runtime OpenClaw:

- Result: not run.
- No protected OpenClaw runtime invocation occurred.
- The only OpenClaw rail execution remains the repo-local
  local/test/sandbox harness described above.

Calendar duplicate write:

- Result: not run.
- No duplicate Calendar event was created.

## Mobile Continuity Commands

Local setup script:

```bash
scripts/phase14c_connectivity_setup.sh
```

The script refuses to overwrite an existing `.env.local`, prompts without
echoing Gmail app password, token, or API-key values, writes through a
temporary file before moving the completed file to `.env.local`, and leaves
`.env.local` gitignored. It must not be committed or pasted into chat.

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

Gmail SMTP no-execution gate:

```bash
set -a; source .env.local; set +a; PYTHONPATH=src python3 -m personalos.cli phase14c gmail-smtp-smoke --json
```

OpenRouter no-execution gate:

```bash
set -a; source .env.local; set +a; PYTHONPATH=src python3 -m personalos.cli phase14c openrouter-model-smoke --json
```

Live commands already used once for this evidence packet:

```bash
set -a; source .env.local; set +a; PYTHONPATH=src python3 -m personalos.cli phase14c gmail-smtp-smoke --execute-live --approval-reference phase14c-2026-06-30-connectivity-live-smoke --json
set -a; source .env.local; set +a; PYTHONPATH=src python3 -m personalos.cli phase14c todoist-inbox-smoke --execute-live --approval-reference phase14c-2026-06-30-connectivity-live-smoke --json
set -a; source .env.local; set +a; PYTHONPATH=src python3 -m personalos.cli phase14c openrouter-model-smoke --execute-live --approval-reference phase14c-2026-06-30-connectivity-live-smoke --json
```

Do not rerun any of those three live commands for this evidence packet.
Gmail already passed, Todoist has an unconfirmed create-attempt result, and
OpenRouter already exhausted the allowed primary/fallback call budget.

OpenClaw local/test/sandbox harness:

```bash
PYTHONPATH=src python3 -c 'import json; from personalos.phase14c_supervised_smoke import run_phase14c_openclaw_local_sandbox_smoke; print(json.dumps(run_phase14c_openclaw_local_sandbox_smoke(), sort_keys=True, indent=2))'
```

## Safety Assertions

- Credential values were read only by the three explicitly approved bounded
  live commands that required them.
- No credential values, tokens, OAuth material, or environment dumps were
  printed, copied, logged, summarized, or committed.
- `.env.local` is gitignored; `.env.example` contains placeholders only.
- Exactly one Gmail email was sent and accepted by Gmail SMTP.
- Exactly one Todoist task-create request was attempted; task creation remains
  unconfirmed and must not be retried without manual review or explicit
  duplicate-risk approval.
- Exactly one OpenRouter Nemotron Super primary call and one GLM 5.2 fallback
  call were made; both failed validation with sanitized transport/parse
  metadata.
- No duplicate Calendar event was created.
- No protected path was accessed.
- No scheduler, LaunchAgent, crontab, daemon, watcher, or background loop was
  activated.
- No production DB path was activated.
- No dynamic cleaning was implemented.
- No broad OpenClaw runtime handoff occurred.
- `readiness.status` remains `not_ready`.
- `inert_report_only` remains `true`.
