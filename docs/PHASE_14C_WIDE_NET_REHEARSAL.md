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
create step without calling the connector. The repo also has no-live Calendar
transcript template and validator commands so a future app-connector precheck
or create transcript can be checked as sanitized JSON without echoing raw event
details or attendee addresses. The repo also has a no-live execution-handoff
command, fillable evidence-template command, and redacted evidence validator so
the next operator can inspect the bounded command, Calendar connector handoff
contract, call budgets, post-run evidence shape, and post-run evidence
requirements without reading credentials or calling live services. It also has
a post-run crosscheck command to verify that sanitized Calendar transcript
evidence and sanitized wide-net evidence agree without echoing raw inputs, plus
a synthetic evidence rehearsal command that exercises the full validator chain
without returning raw fixture payloads or producing live evidence.

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

Calendar connector transcript template and validator:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c wide-net-calendar-transcript-template --json
PYTHONPATH=src python3 -m personalos.cli phase14c wide-net-calendar-transcript-validate --input-file <sanitized-calendar-transcript.json> --json
```

These commands are repo-local/report-only. They do not read `.env.local`, read
environment variables, load credentials, initialize live clients, call the
Google Calendar app connector, create events, call OpenRouter, create Todoist
tasks, send Gmail, invoke OpenClaw, open a database, write files, or touch
protected paths. The template reports the sanitized transcript shape for the
future Calendar duplicate precheck and create handoff. The validator reads one
explicit sanitized JSON file, rejects oversized files before JSON parsing, and
prints only redacted pass/block reason codes. It accepts a precheck-clear
transcript only when the connector action and args match the approved
`search_events` payload, the normalized response carries the explicit
`matching_event_count` contract, the count is zero, and no event details or
attendee addresses were logged. It accepts a post-create transcript only after
that clear precheck and only with the approved `create_event` payload and
sanitized result keys.

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

Evidence template:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c wide-net-evidence-template --json
```

The evidence-template command is repo-local/report-only. It does not read
`.env.local`, read environment variables, load credentials, initialize live
clients, call the Google Calendar app connector, call OpenRouter, create
Todoist tasks, send Gmail, write Calendar, invoke OpenClaw, open a database,
write files, or touch protected paths. It reports a fillable sanitized
wide-net evidence shape, the accepted complete statuses, call budgets, Calendar
transcript validator command, and post-run evidence validator command. The
template payload is not evidence and is expected to fail the evidence validator
until a separately approved live run fills the observed counts, booleans, and
status. It must not be used to record live results without validated sanitized
evidence.

Evidence validator:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c wide-net-evidence-validate --input-file <sanitized-wide-net-report.json> --json
PYTHONPATH=src python3 -m personalos.cli phase14c wide-net-evidence-crosscheck --calendar-transcript-file <sanitized-calendar-transcript.json> --evidence-file <sanitized-wide-net-report.json> --json
PYTHONPATH=src python3 -m personalos.cli phase14c wide-net-evidence-rehearsal --json
```

The evidence validator reads one explicit sanitized JSON file and prints a
redacted pass/block report. It does not read credentials, inspect `.env.local`,
call connectors, initialize live clients, open a DB, or print raw evidence. It
does not echo raw evidence. It rejects oversized local evidence files before
JSON parsing and uses shared bounded redaction checks with explicit depth and
node limits, returning reason codes instead of offending values. It accepts
only complete sanitized wide-net evidence within the one-call budgets, with a
Calendar duplicate precheck performed, `matching_event_count=0`, no event
details or attendee addresses logged, diagnostic-only model metadata, and no
protected OpenClaw runtime, scheduler/background, production DB, protected
path, dynamic-cleaning, broad-live-activation, credential-value,
raw-provider-response, full-prompt, configured-model-ID, or unmasked-email
exposure.

The evidence crosscheck reads one explicit sanitized Calendar transcript file
and one explicit sanitized wide-net evidence file. It runs the existing
transcript and evidence validators, then checks that both reports agree on the
marker, duplicate-precheck count, Calendar event create count, and no raw
event-details or attendee-address logging. It returns only reason codes,
counts, booleans, and summaries. It does not echo raw inputs, event IDs,
attendee addresses, credential values, raw provider responses, full prompts,
or unmasked emails.

The evidence rehearsal command constructs deterministic synthetic sanitized
inputs in memory, runs the Calendar transcript validator, wide-net evidence
validator, and evidence crosscheck, then returns only validation summaries. It
does not read credentials, call connectors, initialize live clients, write
files, or return raw fixture payloads. The rehearsal output is not live
evidence and must not be recorded as proof of a real wide-net run.

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
  `phase14c wide-net-calendar-transcript-template --json` plus
  `phase14c wide-net-calendar-transcript-validate --input-file <file> --json`
  validate sanitized Calendar connector transcripts without calling the
  connector or echoing raw event details. The
  `phase14c wide-net-evidence-template --json` command reports the fillable
  sanitized post-run evidence shape without calling services; that template is
  not accepted evidence until a separately approved run fills it with observed
  values. The
  `phase14c wide-net-evidence-validate --input-file <file> --json` validates
  sanitized evidence without echoing the raw payload. The
  `phase14c wide-net-evidence-crosscheck --calendar-transcript-file <file> --evidence-file <file> --json`
  command crosschecks sanitized Calendar transcript evidence against sanitized
  wide-net evidence without echoing raw inputs. The
  `phase14c wide-net-evidence-rehearsal --json` command exercises the same
  validator chain with synthetic sanitized inputs and returns summaries only,
  not live evidence. The validator rejects oversized files before JSON parsing
  and uses shared bounded redaction checks with explicit depth and node limits.
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
- The Calendar transcript template/validator commands may be inspected before
  a live run, but they are not authorization and do not call the Calendar
  connector. Sanitized transcripts must not contain raw event details,
  attendee addresses, credential values, or unmasked emails.
- The execution-handoff command may be inspected before a live run, but it is
  not authorization and does not wire the Calendar connector.
- The evidence-template command may be inspected before a live run, but it is
  not authorization and does not produce accepted evidence by itself.
- The evidence-rehearsal command may be run before a live run, but it uses
  synthetic sanitized inputs only and must not be recorded as live evidence.
- Post-run evidence must be validated from a sanitized JSON report with
  `phase14c wide-net-evidence-validate --input-file <file> --json`; the
  validator must not receive or print credential values, raw provider
  responses, full prompts, configured model IDs, event details, attendee
  addresses, or unmasked emails. Oversized, malformed, deeply nested, or
  scan-limit-exceeding evidence must fail closed without echoing raw input.
- Post-run Calendar evidence should be crosschecked with
  `phase14c wide-net-evidence-crosscheck --calendar-transcript-file <file> --evidence-file <file> --json`
  before evidence is recorded. The crosscheck is repo-local and does not call
  the Calendar connector.
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
