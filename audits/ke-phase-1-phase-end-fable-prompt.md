# Checkpoint prompt — Knowledge Edge Phase 1 phase-end (Fable, fresh session)

Read `audits/PHASE-END-AUDITOR-BRIEF-fable.md` first; this prompt scopes YOUR checkpoint.
You are in a fresh session by design: the session that operated Phase 1's packets did
not and must not write this report. Resolve to **sign_off / hold** with located
conditions in `audits/ke-phase-1-phase-end-fable-report.md` (the ONLY file you write).

## Scope

The Knowledge Edge Phase 1 tree on `main`: packets P-KE-1A (state layer + migrations
00017-00021 + seeds), P-KE-1B (queue engine + fixture adapter contracts), P-KE-1C
(dashboard + CLI). Diff range: from the commit before the `merge packet/P-KE-1 into
main (P-KE-1A)` merge (585e165's first parent) through `d57d51d` (the P-KE-1C merge).
Authorities: `docs/knowledge_edge/PRD_AMENDMENT_KNOWLEDGE_EDGE.md` (esp. §8, §10.5,
§11, §14.4, §19 Phase 1 acceptance), `PHASE0_ARCHITECTURE_DECISIONS.md` AD-1/AD-4/AD-5,
`PHASE0_TRACEABILITY.md` Phase-1 rows, `PHASE0_ROSTER.md`, DECISIONS.md D-PO-018/019.

## Phase guarantee to verify end-to-end (drive it, don't read about it)

Fixture-rung daily loop: build the four-lane queue from fixture adapters end to end;
re-run the same window (idempotent — no duplicates); caps enforced; deterministic
(identical inputs twice → identical snapshot). Amendment §19 Phase 1 + PHASE0_PLAN §2.

## This phase's specific soft spots (probe these adversarially; history says so)

1. **The §8.3 ambiguous rule, BOTH directions, EVERY surface.** This rule cost three
   rework rounds: iteration 3 promoted ambiguous items to P0 by lane membership;
   the fix then silently DROPPED them from the queue snapshot; the CLI then summarized
   them into counts. Construct unknown-duration approved-source segments in every lane
   and verify: never P0, never absent, always visibly demoted WITH ambiguity reason —
   in the queue snapshot, the dashboard render, AND the CLI human output. Derive your
   own boundary cases (threshold-exactly, threshold-minus-one-second, unknown vs zero
   duration, ambiguous items competing with caps).
2. **urllib.parse containment (Conductor-authorized carve-out, G-GOV 2026-07-16).**
   Exactly one file (`engine/canonicalize.py`) may import exactly `urllib.parse`.
   Verify the recursive AST scanner in the migration test actually catches: bare
   `import urllib`, `urllib.request`, an alias smuggle (`from urllib import parse as
   p` — is THAT caught or allowed? decide if the gate's letter matches its intent),
   and any new file importing urllib.parse. Positive-control: plant a violation
   in-session, confirm the guard fires, revert.
3. **Seed fidelity as data, not diff.** Query the seeded DB: five role seats with
   correct occupants/effective dates (Warsh 2026-05-22; Selig 2025-12-22 — this date
   was wrong once; Cook with Ternus succession effective 2026-09-01 — verify the
   query flips correctly on 2026-08-31 vs 2026-09-01); WGMI companies present as
   CANDIDATES not confirmed; no company/person/date beyond D-PO-018/PHASE0_ROSTER.md.
4. **Engine purity + single write path (correlated blind-spot class).** No wall-clock/
   random in classification/ranking (time is a parameter — prove by calling with a
   fixed `now` twice); state writes only through the state API (the Codex trail
   caught one raw-SQL test bypass — hunt for survivors on the production path);
   network purity of the entire package (the tripwire test is itself in-scope for
   your review).
5. **Disabled-mode byte-identity.** KE mode `disabled` → existing dashboard output
   byte-identical; prove it yourself, not via the packet's own test alone.
6. **Migrations 00017-00021**: purely additive against a pre-phase DB (apply to an
   empty pre-phase schema; verify no existing-table ALTER/DROP; checksum tracking
   intact; delete-and-remigrate clean).

## Context you build on (do not repeat)

Codex per-packet trail: 1A two rounds (Selig date), 1B six rounds (P0 rule both
directions, raw-SQL test bypass, urllib arbitration — third-reviewer override then
Conductor authorization), 1C two rounds (CLI summarizing). Infrastructure noise
(ECONNRESET rounds) was harness-side (egress relay defect, fixed + audited in the
harness repo) — packet content was unaffected, but treat any residual oddity in the
tree as in-scope. Suite baseline: 567 pre-phase → verify the current green count
matches the final declared delta exactly.

## Mandatory closing sections

`WAYS_THIS_REVIEW_COULD_BE_WRONG` (include the same-family caveat: builder and you
are both Anthropic; Codex per-packet audits are the standing cross-family check) and
the manifest attestation (no manifest-listed file changed beyond sanction in the
phase range).
