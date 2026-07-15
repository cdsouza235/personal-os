# H2 Rail-Dispatch Design Consult — Fable Report

> Design consult, not an audit. No code was changed. This is a proposal for the Conductor
> (Chris) and the prompt author to review and decide on together.

## Provenance of the source I read (read this first)

The brief lives on `main` at commit `6f3bd81`. **The working tree of the branch I was handed
(`worktree-agent-…`, HEAD `56bf649`) is behind `main` and is literally missing three of the
files the brief names** — `src/personalos/cli/today.py`, `src/personalos/rails/todoist.py`,
`src/personalos/rails/gmail.py` do not exist at `56bf649`. So every file:line citation below is
against **`main` @ `6f3bd81`**, which is the state the brief was written against and the state
that actually contains the code under discussion. I verified `6f3bd81` is a descendant of my
worktree HEAD, so nothing I cite is speculative future code — it is merged `main`. This is worth
flagging on its own: whoever acts on this proposal must do so on `main`, not on the stale
worktree, or they will be editing a tree where half the subject matter is absent.

---

## 1. Independent confirmation of the problem statement

I re-derived every numbered claim in the brief against `6f3bd81`. **All five hold.** Corrections
and sharpenings are called out inline.

### 1.1 Zero production callers of the rail adapters — CONFIRMED, with a naming trap worth naming

`git grep "from personalos.rails" 6f3bd81` returns **only** test files
(`tests/test_rails_todoist.py`, `tests/test_rails_gmail.py`, `tests/test_rails_calendar.py`, the
three `*_kill_drill.py`, `tests/test_permission_evaluator_equivalence.py`). No module under
`src/personalos/` imports the `personalos.rails.*` package at all.

Sharpening the brief: there are **two decoy names** that a careless grep will mistake for a
production caller, and neither is one —

- `from personalos import execution_rails as rails` (in `composer.py:13`, `side_effects.py:11`,
  `synthesis_import.py:13`, and five other modules). This is the *validation-helpers* module
  (`validate_risk_level`, `normalize_dedupe_key`, …), aliased `rails`. It is **not** the
  `personalos.rails` adapter package. The alias collision is a readability hazard but not a
  functional one.
- `src/personalos/todoist.py` — a top-level module distinct from `rails/todoist.py`.

Once those are excluded, the brief's claim is exactly right: **nothing in production reaches
`create_live_todoist_task` or `send_live_gmail_message`.** I confirmed directly that
`git grep "create_live_todoist_task\|send_live_gmail_message" 6f3bd81 -- src/**` outside `rails/`
returns nothing, and that no module named or containing "dispatch" exists in `src/personalos/`.

### 1.2 The type system has no "live" concept — CONFIRMED and stronger than stated

- `scheduler.py:42`: `SCHEDULER_RUN_TYPES = ("manual_simulated", "due_check_simulated",
  "no_send_preview")`. Every value is a simulation.
- `briefings.py:40`: `BRIEFING_DELIVERY_MODES = ("no_send", "manual_export")`. No "send" value.

The brief undersells this. It is not merely that no "live" *value* exists — the scheduler layer
**actively rejects** live intent. `scheduler.py:66-84` defines `_FORBIDDEN_JOB_TYPE_MARKERS`
(`"gmail"`, `"send"`, `"draft"`, `"todoist_write"`, `"calendar_write"`, `"activate"`,
`"live_model"`, `"background"`, `"daemon"`, …) and `validate_scheduler_job_type`
(`scheduler.py:492-501`) raises `SchedulerValidationError` on any job_type containing one of
them. On top of that, **every** workflow return and completion report is unconditionally stamped
with `SCHEDULER_SAFETY_FLAGS` (`scheduler.py:50-64`: `"live_write": False`, `"no_gmail_send":
True`, `"no_todoist_writes": True`, …) — see the `**SCHEDULER_SAFETY_FLAGS` splat at lines 407,
446-453, 488, and inside every branch of `_run_simulated_workflow` (635, 649, 659, 669, 689,
718). **This changes the shape of the fix (see §5.1): the scheduler is not a neutral pipe you can
teach a new run-type; it is a fail-closed simulation harness whose entire contract is "I cannot
touch a rail." A dispatcher must not be threaded *through* `run_scheduler_job_simulated`.**

### 1.3 `run morning`'s call chain — CONFIRMED exactly

`cli/today.py:53 _command_run_morning` → `run_scheduler_job_simulated(job_type="briefing_preview",
run_type="manual_simulated")` (`today.py:62-70`) → `_run_simulated_workflow` (`scheduler.py:386`)
→ the `job_type == "briefing_preview"` branch (`scheduler.py:671-690`) →
`generate_no_send_briefing_preview(..., delivery_mode="no_send")` (`scheduler.py:678-684`,
`delivery_mode` hardcoded). This is the only path `run morning` takes. Confirmed.

### 1.4 Each rail has a complete, unused live-write path — CONFIRMED

`rails/todoist.py:121 create_live_todoist_task` (with
`evaluate_todoist_rail_live_write_permission` at :259, `require_…` at :274,
`_persist_live_write_idempotency_record` at :295) and `rails/gmail.py:168 send_live_gmail_message`
(`evaluate_gmail_rail_live_send_permission` at :367, its own persist at :422) both exist, both
enforce the fixed order `permission → ledger/dedupe → rail-state → credentials` (todoist.py:137,
155, 170, 182; gmail.py:205, 223, 238, 250), and neither is called from anything but tests. I did
**not** re-audit their internal correctness (out of scope per the brief) and I found nothing that
would force reopening TD-02/GM-02 trust — the wiring I propose calls these functions *as-is*,
through their existing public signatures, and honors their existing structured refusals. One
material shape fact the brief omits, load-bearing for §4.4: **`send_live_gmail_message` is a
self-send-only channel.** Beyond the four gates it enforces a fifth "recipient scoping" check
(gmail.py:291-307) that refuses unless `to_address` exactly equals the single controlled
recipient in `PERSONALOS_RAIL_GMAIL_CONTROLLED_RECIPIENT` (per `D-PO-015`, Chris's own inbox).
The adapter **cannot** send to arbitrary third parties. Any "messages to other people" candidate
is structurally un-dispatchable through the rail as built.

### 1.5 Two "is this rail live" mechanisms — CONFIRMED, but they are already an AND-gate (see §2)

Both mechanisms exist exactly as described: the private `_RAIL_STATES` literal
(`status.py:55-60`, all four rails `"inert"`) surfaced immutably as `RAIL_STATES`
(`status.py:84`), and the DB `permission_settings` categories `todoist_rail_live_write` /
`gmail_rail_live_send` read via `evaluate_auto_write_gate`. And `create_status_summary`
(`status.py:108-150`) does report them side by side (`"permission_settings"` at :136,
`"rail_states"` at :138) **with no reconciliation between them in `status.py`.** The brief's
observation is factually correct. But the conclusion "unclear which gate is real" resolves
cleanly once you read the rail functions rather than the status reporter — see §2.

### 1.6 The gate in `briefings.py` is a dev/test permission, not the live gate — CONFIRMED

The brief asks me to confirm the `evaluate_auto_write_gate` call inside the briefing path gates a
DEV/TEST permission, not live-send. Confirmed: `briefings.py:391` gates on the categories
`briefing_loop_dev_test_read/write/run` (`briefings.py:34-36`, used at :95, :121→:687-696). These
are **orthogonal** to `todoist_rail_live_write` / `gmail_rail_live_send`. Enabling the briefing
loop grants nothing toward a live write. Additionally, `briefings.py:434-443
_require_fake_composer_adapter` **hard-rejects any non-fake Composer adapter** — the preview path
structurally cannot run a real model either. So `run morning` today is fail-closed on three
independent axes (fake adapter, dev/test permission, no-send delivery mode), none of which the
live rails share.

**Bottom line: the problem is real and correctly characterized. There is no code path, and no
type-system vocabulary, by which a computed morning candidate can reach a live rail — and the
scheduler layer would actively reject one if you tried to name it.**

---

## 2. Resolving the `status.py` vs `permission_settings` duality

**The two mechanisms are not an unresolved ambiguity; they are a deliberate two-key ignition, and
the reconciliation the brief couldn't find is enforced at the point of action, not at the point of
reporting.** Read `create_live_todoist_task`: it checks the DB permission first (todoist.py:137,
fail-closed) **and then** `RAIL_STATES["todoist"] != "live"` (todoist.py:170-171, fail-closed).
Both must pass. `send_live_gmail_message` is identical (gmail.py:205 and gmail.py:238). So a real
live write already requires **both** `_RAIL_STATES[rail] == "live"` **and** the DB permission set
to `auto_write`. The rail is the reconciler.

Why two keys, and why keep both:

- `_RAIL_STATES` is a **source-code literal** changeable only by editing `status.py`, which
  `HUMAN_GATES.md:41` (G5) and the RISK_REGISTER promote to a Conductor-gated change, validated at
  import (`status.py:82`) and re-validated per report (`status.py:94`). It is the *high-friction,
  human* key.
- The DB permission is flippable by any code path that writes `permission_settings` — the
  *operator-runtime* key.

Requiring both means: a rail cannot go live by a runtime DB flip alone (an agent or a stray
migration can't reach out), **and** it cannot go live by a source edit alone (the operator must
also explicitly enable the permission). That is exactly the belt-and-suspenders posture the whole
project has been building toward, and it is the correct default for irreversible actions.

**Recommendation: leave both mechanisms in place, unified in *documentation* only, and change
nothing about how they gate.** Specifically:

1. **The dispatcher must not re-implement either check.** It should call the rail function and
   honor its structured refusal (`gate_failed`, `status`). Re-deriving "is this rail live?" in a
   second place is precisely how the two gates would drift out of agreement — the thing the brief
   worried about would be *created* by a dispatcher that double-checks, not solved by it.
2. **The dispatcher may read `RAIL_STATES` for one purpose only: routing, not gating** — i.e. to
   decide *up front* "this rail is not live, so don't even build the live call, emit a preview
   instead" (§4.3). That is a cheap optimization and a cleaner report, but it is advisory; the
   rail's own `rail_state` gate remains the authority, so a `RAIL_STATES`-vs-permission
   disagreement can never produce a wrong live write, only a slightly redundant refusal.
3. **Document the AND-gate explicitly** where it is currently only implicit — the status summary
   reports the two side by side with no note that a live write needs *both*. That is a
   documentation gap, not a code gap. (I am **not** recommending you add a reconciliation
   assertion to `create_status_summary`; a "these must agree" check there would be wrong — they
   are *allowed* to disagree during the soak→live transition, e.g. permission enabled while
   `_RAIL_STATES` is still `soaking`. Disagreement is a valid intermediate state, and the rail
   already fails closed on it.)

There is one genuine asymmetry to flag, not fix: the DB permission is the *lower-friction* key, so
if an operator enables `todoist_rail_live_write = auto_write` "to test something" and forgets, the
only thing still standing between that and a live write is the source literal. That is fine —
that's what the source literal is *for* — but it argues for the activation checklist to include
"confirm the DB permission is NOT already left enabled from a prior experiment" before flipping
`_RAIL_STATES`, so the two-key property is real at flip time and not accidentally a one-key flip.

---

## 3. What the morning cycle's candidate computation actually produces

I traced this rather than assume it, because the dispatcher's whole job is to consume it.

`generate_no_send_briefing_preview` builds a Composer packet **from real DB state**
(`build_composer_packet_from_state`, composer.py:1218+ reads `list_routines`, `list_priorities`,
`list_followups`, `list_calendar_blocks`, `list_todoist_tasks`), then runs the **FakeComposerAdapter**
(`composer.py:141`) to produce `output_json`. The candidate arrays (composer.py:203-252) are:

- `todoist_tasks[]` — one per due routine, each shaped by `_routine_todoist_candidate`
  (composer.py) with `task_title`, `description`, `source_type="composer_output"`,
  `source_id=packet_id`, `labels`, `due_date_or_due_string`, `priority`, `dedupe_key`,
  `risk_level="low"`, `approval_mode="auto_allowed"`. **These fields map directly onto what
  `create_live_todoist_task`/`build_todoist_task_record` consume.** Candidate identity (routine
  id, due date) is grounded in real state; only surrounding prose is synthetic.
- `calendar_blocks[]` — a single self-review block (calendar rail is out of scope for H2 per the
  brief, but note it's here).
- `followups[]` — review candidates; these have **no rail** (there is no "follow-up rail"), so
  they are preview-only by construction.
- `email_briefs[]` — `{briefing_window, subject, body_markdown, summary}`. **Note the field
  mismatch with the Gmail rail:** `send_live_gmail_message` wants `source_type`, `source_id`,
  `subject`, `body`, `to_address` (gmail.py:171-175). The email_brief candidate supplies `subject`
  and `body_markdown` but **no `source_type`/`source_id`/`to_address`** — the dispatcher would have
  to synthesize `source_type="composer_output"`, `source_id=packet_id`, and
  `to_address=<controlled recipient>`. This is a small adapter shim, but it means "wire the email
  brief to Gmail" is not a field-for-field pass-through.

**The single most important thing I found in this trace (Q2-critical):** the `packet_id` these
candidates derive their `source_id` and `dedupe_key` from is **per-run, not per-day**.
`briefings.py:145-147`: `packet_id = stable_composer_id("briefing-packet",
f"{daily_plan['id']}|{briefing_window_name}|{started_at}")`, and `started_at = run_at or _utc_now()`
(`briefings.py:118`). The `daily_plan['id']` is stable per date, but `started_at` is the wall-clock
time of *this run*. So every `run morning` invocation for the same date produces a **different**
`packet_id`, hence different `source_id` and `dedupe_key` on every candidate. See §4.6 for why
this quietly breaks the rail-level idempotency guarantee the activation checklists assume.

---

## 4. Recommended dispatch mechanism

### 4.1 Where it lives

**A new module, `src/personalos/rail_dispatch.py`, called from a new CLI command, NOT from the
simulated scheduler.** Rationale flows directly from §1.2: the scheduler is a fail-closed
simulation harness that stamps `no_*` safety flags on everything and rejects any live-shaped
job_type. Wiring dispatch through `run_scheduler_job_simulated` would mean either subverting those
flags (destroying the guarantee the whole scheduler exists to give) or lying in the report. Keep
`run morning` exactly as it is — the no-send preview *is* the soak-evidence stage of the
activation ladder (`HUMAN_GATES.md:53-58`), and it should stay pristine. Add a **sibling** command
(e.g. `personalos run morning-live` / `dispatch morning`) that is honest about what it is.

This also keeps the reachability change auditable: introducing a module that *can* reach a live
rail is itself a G5 event (`HUMAN_GATES.md:41`, "ANY code path that can write Todoist / send Gmail
… becoming reachable"). A self-contained new module + new command is a far cleaner G5 review
surface than a new branch buried inside the scheduler's simulation switch.

### 4.2 What it takes as input

The dispatcher should **reuse the exact candidate computation** `run morning` already performs —
call the same packet-build + Composer path to get `output_json`, so live dispatch and the no-send
preview provably operate on the *same* candidate set (this is what makes the soak evidence
meaningful: the artifact you reviewed is the thing that gets dispatched). Input to the dispatcher
proper: the connection, the resolved date/window, and the computed `output_json` candidate arrays.

### 4.3 Per-candidate decision (preview-or-dispatch)

For each candidate, in this order:

1. **Route by rail availability (advisory, cheap):** if `RAIL_STATES[rail] != "live"`, do not
   build a live call — record a `preview` outcome for that candidate and move on. This is the
   fast path that keeps a fully-inert system (today's reality) producing exactly the preview it
   produces now.
2. **If `RAIL_STATES[rail] == "live"`, call the real rail function** (`create_live_todoist_task`
   / `send_live_gmail_message`) with the candidate's fields (plus the Gmail shim from §3). **Do
   not pre-check permission or credentials** — the rail function does all four gates itself and
   returns a structured refusal. The dispatcher's job is to *translate*, not to *re-gate*.
3. **Interpret the rail's structured result, don't guess:** `gate_failed is None` + `status ==
   *_CLIENT_CALL_PASSED` → dispatched. `gate_failed is not None` → blocked-and-previewed (carry
   `gate_failed`/`reason` into the report). `status == *_CLIENT_CALL_FAILED` → attempted-and-failed
   (see §4.7 partial-failure).

Candidates with **no rail** (followups, and email_briefs if you choose not to self-send) are
always `preview` — reported, never dispatched.

### 4.4 A decision Chris must make, not me: what "dispatch Gmail" even means

Because the Gmail rail is self-send-only (§1.4), the only email it can send is *to Chris's own
inbox*. So "dispatch the morning briefing via Gmail" means "email Chris his own briefing," which
is a plausible and useful feature (a real inbox delivery instead of a Markdown export). But the
`email_briefs` candidate is a *briefing*, not a *message to another person*, and the project's
permission model (`permissions.py:27,42` `MESSAGES_TO_OTHER_PEOPLE` = `approval_required`) treats
outbound-to-others as a categorically higher risk that the rail **cannot currently perform at
all**. **Recommendation framing:** scope H2's Gmail dispatch to *self-delivery of the briefing
only*, and treat "send messages to other people" as explicitly out of scope until a separate
packet widens the recipient model — which the Gmail adapter docstring (gmail.py:30-38) already
flags as needing its own review. This keeps H2 to "deliver Chris his own day," which is the safe,
useful 80%.

### 4.5 How results report back through `run morning`'s existing shape

`run morning` already returns a `workflow_report` that `cli/today.py:72-100` unpacks, and it
already has a slot for `manual_export_markdown`. Mirror that shape: the dispatcher returns a
`dispatch_report` with a per-candidate list `[{candidate_id, rail, outcome:
dispatched|preview|blocked|failed, gate_failed, idempotency_key, external_task_id/…}]` plus roll-up
counts, and the CLI emits it through the **same** `_with_workflow_context` / `_emit_report`
machinery (`today.py:83-100`) — but with the *live* safety flags told truthfully (`live_write:
True` where a write actually happened), **not** the hardcoded `SCHEDULER_SAFETY_FLAGS`. The
existing `no_send` preview report stays byte-for-byte unchanged; the new command emits a parallel,
honestly-flagged report. The `would_write` / `client_result` blocks the rails already return
(todoist.py:229-256, gmail.py:335-364) give you everything the report needs per candidate.

### 4.6 The idempotency fix this exposes (do this *before* any flip)

From §3: candidate `dedupe_key`/`source_id` embed the per-run `packet_id`. Feed those straight
into the rails and **the rail-level dedupe cannot protect a double `run morning-live` for the same
day** — each run mints a fresh `packet_id` → fresh `dedupe_key` → fresh
`generate_idempotency_key` (idempotency.py hashes `source_id` + `dedupe_key` + payload) → the
second run's `get_idempotency_record` lookup misses → the same routine task is created **twice**.
This directly contradicts the guarantee `TODOIST_ACTIVATION_REVIEW.md` §2 tells Chris to verify
("a re-run of identical input … was blocked with `STATUS_BLOCKED_DUPLICATE`"). The dedupe gate as
wired would silently *not* fire.

**Fix, at the candidate layer, not with a new run-level guard:** derive each candidate's
`source_id`/`dedupe_key` from **day-stable identity** — `(source_date, briefing_window, item
identity e.g. routine_id)` — instead of from `packet_id`. Concretely, key off `daily_plan['id']`
(already stable per date, briefings.py) rather than `packet_id` (per run). Then two runs for the
same day produce identical dedupe keys, the payload is stable (the routine description embeds
`source_date`, not a timestamp), the full idempotency key matches, gate 2 fires, and the
`UNIQUE(target_system, operation_type, dedupe_key)` constraint (migration 00011) backstops it at
the DB. This makes the rail-level record *sufficient* for Q2 and makes the activation checklist's
promise true. See §4.7 for why I still would not add a *separate* run-level key on top.

### 4.7 Answers to the three open questions (recommendations — Chris's to accept or override)

**Q1 — Mixed live state across rails. Recommendation: per-rail independence, dispatch what's
live.** If Todoist is live and Gmail is inert, dispatch the Todoist tasks and preview the Gmail
brief. Reasons: (a) the rails are *already* independent gates — `RAIL_STATES` is per-rail
(status.py:55-60) and each rail checks only its own state; there is no code notion of "the whole
cycle is live," and inventing an all-or-nothing barrier would be a new, heavier invariant with no
existing support. (b) The activation ladder itself is explicitly *one rail at a time*
(`HUMAN_GATES.md:54`, "Live rails go live one at a time … Never bundled") — an all-or-nothing
dispatcher would contradict the governance model, forcing you to flip two rails together to get
either. (c) Gmail-inert-while-Todoist-live is the *expected* steady state for a long time, since
"email is irreversible … Gmail soaks longest" (`GMAIL_ACTIVATION_REVIEW.md:17`). An all-or-nothing
rule would mean Todoist can never dispatch until you're ready to also send email — coupling the
cheap-reversible rail to the expensive-irreversible one, backwards from the risk gradient.
*Half-done-cycle worry:* the only "confusing later state" is "tasks created but no email brief
delivered," and that is not actually confusing — the tasks are self-describing in Todoist, and the
briefing still exists as the Markdown export/preview it is today. Per-rail is safe here. **Caveat
that is Chris's call, not mine:** if you have a personal-workflow reason to want "either I get the
whole day or none of it," that is a genuine preference, not an engineering constraint — say so and
it's a trivial roll-up gate. I'm recommending per-rail on the merits, not asserting the other
choice is wrong.

**Q2 — Cycle-level idempotency. Recommendation: rail-level records are sufficient *only after*
the §4.6 dedupe-key fix; do NOT add a separate run-level key.** The rail dedupe keys on stable
intent identity (idempotency.py), which is the right grain — it dedupes "this routine, this day"
regardless of how many times the cycle runs. A *second*, cycle-level idempotency key would be
either redundant (if it keys on the same day identity) or wrong (if it keys on the run, it would
block a legitimate re-trigger after a partial failure — the exact recovery path Q3 cares about).
The bug to fix is not "add a guard," it's "the existing guard is keyed to the wrong thing"
(§4.6). Once candidate identity is day-stable, invoking `run morning-live` twice for the same date
does the right thing automatically: already-dispatched items hit `STATUS_BLOCKED_DUPLICATE`,
not-yet-dispatched items (e.g. the ones that failed on the first run) go through. That is *better*
than a run-level lock, which would refuse the whole second run. **I flag this as the one place my
"confirm the problem" turned into "the problem is slightly different than framed":** the brief
asks "is rail-level enough or do we need a cycle-level guard?" — the honest answer is "rail-level
is enough *and* is currently broken for this use, and the fix is at the candidate layer, not a new
guard."

**Q3 — Partial failure (Todoist succeeds, Gmail then fails). Recommendation: report-and-stop, no
auto-retry — and the user-facing cost is low *because of* per-rail independence.** The prompt's
instinct is right and matches the whole project's posture, but push-back on the "Chris never sees
the day's tasks" worry: with per-rail dispatch (Q1) and the Todoist-before-Gmail ordering implied
by risk gradient, **the tasks are already in Todoist before Gmail is even attempted** — Chris sees
his day regardless of the email failing. So "safe degradation from the user's side" is concretely:
tasks present in Todoist, briefing available as the Markdown export it already is, and a report
saying "Gmail send failed, not retried." No day is lost. The genuinely irreversible actor (email)
is the one that failed to *do* anything — that's the safe direction to fail. Auto-retry is exactly
wrong for the Gmail leg: `send_live_gmail_message` deliberately persists its dedupe record **only
after confirmed success** (gmail.py:319-333), so a transient failure leaves no record and *is*
retriable — but retriable-by-a-human-deciding-to, not by an automatic loop that can't tell
"transient network blip" from "the send half-succeeded and the ack was lost." For an irreversible
send, report-and-stop and let Chris (or a deliberate re-run, now safe under §4.6) decide. **The
one thing I'd add:** the report must make the *asymmetry* legible — "Todoist: 3 dispatched. Gmail:
FAILED (not retried). Your tasks are live; your email is not." A partial-failure report that just
says "1 error" would hide which side won.

---

## 5. Additional risks / things that change the scope of "fixing H2"

**5.1 The fix is a new command + module, not a scheduler branch (see §4.1).** If someone
implements H2 by adding a `briefing_dispatch` job_type to the scheduler, they will collide head-on
with `_FORBIDDEN_JOB_TYPE_MARKERS` and the unconditional `SCHEDULER_SAFETY_FLAGS`, and the
"natural" way around that is to weaken those — which would silently degrade the guarantee for
*every* existing simulated job, not just the new one. Scope note: keep the scheduler out of it.

**5.2 The side-effects ledger schema structurally cannot record a live write — this is a G4
(migration) sub-project hiding inside H2.** `migrations/00011` hard-CHECKs
`live_write = 0` and `no_external_writes = 1` on both `external_write_intents` (lines 51-53) and
`external_write_attempts` (line 78, plus `mode IN ('dry_run','simulated','live_blocked')`), and
`idempotency_records.status` enumerates only up to `'completed_simulated'` (no `'completed_live'`).
Both rails already work around this by writing their dedupe row into `idempotency_records` with
`status='completed_simulated'` and `linked_intent_id/linked_attempt_id = NULL`
(todoist.py:333, gmail.py:458) — i.e. **a real live write, once it happens, will be recorded in the
ledger mislabeled as "simulated" with no linked intent/attempt.** The activation review checklists
already flag this as an accepted wart (`TODOIST_ACTIVATION_REVIEW.md` §3). But it means: the
moment you actually flip a rail live, your side-effect ledger and status counts (`status.py:125-127`
counts `external_write_intents`/`attempts`/`idempotency_records`) become *misleading* about what's
real. **Scope call for Chris:** either accept the mislabel for the first bounded live period
(documented, and the review checklist catches it manually), or do the migration to add
`'completed_live'` + a live-capable intent/attempt row *first*. The migration is G4 and is
arguably the honest prerequisite; at minimum it should be a named follow-up, not a surprise.

**5.3 "Dispatch" is a reachability change = its own G5, separate from any actual flip.** Building
the dispatcher makes a live-write path *reachable* even while all rails stay inert. Per
`HUMAN_GATES.md:41` that is itself G5 ("… becoming reachable, and separately EVERY activation").
So H2 is *two* G5 events minimum: (1) merge the dispatcher (reachable-but-inert), (2) each rail
flip. Don't let the merge of the dispatcher ride in as a normal packet.

**5.4 Credentials exist, which removes the last accidental backstop.** Per `D-PO-015`, all four
rail env vars are set on the Mac Mini as of 2026-07-14. Today the credential gate (gate 4) fails
closed only because `_RAIL_STATES` is inert (gate 3 stops execution before gate 4 is reached). But
once a rail is flipped live, the credential gate will *pass* — the "we're safe because there are no
real credentials" era is over (the decision text says as much). This raises the stakes on getting
§4.6 (dedupe) and §5.2 (ledger honesty) right *before* the flip, not after.

**5.5 The stale-worktree hazard is itself a finding.** That the handed-to-me branch is missing
`today.py` and both rail modules (see provenance note) means an implementer who works in that
worktree will be building against a tree where the subject code is absent. Whoever picks this up
must confirm they're on `main` (or a fresh branch from it) first.

---

## 6. WAYS THIS PROPOSAL COULD BE WRONG

- **Same-family correlated blind spot (the load-bearing caveat).** I am Fable, the same model
  family that produced the two phase-end audits that found H2 and wrote this brief. If there is a
  *category* of error we share — e.g. over-trusting a "structured refusal / fail-closed" story
  because it reads as disciplined, or systematically reading an AND-gate as safer than it is — then
  my "the two gates already reconcile at the rail" conclusion (§2) is exactly the kind of thing
  that would sail past all three of us identically. An independent, *different*-family reviewer
  should specifically re-derive §2 by trying to construct a live write with only *one* key
  satisfied, and re-derive §4.6 by actually running `run morning`-equivalent candidate generation
  twice and hashing the two idempotency keys, rather than trusting my read of the code.
- **I did not execute anything.** Every claim is from reading source at `6f3bd81`, not from
  running it. The §4.6 double-run duplicate claim in particular is a *predicted* behavior from
  tracing `packet_id → dedupe_key → idempotency_key`; I did not empirically invoke the path twice
  and observe two Todoist calls (the rails are inert, so I couldn't without flipping state). If
  `stable_composer_id` or `_ensure_daily_plan` normalizes `started_at` away in some path I didn't
  read, the duplicate risk could be smaller than I claim. It should be verified by test before it's
  relied on.
- **I read `main` @ `6f3bd81`, not the branch I was handed.** If work has landed on `main` after
  `6f3bd81` that I didn't see, or if the intended integration target is actually the stale
  worktree branch (unlikely, but I inferred), my line numbers and even some structural claims could
  be off. The provenance note is my mitigation, but it's an assumption.
- **The Gmail-is-self-send-only claim (§1.4/§4.4) reframes the problem in a way the brief didn't,
  and I might be over-reading `recipient_scoping` as more permanent than it is.** It is enforced in
  code today (gmail.py:291-307), but the docstring calls it a "this first inert adapter packet"
  scope. If a follow-up packet has already widened it (I checked `6f3bd81` and it had not), my "email
  to others is out of scope" framing would be stale.
- **My §4.1 "new command, not the scheduler" recommendation could be wrong if there's a product
  reason `run morning` must be the single entry point** (e.g. a launchd/cron job already wired to
  exactly `personalos run morning` that Chris wants to become live without changing the invocation).
  I recommended a sibling command on safety-architecture grounds; if operational reality wants one
  command, the honest alternative is a `--live` flag on `run morning` that bypasses the scheduler
  path internally — more invasive to the safety story, but a legitimate call I'm not positioned to
  make.
- **§4.6 assumes making `dedupe_key` day-stable has no downstream consumers that rely on its
  current per-run uniqueness.** I did not exhaustively trace every reader of composer `dedupe_key`
  (e.g. `build_candidate_routing_report`, composer.py:423). If some consumer *wants* per-run
  uniqueness, the fix needs to be scoped to the rail-input derivation only, not the candidate
  itself — a real possibility I didn't fully rule out.
- **Q1/Q3 are partly risk-tolerance calls dressed as engineering.** I gave per-rail + report-and-
  stop on the merits, but "do I want a half-live day?" and "is no-email-today an acceptable
  degradation?" are genuinely Chris's to weigh against how he actually uses the system. If my model
  of "tasks in Todoist = he sees his day" is wrong for his real workflow, Q3's "low user-facing
  cost" conclusion doesn't hold.
