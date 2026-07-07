# Phase 14-C Connected Rehearsal Plan

Date: 2026-07-01

This document defines the next larger supervised Phase 14-C test now that
Gmail, Todoist, and OpenRouter connectivity are confirmed. It started as a
plan only; the bounded live form has now been run once under the explicit
approval reference below and must not be rerun without a new explicit
approval.

CLI report:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c connected-rehearsal-plan --json
```

The plan command is repo-local/report-only. It does not read `.env.local`, read
environment variables, load credentials, initialize live clients, call
OpenRouter, create Todoist tasks, send Gmail, write Calendar, invoke OpenClaw,
open a database, write files, or touch protected paths.

Executable gate:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c connected-rehearsal --json
```

The default executable gate is also report-only. It reads environment key names
only and does not read credential values, initialize live clients, call
OpenRouter, create Todoist tasks, send Gmail, write Calendar, invoke OpenClaw,
open a database, write files, or touch protected paths.

The live form was a separate human/audit gate and has now been used once:

```bash
SSL_CERT_FILE=/opt/homebrew/etc/ca-certificates/cert.pem PYTHONPATH=src python3 -m personalos.cli phase14c connected-rehearsal --execute-live --approval-reference phase14c-2026-07-01-connected-rehearsal --json
```

The live form passed read-only Claude Code audit and Chris separately
confirmed the live run. Do not rerun it without a new explicit approval and a
new call/write budget.

## Confirmed Foundation

- Gmail SMTP self-send has passed once with one controlled self-send and
  masked sender/recipient only.
- Todoist Inbox/default has passed once after the CA-bundle retry, creating
  exactly one bounded test task.
- OpenRouter has passed once after the CA-bundle retry, with Nemotron Super
  primary validation passing and `fallback_calls=0`.
- Google Calendar has one existing bounded smoke event; duplicate Calendar
  creation is not authorized for this rehearsal.
- Protected OpenClaw runtime remains uninvoked and is not part of this
  rehearsal.
- The connected rehearsal live run used the full allowed OpenRouter model
  budget, stopped at model validation, and did not create the Todoist task or
  send Gmail.

## Rehearsal Objective

The next useful test is not another isolated connectivity probe. It should
exercise a small connected workflow:

1. Use OpenRouter to generate one OpenRouter brief from a short, non-secret
   test prompt.
2. Create one Todoist Inbox/default task from that marked brief.
3. Send one controlled Gmail self-email containing the same marked brief.

This tests model-to-task-to-email flow under supervision. It is not dynamic
cleaning, broad live activation, production DB activation, scheduler adoption,
or OpenClaw runtime handoff.

## Proposed Live Envelope

Approval reference to request:

```text
phase14c-2026-07-01-connected-rehearsal
```

Required marker:

```text
[Phase 14-C Connected Test] Kitchen Reset Briefing
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
- Calendar event creates: 0.
- Protected OpenClaw runtime invocations: 0.
- Scheduler/background jobs: 0.
- Production DB writes: 0.

Todoist target:

- Project: Inbox/default.
- Title: `[Phase 14-C Connected Test] Kitchen Reset Briefing`.
- Due date: 2026-07-06 while that date is current; the executable gate rolls
  a stale planned date forward to the next upcoming Monday.
- No recurrence, subtasks, labels, comments, attachments, automatic edits,
  deletes, rescheduling, or skip/push/bump behavior.

Gmail target:

- Recipient: configured controlled recipient or self only.
- Subject: `[Phase 14-C Connected Test] Kitchen Reset Briefing`.
- No CC, BCC, attachments, reply, forward, or bulk send.

OpenRouter target:

- Primary: Nemotron Super.
- Fallback: GLM 5.2 only if primary validation fails.
- Prompt: fixed, short, non-secret test prompt.
- No protected paths, credentials, or personal data in the prompt.
- Do not log the full prompt, model-generated brief text, raw provider
  response, configured model IDs, or credential values.
- If both model attempts fail validation, stop before Todoist and Gmail.

## Stop Conditions

Stop before or during any future live run if:

- Any rail would exceed its stated call/write budget.
- A Todoist task already exists with the connected rehearsal marker.
- Gmail recipient is not the configured controlled recipient or self.
- OpenRouter prompt would include secrets, protected paths, or personal data.
- OpenRouter returns a brief that appears to contain secrets, account
  identifiers, links, or protected paths.
- Calendar creation appears.
- Protected OpenClaw runtime invocation appears.
- Scheduler/background, production DB, dynamic cleaning, or protected paths
  appear.
- Credential values would be printed, logged, copied, committed, or
  summarized.

## Live Result

Approval reference used once:

```text
phase14c-2026-07-01-connected-rehearsal
```

Result:

- Status: `phase14c_connected_rehearsal_model_validation_failed`.
- OpenRouter primary call: `nemotron_super`, `primary_calls=1`,
  `success=true`, `input_tokens=79`, `output_tokens=160`,
  `validation_passed=false`.
- OpenRouter fallback call: `glm_5_2`, `fallback_calls=1`, only after primary
  validation failed; sanitized failure metadata was `failure_category=http_error`,
  `error_kind=HTTPError`, `http_status=402`.
- Selected model attempt: fallback; selected validation passed: false.
- Model brief summary: `brief_generated=false`, `brief_line_count=0`,
  `brief_char_count=0`, `brief_text_logged=false`,
  `raw_provider_response_logged=false`.
- Todoist task creates: `todoist_task_create_calls=0`;
  `todoist_task_created=false`.
- Gmail sends: `gmail_email_send_calls=0`; `gmail_email_sent=false`.
- Calendar event creates: `calendar_event_create_calls=0`.
- Protected OpenClaw runtime invocations:
  `protected_openclaw_runtime_invocation_calls=0`.
- Mutation state: `not_attempted`; `external_mutation=false`.
- Credential values were read for the explicitly approved bounded live run,
  but `credential_values_logged=false`, `credential_values_committed=false`,
  and no environment dump was printed or committed.

Do not rerun this connected rehearsal command without a new explicit approval.
The approved OpenRouter primary/fallback model budget for this connected
rehearsal evidence is exhausted. Because model validation failed, the bounded
sequence stopped before Todoist and Gmail.

## Historical Approval Text

```text
Approved: run exactly one Phase 14-C connected rehearsal using approval reference phase14c-2026-07-01-connected-rehearsal with SSL_CERT_FILE=/opt/homebrew/etc/ca-certificates/cert.pem. Allowed live actions: one OpenRouter model call with one fallback only if primary validation fails, one Todoist Inbox/default task, and one Gmail controlled self-send. Do not run Calendar or protected OpenClaw runtime.
```

This approval text was used once for the recorded live result above. It is not
reusable authorization embedded in this document or the CLI report.

## Safety Assertions

- `readiness.status` remains `not_ready`.
- `inert_report_only` remains `true`.
- `live_rails_activated` remains `false`.
- The plan command does not read credential values.
- The default executable gate does not initialize live clients.
- The one approved live run read credential values and initialized live
  clients only inside the explicit bounded approval.
- The one approved live run did not perform external mutation.
- This packet does not authorize Calendar duplicates.
- This packet does not invoke protected OpenClaw runtime.
