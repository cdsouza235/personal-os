# Knowledge Edge — Earnings-Coverage Company Roster (D-PO-019)

Status: **seed list, pending Conductor confirmation at this packet's gate** (mirrors the
launch role appendix pattern — proposed here, ratified by Chris before Packet 3A builds
against it). Owner: Builder (P-KE-00C) · Date: 2026-07-16
Zero network requests, zero credentials touched in producing this document (hard
constraint). Every figure below is either cited from the Conductor-verified candidate
data supplied for this packet or explicitly marked TBC — none are drawn from or
"corrected" against training-data recall.

---

## 1. Why this document exists

D-PO-016 chose Financial Modeling Prep (paid) for earnings-calendar coverage. At Session
1 (2026-07-15) Chris verified FMP's actual pricing — earnings/corporate-events access
requires a ~$50/month tier — and rejected it as over budget (**D-PO-019**,
`governance/living/agent-writable/DECISIONS.md`). The replacement, defined by Chris in
that same decision, is a bounded, rule-defined company roster whose earnings dates are
discovered for free via SEC EDGAR + official IR pages (both already approved — see
`PHASE0_PROVIDERS_AND_ACCESS.md` §2 banner and §6). This document is that roster: the
membership rule, the candidate seed list, the dedupe rule, and the quarterly refresh
procedure.

---

## 2. The roster rule (verbatim from D-PO-019)

> a **bounded, rule-defined company roster** — top 10 Nasdaq-100 companies + top 3
> publicly listed crypto-native companies + top 5 WGMI-ETF (CoinShares/Valkyrie Bitcoin
> Miners) constituents, all ranked by market cap (~18 names, overlap deduped) — with the
> roster **refreshed quarterly**.

D-PO-016's original anti-scraper rationale targeted an unbounded 20-40-company universe;
a fixed ~18-name roster with quarterly human refresh does not reopen that rationale
(D-PO-019 states this explicitly) — this roster stays bounded by construction, not by
convention.

---

## 3. Candidate seed list (pending Conductor confirmation)

All figures below are **Conductor-verified via web search 2026-07-15, pending final
confirmation at the roster gate** unless marked TBC. Source and as-of date given per
group, per the rule's own "ranked by market cap" instruction.

### 3.1 Group A — Top 10 Nasdaq-100 by market cap

Source: marketcap.company NDX ranking, 2026-07.

| Rank | Ticker | Company | Market cap |
|---|---|---|---|
| 1 | NVDA | NVIDIA | $4.60T |
| 2 | AAPL | Apple | $4.02T |
| 3 | GOOGL | Alphabet | $3.81T |
| 4 | MSFT | Microsoft | $3.52T |
| 5 | AMZN | Amazon | $2.42T |
| 6 | AVGO | Broadcom | $1.65T |
| 7 | META | Meta Platforms | $1.64T |
| 8 | TSLA | Tesla | $1.46T |
| 9 | ASML | ASML Holding | $450B |
| 10 | NFLX | Netflix | $386B |

**Filing-mechanism note (ASML):** ASML is Nasdaq-listed and part of the NDX ranking, but
files with the SEC as a foreign private issuer (Forms 20-F/6-K, not 10-K/10-Q) — its
earnings-date discovery still works via the same SEC EDGAR + official IR page path used
for every other roster company, just against different form types. No special-casing
needed beyond that.

### 3.2 Group B — Top 3 publicly listed crypto-native companies by market cap

Source: companiesmarketcap.com + The Block, 2026-07.

| Rank | Ticker | Company | Market cap |
|---|---|---|---|
| 1 | COIN | Coinbase | ~$41.5B |
| 2 | MSTR | Strategy (MicroStrategy) | ~$34.8B |
| 3 | CRCL | Circle | ~$25.7B |

**Exclusion note:** Robinhood (HOOD) and Block (XYZ/formerly SQ) are crypto-*adjacent*
(they offer crypto trading/products alongside a broader non-crypto business), not
crypto-*native* (a business whose core product is crypto/blockchain infrastructure) —
excluded by the rule as written. Recorded here so the quarterly refresh doesn't drift
into including them without an explicit rule change.

### 3.3 Group C — WGMI-ETF (CoinShares Bitcoin Mining ETF) candidate pool

Source: stockanalysis.com/etf/wgmi/holdings, as of 2026-07-13.

| Ticker | Company | Fund weight |
|---|---|---|
| CIFR | Cipher Mining | 17.88% |
| HUT | Hut 8 | 11.15% |
| IREN | IREN | 10.33% |
| — | Keel Infrastructure | 9.79% |
| MARA | MARA Holdings | 5.03% |
| HIVE | HIVE Digital Technologies | 4.72% |
| CLSK | CleanSpark | 4.69% |
| RIOT | Riot Platforms | 4.36% |
| BTDR | Bitdeer Technologies | 4.31% |

**Discrepancy — read before using this table:** the roster rule ranks WGMI constituents
by **company market cap**; the table above ranks by **fund weight** (WGMI's own portfolio
allocation), because that is what the source publishes and per-company market caps were
not verified at task-authoring time. Fund weight and market cap are different
quantities and can rank differently (fund weight reflects the ETF's position-sizing
methodology, not raw company size). **This table is the candidate pool, not the
final top-5** — the actual top 5 WGMI-derived roster rows are **determined by market-cap
ranking at Conductor confirmation**, drawn from this pool of 9. Do not treat the
fund-weight order above as the roster order.

---

## 4. Dedupe rule

A company appearing in more than one group occupies **one row** in the final roster,
attributed to whichever group has the highest priority in this fixed order:

```
Group A (Nasdaq-100)  >  Group B (crypto-native)  >  Group C (WGMI)
```

Applied to the seed data above: no overlaps exist between Group A, Group B, or the Group
C candidate pool as currently listed, so the seed roster is expected to land at the full
~18 names (10 + 3 + 5) once Group C's final five are market-cap-ranked. If a future
quarterly refresh produces an overlap (e.g. a Group C constituent grows into Group A),
the higher-priority group's row wins and the lower-priority group's slot is backfilled
from the next-ranked candidate in that group.

---

## 5. Effective-dating (mirrors the launch role appendix pattern)

Every roster row carries an **added date** and, when applicable, a **removed date** —
the same effective-dating discipline used for the Session 1 launch role appendix
(D-PO-018 item 5: role, occupant, effective date). A company leaving the roster at a
quarterly refresh is not deleted from history; its row is closed with a removed date so
past coverage remains attributable to "this company was on the roster from X to Y." No
row in this seed list has a removed date yet; every row below is a proposed initial
addition:

| Ticker | Group | Added | Removed | Status |
|---|---|---|---|---|
| NVDA, AAPL, GOOGL, MSFT, AMZN, AVGO, META, TSLA, ASML, NFLX | A | pending confirmation | — | proposed |
| COIN, MSTR, CRCL | B | pending confirmation | — | proposed |
| 5 of {CIFR, HUT, IREN, Keel Infrastructure, MARA, HIVE, CLSK, RIOT, BTDR}, by market cap | C | pending confirmation | — | proposed, final 5 TBC (§3.3) |

The `added`/`removed` columns are populated with actual calendar dates only once Chris
confirms the roster at this packet's gate (mirroring how the launch role appendix's
effective dates were supplied and ratified by Chris, not invented by the packet that
proposed it).

---

## 6. Quarterly refresh procedure

- **Who:** the Conductor (Chris), not any packet builder — same gate discipline as the
  §10.3 source/channel allowlist (`PHASE0_PROVIDERS_AND_ACCESS.md` §6: additions are
  never fetched from "solely because it passed an automated verification step").
- **When:** within 2 weeks after each calendar-quarter close (aligned to earnings
  seasons, per D-PO-019's own reasoning for choosing quarterly over semi-annual).
- **How:**
  1. Re-rank each group by current market cap from public sources (the same source
     types used for this seed list: an index/market-cap ranking site for Group A, a
     crypto-market-cap tracker for Group B, WGMI's published holdings plus per-company
     market caps for Group C).
  2. Diff the re-ranked list against the current roster (this document's live table).
  3. Every add or remove is an explicit Conductor acknowledgment before it takes
     effect — no automatic promotion/demotion, matching the source-allowlist gate
     pattern exactly (`PHASE0_PROVIDERS_AND_ACCESS.md` §6: "never silent or automatic").
  4. On acknowledgment, update the effective-dating table (§5): close the removed row's
     `Removed` date, open the added row's `Added` date.
- **Scope discipline:** the refresh only re-ranks within the fixed rule (top 10 / top 3 /
  top 5, by market cap, deduped) — it is not an opportunity to change the rule itself
  (group sizes, ranking metric, or dedupe priority) without a new Conductor decision,
  same as how the §10.3 allowlist's verification step establishes legitimacy but a
  separate acknowledgment closes the gate for each specific change.

---

## 7. Confirmation status

**The entire seed list in §3 and the effective-dating table in §5 are pending Conductor
confirmation at this packet's gate.** Nothing in this document authorizes Packet 3A to
build against these company identifiers as final until Chris confirms — same pattern as
the Session 1 launch role appendix (D-PO-018 item 5), which Packet 1A only seeded from
once ratified.
