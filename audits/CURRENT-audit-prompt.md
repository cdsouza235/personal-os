# CURRENT audit prompt — packet P-CLEAN-02 — ITERATION 3 (scoped B1 closure)

Packet: `P-CLEAN-02` · Iteration: 3 · Date: 2026-07-07
Auditor: Codex, per `audits/AUDITOR-BRIEF-codex.md`.
Branch: `packet/P-CLEAN-02`. Your iteration-2 verdict: **reject** solely on **B1**
(a Conductor signoff artifact inside the agent packet commit); you verified F1 and F2
CLOSED. This is a SCOPED pass: verify B1's closure and any regression from it. Do not
re-open F1/F2 (spot-checks welcome, full re-derivation not required).

## B1 closure to verify
1. `main` carries the signoff as a dedicated Conductor-record commit (`cc819db`,
   "P-CLEAN-01 Conductor sign-off record (G4/G1)") created in the Conductor's merge flow —
   separate from any packet work — followed by the P-CLEAN-01 merge (`1772f40`).
2. `main` has been merged INTO `packet/P-CLEAN-02`, so
   `git diff main...HEAD -- audits/signoffs/` is now EMPTY — the signoff is no longer part
   of the packet diff; the packet contributes no approval-record content whatsoever.
3. The packet diff (`git diff main...HEAD`) otherwise matches iteration 2's verified shape
   (75 files; process-layer deletions + rail-state surface + manifest rider).
4. Suite still green at 421; run the QUALITY_GATES steps.
5. Note for your report: the Conductor confirms authorship of the signoff file (he created
   it directly, before the agent's r2 commit swept it up; the sweep was the agent's
   staging error, now a recorded Builder convention in STATUS.md — staging always excludes
   `audits/signoffs/`).

## Output
Overwrite `audits/CURRENT-audit-report.md`; append to `audits/AUDIT-LOG.md`.
Verdict: **accept / accept_with_conditions / reject**. Short closure report is fine.
Bootstrap attestation + ways-this-could-be-wrong as always. Same constraints (read-only
except your two files; never open `.env.local`; no live paths).
