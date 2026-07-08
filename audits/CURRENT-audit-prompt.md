# CURRENT audit prompt — packet P-CLEAN-01 (dead skeletons) — iteration 1

Packet: `P-CLEAN-01` · Iteration: 1 · Date: 2026-07-07
Auditor: Codex, per `audits/AUDITOR-BRIEF-codex.md`.
Branch: `packet/P-CLEAN-01` (you are auditing this checkout; base = `main` @ `229f974`).

## The packet (governance/ROADMAP.md → P-CLEAN-01)
Deletion-only: remove the two dead skeleton trees — top-level `personalos/` (8 `.gitkeep`
placeholder dirs shadowing the real `src/personalos` package) and `app/` (`api/`,
`dashboard/` `.gitkeep` only). Tier: G4 (deletion) — reversible via git history.
- allowed_paths: `personalos/**`, `app/**` (+ the living STATUS update and this prompt,
  standard packet overhead)
- forbidden_paths: everything else — especially `src/**`, `tests/**`, `migrations/**`,
  `governance/**` (excl. living), `GOVERNANCE_MANIFEST.yaml`

## Acceptance criteria (audit against these; sanctioned-deletion lens per your brief)
1. The diff vs `main` is EXACTLY: 10 deleted `.gitkeep` files (8 under `personalos/`,
   2 under `app/`) + the living STATUS.md update + `audits/CURRENT-audit-prompt.md`.
   Anything else in the diff is a scope-drift finding.
2. No source, test, config, packaging (`pyproject.toml`), or doc file references either
   deleted tree (derive your own grep; note `src/personalos/**` is the REAL package and
   must be untouched — do not confuse the two).
3. QUALITY_GATES all green on this branch (run all six steps yourself): 809 tests ×2,
   hygiene finds, gitleaks, env checks.
4. Bootstrap attestation: no GOVERNANCE_MANIFEST-listed file changed.

## Output
Overwrite `audits/CURRENT-audit-report.md`; append one line to `audits/AUDIT-LOG.md`.
Verdict: accept / accept_with_conditions / reject, with located findings and mandatory
"ways this review could be wrong". Same constraints as always (read-only except your two
files; never open `.env.local`; no live paths).
