# CURRENT audit prompt — packet P-CLEAN-02 — ITERATION 4 (scoped B2 closure)

Packet: `P-CLEAN-02` · Iteration: 4 · Date: 2026-07-07
Auditor: Codex, per `audits/AUDITOR-BRIEF-codex.md`.
Branch: `packet/P-CLEAN-02`. Your iteration-3 verdict: **reject** solely on **B2** (the
checkout carried an unstaged DELETION of `audits/signoffs/P-CLEAN-01-G4-G1-signoff.md`);
you accepted the committed-graph B1 closure and the packet shape. This is a SCOPED pass:
verify B2's closure only.

## What happened (for your provenance record)
The deletion was Builder tooling fallout, not intent: during the B1 fix the Builder ran
`rm` on the signoff (believing it untracked — it had become tracked via the very sweep B1
flagged), then merged main; the new staging convention (exclude `audits/signoffs/`) kept
the deletion out of commits but also left it sitting dirty in the worktree.

## B2 closure to verify
1. The file was restored via `git checkout -- audits/signoffs/` — i.e. from HEAD, whose
   copy descends from main's Conductor-record commit `cc819db`. Verify:
   `audits/signoffs/P-CLEAN-01-G4-G1-signoff.md` exists on disk, content is byte-identical
   to `git show cc819db:audits/signoffs/P-CLEAN-01-G4-G1-signoff.md` (a RESTORE of
   Conductor content, not agent authorship).
2. `git status --short` prints nothing at your audit start (before your own report writes).
3. `git diff main...HEAD -- audits/signoffs/` remains empty.
4. Run the QUALITY_GATES steps (421 green expected).
5. Housekeeping check: `audits/AUDIT-LOG.md` — confirm your r1/r2/r3 P-CLEAN-02 lines are
   all present; if any relaunch/capacity failure dropped one, note it and append a
   reconciling line (you are the log's sole writer).

## Output
Overwrite `audits/CURRENT-audit-report.md`; append to `audits/AUDIT-LOG.md`.
Verdict: **accept / accept_with_conditions / reject**. Short report fine. Attestation +
ways-wrong as always. Same constraints (read-only except your two files; never open
`.env.local`; no live paths).
