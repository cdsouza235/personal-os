# HUMAN_GATES.md — Personal OS

The Conductor (Chris) decides every gate below on **orchestrator-run evidence** (or, until
B-00 lands, evidence produced by the pinned manual-loop procedure) — never on an agent's
prose summary of its own work. Approvals are recorded as committed sign-off files at
`audits/signoffs/<packet>-<gate>-signoff.md`, **authored and committed by the Conductor
only** — `audits/signoffs/**` is a manifest-protected path; ANY agent write there is a
blocker finding, and an approval file whose git author is not the Conductor is void
(interim unforgeable-store stand-in until B-00's OS-permissioned store). Chat-borne
approvals are void (`POLICY_EXCEPTIONS.md`).

Honest expectation: zero risk flags + clean evidence = a seconds-long decision. Any risk
flag, open auditor concern, or high iteration count = expect deeper review.

## Continuous operation — no routine check-ins

The agent driving packets does not pause to ask "should I continue?" between packets, after
recording a decision, after a retry, or at any other point that is not one of the gates below.
Routine sequencing through the roadmap, re-running a packet after a fix, updating living
status docs, and recording an already-made Conductor decision all happen without a check-in.

The **only** interruption points are:
1. One of the gates in the table below (an actual `required_gates` entry on a real run).
2. A **genuine judgment call** — real, irreducible ambiguity or a tradeoff only Chris can
   resolve (a design choice with no clearly-better option, a factual mismatch between what
   Chris remembers and what the repo actually shows, a destructive git operation that needs
   Chris's own exact wording naming the target).

This does not soften any gate. Sign-offs still go through the unforgeable channel only,
authored and committed by Chris himself; destructive operations still wait for Chris's own
explicit confirmation naming the target; G-GOV still requires Chris's own read of what rule
changed and why. It only removes interruptions that were never gates to begin with.

| Gate | Trigger in this repo | Digest must show |
|---|---|---|
| **G0 Plan** | First packets of a phase; any high-stakes or vague packet | Plan + scope + non-goals; planning is read-only |
| **G1 Merge** | Every packet (Codex accept + fresh digest) | Evidence, SHAs, coverage, all gates |
| **G2 Money** | New paid provider (e.g. OpenRouter budget), projected budget breach | Cost + ledger impact |
| **G3 Secrets** | `.env*` touched, credential-name surfaces changed, or secret-like content in any diff/log | What + why; blocked until sanitized |
| **G4 Irreversible** | Any `migrations/**` change that drops/alters data; deletion packets (P-CLEAN); production DB path activation | Blast radius + rollback |
| **G5 External / LIVE RAILS** | ANY code path that can write Todoist / send Gmail / write Calendar / call a model API becoming reachable, and separately EVERY activation of such a path | What, reversibility, kill procedure. **Rail activation is always its own packet + its own G5. Never bundled.** |
| **G6 Design** | Design decisions (first: the routine model, P-DESIGN-01) | Decision + options + reco + reversibility; lands in DECISIONS.md + ARCHITECTURE.md before implementation resumes |
| **G7 Dependency** | Any new package / lockfile / `pyproject.toml` change (repo currently has zero runtime deps — keep it that way by default) | Package + license + risk |
| **G-GOV** | Any file in `GOVERNANCE_MANIFEST.yaml` | What rule changed + why |
| **G-RECOVERY** | Fail-safe fired (crash / dirty tree / unparseable output) | Constrained recovery choices |

## Standing high-stakes defaults (SPEC §4)
Security, auth, permissions-model, schema/data-model changes are high-stakes by default.
For Personal OS specifically, additionally always high-stakes: anything touching the
permission evaluator, `path_safety.py`, ledger/idempotency semantics, or a protected path in
the manifest.

## The activation ladder (replaces the old readiness machinery)
Live rails go live one at a time, each through: adapter packet (inert, G5-flagged for
reachability) → soak evidence (no-send parallel run producing would-have-sent artifacts) →
**activation packet** (config flip + G5 sign-off + kill procedure verified) → bounded live
period → review. `not_ready` is retired as a concept; what exists instead is "rail X:
inert | soaking | live" recorded in STATUS.md, each transition Conductor-gated.
