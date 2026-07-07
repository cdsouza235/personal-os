# PR #103 Audit — Wide-net Calendar duplicate precheck

- Branch: PR #103 head `88193c65fb56980bac797b22373e2e616e5c81de`
- Base: `origin/main` @ `a74d3d9` (after PR #102 merge)
- Reviewer: Claude Code `/code-review` (high effort, recall-biased)
- Scope: `git diff main...HEAD` (16 files, +523 / -50)

## Verdict

**Approve for merge.** Cleanly resolves the PR #102 deferred Calendar duplicate-precheck gap and
both parts of PR #102 finding 2 (http_status + calendar HTTPError close). One Low hardening finding
about the precheck parser's fail-open default, to be pinned down with the future Calendar bridge.

## Findings

### 1. (Low, harden with bridge PR) Precheck count parser fails open on unrecognized shapes
`phase14c_wide_net_rehearsal_live.py:601` — `_calendar_matching_event_count` returns `0` (→ proceed
to create) when the precheck response has none of the recognized keys (`matching_event_count`,
`found`, `events`, `items`) or when `events`/`items` aren't lists. For a guard whose purpose is
preventing duplicate calendar events, an unrecognized response should be treated conservatively.
Not active now (no Calendar bridge exists; fail-closed at the client-None gate). Harden with the
bridge PR: pin the response contract to an explicit `matching_event_count` (or `events` list), and
treat an unrecognized / absent-of-known-keys response as a precheck failure (fail-closed) rather
than proceeding. Blast radius if it ever slipped through: one duplicate self-only 15-min event.

## Verified OK

- **Precheck runs first and fails safe.** After the gates + credential read, the FIRST live action
  is `calendar_client.find_events_by_title(...)`. A match → `WIDE_NET_NOT_RUN_DUPLICATE_CALENDAR_MARKER`;
  a precheck exception → `WIDE_NET_CALENDAR_PRECHECK_FAILED`. Both: `external_mutation=false`, no
  writes, `model_provider_called=false` (precheck precedes the model). Stronger than the plan — it
  gates the whole sequence, not just the calendar create.
- **PR #102 finding 2 resolved.** `_safe_failure` now records `http_status` via
  `getattr(error, "code", ...)` for all rails; the calendar `create_event` HTTPError path now
  `error.close()`s the file-like response. (Gmail needs no urllib close — it's SMTP.)
- **Fail-closed still airtight.** CLI `calendar_client_available = False` unchanged; runner returns
  `WIDE_NET_NOT_RUN_MISSING_CALENDAR_CLIENT` before `credential_values_read = True`; the precheck is
  reachable only with an injected/bridge client, so CLI `--execute-live` still reads no credentials
  and makes no live call.
- **Plan ↔ runner consistency.** Plan resequenced to precheck-first (steps 1–5) with
  `calendar_duplicate_precheck_enforced_by_runner: True`; `call_limits` adds
  `max_calendar_duplicate_precheck_reads: 1`; CLI counts precheck reads as live activity in
  `no_live_rails_activated` / workflow_mode.
- **No leakage.** Precheck report emits only a count + time window + marker title
  (`event_details_logged: False`, `attendee_addresses_logged: False`); precheck payload sets
  `attendee_data_required: False`; no email/attendee addresses anywhere. Tree-wide sweep clean.
- **Bounded budgets & chain-stop preserved**, honest mutation states per step; correct exception
  ordering; import order unchanged; focused tests pass locally (33 OK); readiness unchanged
  (`not_ready` / `inert_report_only=true` / `live_rails_activated=false`).

## Note for the Calendar bridge PR (next step)

The bridge is what flips `calendar_client_available` to True and un-gates credential reads + live
calls. It must: (a) implement finding 1's response contract / fail-closed parsing, (b) get its own
pre-run audit + fresh explicit approval, (c) have OpenRouter topped up (prior 402 — affects only the
diagnostic-only model step here, not the rails).

## Test status (per PR)

- Focused wide-net/CLI/docs/model suite: 102 OK
- Full suite: 787 OK; ResourceWarning suite: 787 OK
- Readiness still `not_ready` / `inert_report_only=true` / `live_rails_activated=false`
