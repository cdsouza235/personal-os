# CURRENT audit prompt — packet P-GOV-01 — ITERATION 3 (scoped condition-closure pass)

Packet: `P-GOV-01` · Iteration: 3 · Date: 2026-07-07
Auditor: Codex, per `audits/AUDITOR-BRIEF-codex.md`.
Your iteration-2 verdict was **adopt_with_fixes** with three conditions. This is a SCOPED
one-round closure pass (§16.6): verify ONLY the three conditions and any regression the
fixes themselves introduced. Do not re-open the settled findings.

## Conditions to verify
- **N1 (high):** `.gitleaks.toml` no longer allowlists `archive/`; run the canonical
  command (`gitleaks detect --no-git --source . --config .gitleaks.toml --exit-code 9`)
  yourself — it must pass with the whole tree, archive included, in scope.
- **N2 (medium):** doc-phrase test retirement is now unambiguously P-GOV-01's
  (ROADMAP P-GOV-01 entry + QUALITY_GATES test-integrity note); P-CLEAN-02 claims only
  the process-layer modules + their remaining tests.
- **N3 (low):** PR-audit archive count corrected to 32 (PR93–PR124) and matches
  `archive/pr-audits/` contents.

## Output
Overwrite `audits/CURRENT-audit-report.md` (a short closure report is fine); append one
line to `audits/AUDIT-LOG.md`. Verdict: **conditions_closed_ready_for_gate** or
**conditions_not_closed** (state which, with evidence). Include the bootstrap attestation
and "ways this review could be wrong". Same constraints as before (read-only except your
two files; never open `.env.local`).
