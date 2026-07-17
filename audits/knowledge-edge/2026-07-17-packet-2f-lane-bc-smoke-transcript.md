# Packet 2F Lane B/C Supervised Smoke — Transcript + FORMAL WINDOW START

Executed 2026-07-17 ~19:00 UTC by the Conductor session per
docs/knowledge_edge/PACKET_2F_YOUTUBE_LANE_BC_SUPERVISED_SMOKE.md, post-merge of
P-KE-2F (9db552a), after the Conductor's §10.3 channel acknowledgment at the 2F gate.

## Channel RSS probes (one GET each, no key)
| Channel | Result |
|---|---|
| CNBC Television | PASS — 200, 15 entries, live segment titles parsed |
| Bloomberg Television | PASS — 200, 15 entries |
| Bloomberg Technology | PASS — 200, 15 entries |
| Yahoo Finance | PASS — 200, 15 entries |

## Person-search row
ke-source-youtube-person-search flipped on the strength of the P-KE-2B smoke's
mechanism verification (see 2026-07-16 transcript session #2: search.list 200/5 items)
— no additional live call made.

## Flips — sanctioned path
All five rows trial→active + endpoint verification recorded
(verified_by conductor:2026-07-17-lane-bc-smoke) via state.registries helpers in the
shadow DB. Active sources now 15 (9 podcasts + 4 channels + person-search + EDGAR).

## ★ FORMAL SAMPLING WINDOW — DAY 1 = 2026-07-17 (D-PO-021)
Every lane is now live in shadow: A (9 podcasts), B/C (4 network channels +
person-search), D (EDGAR earnings mechanism). Per D-PO-021 the 14-consecutive-day
all-lanes window starts TODAY with the 16:30 scheduled scan (D-PO-022 launchd job).
Earliest sample freeze: **2026-07-31**. Rehearsal scans of 2026-07-17 (pre-flip)
are excluded from the formal window per the decision's own terms.

— Conductor session (Fable seat)
