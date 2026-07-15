# MVP-Boundary Checkpoint Prompt — Fable (phase-end seat)

Date posted: 2026-07-14 · Builder seat: Claude Sonnet 5, driving the harness orchestrator
throughout · **Independence: run this in a FRESH session that did not build this work,
and ideally a fresh session from whichever one reviewed the Phase-B checkpoint** (read
`audits/phase-B-phase-end-fable-report.md` first if it exists yet — this checkpoint's work
was built on top of Phase B's cadence engine, and you should know whether that foundation
was signed off or held before assessing what's built on it).

Read `audits/PHASE-END-AUDITOR-BRIEF-fable.md` first — your standing rules, including the
correlated-blind-spot lens (§9). The class to hunt: doctrine-as-implementation.

**Provenance note, stated plainly:** per `governance/ROADMAP.md`'s own line — "Fable
checkpoints: end of A (clean state), end of B (the engine), MVP boundary (TD-02 + GM-02 +
SCHED-02)" — this is the THIRD and (for the original personal-os re-baseline) FINAL
defined Fable checkpoint. It should have run once TD-02+GM-02+SCHED-02 all merged. It did
not — same lapse as Phase B, discovered only once a new, much larger PRD amendment
(Knowledge Edge, D-PO-016) was already accepted and about to build further on this exact
foundation (the rails four-gate pattern, the credential convention, the scheduler design)
in a much bigger way. This is the highest-stakes of the two missed checkpoints: this is
the boundary where the project's own PRD says "unattended" execution — creating real
Todoist tasks, sending a real Gmail briefing, on a real schedule — becomes possible for
the first time. Treat accordingly.

## The phase under review

Everything from Phase C plus the Todoist/Gmail/Scheduler activation half of Phase D, all
merged into `main`:

- **P-BRIEF-01** (`db21fd4`): deterministic 8am briefing generator from real state (due
  routines, priorities, carryovers) through plan → window → preview → export.
- **P-SCHED-01** (`cfd085f`): real scheduler, manual trigger — `personalos run morning`
  executes the full morning cycle end-to-end in no-send mode, producing would-have-sent
  artifacts + ledger rows (the soak evidence for G5).
- **P-RAIL-TD-01** (`1153ea7`): Todoist adapter (inert). **Known finding from this
  session's own history**: the third-reviewer caught a real idempotency gap on this
  packet's original build (referenced in `OPEN_QUESTIONS.md`'s Q-PO-005 closure note).
  Confirm the fix actually landed and the duplicate-send class of bug is genuinely closed.
- **P-RAIL-TD-02** (`c2a4d28`): Todoist activation scaffolding — `docs/
  TODOIST_ACTIVATION_REVIEW.md`, `docs/TODOIST_KILL_PROCEDURE.md`,
  `tests/todoist_kill_drill.py`. Does NOT flip `status.py`'s rail state (confirmed by this
  session's own direct diff inspection at build time) — verify this is still true on the
  real merged code, not just historically true at merge time.
- **P-RAIL-GM-01** (`89dc85f`): Gmail adapter (inert), with its own controlled-recipient
  safety restriction added on the Builder's own initiative (not originally required).
- **P-RAIL-GM-02** (`f7a47b6`): Gmail activation scaffolding — same shape as TD-02.
  **Known finding**: the third-reviewer caught a restart-claim error in this packet's
  original kill-doc build (`OPEN_QUESTIONS.md`'s Q-PO-005 closure note). Confirm the kill
  procedure's actual documented restart behavior is now accurate.
- **P-SCHED-02** (`7c885cc`): background activation — `docs/com.personalos.morning.plist`
  (LaunchAgent, authored-only, never loaded), unload-proof kill-drill, `config.py`'s
  narrow production-DB-path exception, `docs/PRODUCTION_DB_RESTORE_DRILL.md`. This session's
  own history flags this as "the highest-stakes packet built this session" at the time —
  first packet to touch a real, protected, personally-meaningful filesystem location.
  A follow-up packet, **P-SCHED-03**, closed a path-safety gap this packet's own plist
  comments flagged as missing (`src/personalos/path_safety.py`'s guard chain) — confirm
  that fix is real and still correct on current `main`.

**Current live-state fact, verified directly this session**: as of 2026-07-14,
`src/personalos/status.py`'s `_RAIL_STATES` dict has every rail (`todoist`, `gmail`,
`calendar`, `model_api`) still `"inert"`, and `_SCHEDULER_STATE` is still `"off"`. Nothing
in this checkpoint's scope has ever actually been flipped live — HI-10 (Mac Mini launchd
authorization) remains genuinely open, separate from and not satisfied by any packet
merging. Real credentials (Todoist token, Gmail app password/sender/recipient) WERE
confirmed set on the Mac Mini as of 2026-07-14 (D-PO-015) — meaning the system is
credential-ready but state-inert. Your review is of code and scaffolding that has never
been exercised against a real external service; say so explicitly if any of your findings
depend on that distinction.

## Phase-boundary definition (audits/test-strategy.md, ROADMAP.md's "MVP boundary" line)

"Every morning, unattended: the system computes today's routines/priorities via a real
cadence engine, writes the day's routine tasks to Todoist (ledger-deduped), and emails the
8am briefing via Gmail." The full morning cycle must work end-to-end in no-send/soak mode;
each rail's four-gate pattern (permission → ledger/dedupe → rail-state → credentials) must
fail closed under hostile/careless callers; kill procedures must actually kill; nothing
must be able to reach a live rail from any code path without its rail-state gate being
satisfied.

## Your checkpoint charge (beyond re-running what the per-packet auditor ran)

1. **Drive the full morning cycle yourself**, end to end, against a scratch DB in no-send
   mode (`personalos run morning`). Does it actually produce the right due-today set (per
   the Phase-B cadence engine), the right briefing content, and the right
   would-have-sent Todoist/Gmail artifacts, with correct ledger rows?
2. **Verify the rail gating order under hostile/careless callers, on the real code, for
   ALL THREE rails** (`rails/todoist.py`, `rails/gmail.py`, and ALSO
   `rails/calendar.py` even though Calendar activation is a separate, later, still-pending
   packet not formally in this checkpoint's packet list — Calendar shares the exact same
   gate infrastructure conventions and is worth a quick sanity pass). For each: can you
   construct a call that reaches the live-write path while skipping or confusing any one
   of the four gates (permission, ledger/dedupe, rail-state, credentials)? Try genuinely
   adversarial argument orders, missing/malformed inputs, and race-shaped double-calls.
3. **Verify kill procedures actually kill**, on the real code, not just per the documented
   steps. Run `tests/todoist_kill_drill.py` and `tests/gmail_kill_drill.py` yourself and
   confirm they pass; then go further than the drills do — hand-construct at least one
   scenario each drill doesn't already cover and confirm the kill mechanism still holds.
4. **Confirm nothing bad can reach a live rail from any surface without its G5 state** —
   check every call site of each rail's live-write entry point (`create_live_todoist_task`,
   `send_live_gmail_message`, `create_live_calendar_event`) across the whole `src/` tree;
   confirm none of them are reachable from `personalos run morning`'s no-send path, the
   CLI's other subcommands, or the dashboard, without an explicit, deliberate live-mode
   invocation.
5. **Hunt survivors and confirm the three known third-reviewer-caught defects are actually,
   durably fixed** on current `main` (weekly-target undercounting from P-CORE-02, the
   Todoist idempotency gap from P-RAIL-TD-01, the Gmail kill-doc restart-claim error from
   P-RAIL-GM-02) — re-derive each bug class yourself and confirm it's closed, not just
   trust the historical "fixed" claim.
6. **Attestation:** confirm no `GOVERNANCE_MANIFEST.yaml`-listed file changed beyond each
   packet's sanctioned targets across this whole span (`git diff 96451fb..7c885cc` — end
   of Phase B through P-SCHED-02's merge — is in scope; note P-SCHED-03's later fix at
   `3d014e6` is a real, in-scope follow-up worth including even though it's chronologically
   after P-SCHED-02).

## Output

Write ONLY `audits/mvp-boundary-phase-end-fable-report.md`. Resolve to **sign_off / hold**
(hold = named, located conditions). Mandatory `WAYS_THIS_REVIEW_COULD_BE_WRONG` including
the same-family caveat. Do not touch STATUS.md, DECISIONS.md, ROADMAP.md, or any
per-packet auditor's own files. You never run git commands that mutate state (read-only
`git show`/`git diff`/`git log` are fine for citation purposes).
