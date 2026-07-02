# Phase 14-C Wide-Net Rehearsal Plan

Date: 2026-07-01

This document defines the next wider supervised Phase 14-C live-test packet.
It does not authorize or run live rails. The repo now has a default no-live
executable gate, but that gate fails closed before credential values are read
unless a future audited Calendar client/connector bridge is available. The
injected runner now enforces a Calendar duplicate-marker precheck before any
model, Todoist, Gmail, or Calendar create step can run. The repo also has a
Calendar bridge scaffold that normalizes connector search responses into an
explicit precheck contract; unrecognized precheck response shapes fail closed.
The repo-local Calendar app-bridge payload command now prints the exact Google
Calendar app connector arguments for the duplicate precheck and self-only
create step without calling the connector. The repo also has a no-live
execution-handoff command and a redacted evidence validator so the next
operator can inspect the bounded command, Calendar connector handoff contract,
call budgets, and post-run evidence requirements without reading credentials
or calling live services.

CLI report:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c wide-net-rehearsal-plan --json
```

The plan command is repo-local/report-only. It does not read `.env.local`, read
environment variables, load credentials, initialize live clients, call
OpenRouter, create Todoist tasks, send Gmail, write Calendar, invoke OpenClaw,
open a database, write files, or touch protected paths.

Executable gate:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c wide-net-rehearsal --json
```

The default gate is also repo-local/report-only. It reads environment key names
only and does not read credential values, initialize live clients, call
OpenRouter, create Todoist tasks, send Gmail, write Calendar, invoke OpenClaw,
open a database, write files, or touch protected paths.

The live form requires `--execute-live` and the exact approval reference
`phase14c-2026-07-01-wide-net-live-test`. Once required config names are
present, the current CLI still returns
`phase14c_wide_net_rehearsal_not_run_missing_calendar_connector_or_client`
before reading credential values. The runner protocol now requires a
duplicate-marker lookup before `create_event`, but a separate audited Calendar
bridge is still required before the CLI can run the future wide-net live
sequence. The scaffolded bridge does not import or initialize a live connector
by itself.

Calendar app-bridge payloads:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c wide-net-calendar-bridge-payloads --json
```

The bridge-payload command is repo-local/report-only. It does not read
`.env.local`, read environment variables, load credentials, initialize live
clients, create events, call
OpenRouter, create Todoist tasks, send Gmail, invoke OpenClaw, open a
database, write files, or touch protected paths. It does not call the Google
Calendar app connector. It reports the Google Calendar app connector payloads
for `search_events` and `create_event`, plus the normalized precheck response
contract required by the runner. It is not live authorization and does not
inject a Calendar client into the wide-net runner.

Execution handoff:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c wide-net-execution-handoff --json
```

The execution-handoff command is repo-local/report-only. It does not read
`.env.local`, read environment variables, load credentials, initialize live
clients, call the Google Calendar app connector, call OpenRouter, create
Todoist tasks, send Gmail, write Calendar, invoke OpenClaw, open a database,
write files, or touch protected paths. It reports the future bounded live
command template, required approval reference, Calendar connector handoff
payloads, normalized precheck contract, call budgets, stop boundaries, and
post-run evidence validator command. It is not live authorization and does not
wire or inject a Calendar client into the wide-net runner.

Evidence validator:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c wide-net-evidence-validate --input-file <sanitized-wide-net-report.json> --json
```

The evidence validator reads one explicit sanitized JSON file and prints a
redacted pass/block report. It does not read credentials, inspect `.env.local`,
call connectors, initialize live clients, open a DB, or print raw evidence. It
does not echo raw evidence. It accepts only complete sanitized wide-net
evidence within the one-call budgets, with a Calendar duplicate precheck
performed, `matching_event_count=0`, no event details or attendee addresses
logged, diagnostic-only model metadata, and no protected OpenClaw runtime,
scheduler/background, production DB, protected path, dynamic-cleaning,
broad-live-activation, credential-value, raw-provider-response, full-prompt,
configured-model-ID, or unmasked-email exposure.

## Confirmed Foundation

- Gmail SMTP self-send has passed once with one controlled self-send and
  masked sender/recipient only.
- Todoist Inbox/default has passed once after the CA-bundle retry, creating
  exactly one bounded test task after manual `not_found` reconciliation.
- OpenRouter has passed once after the CA-bundle retry, with Nemotron Super
  primary validation passing and `fallback_calls=0`.
- The first connected rehearsal then used one Nemotron Super primary call and
  one GLM 5.2 fallback call before stopping at model validation; no Todoist
  task, Gmail email, Calendar event, or protected OpenClaw runtime invocation
  happened in that run.
- Google Calendar has one existing bounded smoke event. This wide-net plan
  uses a new marker, and the executable runner now requires a duplicate-marker
  precheck before any future Calendar create. The Calendar bridge scaffold
  requires a normalized `matching_event_count` contract before the runner can
  proceed; malformed or unrecognized precheck responses stop the sequence. The
  `phase14c wide-net-calendar-bridge-payloads --json` command reports the
  Google Calendar app connector payloads for the future audited bridge without
  calling the connector. The `phase14c wide-net-execution-handoff --json`
  command reports the bounded future command and evidence checks without
  wiring the connector, and
  `phase14c wide-net-evidence-validate --input-file <file> --json` validates
  sanitized evidence without echoing the raw payload.
- Protected OpenClaw runtime remains uninvoked and is not part of this
  rehearsal.

## Rehearsal Objective

The next useful test is to widen the net without depending on model-generated
content for downstream writes:

1. Read the primary/self Calendar for the exact marker in the target event
   window; stop before every write if a duplicate marker exists.
2. Run one OpenRouter diagnostic model probe.
3. Create one Todoist Inbox/default marker task.
4. Send one Gmail controlled self-email with the same marker.
5. Create one self-only Google Calendar marker event after the duplicate-marker
   precheck passes.

The OpenRouter probe is diagnostic-only. If the model validation fails again,
the report should record the safe metadata and continue only if the separately
audited live runner or operator packet explicitly allows the fixed-marker
Todoist/Gmail/Calendar steps. Model text must not be used as task/email/event
content.

This is not dynamic cleaning, broad live activation, production DB activation,
scheduler adoption, protected OpenClaw runtime handoff, or a background
operator loop.

## Proposed Live Envelope

Approval reference to request:

```text
phase14c-2026-07-01-wide-net-live-test
```

Required marker:

```text
[Phase 14-C Wide Test] Evening Reset Coordination
```

Required CA bundle:

```bash
SSL_CERT_FILE=/opt/homebrew/etc/ca-certificates/cert.pem
```

Call/write budgets:

- OpenRouter primary calls: 1.
- OpenRouter fallback calls: at most 1, only if primary validation fails.
- Todoist task creates: 1.
- Gmail emails sent: 1.
- Calendar duplicate precheck reads: 1 before model, Todoist, Gmail, or
  Calendar create.
- Calendar event creates: 1.
- Protected OpenClaw runtime invocations: 0.
- OpenClaw local/test/sandbox harness invocations: 0.
- Scheduler/background jobs: 0.
- Production DB writes: 0.

Todoist target:

- Project: Inbox/default.
- Title: `[Phase 14-C Wide Test] Evening Reset Coordination`.
- Due date: next upcoming Monday at runtime.
- No recurrence, subtasks, labels, comments, attachments, automatic edits,
  deletes, rescheduling, or skip/push/bump behavior.

Gmail target:

- Recipient: configured controlled recipient or self only.
- Subject: `[Phase 14-C Wide Test] Evening Reset Coordination`.
- No CC, BCC, attachments, reply, forward, or bulk send.

Calendar target:

- Calendar: primary or authenticated self calendar only.
- Title: `[Phase 14-C Wide Test] Evening Reset Coordination`.
- Duration: 15 minutes.
- Duplicate precheck: required before model, Todoist, Gmail, or Calendar
  create.
- No attendees, recurrence, conference link, attachments, invite fanout, or
  duplicate of the prior Calendar smoke event.

OpenRouter target:

- Primary: Nemotron Super.
- Fallback: GLM 5.2 only if primary validation fails.
- Prompt: fixed, short, non-secret diagnostic prompt.
- No protected paths, credentials, or personal data in the prompt.
- Do not log the full prompt, model-generated text, raw provider response,
  configured model IDs, or credential values.
- If GLM returns another `http_status=402`, record the safe diagnostic metadata
  and do not retry.

## Preconditions

- A new explicit live approval is required.
- Claude Code read-only audit is required before any live run.
- `SSL_CERT_FILE=/opt/homebrew/etc/ca-certificates/cert.pem` is required.
- Gmail, Todoist, OpenRouter, and Google Calendar connector/client access must
  be configured.
- The Calendar app-bridge payload command may be inspected before a live run,
  but connector execution still requires a separate audited injection/wiring
  step.
- The execution-handoff command may be inspected before a live run, but it is
  not authorization and does not wire the Calendar connector.
- Post-run evidence must be validated from a sanitized JSON report with
  `phase14c wide-net-evidence-validate --input-file <file> --json`; the
  validator must not receive or print credential values, raw provider
  responses, full prompts, configured model IDs, event details, attendee
  addresses, or unmasked emails.
- Google Calendar must pass a duplicate-marker precheck before any create.
- The duplicate-marker precheck must stop before model, Todoist, Gmail, and
  Calendar create if the marker already exists.
- Unrecognized Calendar precheck response shapes must fail closed before model,
  Todoist, Gmail, or Calendar create.
- Config names may be checked, but credential values must not be printed,
  summarized, committed, or pasted into chat.
- This document and CLI report do not read environment variables or call the
  Google Calendar connector.

## Stop Conditions

Stop before or during any future live run if:

- Any rail would exceed its stated call/write budget.
- A Todoist task already exists with the wide-net marker.
- A Calendar event already exists with the wide-net marker.
- Gmail recipient is not the configured controlled recipient or self.
- Calendar would include attendees, recurrence, conference link, or
  attachments.
- OpenRouter prompt would include secrets, protected paths, or personal data.
- OpenRouter would need more than the one primary and one fallback diagnostic
  call, or would enter a spend/config retry loop.
- Protected OpenClaw runtime invocation appears.
- Scheduler/background, production DB, dynamic cleaning, or protected paths
  appear.
- Credential values would be printed, logged, copied, committed, or summarized.

## Suggested Approval Text

```text
Approved: run exactly one Phase 14-C wide-net live test using approval reference phase14c-2026-07-01-wide-net-live-test with SSL_CERT_FILE=/opt/homebrew/etc/ca-certificates/cert.pem. Allowed live actions: one OpenRouter diagnostic model call with one fallback only if primary validation fails, one Todoist Inbox/default task, one Gmail controlled self-send, and one self-only Google Calendar event using marker [Phase 14-C Wide Test] Evening Reset Coordination. Do not run protected OpenClaw runtime, scheduler/background, production DB, protected paths, dynamic cleaning, or broad runtime handoff.
```

This is a future human gate, not reusable authorization embedded in this
document or the CLI report.

## Safety Assertions

- `readiness.status` remains `not_ready`.
- `inert_report_only` remains `true`.
- `live_rails_activated` remains `false`.
- The plan command and default gate do not read credential values.
- The plan command and default gate do not initialize live clients.
- The plan command and default gate do not call OpenRouter.
- The plan command and default gate do not create Todoist tasks.
- The plan command and default gate do not send Gmail.
- The plan command and default gate do not write Calendar.
- The plan command and default gate do not invoke protected OpenClaw runtime.
- The current `--execute-live` path fails closed before credential values are
  read unless a future audited Calendar client/connector bridge is available.
- The injected runner enforces a Calendar duplicate-marker precheck before
  model, Todoist, Gmail, or Calendar create.
- The Calendar bridge scaffold requires a normalized precheck response
  contract and fails closed on unrecognized shapes.
- This packet does not authorize Calendar duplicates.
- This packet does not implement dynamic cleaning.
