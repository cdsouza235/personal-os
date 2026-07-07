# PR #104 Audit — Wide-net Calendar bridge contract + fail-closed precheck

- Branch: `phase-14c-calendar-bridge-contract`
- Head: `76fd55523ce72d9a7339d88969643299d1bc2117`
- Base: `origin/main` @ `40a4429` (after PR #103 merge)
- Reviewer: Claude Code `/code-review` (high effort, recall-biased)
- Scope: `git diff main...HEAD` (17 files, +449 / -46)

## Verdict

**Clean — approved for merge.** No material findings. Fully resolves PR #103 finding 1 with a
two-layer fail-closed design, adds strong bridge-layer payload bounds enforcement, and keeps the CLI
unchanged / fail-closed.

## Findings

None material. (Non-blocking nit: `_optional_string` re-implemented again — recurring helper
duplication; promote to a shared util someday.)

## Verified OK

- **PR #103 finding 1 resolved (fail-closed).** The old fail-open parser (`return 0` default +
  `None`-returning `_calendar_matching_events`) is deleted. `_calendar_matching_event_count` now
  delegates to `require_explicit_calendar_matching_event_count`, which raises
  `CalendarBridgeContractError` unless the response carries the exact precheck `contract` AND a
  non-negative int `matching_event_count`. That error (`ValueError` subclass) is caught by the
  precheck `try/except` → `_post_calendar_precheck_failure_report` (no writes,
  `external_mutation=false`). Malformed/unrecognized/absent-shape responses now stop the run.
- **Strong bridge-layer bounds enforcement (defense in depth).**
  `WideNetGoogleCalendarConnectorBridge` validates both payloads structurally:
  - precheck: title == approved marker, `calendar_id == "primary"`, `exact_title_match_required` is
    True, `attendee_data_required` is False — else `CalendarBridgeContractError`.
  - create: title == marker, `calendar_id == "primary"`, `attendees == []`, `add_google_meet` False,
    `recurrence` None, `attachments == []` — else error.
  So even a malformed runner payload cannot produce an unbounded calendar write.
  `count_matching_calendar_events` also fails closed on non-list `events`/`items` or unrecognized
  shapes.
- **Genuinely inert scaffold.** The bridge takes injected `search_events`/`create_event` callables
  only — imports/initializes no live connector, reads no credentials, does no network I/O itself.
- **CLI unchanged / still fail-closed.** `src/personalos/cli.py` is NOT in this PR's diff;
  `calendar_client_available = False` remains hardcoded, so the CLI bridge is unavailable and
  `--execute-live` reads no credentials and makes no live call.
- **No import cycle** (plan ← bridge ← runner); runner import correctly ordered; plan/docs record
  the new fail-closed contract; no leakage (bridge emits only counts/booleans;
  `event_details_logged`/`attendee_addresses_logged` False). Focused tests pass locally (27 OK);
  readiness unchanged (`not_ready` / `inert_report_only=true` / `live_rails_activated=false`).

## Note for the next (connector-wiring) PR

This PR is a tested contract/scaffold; the bridge is not wired to the CLI. The PR that injects a
real audited Google Calendar connector into `WideNetGoogleCalendarConnectorBridge` and flips
`calendar_client_available` to True is the one that finally un-gates credential reads + live calls.
It must get its own pre-run audit + fresh explicit approval, and OpenRouter should be topped up
(prior 402 — affects only the diagnostic-only model step here).

## Test status (per PR)

- Focused wide-net bridge/gate/CLI/docs/model suite: 108 OK
- Full suite: 793 OK; ResourceWarning suite: 793 OK
- Readiness still `not_ready` / `inert_report_only=true` / `live_rails_activated=false`
