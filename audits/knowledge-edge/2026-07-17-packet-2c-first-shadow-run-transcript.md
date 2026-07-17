# Packet 2C First Shadow Run — Transcript (Day 1 of the sampling window)

Executed 2026-07-17 (UTC) by the Conductor session per
docs/knowledge_edge/PACKET_2C_FIRST_SHADOW_RUN.md, post-merge of P-KE-2C (56eea76)
and P-KE-2D (2fd3bce).

## Run log
1. `shadow bootstrap` → 9/9 sources re-verified+active from the 2A transcript (twice:
   the shadow DB was found WIPED before the second scan — see Collision below).
2. First scan (pre-2D): status partially_completed — 3 healthy / 6 failed with
   `podcast_rail_live_fetch_response_too_large`; 503 items from the 3. The refusal
   machinery was correct; the cap was mis-tuned vs the verified real feeds → fixed as
   micro-packet **P-KE-2D** (evidence-justified cap + Content-Length preflight; Codex
   accept_with_conditions; Conductor-gated; merged).
3. Post-2D rescan (fresh DB after the wipe): **status completed, 9/9 healthy, 1,703
   media items**, shadow DB only, zero external writes, all §14.4 fences held.
4. `sample-freeze` → REFUSED: "sampling window must span at least 14 consecutive
   calendar days (Part 3); got 1". Correct per PHASE0_THESIS_MATCHING Part 3 — the
   ground-truth sample is a wall-clock deliverable. **Day 1 = 2026-07-17; earliest
   freeze = 2026-07-30**, requiring a bounded supervised scan each calendar day.

## COLLISION (named finding for the Phase 2 checkpoint): shadow DB vs harness runs
AD-4 places the shadow DB at repo-local `var/shadow/`; the harness wipes untracked
repo files on every packet run (observed: the P-KE-2D run destroyed the day's shadow
DB between scans). A 14-day accumulation cannot coexist with ANY packet run under
this layout. Remediation micro-packet (P-KE-2E, launched 2026-07-17): relocate the
shadow DB outside the repo with a path-safety-sanctioned amendment to AD-4's path,
BEFORE the sampling window meaningfully accumulates.

— Conductor session (Fable seat)
