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
- `build_phase14c_credential_preflight_report`
- `validate_phase14c_supervised_smoke_request`
- `execute_phase14c_supervised_smoke_request`

CLI discovery:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c supervised-smoke-runbook --json
```

That CLI command is a runbook/status surface only. It does not load
credentials, open a database, initialize live clients, create Todoist tasks,
create Calendar events, create or send Gmail, invoke OpenClaw, or perform
external writes. In short, it does not initialize live clients.

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

## Dry-Run Boundary

Dry-run validation may:

- Build and validate the one-object-per-rail smoke request.
- Check that required environment/config entry names are present.
- Report missing environment/config entry names.
- Produce a runbook or validation report.
- Use fake or injected test clients in unit tests.

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

Guardrail failures block the request before any client can be called.

## Credential Preflight

The preflight checks names only:

- `PERSONALOS_PHASE14C_TODOIST_TOKEN`
- `PERSONALOS_PHASE14C_GOOGLE_CALENDAR_CREDENTIAL`
- `PERSONALOS_PHASE14C_GMAIL_CREDENTIAL`
- `PERSONALOS_PHASE14C_OPENCLAW_TEST_MODE`

Reports may include missing names. Reports must not include credential values,
token contents, OAuth material, or summaries of auth material.

## Non-Goals

This packet does not:

- Run the actual live smoke test.
- Create a real Todoist task.
- Create a real Calendar event.
- Create or send a real Gmail email.
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
  assertions.
- The default dry-run request validates without credentials and does not call
  clients.
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
- Gmail uncontrolled recipients, attachments, existing-thread replies, and
  forwarding are blocked.
- Scheduler/background, production DB, dynamic cleaning, bulk-write,
  protected-path, and broad OpenClaw boundary flags are blocked.
- OpenClaw production mode, broad scope, broad handoff, and protected paths are
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
but has not run the live smoke test yet.
