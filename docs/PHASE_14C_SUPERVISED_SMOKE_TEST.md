# Phase 14-C Supervised Multi-Rail Smoke Test

This runbook prepares the next Phase 14-C learning step: a bounded supervised
smoke test across Todoist, Google Calendar, Gmail, and OpenClaw.

It records the current human direction that these rails are acceptable
low-blast-radius smoke-test rails for Personal OS when the action is clearly
marked, manually supervised, and limited to one test operation per rail. This
document does not run the smoke test by itself.

Source contract:

- `src/personalos/phase14c_supervised_smoke.py`
- `build_phase14c_supervised_smoke_runbook`
- `build_default_phase14c_supervised_smoke_request`
- `build_phase14c_supervised_live_smoke_status`
- `build_phase14c_gmail_self_send_readiness_report`
- `build_phase14c_gmail_self_send_smoke_request`
- `resolve_phase14c_todoist_due_date`
- `run_phase14c_openclaw_local_sandbox_smoke`
- `build_phase14c_supervised_smoke_request_template_report`
- `build_phase14c_credential_preflight_report`
- `build_phase14c_supervised_smoke_request_validation_report`
- `validate_phase14c_supervised_smoke_request`
- `execute_phase14c_supervised_smoke_request`
- `run_phase14c_supervised_smoke_dry_run_rehearsal`
- `src/personalos/openclaw_model_strategy.py`
- `build_openclaw_model_provider_readiness_report`
- `run_openclaw_model_smoke_probe`
- `src/personalos/phase14c_wide_net_rehearsal.py`
- `build_phase14c_wide_net_rehearsal_plan`

CLI discovery:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c supervised-smoke-runbook --json
```

That CLI command is a runbook/status surface only. It does not load
credentials, open a database, initialize live clients, create Todoist tasks,
create Calendar events, create or send Gmail, invoke OpenClaw, or perform
external writes. In short, it does not initialize live clients.

Request template:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c supervised-smoke-request-template --mode dry_run --json
```

That CLI command prints a request-template report for the one-object-per-rail
smoke request. It is stdout-only: it does not read environment variables, load
credentials, open a database, initialize live clients, create Todoist tasks,
create Calendar events, create or send Gmail, invoke OpenClaw, write files, or
perform external writes. The report includes `template_only_not_authorization`
and `ready_for_live_execution=false`.

The command also accepts `--mode live_run`, but that mode is still only a
template. It keeps `live_run_requested=false` and `approval_reference=null` so
the generated request is not a live authorization and still requires a
separate explicit live-test initiation, request validation, credential-name
preflight, live-readiness review, injected clients, and `live_run_approved=true`
before any future execution path could run.

Request validation:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c supervised-smoke-validate --input-file <safe_request_json> --json
```

That CLI command reads one explicit safe JSON request file and prints a
redacted validation report. It does not load credentials, open a database,
initialize live clients, create Todoist tasks, create Calendar events, create
or send Gmail, invoke OpenClaw, write files, or perform external writes. The
validation output includes counts, booleans, guardrail status, and missing
config entry names only; it must not include raw `normalized_request`, raw
controlled test recipients, credential values, OAuth material, or authorization
material.

Credential preflight:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c supervised-smoke-credential-preflight --json
```

That CLI command checks required environment/config entry names only and prints
a redacted missing-name report. It must not read, print, log, copy, summarize,
or commit credential values, token contents, OAuth material, authorization
material, or present non-required environment names. It does not load
credentials, open a database, initialize live clients, create Todoist tasks,
create Calendar events, create or send Gmail, invoke OpenClaw, write files, or
perform external writes.

Live-readiness report:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c supervised-smoke-live-readiness --input-file <safe_request_json> --json
```

That CLI command reads one explicit safe JSON request file, checks required
environment/config entry names only, and prints a redacted live-readiness
report. It can confirm whether request/config prerequisites are met for a
separate manually initiated live step, but `ready_for_live_execution_in_this_cli`
is always false and `live_run_executed=false`. It does not read credential
values, load credentials, open a database, initialize live clients, create
Todoist tasks, create Calendar events, create or send Gmail, invoke OpenClaw,
write files, or perform external writes.

OpenClaw model readiness:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c openclaw-model-readiness --json
```

That CLI command checks OpenClaw model-provider config entry names only and
prints the deterministic Nemotron Super / GLM 5.2 smoke-lane plan. It does not
read credential values, load credentials, initialize a model client, call a
model provider, execute tools, invoke OpenClaw, open a database, or write
files. It does not initialize a model client.

Todoist Inbox/default smoke gate:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c todoist-inbox-smoke --json
```

That default command is report-only. It reads environment key names only,
checks the one-task smoke shape, reports the next upcoming Monday due date,
and does not read the Todoist token, initialize a live client, create a task,
open a database, write files, activate a scheduler, or touch protected paths.
Without `--execute-live`, it reports
`todoist_not_run_missing_execute_live_flag`.

A future supervised live Todoist smoke, after credentials are configured and a
separate explicit approval is present, uses the same command with
`--execute-live --approval-reference <ref>`. That path may load
`PERSONALOS_PHASE14C_TODOIST_TOKEN` and create exactly one Inbox/default task
with title `[Phase 14-C Test] Clean Kitchen Countertops and Stovetop`. It does
not set `project_id`, so the task is created in Inbox/default. It sends
`due_date` in `YYYY-MM-DD` form, matching Todoist API v1 `POST /api/v1/tasks`
request fields. It does not set recurrence, subtasks, labels, comments,
attachments, edits, deletes, skip/push/bump behavior, or automatic
rescheduling.

If the Todoist create request is attempted but the client cannot validate the
response, the report uses
`mutation_state=unconfirmed_after_task_create_attempt` and does not assert
`external_mutation=false` or `todoist_task_created=false`.

Gmail SMTP self-send smoke gate:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c gmail-smtp-smoke --json
```

That default command is report-only. It reads environment key names only,
checks the one-email smoke shape, masks sender/recipient addresses, and does
not read the Gmail app password, initialize SMTP, send Gmail, open a database,
write files, activate a scheduler, or touch protected paths. Without
`--execute-live`, it reports `gmail_not_run_missing_execute_live_flag`.

A future supervised live Gmail SMTP smoke, after credentials are configured
and a separate explicit approval is present, uses the same command with
`--execute-live --approval-reference <ref>`. That path may load
`PERSONALOS_PHASE14C_GMAIL_SMTP_ADDRESS`,
`PERSONALOS_PHASE14C_GMAIL_APP_PASSWORD`, and
`PHASE14C_GMAIL_CONTROLLED_RECIPIENT`, then send exactly one clearly marked
test email with subject `[Phase 14-C Test] Clean Kitchen Countertops and
Stovetop`. It does not create CC, BCC, attachments, forwarding,
existing-thread replies, local DB writes, scheduler/background behavior,
protected-path access, or broad Gmail automation. If the SMTP send is attempted
but the client cannot confirm the result, the report uses
`mutation_state=unconfirmed_after_send_attempt` and does not assert
`external_mutation=false` or `gmail_email_sent=false`.

OpenRouter model smoke gate:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c openrouter-model-smoke --json
```

That default command is report-only. It reads environment key names only and
does not read the OpenRouter API key, initialize a live client, call a model
provider, execute tools, invoke OpenClaw, open a database, write files,
activate a scheduler, or touch protected paths.
When config names are present but `--execute-live` is omitted, it reports
`openclaw_model_smoke_not_run_missing_execute_live_flag`.

A future supervised live model smoke, after credentials are configured and a
separate explicit approval is present, uses the same command with
`--execute-live --approval-reference <ref>`. That path may load
`PERSONALOS_OPENCLAW_MODEL_API_KEY` and configured model IDs, call Nemotron
Super at most once, and call GLM 5.2 at most once only if the primary response
fails validation. It does not log credential values, full prompts, raw
provider responses, or configured model IDs.

Live-smoke follow-up diagnostics:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c live-smoke-diagnostics --json
```

That command is report-only. It does not read environment variables, load
credentials, initialize live clients, create Todoist tasks, send Gmail, write
Calendar, call OpenRouter, invoke OpenClaw, open a database, or write files.
It reports the manual Todoist outcome check required before any Todoist retry
and records that future approved OpenRouter failures can include safe
`error_kind` and `http_status` diagnostics without raw provider responses,
full prompts, configured model IDs, or credential values.

Connected rehearsal plan:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c connected-rehearsal-plan --json
```

That command is report-only. It does not read environment variables, load
credentials, initialize live clients, create Todoist tasks, send Gmail, write
Calendar, call OpenRouter, invoke OpenClaw, open a database, or write files.
It defines the next larger supervised rehearsal after connectivity
confirmation: one OpenRouter brief, one Todoist Inbox/default task, and one
Gmail controlled self-send, with no Calendar duplicate and no protected
OpenClaw runtime invocation. The plan requires a new explicit approval
reference before any future live run.

Connected rehearsal executable gate:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c connected-rehearsal --json
```

The default command is report-only and reads environment key names only. The
live form requires `--execute-live`, the exact approval reference
`phase14c-2026-07-01-connected-rehearsal`, and the configured Gmail, Todoist,
and OpenRouter values before it reads credential values. The live form may make
at most one OpenRouter primary call, one fallback call only if primary
validation fails, one Todoist Inbox/default task create, and one controlled
Gmail self-send. It does not write Calendar, invoke protected OpenClaw runtime,
open a database, write files, activate a scheduler, or touch protected paths.
It passed Claude Code audit before the approved live run. Do not rerun it
without a new explicit approval and a new call/write budget.

The connected rehearsal live form has now been run once under approval
reference `phase14c-2026-07-01-connected-rehearsal` with
`SSL_CERT_FILE=/opt/homebrew/etc/ca-certificates/cert.pem`. It returned
`phase14c_connected_rehearsal_model_validation_failed` after one Nemotron Super
primary call and one GLM 5.2 fallback call. The sequence stopped before
Todoist and Gmail: `todoist_task_create_calls=0`,
`gmail_email_send_calls=0`, `calendar_event_create_calls=0`,
`protected_openclaw_runtime_invocation_calls=0`, and
`external_mutation=false`. Do not rerun that connected live command without a
new explicit approval and a new call/write budget.

Wide-net rehearsal plan:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c wide-net-rehearsal-plan --json
```

That command is repo-local/report-only. It does not read environment
variables, load credentials, initialize live clients, call OpenRouter, create
Todoist tasks, send Gmail, write Calendar, invoke OpenClaw, open a database,
or write files. It defines the next wider supervised test plan with one
OpenRouter diagnostic model probe, one Todoist Inbox/default marker task, one
Gmail controlled self-email, and one self-only Google Calendar marker event
after a duplicate-marker precheck. The OpenRouter step is diagnostic-only and
model-generated text must not be used as task/email/event content. The plan
requires a new explicit approval reference and Claude Code audit before any
future live run; it has no executable live runner in this packet.

Connectivity setup:

```bash
scripts/phase14c_connectivity_setup.sh
set -a; source .env.local; set +a; PYTHONPATH=src python3 -m personalos.cli phase14c connectivity-setup --json
```

The setup script prompts locally for Gmail SMTP address, Gmail app password,
controlled Gmail recipient, Todoist token, Google Calendar credential label,
OpenClaw local/test/sandbox mode, OpenRouter provider, OpenRouter API key, and
model IDs. It refuses to overwrite an existing `.env.local`, writes through a
temporary file before moving the completed file to `.env.local`, and keeps app
password/token/API-key prompts hidden. `.env.local` is gitignored. The
`connectivity-setup` command reads environment key names only and reports
missing names for Gmail, Todoist, and OpenRouter. It does not read credential
values, initialize live clients, send Gmail, create Todoist tasks, call
OpenRouter, invoke OpenClaw, or perform external writes.

Dry-run rehearsal:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c supervised-smoke-dry-run --output-dir <safe_temp_output_dir> --json
```

That CLI command runs a fake-client dry-run rehearsal only. It validates the
default one-object-per-rail request, calls deterministic repo-local fake
clients, and writes a redacted evidence bundle only under the explicit safe
temp output directory. It does not load credentials, open a database,
initialize live clients, create Todoist tasks, create Calendar events, create
or send Gmail, invoke OpenClaw, or perform external writes.

Dry-run rehearsal artifacts:

- `request.json`
- `validation.json`
- `fake_client_results.json`
- `completion_report.json`
- `summary.md`

The `request.json` artifact is sanitized. It records marker presence, counts,
booleans, allowed modes, and boundary status rather than raw invalid request
values. Rehearsal artifacts must report `live_run_executed=false`,
`external_mutation=false`, credential values not read or logged, no production
DB, no scheduler activation, no protected paths touched, and writes only to
the explicit output directory.

Executor reports from `execute_phase14c_supervised_smoke_request` also use a
redacted validation summary. Dry-run, blocked, and live-completed executor
reports must not include a raw `normalized_request` payload or raw controlled
test recipient. Direct in-memory validation may still retain normalized data
for guardrail and injected-client execution logic.

Calendar smoke result:

- One supervised Google Calendar external write has already passed.
- Event ID: `memu6fhql6stl71auv05e1a6d0`
- Title: `[Phase 14-C Test] Clean Kitchen Countertops and Stovetop`
- Time: Monday, 2026-07-06, 09:00-09:15 America/Chicago.
- Readback confirmed one matching event, no attendees, no recurrence, no
  attachments, no conference link, and default reminders disabled.
- This does not change `readiness.status`, does not activate broad live rails,
  and does not authorize another Calendar event unless a separate repair need
  is identified.

Remaining-rail live smoke result:

- First approval reference:
  `phase14c-2026-06-30-connectivity-live-smoke`.
- Gmail SMTP self-send passed with `gmail_self_send_smoke_passed`.
- Gmail sent exactly one controlled test email from masked sender
  `c***@gmail.com` to masked recipient `c***@gmail.com`, subject
  `[Phase 14-C Test] Clean Kitchen Countertops and Stovetop`.
- Gmail used no CC, BCC, attachments, forwarding, or existing-thread reply.
- Todoist Inbox/default made exactly one create attempt for
  `[Phase 14-C Test] Clean Kitchen Countertops and Stovetop`, due
  2026-07-06.
- Todoist returned `todoist_inbox_default_task_smoke_failed` with
  `mutation_state=unconfirmed_after_task_create_attempt`, so the repo does not
  assert whether the task exists.
- OpenRouter model smoke called Nemotron Super once, then GLM 5.2 once after
  primary validation failed.
- OpenRouter returned `openclaw_model_smoke_validation_failed`; both attempts
  reported sanitized `transport_or_parse_error` metadata only. Do not rerun the
  OpenRouter smoke for this evidence packet because the approved
  primary/fallback call budget is exhausted.
- Manual Todoist outcome check after the first remaining-rail run returned
  `not_found`.
- CA-bundle retry approval reference:
  `phase14c-2026-06-30-connectivity-ca-retry`.
- CA-bundle retry used
  `SSL_CERT_FILE=/opt/homebrew/etc/ca-certificates/cert.pem` after diagnostics
  showed local Python TLS trust was missing the Homebrew CA bundle.
- Todoist CA-bundle retry returned
  `todoist_inbox_default_task_smoke_passed`, created exactly one Inbox/default
  task with the same title and due date, and reported
  `mutation_state=confirmed_task_created`.
- Do not rerun Todoist without a new explicit duplicate-risk approval.
- OpenRouter CA-bundle retry returned `openclaw_model_smoke_passed` after one
  Nemotron Super primary call; `fallback_calls=0`, so GLM 5.2 was not called
  in the successful retry.
- No credential values, raw provider responses, full prompts, environment
  dumps, database writes, scheduler/background activation, production DB
  activation, protected-path access, broad OpenClaw handoff, or protected
  OpenClaw runtime invocation occurred.

Connected rehearsal live result:

- Approval reference:
  `phase14c-2026-07-01-connected-rehearsal`.
- Result: `phase14c_connected_rehearsal_model_validation_failed`.
- OpenRouter primary call: `nemotron_super`, `primary_calls=1`,
  `success=true`, `input_tokens=79`, `output_tokens=160`,
  `validation_passed=false`.
- OpenRouter fallback call: `glm_5_2`, `fallback_calls=1`,
  `failure_category=http_error`, `error_kind=HTTPError`, `http_status=402`.
- The model brief text, raw provider response, full prompt, configured model
  IDs, and credential values were not logged or recorded.
- Todoist task creates: `todoist_task_create_calls=0`.
- Gmail sends: `gmail_email_send_calls=0`.
- Calendar event creates: `calendar_event_create_calls=0`.
- Protected OpenClaw runtime invocations:
  `protected_openclaw_runtime_invocation_calls=0`.
- Mutation state: `not_attempted`; `external_mutation=false`.
- Do not rerun the connected live command without a new explicit approval.

## Test Marker

Every object or invocation must include this marker:

```text
[Phase 14-C Test] Clean Kitchen Countertops and Stovetop
```

Objects missing that marker fail the smoke request guardrail validation.

## Rails

The supervised smoke test may include these rails after Chris explicitly
initiates the live-test step:

| Rail | Allowed smoke operation | Maximum |
| --- | --- | --- |
| Todoist | Create one clearly marked test task | 1 task |
| Google Calendar | Create one clearly marked self test event | 1 event |
| Gmail | Create or send one clearly marked test email to a controlled/self recipient | 1 email |
| OpenClaw | Run one local/test/sandbox smoke invocation | 1 invocation |

These rails are not categorically blocked for this supervised smoke plan. They
are allowed only inside this bounded manually supervised test envelope.

Gmail self-send readiness may use an injected client/profile method to discover
the authenticated sender identity safely, or it may use
`PHASE14C_GMAIL_CONTROLLED_RECIPIENT` when a controlled recipient is configured.
Reports must mask sender and recipient values and must not print tokens,
environment dumps, OAuth material, send-as settings, or credential values. If
the authenticated sender cannot be safely determined and no controlled
recipient is configured, the Gmail rail remains blocked with
`gmail_not_run_missing_sender_or_controlled_recipient`.

Todoist defaults to Inbox/default. The smoke request uses no recurrence,
subtasks, labels, comments, automatic edits, automatic deletion,
skip/push/bump behavior, or automatic rescheduling. If the original planned
due date is stale, the due date resolves to the next upcoming Monday. The
bounded live command omits `project_id` and sends `due_date` for the full-day
due date.

OpenClaw now has a repo-local local/test/sandbox compatibility harness:
`run_phase14c_openclaw_local_sandbox_smoke`. That harness is a no-op/status
smoke path for `phase14c_smoke_test`; it does not call protected OpenClaw
runtime, access protected paths, activate scheduler/background behavior,
activate production DB, perform external mutation, or broaden runtime handoff.
The 2026-06-29 connectivity sprint ran that harness once and recorded
`openclaw_local_harness_passed` with `mode=local_test_sandbox`.

OpenClaw model lane strategy is documented in
[OPENCLAW_MODEL_STRATEGY.md](OPENCLAW_MODEL_STRATEGY.md). The smoke lane uses
Nemotron Super primary with GLM 5.2 fallback. The reasoning lane uses GLM 5.2
primary with Nemotron Super fallback. Routing is explicit by lane/task type,
with no hidden model choice or provider auto-escalation.
Model-provider readiness reports use
`openclaw_model_smoke_not_run_missing_provider_config`,
`openclaw_model_smoke_not_run_missing_client`, or
`openclaw_model_smoke_passed`. A bounded live provider attempt can also return
`openclaw_model_smoke_validation_failed` after the allowed primary/fallback
budget is exhausted. Reports must not expose credential values, present config
names, full prompts, or raw provider responses.

## Dry-Run Boundary

Dry-run validation may:

- Build and validate the one-object-per-rail smoke request.
- Print a template-only one-object-per-rail request report.
- Validate one explicit safe JSON request file with a redacted stdout report.
- Check that required environment/config entry names are present.
- Report missing required environment/config entry names only.
- Produce a redacted live-readiness report for one explicit safe JSON request
  file without executing it.
- Produce a runbook or validation report.
- Use deterministic fake clients in the dry-run rehearsal.
- Write redacted dry-run rehearsal artifacts only under an explicit safe temp
  output directory.

Dry-run validation must not:

- Create a real Todoist task.
- Create a real Calendar event.
- Create or send a real Gmail email.
- Invoke OpenClaw against real/protected/runtime targets.
- Read, print, copy, log, commit, or summarize credential/token values.
- Activate scheduler/background behavior.
- Activate production DB.
- Touch protected paths.
- Perform external writes.
- Write inside the repository, protected paths, credential-looking paths,
  scheduler-looking paths, production-looking paths, or non-temp output paths.
- Read request input files from protected, credential-looking,
  production-looking, or unsafe paths.
- Treat a request template as live authorization.

## Live-Run Boundary

A future live run must be manually invoked and foreground-only. The source
executor requires:

- `mode=live_run`.
- `live_run_requested=true`.
- A current approval reference.
- `live_run_approved=true` passed by the caller.
- All required config entry names present.
- Explicit injected clients for Todoist, Google Calendar, Gmail, and OpenClaw.
- A request that passes all guardrail validation.

The executor has no built-in Todoist, Google Calendar, Gmail, or OpenClaw SDK
client. Live clients must be supplied explicitly by the future supervised
operator path. This prevents repo prep from accidentally becoming live
operation.

## Guardrails

The validator enforces:

- Max one Todoist task.
- Max one Calendar event.
- Max one Gmail email.
- Max one OpenClaw invocation.
- Required test marker.
- No Calendar attendees/invites except the self test identity if an API
  requires a self attendee.
- No Calendar recurrence.
- No Gmail to uncontrolled recipients.
- No Gmail CC or BCC.
- No Gmail attachments.
- No Gmail forwarding.
- No Gmail reply to an existing real thread.
- No scheduler/background loop.
- No production DB.
- No dynamic cleaning.
- No bulk writes.
- No protected path access.
- No broad OpenClaw runtime handoff.
- OpenClaw mode must be local/test/sandbox.
- OpenClaw scope must remain one supervised smoke invocation.
- OpenClaw invocation name must be `phase14c_smoke_test`.
- OpenClaw production operation, scheduler/background behavior, and external
  mutation must remain false.

Guardrail failures block the request before any client can be called.

## Credential Preflight

The preflight checks names only:

- `PERSONALOS_PHASE14C_GMAIL_SMTP_ADDRESS`
- `PERSONALOS_PHASE14C_GMAIL_APP_PASSWORD`
- `PHASE14C_GMAIL_CONTROLLED_RECIPIENT`
- `PERSONALOS_PHASE14C_TODOIST_TOKEN`
- `PERSONALOS_PHASE14C_GOOGLE_CALENDAR_CREDENTIAL`
- `PERSONALOS_PHASE14C_GMAIL_CREDENTIAL`
- `PERSONALOS_PHASE14C_OPENCLAW_TEST_MODE`

Model-provider readiness checks these additional names for a future injected
OpenClaw model smoke client:

- `PERSONALOS_OPENCLAW_MODEL_PROVIDER`
- `PERSONALOS_OPENCLAW_MODEL_API_KEY`
- `PERSONALOS_OPENCLAW_NEMOTRON_SUPER_MODEL`
- `PERSONALOS_OPENCLAW_GLM_5_2_MODEL`

Reports may include missing names. Reports must not include credential values,
token contents, OAuth material, summaries of auth material, or present
non-required environment names.

## Non-Goals

This runbook and repo prep do not by themselves:

- Run broad live activation.
- Create another Calendar event unless a separate repair need is identified.
- Create or retry a real Todoist task outside a separately approved bounded
  live smoke command.
- Create or send a real Gmail email outside a separately approved bounded live
  smoke command.
- Invoke OpenClaw against real/protected/runtime targets.
- Print, inspect, copy, commit, or expose credentials/tokens.
- Send Gmail to uncontrolled recipients.
- Invite external Calendar attendees.
- Create recurring events or tasks.
- Perform bulk writes.
- Activate scheduler/background behavior.
- Activate production DB.
- Implement dynamic cleaning.
- Change `readiness.status` to ready.
- Add `.agent/`.
- Add `CLAUDE.md`.
- Add broad runtime/operator scaffolding.

## Validation Coverage

`tests/test_phase14c_supervised_smoke.py` verifies:

- The runbook records all four supervised smoke rails and repo-prep safety
  assertions, and records the passed supervised Calendar smoke event separately
  from broad live activation.
- The default dry-run request validates without credentials and does not call
  clients.
- Gmail self-send readiness resolves an injected authenticated sender identity
  or configured controlled recipient while masking raw values in reports.
- Todoist defaults to Inbox/default, resolves stale due dates to the next
  upcoming Monday, and blocks recurrence, subtasks, labels, comments,
  automatic edits/deletion, skip/push/bump behavior, and automatic
  rescheduling.
- The repo-local OpenClaw local/test/sandbox smoke harness returns safe
  metadata only and does not call OpenClaw runtime or mutate external state.
- The OpenClaw model readiness CLI reports missing provider config names only,
  does not report present config names, and does not call a provider or
  initialize a model client.
- The request-template report emits a one-object-per-rail template and records
  `template_only_not_authorization=true` and `ready_for_live_execution=false`.
- The dry-run rehearsal writes `request.json`, `validation.json`,
  `fake_client_results.json`, `completion_report.json`, and `summary.md` only
  under an explicit safe temp output directory.
- Dry-run rehearsal artifacts are redacted and do not echo unsafe blocked
  request values.
- Executor dry-run, blocked, and live-completed reports do not include raw
  `normalized_request` payloads or raw controlled test recipients.
- The request-validation CLI reads one safe JSON file, prints only a redacted
  validation report, blocks invalid requests without echoing unsafe values, and
  rejects credential-looking input paths.
- The credential-preflight CLI reads environment key names only, reports missing
  required names, omits present names and values, and performs no writes or live
  initialization.
- The live-readiness CLI composes request validation and credential-name
  preflight, omits raw recipients, approval references, present config names,
  and credential values, and always reports no live execution in that CLI.
- The live-readiness CLI rejects credential-looking input paths before reading
  JSON, matching the request-validation input-path guard.
- Dry-run rehearsal fake clients report no network calls, no credential reads,
  and no external mutation.
- Dry-run rehearsal output directories must be fresh, temp-only, and outside
  the repository.
- Credential preflight reports missing names only and does not echo secret
  values.
- Live-run validation requires explicit request approval, approval reference,
  and config entry names.
- Live execution requires the caller's `live_run_approved=true`.
- Missing injected clients block before any rail client is called.
- A valid live-run payload invokes each injected test client exactly once.
- Every max-one guardrail blocks extra Todoist, Calendar, Gmail, and OpenClaw
  objects.
- Every rail requires the test marker.
- Calendar attendees and recurrence are blocked outside the self-only rule.
- Gmail uncontrolled recipients, CC, BCC, attachments, existing-thread replies,
  and forwarding are blocked.
- Scheduler/background, production DB, dynamic cleaning, bulk-write,
  protected-path, and broad OpenClaw boundary flags are blocked.
- OpenClaw production mode, broad scope, broad handoff, production operation,
  scheduler/background behavior, external mutation, and protected paths are
  blocked.
- Blocked validation output does not echo caller-controlled unsafe values.

## Stop Conditions

Stop before execution if:

- Credentials would need to be printed, inspected, copied, committed, or
  summarized.
- More than one Todoist task, Calendar event, Gmail email, or OpenClaw
  invocation could occur.
- Gmail would go to uncontrolled recipients.
- Calendar would invite uncontrolled attendees.
- Recurrence appears.
- Scheduler/background behavior appears.
- Production DB appears.
- Dynamic cleaning appears.
- OpenClaw scope expands beyond one local/test/sandbox smoke invocation.
- Validation fails in a way requiring product, safety, workflow, or
  architecture judgment.
- Wording implies broad live authorization rather than this bounded supervised
  smoke test.

## Current Status

Repo prep keeps:

- `readiness.status=not_ready`
- `inert_report_only=true`
- `live_rails_activated=false`

That status means the repo has prepared a guarded supervised smoke-test path
plus request-template, redacted request-validation, credential-preflight,
live-readiness, fake-client dry-run rehearsal, Gmail self-send readiness,
Todoist Inbox/default readiness, and a repo-local OpenClaw local/test/sandbox
smoke harness. It also includes explicit Todoist Inbox/default and OpenRouter
model smoke gate commands whose default mode is no-execution/report-only and
whose live modes require separate explicit approval, plus a no-live
`phase14c live-smoke-diagnostics` command for the Todoist/OpenRouter
follow-up. It also records that one
supervised Calendar smoke event passed; one controlled Gmail SMTP self-send
passed; one first-run Todoist Inbox/default create attempt was unconfirmed
after the request; one first-run OpenRouter primary/fallback model smoke failed
validation with sanitized transport/parse metadata; one separately approved
CA-bundle Todoist retry created the bounded Inbox/default task; and one
separately approved CA-bundle OpenRouter retry passed on the Nemotron Super
primary call without a GLM 5.2 fallback. The next repo-local plan is
[PHASE_14C_CONNECTED_REHEARSAL.md](PHASE_14C_CONNECTED_REHEARSAL.md), which
defines a model-to-task-to-email rehearsal without authorizing live execution.
Broad live activation remains false and readiness remains not ready.
