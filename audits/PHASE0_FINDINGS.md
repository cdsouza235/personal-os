# Personal OS — Phase 0 Findings Audit

**Date:** 2026-07-07 · **Audited baseline:** `main` @ `58fc27e` (PR #123)
**Auditors:** Claude (Fable 5, architect pass) + Codex (gpt-5.5, independent machine-invoked
cross-family audit — see `PHASE0_CODEX_AUDIT.md` and §8 reconciliation)
**Charge:** evidence-backed findings to seed the re-baseline (governance overlay + PRD delta +
packet ROADMAP). No code changes were made.

---

## 1. Verdict summary

The project stalled because **the product's brain was never built, and the process grew a
substitute for it.** The repo has a genuinely solid local foundation (SQLite state layer,
migrations, synthesis import/apply, no-send briefing pipeline, ledgers, dashboard — all green:
861 tests in 13s), but the thing the PRD calls the product — a routine engine that knows
cadence, missed-behavior, rotation, and what is due today — does not exist. Instead,
roughly a third of the codebase and two years of PR history are activation *ceremony*:
readiness reporters, report-contract validators, validator-matrix tests, and decision-record
templates that guard a live activation that was never going to be reachable, because the
readiness machinery reports `not_ready` **by construction** (§5). The honest answer to "what
blocks `not_ready`" is: nothing you could approve — there is not yet a complete product to
activate, and the machinery that says so cannot say anything else.

The re-baseline is therefore not primarily a cleanup; it is **finishing the product** under a
process that can actually terminate. The good news: no product module imports the phase-14C
machinery, so that layer deletes surgically; the readiness/status layer that Today View does
consume swaps out behind a lean interface (§8, correction 1); and the foundations underneath
are worth keeping.

## 2. What is solid (keep)

| Surface | Evidence | Assessment |
|---|---|---|
| SQLite state layer | `src/personalos/state.py` (186 fns, uniform validate/get/list/count/create/update CRUD), `db/` (connection, migrations), 14 migrations with FK enforcement | Real. Oversized single module but consistent idiom; safe to keep and split later. |
| Synthesis import → preview → approval-gated apply | `synthesis_import.py` (1,394 LOC), `synthesis_apply.py` (1,692 LOC), atomicity + audit trail, 25+18 tests | Real; one of the most complete PRD features (§13). |
| No-send briefing pipeline | `briefings.py` (857 LOC): daily plan → window select → preview → manual export; permission-gated | Real as a *pipeline*; content generation is fake-only (see §3). |
| Side-effect / idempotency ledgers | `side_effects.py` (1,149 LOC), 22 tests, dedupe keys per PRD §15/§16 schema | Real; exactly the substrate live rails need. |
| Today view + dashboard + operator CLI | `today.py`, `dashboard.py` (stdlib `http.server`, localhost-only), `operator_status.py`, `cli.py` | Real, no-send. `cli.py` is a 4,233-line, 59-subcommand monolith — works, but a liability (§6). |
| Deterministic e2e demo | `demo/no_send_e2e.py` + fixtures | Real (PRD §9 delivered). |
| Test culture | 861 tests, 13s, deterministic, no network | Strong — though a meaningful slice tests process artifacts, not product (§4). |
| Layering (corrected — see §8) | No product module imports any `phase14c_*` module (verified), so the phase-14C family is surgically removable. **But** `today.py:8-15` consumes `pre_live_readiness`, `operator_status`, `scheduler`, `side_effects` — the readiness/status layer is woven into Today View and must be *replaced* (with lean status), not just deleted. | Removal is still low-risk, but it is a two-class job: delete `phase14c_*` outright; swap the readiness/status calls behind a lean interface. |

## 3. The product gap (PRD §1/§14/§28 vs. code)

The PRD's vision is "a disciplined personal assistant." What the code implements is a
**state store with previews**. The assistant logic is absent:

- **No routine cadence engine.** PRD §14 specifies cadence types (`daily`, `weekdays`,
  `x_times_per_week`, `rotating_sequence`…), missed-behavior options
  (`combine_with_next`, `bump_schedule_by_one_day`…), rotation groups, `next_due`.
  In code: the `routines` table is a generic shell (`name, status, enabled, settings_json`,
  `migrations/0003_core_state_tables.sql:1-11`) — the entire routine model would live in an
  unstructured JSON blob; `routines.py` (327 lines) is CRUD + permission gates + a
  `complete_routine` writer. **Nothing computes what is due today from a cadence rule.**
  The word "cadence" appears in the product only as a seed string and a report-job enum.
- **Composer is fake by construction.** `composer.py` hard-requires the fake adapter
  (`_require_fake_adapter`, `dev_test_fake_adapter=True`); there is no live-model composer
  path at all — only the separate OpenRouter *smoke client*.
- **Todoist/Calendar are preview+simulation records**, not adapters. `todoist.py` writes
  `simulated_created` rows via `FakeTodoistClient`; the only live-capable Todoist/Gmail code
  is the one-object smoke modules (`phase14c_*_live_smoke.py`), which are test harnesses,
  not product rails.
- **Scheduler is simulation-only by design** (`scheduler.py:1` — "No-send scheduler/runtime-loop
  simulation foundation"; run types `manual_simulated`, `due_check_simulated`).
- **Two dead skeletons**: top-level `personalos/` (8 `.gitkeep` dirs shadowing the real
  package) and `app/` (`api/`, `dashboard/` — `.gitkeep` only).
- **Product-looking modules are unwired** (Codex finding, independently verified): no
  non-test source imports `routines.py`, `priorities.py`, `reports.py`, `fitness.py`,
  `runtime_bootstrap.py`, or `completion.py` — not even `cli.py`. The "routine editor" and
  "priority registry" of PRD §28 are tested libraries with **no user surface**; Today View
  reads their tables directly through `state.py`. The dashboard's own banner declares no
  routine/priority/apply routes (`dashboard.py:236-239`).

**Consequence:** even with every gate approved and every credential loaded, Personal OS today
could not send a useful 8am briefing or create the right routine task — there is no engine to
decide *what* to send or create. This—not readiness process—is the real blocker.

## 4. Drift inventory (the process-as-code layer)

- **~24 of 62 modules (~10,500 LOC)** are phase-14C/readiness/closure/handoff machinery:
  report-contract validators, contract-manifest embedders, readiness rollups, evidence
  validators, handoff reporters. Largest: `phase14c_supervised_smoke.py` (1,785),
  `phase14c_candidate_decision_support.py` (1,009), `phase14c_wide_net_rehearsal_live.py` (925),
  `phase14c_wide_net_execution_handoff.py` (899).
- **PRs #47–#76 are ~30 consecutive PRs** hardening validator matrices for an *unfilled
  decision template* — validators validating reports about validators. This is the visible
  signature of a loop optimizing its own process instead of the product.
- **10 `test_*_docs.py` files** assert exact phrases inside markdown docs
  (`docs/ROADMAP.md` even carries an "Exact Phrase Index" to keep them passing). Tests of
  documentation phrasing, and 76 tests for the decision-support validator alone, inflate the
  suite; the routine engine has 21.
- **Every status snapshot is stale in a different way**: PRD says baseline PR #87 / "705
  tests"; STATUS.md (76KB) says PR #118; actual main is PR #123; the actual suite is 861
  tests. Three documents claim canonicality; none is current. (The working tree itself was
  found parked on a merged feature branch with 33 loose untracked `PR##_AUDIT.md` files.)
- **~25 governance/phase docs in `docs/`** restate the same non-authorization boilerplate;
  PRD §0/§6 have become a PR-by-PR changelog rather than a product requirements document.

**Disposition (per Conductor decision 2026-07-07):** all of it is retirable to `archive/`;
nothing is personally load-bearing. SAFETY_POLICY's *content* (protected paths, high-stakes
domains, posture flags) folds into the harness governance overlay as protected paths +
risk-register entries.

## 5. The honest `not_ready` answer

Traced in `src/personalos/pre_live_readiness.py`:

1. Every production caller (`cli.py:1567,1676,4056`, `today.py:83`, `operator_status.py:63`)
   calls `create_default_pre_live_readiness_report()` → `evaluate_pre_live_readiness(config=None)`.
2. With `config=None`, the first gate `CONFIG_PROVIDED` fails ("Missing readiness config fails
   closed", line 311) → `not_ready`. **No code path in the repo constructs a filled
   `PreLiveReadinessConfig`** (sole non-default constructor: an *empty* config in
   `phase14_pilot_prep.py:111`).
3. Even with a fully satisfied config, line 273 grants `READY` only when **all live rails are
   disabled and inactive** — i.e. "ready" is defined as "everything off." A system with a live
   rail enabled can never report ready; the summary layer additionally hardcodes
   `inert_report_only: True` and `live_rails_activated: False` (lines 227–231).

So the blockers are **not technical gaps in the gates and not missing evidence — the readiness
state machine is a posture reporter, not a decision procedure.** It was built to prove the
system is off, and it does that well. Layered on top, the phase-14C "wide-net" machinery keeps
generating new preconditions (rollup contracts, bridge scaffolds, transcript validators,
pre-run checklists — PRs #88–#123) faster than any decision retires them. The only genuine
blockers of the *product* are in §3, plus one decisional gate (Chris authorizing live rails)
that no amount of repo work can satisfy — which is exactly the gate the harness makes a
first-class human gate (G5) instead of an ever-receding process artifact.

**Safety enforcement classes** (what actually holds the inert line today):

| Class | Where | Assessment |
|---|---|---|
| Enforced in code, fail-closed default | 6 live-capable modules (`phase14c_{gmail,todoist}_live_smoke`, `phase14c_{connected,wide_net}_rehearsal_live`, `openrouter_model_smoke_client`, `phase14c_safety_utils`) gate on `execute_live=True` + approval-reference + config-name preflight; composer/todoist/calendar/scheduler have **no live path at all** | Real defaults — but the "approval reference" is a **string constant in the same source file** compared with `==` (`phase14c_wide_net_rehearsal_live.py:166-169`). Any caller — including a careless agent — can self-approve by reading the constant. Instruction-as-boundary, not mechanism. |
| Convention/documentation only | Protected paths, "no credentials," "no scheduler activation," AGENTS.md stop conditions | Nothing mechanical prevents violation; held by agent obedience so far. |
| Already ran live | 2026-06-30 + 2026-07-01 bounded smokes: 1 real Gmail SMTP self-send, 1 real Todoist task (after CA-bundle retry), 1 real Calendar event, real OpenRouter calls (STATUS.md) | The wiring is proven live-capable. "Inert" is a *current posture*, not a historical invariant — the honest framing for the harness's structural containment (egress severed before evidence, G5 gates) being the right replacement. |

## 6. Structural liabilities for the flexibility goal

Chris's first-class requirement: the system stays flexible as routines change or new routines
enter his life. Ranked liabilities:

1. **Routine semantics live nowhere.** With cadence/missed-behavior/rotation unimplemented and
   the schema a `settings_json` blob, every future routine type means inventing the model from
   scratch. The re-baseline's most important design work is a real, state-driven routine model
   (PRD §14 is actually a good spec for it).
2. **`cli.py` (4,233 LOC, 59 subcommands) and `state.py` (4,856 LOC, 186 fns)** are
   accretion points; every feature lands more weight on both. Keep the idiom, split by domain.
3. **Doc-phrase tests + boilerplate replication** make any *description* change ripple through
   tests, ROADMAP phrase indexes, STATUS, and PRD changelog — change-amplifying, the opposite
   of adaptable. Retiring the process layer removes most of this.
4. **Twelve-fold duplicated permission machinery** (Codex finding): `_permission_decision`,
   per-module permission evaluators, and required-text validators are copy-repeated across
   ~12 modules (`routines.py:259`, `priorities.py:525`, `todoist.py:378`, `briefings.py:735`,
   `composer.py:1327`, …) instead of one shared evaluator. Every permission-model change is
   a 12-file change. The live smoke clients additionally bypass `permissions.py` entirely
   with their own flag gates — so "configured permission" is not a single source of truth.
5. **Dead skeletons (`personalos/`, `app/`)** invite misplaced code and confuse imports/tools.
6. **The briefing content path has no real generator** — when a live composer arrives it must
   produce the PRD §18 structured output against ledgered execution; that seam
   (composer output → validation → permission → ledger → rail) exists but has never carried
   real content.

## 7. What "done" should mean — proposals

Anchor (Conductor, 2026-07-07): the live daily loop, with zero bias toward the incumbent
design, flexibility as a first-class property, OpenClaw decided on merits.

**Proposed MVP ("Personal OS v1 actually running"):**
> Every morning, without Chris touching anything: the system computes today's routines and
> priorities from state via a real cadence engine, writes the day's routine tasks to Todoist
> (deduped via the existing ledgers), and emails the 8am briefing via Gmail. Chris edits
> routines/priorities via dashboard or synthesis import, and the next cycle reflects it.
> Calendar blocks and the 12/4/8pm windows are fast-follows, not MVP.

Rationale: it forces the three real gaps (cadence engine, content generation, thin live
adapters) and consumes the already-built substrate (state, ledgers, permissions, briefing
pipeline). Everything else in the PRD is a follow-on, not MVP.

**Design stance for the rebuild (the zero-bias part):**
- **Cadence engine as pure functions over state** (`(routine defs, completions, date) → due
  set`), promoted out of `settings_json` into real columns/tables. Editable state, not code.
- **Briefing content: template-first, model-optional.** A deterministic template briefing from
  real state ships the loop without any model dependency; the PRD §18 composer becomes an
  *upgrade* behind the same structured-output contract. (Kills the fake-composer dead end as
  a blocker.)
- **Live adapters as thin, ledger-guarded clients** (the smoke modules prove the transport in
  ~300 LOC each); rails stay inert until a deliberate G5-gated activation packet per rail.
- **OpenClaw: recommend CUT from the product** (defer indefinitely). Its PRD role — operator
  that runs approved runtime workflows — is now filled by the scheduler-to-be + the MIS
  harness itself (gated, audited execution); its model-lane strategy is already served by the
  OpenRouter client. It is the least-built rail, a whole extra trust surface, and nothing in
  the MVP needs it. The fitness CSV workflow it touches stays untouched and out of scope.
  If a future need appears, it re-enters as its own packet with its own gate.

## 8. Cross-family reconciliation (Codex)

Codex (gpt-5.5, xhigh reasoning) ran headlessly against the same baseline with a clean-context
brief (`PHASE0_AUDIT_BRIEF_codex.md`); full report in `PHASE0_CODEX_AUDIT.md`. Reconciliation
below — disagreements surfaced, not averaged.

**Convergent (independently reached by both):** product rails are fake/scaffold-only with no
live product path (Todoist/Calendar/Gmail/composer/scheduler); routine semantics live in an
unstructured `settings_json` blob with no first-class cadence/missed-behavior enforcement;
readiness is `not_ready` by construction; `state.py`/`cli.py` are cross-domain monoliths;
the test suite over-proves inertness relative to product behavior (Codex quantified: 232
test-grep hits on inert/contract wording); live smokes already ran on all four external rails;
the top-level `personalos/` skeleton is dead.

**Codex findings adopted after independent verification (each corrects or extends this report):**
1. **Layering correction (against §2's first draft):** product code *does* consume the
   readiness/status process layer (`today.py:8-15`) even though it never imports `phase14c_*`.
   Retirement is delete-plus-replace, not pure deletion. *(Adopted into §2.)*
2. **Orphaned product modules:** `routines.py`, `priorities.py`, `reports.py`, `fitness.py`,
   `runtime_bootstrap.py`, `completion.py` have zero non-test importers — PRD §28's "routine
   editor" and "priority registry" have no user surface at all. *(Adopted into §3.)*
3. **Duplicated permission machinery** across ~12 modules; smoke clients bypass
   `permissions.py`. *(Adopted into §6.)*
4. **Weaker-than-reported approval gates on two rails:** the standalone Gmail/Todoist smoke
   clients check the approval reference for *presence only*
   (`phase14c_todoist_live_smoke.py:101` — `bool(optional_string(...))`), not even the
   exact-match of the wide-net runner. Any non-empty string "approves" a live send.
   *(Strengthens §5's instruction-as-boundary conclusion.)*
5. **Three independent not-ready mechanisms**, not one: beyond `pre_live_readiness`'s
   structure (this report §5), `mvp_readiness.py:20` hardcodes `MVP_READINESS_STATUS =
   "not_ready"` as a module constant, and `phase14c_wide_net_readiness_rollup.py:96` pins
   `ready_for_live_execution` in a required-false field set. All three would need code
   changes to ever say ready — under a process whose rules forbid exactly such changes
   without an approval that the reports themselves say is pending. The circularity is
   triple-locked.

**This report's findings not in Codex's** (complementary, not contradicted): the
`config=None` trace showing no production caller can even reach the satisfiable branch of
`evaluate_pre_live_readiness` (§5.1–5.2); `READY` requiring all-rails-disabled at the
evaluator level (`pre_live_readiness.py:273` — Codex read the same lines and framed it as
"ready-for-inertness," an agreeing framing); the PR-history drift signature (§4); the
done-definition and packet-shape proposals (§7, §9 — outside Codex's charge).

**Framing difference (real, worth naming):** Codex enumerates the Phase-14C rollup's
remaining gates (Calendar connector wiring, fresh approval, transcripts, crosschecks) as
"technical/evidential blockers" — i.e., it answers *within* the existing process frame.
This report's position is one level up: those gates guard a smoke rehearsal, not the product;
satisfying every one of them still ships nothing (no cadence engine, no content generator,
no product rails — §3). Both are true; the re-baseline should treat Codex's list as the
definition of what the *old* frame wanted, and §7 as what done actually means.

## 9. Recommended Phase 1 packet shapes (input to the ROADMAP)

Low-blast-radius first, rails inert throughout; every packet = branch = audit unit:

1. **P-CLEAN-01 — kill the dead skeletons + loose artifacts** (delete `personalos/`, `app/`,
   the 33 `PR##_AUDIT.md`; archive superseded docs to `archive/`). Pure deletion, high signal.
   The `phase14c_*` module family deletes with it (no product importers — verified);
   the readiness/status modules that `today.py`/`cli.py` consume are **not** in this packet —
   they get replaced behind a lean status interface in P-GOV-01 (the §8 correction).
2. **P-GOV-01 — governance overlay**: GOVERNANCE_MANIFEST (protected: `migrations/**`,
   `.env*`, live-rail modules, safety policy), lean STATUS, QUALITY_GATES (the real 861-test
   command), RISK_REGISTER folding SAFETY_POLICY content, PRD v0.3 (product spec, changelog
   amputated), packet ROADMAP from this report.
3. **P-DESIGN-01 (G6) — routine model + cadence engine design** — the one real design
   decision; deserves its own gate before code.
4. **P-CORE-0x — cadence engine + due-today computation** (+ schema migration, G4-flagged).
5. **P-BRIEF-01 — template briefing generator** over real state through the existing pipeline.
6. **P-RAIL-0x — one thin live adapter per rail** (Todoist first), ledger-guarded, inert until
   its own G5 activation packet.
7. **P-DEBT-0x — split `cli.py`/`state.py` by domain; unify the 12-fold duplicated
   permission evaluator into one shared module; wire or delete the orphaned modules**
   (mechanical, batched, low-stakes).

## 10. Ways this audit could be wrong

- Both auditors read code statically plus the test suite; neither drove the dashboard/CLI
  surfaces end-to-end. A "real" verdict on e.g. synthesis apply rests on its tests.
- `settings_json` blobs could carry more de-facto routine semantics through external usage
  than the code reveals; only Chris's actual usage would show this. (Mitigated: no cadence
  *consumer* exists in code regardless of what the blobs hold.)
- The claim "no code path constructs a filled readiness config" is a repo-wide grep; a
  filled config supplied out-of-repo (operator JSON) was not found but cannot be fully
  excluded. The `READY`-requires-all-rails-disabled finding stands regardless (it's in the
  evaluator itself).
- LOC/module counts of "process vs product" involve judgment at the margins (e.g.
  `pre_live_readiness.py` is counted as process; its permission substrate has product value).
- Fable (this auditor) and the future Builder are same-family; the Codex cross-audit and the
  harness's per-packet audit are the designed backstops for shared blind spots.
