# Packet 0C Bounded Probe — Supervised Execution Transcript

Executed: 2026-07-15 ~20:20 PDT, post-merge of P-KE-00C (`70daef6`), by the Conductor
session (Fable seat) under Chris's standing authorization for this session's
merge→push→probe sequence. Procedure: `docs/knowledge_edge/PHASE0_PROBE_PLAN.md`
(merged, Codex-accepted). Read-only throughout; shadow scope; no retries performed.

## Halt record (STOP rule honored)

The first probe initiation HALTED per §2's STOP rule: EDGAR returned HTTP 403.
Root cause was ours, not SEC's: `.env.local` had been silently deleted from the repo
working tree by the orchestrator's git staging during the P-KE-00C build iterations
(the harness owns the repo tree and cleans untracked files), so the request carried no
User-Agent — SEC's fair-access rules reject anonymous automated requests, exactly as
documented. The provider behaved correctly; the approved request was never actually
transmitted. Disposition: credentials restored from the session record; canonical copy
relocated OUTSIDE the repo to `~/.config/personal-os/ke.env` (0600) with `.env.local`
recreated as the working copy; a fail-closed guard added to the probe commands (empty
UA/key aborts BEFORE any request leaves the machine). The probe was then deliberately
re-initiated as a fresh supervised pass, recorded below. Standing lesson: secrets must
never live only as untracked files inside the orchestrator-owned repo tree.

## EDGAR probe — PASS (2 of ≤3 GETs used)

| # | Request | Result |
|---|---|---|
| 1 | `GET data.sec.gov/submissions/CIK0000320193.json` (Apple), approved UA | HTTP 200; valid JSON; entity "Apple Inc."; `filings.recent` non-empty (1000 entries); latest filing Form 4, 2026-06-17 |
| 2 | `GET data.sec.gov/submissions/CIK0001045810.json` (NVIDIA), approved UA | HTTP 200; valid JSON; entity "NVIDIA CORP"; `filings.recent` non-empty (1004 entries); latest 10-Q dated 2026-05-20 |

All three success criteria met on both requests. Stopped at 2 requests (ceiling 3 —
"not a target to reach"). Rate: 2 requests total, far under the 10 req/s fair-access
ceiling.

## YouTube probe — PASS (exactly 1 `search.list` call)

Request: `search.list`, `part=snippet`, `q=Tom Lee` (Lane B roster §8.2 representative),
`type=video`, `maxResults=5`, Session 1 key (search.list-restricted). Result: HTTP 200;
valid JSON; `items` array present with 5 entries; results plausibly on-target (top item:
a CNBC International Live segment titled "S&P 500 to hit 8,000 by year end: Tom Lee").

## Quota TBC — still open (deliberately)

`PHASE0_PROVIDERS_AND_ACCESS.md` §5's TBC (search.list unit cost / default daily
project quota) is NOT closed by this transcript: the API response does not expose quota
figures, and the Google Cloud Console was not inspected during this pass. The
historically documented figures (100 units/call against a 10,000-unit/day default)
remain the working assumption. Closing the TBC requires the Conductor viewing the
console's quota page (screenshot), then a follow-up edit to §5 — flagged as an open
item for the next Conductor terminal session; it blocks nothing before Packet 2B.

## Verdict

Both mechanisms work end-to-end with the Session 1 credentials/UA under the approved
scope limits. Packet 0C's bounded probe (EDGAR + YouTube, per D-PO-019) is COMPLETE.
