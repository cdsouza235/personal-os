# Test Strategy — Personal OS re-baseline (SPEC §16.2 artifact 3)

Suite-wide rules live in `governance/QUALITY_GATES.md` (canonical commands; network-free;
no doc-phrase tests; test-weakening triggers). This file defines per-phase acceptance tests
and the **phase-boundary definition** — what must be true to call the phase done and
trigger the Fable checkpoint.

## Phase A — clean state
Acceptance tests: suite green after each deletion packet with the declared test-count
delta matched exactly; grep-proofs (no reference to deleted paths/modules; no
`import personalos.phase14c`, `mvp_readiness`, `pre_live_readiness` outside archive);
manifest parse + closure check (every listed file exists).
**Boundary:** repo contains exactly: product code + kept substrate (permissions, ledgers,
path_safety, scheduler-sim, state) + governance kit + audits + migrations + tests. One
rulebook, one STATUS. Fable: verify sanction-list fidelity + no product regression +
today/cli/dashboard run without the readiness layer.

## Phase B — the engine
Acceptance tests: table-driven engine matrix — every cadence type × missed-behavior ×
representative boundaries (week wrap, month wrap, DST transitions, rotation-group wrap,
completion-history edge cases: empty, duplicate-day, out-of-order); property: engine is
pure (same inputs → same outputs; no clock/I-O access verified by construction); migration
carry-over test (existing routine rows survive P-CORE-01 with semantics preserved);
end-to-end editor round-trip (create/edit/disable via CLI and dashboard → due-set changes
accordingly).
**Boundary:** Chris can define every routine in PRD §3.1's seed list as state and the
engine produces the correct due-set for arbitrary dates. Fable: adversarial engine attack
with self-derived expected outputs; invariants 1–2 verified on real code.

## Phase C — the loop (inert)
Acceptance tests: `personalos run morning` in no-send mode produces would-have-sent
artifacts (task plan + briefing) from real state, writes ledger rows, is idempotent on
re-run within a day (dedupe proof), and fails closed with rails inert.
**Boundary:** seven consecutive manual no-send mornings produce correct artifacts (the
soak evidence G5 consumes). Fable checkpoint rides with the MVP boundary below.

## Phase D — rails
Acceptance tests per adapter packet: fake-client contract tests; gating-order tests
(each of permission/ledger/rail-state/credentials individually unsatisfied → refusal +
ledgered refusal + NO network attempt — verified with a socket-guard fixture); dedupe
against ledger history; failure taxonomy (4xx/5xx/timeout → fail closed, no retry storms).
Activation packets: live verification script bounded to marked test objects; kill drill
evidence.
**MVP boundary (after TD-02 + GM-02 + SCHED-02):** seven consecutive unattended mornings,
correct Todoist tasks + Gmail briefing, zero manual repair, kill procedures drilled.
Fable: full-cycle adversarial drive; rail-reachability hunt from every surface.

## Phase E — debt
P-DEBT-01: permission-evaluator unification proven by behavioral equivalence tests
(old-vs-new decision matrix) before deletion of the copies. P-DEBT-02: mechanical splits
keep the suite green with zero semantic diffs (import-graph proof).

## Standing rule
Every packet's expected tests are named in its ROADMAP entry or G0 plan **before**
building (this file is the floor, not the ceiling). Evidence of record is runner-executed.
