# Phase-A Checkpoint Prompt — Fable (phase-end seat)

Date posted: 2026-07-07 · Builder seat: Fable session (bootstrap; per-packet cross-family
audit by Codex throughout) · **Independence: run this in a FRESH session that did not
build Phase A.** Read `audits/PHASE-END-AUDITOR-BRIEF-fable.md` first — your standing
rules, including the correlated-blind-spot lens (§9): Builder and you are both Anthropic;
your seat exists to catch what an Anthropic reasoner and the OpenAI per-packet auditor
might both miss. The class to hunt: doctrine-as-implementation.

## The phase under review
Phase A (clean state), three packets, all Codex-accepted + Conductor-signed + merged:
- **P-GOV-01** (`229f974`): governance overlay (manifest, kit, PRD/ARCH v0.3, ROADMAP,
  briefs, templates, secret/env gates); legacy docs archived; doc-phrase test class
  retired (887→809). Codex: rework → adopt_with_fixes → conditions_closed.
- **P-CLEAN-01** (`1772f40`): dead skeleton trees deleted. Codex: accept, zero findings.
- **P-CLEAN-02** (`d5bc829`): process layer retired from code (32 modules, 27 test files,
  CLI purge); fail-closed rail-state surface replaces readiness machinery; manifest
  shrink rider. Codex: reject×3 (fail-open rail state; approval-provenance sweep; dirty
  protected path) → accept. Declared delta 809→421.

## Phase-boundary definition (audits/test-strategy.md → Phase A)
The repo contains exactly: product code + kept substrate (permissions, ledgers,
path_safety, scheduler-sim, state) + governance kit + audits + migrations + tests. One
rulebook, one STATUS. Verify sanction-list fidelity + no product regression +
today/cli/dashboard run without the readiness layer.

## Your checkpoint charge (beyond re-running what Codex ran)
1. **Drive the real thing.** Run the CLI surfaces (workflows/status/today/dashboard
   render, briefing preview, demo no-send-e2e) against a scratch DB. Does the product
   actually work post-surgery, end to end?
2. **Attack the rail-state surface** (`src/personalos/status.py`) — the new safety
   posture core. Codex's probes are in `audits/AUDIT-LOG.md` history; find what BOTH of
   us missed. Interesting angles: import caching across consumers, the private-formatter
   residual Codex noted, subclass/serialization tricks, whether any consumer path renders
   posture without passing through `create_rail_state_report()`.
3. **Hunt survivors.** Any enforcement-relevant code that DIED (vs. the claim that only
   asserting/reporting code died)? Any process-layer remnant that survived (vocabulary,
   helpers, dead config)? Any hole in the governance kit a Builder could walk through in
   Phase B (the next phase touches migrations + the cadence engine)?
4. **Verify the audit trail itself**: sign-offs at `audits/signoffs/` (3 records,
   Conductor-authored), AUDIT-LOG completeness, merge commits referencing the right gates.
5. **Attestation:** no GOVERNANCE_MANIFEST-listed file changed beyond each packet's
   sanctioned targets across the whole phase (`git diff 58fc27e..main` — the full
   re-baseline diff — is in scope for this).

## Output
Write ONLY `audits/phase-A-phase-end-fable-report.md`. Resolve to **sign_off / hold**
(hold = named, located conditions). Mandatory `WAYS_THIS_REVIEW_COULD_BE_WRONG` including
the same-family caveat. The Conductor commits your report; you never run git.
