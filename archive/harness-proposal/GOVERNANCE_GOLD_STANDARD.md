# Personal OS — Gold-Standard Governance (a PROPOSAL for consideration)

> **Status: proposal, not a mandate.** This is a recommended *target shape* derived from the MIS
> harness's own governance (`~/dev/harness-orchestrator/governance/`). Weigh it against the Phase 0
> findings — adopt, adapt, or reject any part. The point is to give Phase 1 a concrete starting
> shape instead of a blank page, **not** to pre-commit the project to a structure before the audit
> tells us what Personal OS actually needs. Where this doc guesses at Personal OS specifics (module
> paths, gate commands), it marks them `<VERIFY>` — the findings audit resolves them against the
> real repo.

---

## 1. The one honest caveat up front

The harness governance is **architecturally** gold-standard, but it was built to govern a
self-auditing AI-agent orchestrator building safety-critical containment. It carries meta-machinery
a productivity app does not need, and its own audit trail sprawled to 137 files. **Copy the
architecture, not the file count.** Below is a *leaner* instantiation tuned to an app that has
dangerous live rails into real accounts.

## 2. What makes it gold-standard (the principles worth keeping)

1. **Law / State / Trail separation, enforced by location.**
   - *Law* (rulebook) lives in `governance/` — changing it trips a gate.
   - *State* (STATUS / DECISIONS / OPEN_QUESTIONS) lives in `governance/living/` — updated under
     rules, verified by git-diff, but it is state, not law.
   - *Ledgers / loop-state* are writer-restricted to the orchestrator (agents cannot touch them).
   - *Audit trail* is separate again.
   - Personal OS today mixes all of these into a 77KB `STATUS.md` + ~30 loose `PR##_AUDIT.md` files.
2. **The closure manifest.** `GOVERNANCE_MANIFEST.yaml` enumerates *every* governed file; any change
   to one requires the governance gate; the manifest governs itself. *Exhaustiveness is the whole
   point — a governed file not on the list is a hole.* This is the single biggest thing Personal OS
   lacks: no mechanical line between "code you can change freely" and "law that needs a gate."
3. **Machine-read config, not prose.** Rules that only live in prose are theater. Gates, protected
   paths, and budgets should be machine-consumable.
4. **Templates define the contract.** One packet shape, one audit shape — uniform every time. The
   two templates in this bundle are near-verbatim from the harness because they are app-agnostic and
   genuinely excellent (`allowed_paths`/`forbidden_paths` wire scope-drift; the audit's mandatory
   "ways this could still be wrong" kills rubber-stamping).
5. **Single-writer per file.** No two actors write the same file. Kills merge ambiguity and
   accountability gaps.
6. **Risk register = protected paths + fail-toward-high-stakes.** Anything unmatched PROMOTES to
   high-stakes; it never defaults to routine. The harness's portable triggers already model Personal
   OS: *"email / external-API path → high-stakes"* and *"migration / schema change → high-stakes."*

## 3. What to deliberately DROP (harness-internal, not app-relevant)

- `LOOP_DOCTRINE.md` and the §11 self-auditing-orchestrator framing.
- Third-reviewer machinery as a default (deferrable; Personal OS can start with Builder + Auditor).
- `orchestrator/**` / `adapters/**` / `fake_agents/**` in the manifest — that's *harness* code, not
  Personal OS code.
- The double `governance/ROADMAP.md` + `projects/<name>/ROADMAP.md` layer — a single app needs one
  authoritative ROADMAP (see §6, the where-it-lives decision).

## 4. Recommended file set (lean — most content already exists in your docs)

This is **re-shaping into machine-enforced structure**, not writing from scratch. Personal OS already
has `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/SAFETY_POLICY.md`, `docs/PRODUCTION_DB_POLICY.md`,
`AGENTS.md` — most of this folds in.

| File | Action | Notes |
|---|---|---|
| `GOVERNANCE_MANIFEST.yaml` | **NEW** | The closure. The #1 missing piece. (Skeleton in this bundle.) |
| `templates/PACKET_TEMPLATE.md` | **COPY** | App-agnostic. (Adapted copy in this bundle.) |
| `templates/AUDIT_TEMPLATE.md` | **COPY** | Same. |
| `QUALITY_GATES.md` | **ADAPT** | Your real commands: `<VERIFY>` ruff / mypy / pytest invocations. |
| `RISK_REGISTER.md` (+ protected paths) | **ADAPT — load-bearing** | Protected: `migrations/**`, `.env*`, live-rail modules, auth/config. |
| `SECURITY.md` | **FOLD from `docs/SAFETY_POLICY.md`** | Add the *inert-rails-until-gated* law + egress posture. |
| `DATA_POLICY.md` | **FOLD from `docs/PRODUCTION_DB_POLICY.md`** | Real-account PII/DB — more important here than in the harness. |
| `HUMAN_GATES.md` | **ADAPT — load-bearing** | The **live-rail activation gate** is the marquee human gate. |
| `DEPENDENCY_POLICY.md` | **NEW (light)** | New-dependency rule. |
| `AGENTS.md` | **REWRITE** | Reshape your existing one to harness form (stop conditions, single-writer). |
| `ROADMAP.md` | **REPLACE** | The re-baselined packet queue — output of Phase 0/1. |
| `RUNBOOK.md` | **NEW** | Rollback / restore / incident — matters with real accounts. |
| `living/{STATUS,DECISIONS,OPEN_QUESTIONS}.md` | **NEW** | A *lean* STATUS replaces the 77KB one. |
| audit trail | **NEW convention** | `audits/<packet>/{prompt,report,log}.md` — per-packet subdirs, NOT a flat pile (the harness's sprawl lesson). |

Net: ~10 governed files + 2 templates + 3 living files + a clean audit convention. Gold standard
*for an app* — closure + separation + templates preserved, meta-weight shed.

## 5. Personal-OS-specific emphasis (because of the live rails)

The load-bearing files here are `RISK_REGISTER`, `SECURITY`, `DATA_POLICY`, and `HUMAN_GATES` — more
than in a typical app. The whole `inert / no-send / not_ready` posture you hold today by documented
convention should become **machine-enforced law**:
- **Protected paths** (any change → high-stakes gate): `migrations/**`, `.env*`, and the modules that
  talk to Gmail / Google Calendar / Todoist / OpenClaw and hold credentials/config. `<VERIFY exact
  paths under src/personalos during Phase 0>`.
- **The inert-rails law** in `SECURITY.md`: live rails stay inert; activation is a *deliberate*
  high-stakes human gate, never a default, never reachable from a routine packet.
- **Egress posture**: builds/evidence run with network severed; no real API call happens inside the
  loop unless a rail is explicitly gated live.

## 6. The one pivotal structural decision (please settle this deliberately)

**Where does Personal OS's governance physically live?**

- **Model A (recommended) — harness-side overlay.** Personal OS stays a *target repo* (code / tests /
  migrations). Its law lives in the harness repo under `projects/personal-os/`, and the harness
  targets `~/dev/personal-os`. This is the pattern the harness was built for and just proved with
  MIS; the portable rulebook stays single-source and reusable — the entire thesis of the harness.
- **Model B — self-contained `governance/` inside the Personal OS repo.** Governance travels with the
  code, but you duplicate the portable rulebook and it drifts from the harness's copy.

Lean: **A.** Wrinkle to note: the Phase 0 session works *inside* `~/dev/personal-os`, so under Model A
the governance-authoring lands in the *harness* repo, not here. This is exactly what **B-00
(onboarding)** must formalize — so the clean sequence is: Phase 0 produces findings and drafts the
governance *content* (using the shapes in this bundle); *where it physically lands* is settled when
B-00 is built. The file paths in this bundle are written repo-relative and are agnostic to A vs B.

## 7. How to use this bundle

- `GOVERNANCE_GOLD_STANDARD.md` — this doc.
- `GOVERNANCE_MANIFEST.example.yaml` — a starting-point manifest with `<VERIFY>` placeholders.
- `templates/PACKET_TEMPLATE.md`, `templates/AUDIT_TEMPLATE.md` — adapted, near-ready to copy.

Treat all of it as a **first draft to react to**, not a checklist to execute. The findings audit
comes first; the governance shape should be *informed by* what Phase 0 finds (especially the real
module layout and the honest definition of "done"), not imposed ahead of it.
