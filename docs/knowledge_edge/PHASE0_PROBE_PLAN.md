# Knowledge Edge — Packet 0C Bounded Probe Plan (EDGAR + YouTube only)

Status: proposed procedure, for execution post-merge under direct Conductor-session
supervision only. Owner: Builder (P-KE-00C) · Date: 2026-07-16
Zero network requests, zero credentials touched in producing this document (hard
constraint) — this is a plan to be executed later, by a human-supervised session, not a
script run by this packet.

---

## 1. Why this document exists, and why it is narrower than the original Packet 0C

The amendment's own Packet 0C scope (`PRD_AMENDMENT_KNOWLEDGE_EDGE.md` §"Packet 0C —
Live probe and golden fixtures") named a broader thin-pull set, including one week of
earnings-calendar data from Financial Modeling Prep. **D-PO-019 removes FMP entirely**
(`governance/living/agent-writable/DECISIONS.md`) and states directly: "Packet 0C's probe
scope drops FMP and probes EDGAR + YouTube only." This document is that narrowed,
concrete procedure for the two providers that remain in scope for the bounded live probe.
It does not re-litigate or replace the podcast/channel-upload portions of the original
Packet 0C description — it specifies the EDGAR and YouTube requests only, per D-PO-019's
explicit instruction.

---

## 2. Execution constraints (non-negotiable)

- **Who runs this:** the Conductor session, directly and supervised, in real time. **Not
  any packet builder, and not scheduled** — no automation, no cron, no unattended run.
- **When:** post-merge of this packet only. Nothing in this document is executed by the
  packet that writes it.
- **Scope:** read-only; shadow-scope (no production database, no production writes);
  uses only the Session 1-approved credentials/UA strings already in `.env.local`
  (SEC EDGAR user-agent per D-PO-018 item 4; YouTube Data API key per Session 1's
  external-access bundle).
- **Transcript:** results (request, response status, and a redacted/summarized body —
  not necessarily the full raw payload if it contains anything provider-policy-sensitive)
  saved under `audits/knowledge-edge/` by the supervising session itself, not by this
  packet.
- **STOP rule, no exceptions:** any non-200 response, any unexpected redirect, or any
  quota warning **halts the probe immediately**. No retries. The supervising session
  records what stopped it and why, and the probe resumes only in a fresh, deliberately
  re-initiated supervised session — never auto-retried inline.

---

## 3. EDGAR probe — ≤3 GETs

**Fair-access ceiling:** SEC's published fair-access rule permits up to 10 requests/second
per user agent. This probe uses **≤3 requests total**, far under that ceiling — it is not
attempting to characterize the ceiling, only to confirm the mechanism works end-to-end.

**Target company:** Apple Inc. (roster Group A, `PHASE0_ROSTER.md` §3.1), CIK
`0000320193` — chosen because it is unambiguous, large, and files standard 10-K/10-Q
forms (unlike ASML's 20-F/6-K path, which is not being probed here).

**Request:**

```
GET https://data.sec.gov/submissions/CIK0000320193.json
User-Agent: <PERSONALOS_RAIL_KE_EDGAR_USER_AGENT from .env.local>
```

**Success criteria (all must hold):**
1. HTTP 200 response.
2. Response body parses as valid JSON.
3. The parsed JSON contains a recent-filings list (the `filings.recent` structure EDGAR's
   submissions endpoint documents) that is non-empty.

**Bound:** if the first request succeeds, at most 2 further GETs may be made — e.g. a
second roster company's submissions endpoint, or a specific filing document referenced
from the first response — strictly to confirm the pattern generalizes, not to begin bulk
collection. 3 total is the hard ceiling for this probe, not a target to reach.

---

## 4. YouTube probe — 1 `search.list` call

**Request:** exactly one call to the YouTube Data API v3 `search.list` endpoint.

```
GET https://www.googleapis.com/youtube/v3/search
  ?part=snippet
  &q=<one Lane B Market Voice person's name>
  &type=video
  &maxResults=5
  &key=<PERSONALOS_RAIL_KE_YOUTUBE_API_KEY from .env.local>
```

The `q` value is one representative Lane B (Market Voices) tracked person — chosen at
probe time by the supervising session, not fixed in this document, since the exact Lane
B roster is defined elsewhere (`PRD_AMENDMENT_KNOWLEDGE_EDGE.md` §8.2) and this probe
only needs one representative name to confirm the mechanism.

**Success criteria (all must hold):**
1. HTTP 200 response.
2. Response body parses as valid JSON and contains an `items` array (may be empty if the
   query genuinely returns no results — that is a valid response shape, not a failure —
   but the array key itself must be present).

**Quota note:** `search.list` has historically cost 100 quota units per call
(`PHASE0_PROVIDERS_AND_ACCESS.md` §5 already flags this as **TBC, reconfirm at Session
1** — not independently re-verified live by any prior packet). This one-call probe is the
first opportunity to close that TBC: the supervising session records the actual unit cost
and the actual current default daily project quota as shown in the Google Cloud Console
at probe time, and updates `PHASE0_PROVIDERS_AND_ACCESS.md` §5's TBC marker in a
follow-up edit once confirmed (out of scope for this probe-plan document itself, which
only specifies the request).

---

## 5. Combined STOP conditions

Either sub-probe halts independently of the other — an EDGAR failure does not block
attempting the YouTube probe, and vice versa, but each individually stops on its own
first failure per §2's STOP rule. Neither probe retries on failure. Both are one-shot,
supervised, read-only, and produce a saved transcript before the supervising session
ends.
