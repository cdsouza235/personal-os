# Phase 14-C Connected Rehearsal Plan

Date: 2026-07-01

This document defines the next larger supervised Phase 14-C test now that
Gmail, Todoist, and OpenRouter connectivity are confirmed. It is a plan only;
it does not authorize or run live rails.

CLI report:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c connected-rehearsal-plan --json
```

The command is repo-local/report-only. It does not read `.env.local`, read
environment variables, load credentials, initialize live clients, call
OpenRouter, create Todoist tasks, send Gmail, write Calendar, invoke OpenClaw,
open a database, write files, or touch protected paths.

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
- Due date: 2026-07-06.
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
- Do not log the full prompt, raw provider response, configured model IDs, or
  credential values.

## Stop Conditions

Stop before or during any future live run if:

- Any rail would exceed its stated call/write budget.
- A Todoist task already exists with the connected rehearsal marker.
- Gmail recipient is not the configured controlled recipient or self.
- OpenRouter prompt would include secrets, protected paths, or personal data.
- Calendar creation appears.
- Protected OpenClaw runtime invocation appears.
- Scheduler/background, production DB, dynamic cleaning, or protected paths
  appear.
- Credential values would be printed, logged, copied, committed, or
  summarized.

## Suggested Approval Text

```text
Approved: run exactly one Phase 14-C connected rehearsal using approval reference phase14c-2026-07-01-connected-rehearsal with SSL_CERT_FILE=/opt/homebrew/etc/ca-certificates/cert.pem. Allowed live actions: one OpenRouter model call with one fallback only if primary validation fails, one Todoist Inbox/default task, and one Gmail controlled self-send. Do not run Calendar or protected OpenClaw runtime.
```

This approval text is a future human gate, not authorization embedded in this
document or the CLI report.

## Safety Assertions

- `readiness.status` remains `not_ready`.
- `inert_report_only` remains `true`.
- `live_rails_activated` remains `false`.
- This plan does not read credential values.
- This plan does not initialize live clients.
- This plan does not perform external mutation.
- This plan does not authorize Calendar duplicates.
- This plan does not invoke protected OpenClaw runtime.
