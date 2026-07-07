# Kickoff prompt — bring Personal OS under the MIS harness (paste into a fresh Claude Code session)

---

You are picking up a project handoff. Read this whole message, then **read the real files it points at before doing anything** — this summary is a map, not the territory. Don't take my word for the repo states; verify them.

## Who I am and what I'm asking
I'm Chris. I've just finished building a governance/orchestration harness ("the MIS harness") and I want to use it, for the first time, on a real project of mine (Personal OS). This session's job is **Phase 0: an evidence-backed findings audit of Personal OS**, which becomes the input to a clean re-baseline. Do NOT start building or restructuring code yet. Audit and plan first.

## Two repos are in play

**1. The harness — `~/dev/harness-orchestrator`** (just reached v0.4 DONE)
- What it is: a *deterministic* orchestrator + governance kit for driving AI coding agents through a contained, audited build loop with human oversight. Core bet: **independent adversarial audit — not operator judgment — is what makes correctness real.**
- How it works (the model you'll apply to Personal OS): a **packet = a branch = one auditable unit of work**; the **orchestrator owns git** (the agent gets a git-free sandbox export, writes into it, the orchestrator commits + merges); **no model output can influence the merge decision** (SPEC §11 — the route is deterministic); changes flow build → evidence-in-sandbox → deterministic route → human gates → **machine-invoked cross-family audit** → merge. Human = "Conductor" (approves gates, high-stakes stops).
- **The relevant win:** the per-packet auditor relay is now **machine-invoked with no human relay** (a cross-family Codex audit runs headlessly). That is the exact toil that burned me out hand-driving Personal OS.
- **The relevant gap (B-00):** the user-facing CLI (`orchestrator/cli/run.py` → `build_production_drivers`) currently *fail-closes* on live agents; the proven live wiring (`build_live_drivers` + the sandbox-backed runner) was only exercised through the P-01 proving/attestation harness, not a product command. So before the harness can *drive* an external repo, a small **B-00 "production CLI / project onboarding"** packet must wire `main()` → `build_live_drivers` + an agent/config surface. **B-00 is harness code (`orchestrator/**`), so by SPEC §11 circularity it is hand-built + Codex/Fable audited — NOT dogfooded.** B-00 only gates the *building* phase; the audit + governance work below does not need it.
- **To understand the harness, read (in this order):** `SPEC-v0.4.md` (esp. §5 containment, §9 correlated blind spot, §11 trusted core, §16 doctrine), `projects/mis/BOOTSTRAP_RUNBOOK.md` (roles + cadence), `audits/mis/P-01_merge-signoff.md` (what "done + proven" looks like), `governance/living/agent-writable/DECISIONS.md` and `.../STATUS.md`, `audits/mis/AUDITOR-BRIEF-codex.md` + `audits/mis/PHASE-END-AUDITOR-BRIEF-fable.md` (the two auditor seats), and `orchestrator/cli/run.py` (the CLI + the B-00 gap).
- **Roles/discipline to carry over:** Builder = Claude (you) on Opus; per-packet Auditor = **Codex** (OpenAI, cross-family, machine-invoked); Phase-End Auditor = **Fable** (Anthropic, relayed manually); Conductor = me. Commit/push ONLY when I ask. Single-writer governance files. Never let the built agent edit its own rulebook.

**2. The project — `~/dev/personal-os`** (the thing to re-baseline)
- What it is: my private, local-first productivity OS — routines, priorities, briefings, reporting, and **gated execution rails into my REAL Todoist, Google Calendar, and Gmail** (+ an "OpenClaw" runtime layer). SQLite runtime state; migrations; Mac Mini host; private repo `cdsouza235/personal-os`.
- State (verify, don't trust): ~291 commits; the live package is `src/personalos/` (~62 `.py` files); there's a dead/empty top-level `personalos/` skeleton shadowing it; migrations + a large test tree. It's stuck at **Phase 14-C**, `not_ready`, `inert_report_only=true`, `live_rails_activated=false` — it has been circling live-activation readiness for many phases without shipping.
- Governance today: heavily *documented* but the wrong shape — `docs/PRD.md` (v0.2), `docs/ARCHITECTURE.md`, `docs/SAFETY_POLICY.md`, `docs/ROADMAP.md`, `AGENTS.md`, ~25 phase/readiness docs, a ~77KB `STATUS.md`, and ~30 loose untracked `PR##_AUDIT.md` files. Process-by-narrative, not machine-enforced gates. That narrative process is what made me the exhausted relay and let the project stall at "readiness."
- **Read:** `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/SAFETY_POLICY.md`, `docs/ROADMAP.md`, `AGENTS.md`, skim `STATUS.md`, and the real code under `src/personalos/`. Check test health (`python -m pytest` — report pass/fail/collection state honestly).

## The decision already reached (don't relitigate — build on it)
**Re-baseline in place.** Keep the code (291 commits of real work; do NOT restart from scratch). Throw out the *governance shape* (doc sprawl → harness-standard machine-enforced governance). Let a findings audit produce the new ROADMAP. Neither blind-continue nor scorched-earth.

**Safety reframe (important):** Personal OS is NOT intrinsically low-risk — it has live rails into my real accounts. Today the `inert / no-send / not_ready` line is held by documented convention. The harness enforces that same line *structurally* (egress severed before evidence, sandboxed builds, mandatory human gates for high-stakes). Keep all live rails **inert** through the build phase; activation is a deliberate high-stakes gate I approve, never a default. This safety-fit is a big reason the harness is the right tool to get this unstuck.

## The plan (do them in order; this session = Phase 0)
0. **Findings audit (THIS session — architect work, not the build loop, low-risk).** Read the PRD + ARCHITECTURE + SAFETY_POLICY + the real `src/personalos` code + test health. **Machine-invoke Codex** for an independent cross-family audit of the codebase against the PRD (see the mechanism below). Produce a **findings report**: what's solid, what's drift (e.g. the dead skeleton, the 77KB STATUS, the loose PR audits), the *honest* answer to **what is actually blocking `not_ready`**, and **what "done / MVP" even means here** (my read: it lost the shipping plot). No code changes.
1. **New governance overlay + PRD delta + packet ROADMAP.** Convert sprawl → harness-standard: a `GOVERNANCE_MANIFEST` (protected paths: migrations, `.env*`, the live-rail modules), a ROADMAP decomposed into packets, per-seat audit briefs, a lean STATUS. Fold the good existing docs in; retire the rest.
2. **B-00 onboarding CLI** in the harness repo (hand-built + Codex/Fable audited; §11 — not dogfooded).
3. **Harness-driven build** of Personal OS, low-blast-radius packets first (kill the dead skeleton, de-sprawl), rails inert until a deliberate gate.

## Machine-invoked Codex (the no-relay cross-family audit)
The `codex` CLI is currently OFF `$PATH` but ships in the desktop app bundle. Invoke it directly:
```
/Applications/Codex.app/Contents/Resources/codex --ask-for-approval never exec --sandbox workspace-write "<audit instructions>"
```
Notes: it can take several minutes — allow a long timeout (up to ~10 min). Auth is ChatGPT OAuth in `~/.codex/auth.json` (subscription; no marginal spend). Point it at a written brief and have it audit the real code against `docs/PRD.md`.

## A governance proposal exists — but it is Phase 1 input, NOT a Phase 0 constraint
There is a bundle at `~/dev/personal-os/_harness_proposal/` (`GOVERNANCE_GOLD_STANDARD.md`, a skeleton `GOVERNANCE_MANIFEST.example.yaml`, and two adapted templates) proposing what gold-standard governance could look like for Personal OS. **It is for consideration, not a mandate.** Do NOT let it shape the Phase 0 findings — run the findings audit **unbiased first**, then read the bundle as *Phase 1* input when we design the re-baselined governance. If you reverse-engineer findings to fit the template, you've defeated the point. (One item in it — "where governance physically lives," Model A vs B — is deferred to B-00 and is the Conductor's call, not yours.)

## Start here
Confirm you've read the harness model and the Personal OS state from the actual files (quote a couple of specifics back so I know it's grounded, not assumed). Then propose the shape of the Phase 0 findings audit — what you'll examine, what you'll ask Codex to audit — and, once I say go, run it and deliver the findings report. Ask me the genuine open questions (e.g. what "done" means to me, whether any doc is load-bearing) rather than guessing.
