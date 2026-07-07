# Phase 0 Findings Audit — Independent Auditor Brief (Codex)

You are an **independent adversarial auditor**. Your job is to find what is true about this
codebase, not to agree with anyone. You are penalized for conclusions without located evidence.
Assume the documentation may overstate, understate, or mis-describe the code. The code is the
ground truth; the docs are claims to be verified.

## Context (minimum necessary)

- Repo: `/Users/coldstake/dev/personal-os`, branch `main` @ `58fc27e`. Audit this checkout.
- Product: a private, local-first personal productivity OS (routines, priorities, briefings,
  reports) with gated execution rails into the owner's real Todoist, Google Calendar, and Gmail,
  plus an "OpenClaw" runtime layer. SQLite state, migrations, large unittest suite.
- The canonical PRD is `docs/PRD.md` (v0.2). Section 28 lists the V1 acceptance criteria.
  Section 1 states the product vision. `docs/SAFETY_POLICY.md` states the safety posture the
  repo claims to hold (`readiness.status=not_ready`, `inert_report_only=true`,
  `live_rails_activated=false`).
- The project owner is commissioning a re-baseline. Your audit is one of two independent inputs
  to a findings report. You have NOT been shown the other auditor's conclusions, and you should
  not try to guess them.

## Your charge — answer these five questions with file:line evidence

1. **PRD-vs-code capability matrix.** For each `docs/PRD.md` §28 V1 acceptance criterion, and
   for the major product surfaces of §1 (routines, priorities, briefings, Todoist, Calendar,
   Gmail, composer, dashboard, reports, synthesis import): classify as
   `real` (working implementation with meaningful tests), `partial`, `scaffold-only`
   (interfaces/templates/fakes but no live-capable path), or `absent`. Name the implementing
   module(s) for each verdict.

2. **Dead / orphaned / duplicated code.** Inventory: modules under `src/personalos/` that no
   non-test code imports; the top-level `personalos/` directory; duplicated logic; code that
   exists only to validate other code's report formats. Quantify (files, approximate LOC).

3. **Safety posture: enforced or asserted?** The repo claims live rails are inert and
   fail-closed. Trace the actual enforcement: where in the code is a live external write
   possible, and what mechanically prevents it (flag checks? credential absence? approval
   references? nothing)? Distinguish (a) enforcement in code that would fail closed under a
   hostile or careless caller, (b) enforcement by convention/documentation only, and
   (c) surfaces that already performed live writes (check git history / docs for evidence of
   past live smoke runs). Be precise about which rails (Todoist / Gmail SMTP / Google Calendar /
   OpenRouter / OpenClaw) have which class of protection.

4. **What actually blocks `readiness.status=not_ready`?** Trace how readiness is computed
   (e.g. `src/personalos/pre_live_readiness.py`, `phase14c_wide_net_readiness_rollup.py`, and
   anything else feeding it). Enumerate the concrete conditions that would have to change for
   the system to report ready. Then answer honestly: are the remaining blockers technical
   (missing code), evidential (missing test runs), or decisional (a human choice that no code
   change can satisfy)? If the readiness machinery itself can never reach `ready` by
   construction, say so and show why.

5. **Design quality for the stated goal.** The owner's core requirement is a system that stays
   flexible as routines change or new routines enter his life. Assess: the routine/priority
   data model's extensibility (state-driven vs hardcoded), coupling between product core and
   phase/process machinery, the size and cohesion of `state.py` and `cli.py`, and whether the
   test suite tests behavior or documentation phrasing. Name the 3–5 worst structural liabilities
   for future change, with evidence.

## Constraints

- **Read-only with one exception:** write your report to `PHASE0_CODEX_AUDIT.md` in the repo
  root. Do not modify any other file, do not commit, do not touch anything outside the repo.
- Do not load credentials, contact external services, or execute any CLI path that could
  perform a live action. Running the unittest suite is allowed.
- Protected paths `/Users/coldstake/PersonalOS` and `/Users/coldstake/.openclaw` are out of
  bounds.

## Required report structure (in `PHASE0_CODEX_AUDIT.md`)

1. `## Verdict summary` — one paragraph, the single most important finding first.
2. `## Q1 Capability matrix` — table: criterion/surface | verdict | evidence (module, line refs).
3. `## Q2 Dead & duplicated code` — inventory with quantities.
4. `## Q3 Safety enforcement classes` — per rail: enforced-in-code / convention-only / already-ran-live, with the exact guarding code cited.
5. `## Q4 The honest readiness answer` — the enumerated blockers and their class (technical/evidential/decisional).
6. `## Q5 Structural liabilities` — ranked, with evidence.
7. `## Ways this audit could be wrong` — mandatory; name your own blind spots.

Located, justified findings only. A claim without a file reference is an opinion, not a finding.
