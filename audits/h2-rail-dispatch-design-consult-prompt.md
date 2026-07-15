# H2 Rail-Dispatch Design Consult — Fable

> This is a **design consult**, not a phase-end audit. Nothing has been built yet — your job
> is to verify the problem statement below against the real code yourself (do not trust it as
> given), think through the open questions, and come back with a concrete proposal. No code
> changes; this is a read-and-recommend exercise. Independence matters here the same way it
> does for your phase-end checkpoints: run in a fresh session with no memory of how this
> codebase was built, and ground every claim (yours and mine) in the actual current source.

## Context

Two independent Fable phase-end audits this session (`audits/phase-B-phase-end-fable-report.md`,
`audits/mvp-boundary-phase-end-fable-report.md` — **note: both files are currently missing from
the working tree**, lost uncommitted across branch operations; you will not be able to read them
directly, only the summary below, which is why your independent re-verification of the code
matters more than usual here) each independently identified the same defect, labeled H2 in both:
**no code anywhere routes the morning cycle's computed candidates through the actual rail
adapters, even if a rail's status were flipped to "live."** H1 (a separate, unrelated defect —
routine cadence not wired through CLI/dashboard write surfaces) and two non-blocking findings
(F1, F4) from the MVP-boundary report have already been fixed and merged (`cf8fcbe`, `249ab4e`).
H2 was deliberately tabled at the time for a dedicated conversation, which is what this consult
now feeds.

## Problem statement (verify this yourself against the code; do not trust it as given)

Confirmed by direct code reading before writing this prompt — re-derive each of these
independently, they are the starting map, not the final word:

1. **Zero production callers of the rail adapters.** `grep -rln "from personalos.rails\|personalos\.rails\." --include="*.py" .` across the whole repo returns ONLY test files
   (`tests/test_rails_todoist.py`, `tests/test_rails_gmail.py`, `tests/gmail_kill_drill.py`,
   `tests/todoist_kill_drill.py`, `tests/test_rails_calendar.py`,
   `tests/calendar_kill_drill.py`, `tests/test_permission_evaluator_equivalence.py`). Nothing in
   `src/personalos/` imports `personalos.rails` at all.
2. **The type system itself has no "live" concept yet.** `src/personalos/scheduler.py:42`:
   `SCHEDULER_RUN_TYPES = ("manual_simulated", "due_check_simulated", "no_send_preview")` — every
   defined run type is a simulation/preview. `src/personalos/briefings.py:40`:
   `BRIEFING_DELIVERY_MODES = ("no_send", "manual_export")` — no "actually send" value exists.
3. **`run morning`'s actual call chain** (`src/personalos/cli/today.py:53`
   `_command_run_morning` → `scheduler.py:352 run_scheduler_job_simulated` → `scheduler.py:618
   _run_simulated_workflow` → for `job_type == "briefing_preview"`:
   `briefings.py: generate_no_send_briefing_preview(..., delivery_mode="no_send")`, hardcoded).
   This is the ONLY path `run morning` (the scheduled/manual morning job) ever takes.
4. **Each rail already has its own complete, previously-audited live-write path**, unused by
   anything above: `rails/todoist.py` has `create_live_todoist_task`,
   `evaluate_todoist_rail_live_write_permission` / `require_todoist_rail_live_write_permission`
   (gates on DB category `TODOIST_RAIL_LIVE_WRITE_PERMISSION = "todoist_rail_live_write"` via
   `permissions.py::evaluate_auto_write_gate`), and `_persist_live_write_idempotency_record`.
   `rails/gmail.py` mirrors this exactly (`send_live_gmail_message`,
   `evaluate_gmail_rail_live_send_permission` / `require_gmail_rail_live_send_permission`,
   its own `_persist_live_write_idempotency_record`). These went through their own kill-drills
   and phase-end audits (TD-02/GM-02) and are presumed trustworthy in isolation — your job is
   NOT to re-audit them, only to confirm nothing about wiring them in would require reopening
   that trust.
5. **Two separate, apparently unlinked "is this rail live" mechanisms exist** — this is the one
   piece I was not able to fully resolve and most want your read on:
   - `status.py`'s `_RAIL_STATES` dict (`inert`/`soaking`/`live` per rail) — a private,
     code-level literal, changeable only by editing the source (Conductor-gated per
     `governance/HUMAN_GATES.md`'s activation ladder, RISK_REGISTER-protected). This is what
     `STATUS.md`/dashboards currently mean when they say "todoist=inert."
   - The DB `permission_settings` table's `*_rail_live_write`/`*_rail_live_send` categories,
     read by each rail's own `evaluate_*_rail_live_*_permission` function via
     `evaluate_auto_write_gate` — this is what ACTUALLY gates a real call inside
     `create_live_todoist_task`/`send_live_gmail_message` today.
   - `status.py::create_status_summary` reports both (`RAIL_STATES` and
     `permission_settings`) side by side but I found no code that keeps them in agreement.
     Confirm whether this is true, and if so, what a dispatcher should do about it: check
     both and require agreement? Treat one as authoritative? This looks like exactly the class
     of "guarded-looking primitive, unclear which gate is real" your phase-end brief (§9,
     correlated blind-spot check) was written to catch — I flag it rather than resolve it
     because I'm not confident I've found the whole picture.

## Open design questions Chris wants your independent judgment on

Not mine to answer for him — think through each on the merits and give a reasoned
recommendation, but flag if you think a question is Chris's to decide regardless of the
technical merits (e.g. genuine risk-tolerance calls, not engineering ones):

1. **Mixed live state across rails.** If Todoist is flipped live but Gmail is still inert (or
   vice versa), should `run morning` dispatch real Todoist tasks while still previewing the
   Gmail briefing (per-rail independence), or should it wait until every rail touched by that
   run is live before doing anything for real? Consider: does per-rail independence create any
   half-done-cycle state that's confusing or unsafe to reason about later?
2. **Cycle-level idempotency.** Each rail already has its own idempotency record
   (`_persist_live_write_idempotency_record`) guarding duplicate sends of the same item. Is
   that sufficient on its own if `run morning` is invoked twice for the same date (manual
   re-trigger after a partial failure, or an operator error), or does the morning-cycle level
   itself need its own guard (e.g. a run-level idempotency key) on top? Reason from what the
   rail-level records actually key on — check their idempotency-key construction directly
   before answering.
3. **Partial-failure behavior.** Todoist dispatch succeeds, Gmail then fails mid-run — my
   instinct is report-and-stop, no auto-retry, matching this project's safety-first posture
   all session, but push on this: is there a real user-facing cost to stopping there (Chris
   never sees the day's tasks) that changes the calculus? What would "safe" degradation
   actually look like from the user's side, not just the code's?

Also flag anything you find that changes the shape of the problem — e.g. if the
`status.py`/`permission_settings` duality (item 5 above) means the real fix is narrower or
broader than "add a dispatcher," say so.

## Files to read (start here, follow what they lead you to)

`src/personalos/cli/today.py` (`_command_run_morning`), `src/personalos/scheduler.py` (the
full `run_scheduler_job_simulated` → `_run_simulated_workflow` chain, `SCHEDULER_RUN_TYPES`),
`src/personalos/briefings.py` (`generate_no_send_briefing_preview`,
`BRIEFING_DELIVERY_MODES`, the existing `evaluate_auto_write_gate` call and what it actually
gates — note it appears to be a DEV/TEST permission, not the live-send permission, confirm
this), `src/personalos/rails/todoist.py` and `src/personalos/rails/gmail.py` in full,
`src/personalos/permissions.py` (`evaluate_auto_write_gate`, the shared gate from P-DEBT-01),
`src/personalos/status.py` (`_RAIL_STATES`, `create_status_summary`),
`governance/HUMAN_GATES.md` (activation ladder), `governance/living/agent-writable/
DECISIONS.md` (search for D-PO-015 — real Todoist/Gmail credentials are now provisioned but
per its own text "unblocks nothing new by itself... these are now genuinely available for
real use whenever a rail is flipped live" — i.e. credentials exist, dispatch doesn't),
`docs/TODOIST_KILL_PROCEDURE.md` / `docs/GMAIL_KILL_PROCEDURE.md` / `docs/
TODOIST_ACTIVATION_REVIEW.md` / `docs/GMAIL_ACTIVATION_REVIEW.md` for the existing
per-rail safety posture your proposal needs to fit into, not duplicate or weaken.

## What your proposal should contain

- Independent confirmation (or correction) of the problem statement above, in your own words,
  with your own file:line citations — not a rubber stamp of mine.
- A resolution to the `status.py` vs `permission_settings` duality (item 5): what a dispatcher
  should actually check, and whether the two mechanisms need to be unified, one deprecated, or
  left as-is with a documented reason.
- A recommended dispatch mechanism: where it lives, what it takes as input (presumably the
  morning cycle's due-today/candidate computation — trace exactly what that currently produces
  before assuming its shape), how it decides per-candidate whether to call the real rail
  function or fall back to preview, and how the result gets reported back through
  `run morning`'s existing report/output shape.
- Reasoned answers to the three open questions above, marked clearly as recommendations Chris
  can accept or override, not decisions already made.
- Any additional risks or gaps you find that change the scope of what "fixing H2" means.
- A mandatory `WAYS THIS PROPOSAL COULD BE WRONG` section, same standard as your phase-end
  reports — include the same-family correlated-blind-spot caveat.

## Output

Write ONLY `audits/h2-rail-dispatch-design-consult-fable-report.md`. Do not touch
STATUS/DECISIONS/ROADMAP/any code. This is a proposal for the Conductor (Chris) and me to
review and decide on together — not a merge-track artifact, so no handoff-header/gate
machinery applies. Once you're done, stop; do not act on your own proposal.
