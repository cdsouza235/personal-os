# Knowledge Edge — Packet 3A IR/Webcast Vendor-Domain List: Assembly Frame

Status: FRAME ONLY — every concrete domain in this document is **TBC-Conductor**.
Owner: Builder (P-KE-3A) · Date: 2026-07-17
Zero network requests, zero credentials touched in producing this document (hard
constraint) — this document defines the *structure* a future assembly pass fills in
and the *verification recipe* that assembly must follow; it does not itself perform
that assembly.

---

## 1. Why this document exists, and why it contains no domains

`PHASE0_PROVIDERS_AND_ACCESS.md` §6's "IR/webcast vendor-domain list" checklist item
states the gate this document exists to set up, verbatim:

> **Packet 3A assembles and verifies** the concrete Tier A/B IR-root and
> redirect-target domain list against official sources, as its own deliverable...
> **The assembled list then returns to the Conductor as its own explicit, named
> approval gate — "Packet 3A vendor-domain-list approval" — before any live fetch is
> made against any domain on it.**

`PHASE0_PLAN.md`'s P-KE-3A row names the same gate explicitly and is unambiguous
about what this packet may and may not do: assemble the *structure*, not authorize
any *specific* domain. This packet has zero network access (the same hard
constraint every Knowledge Edge planning/framing document in this repo states), so
it cannot itself visit any company's investor-relations page to discover its actual
webcast-vendor redirect target — attempting to do so from training-data recall would
be exactly the kind of invented, unverified data this project's house discipline
forbids (`PHASE0_ROSTER.md`'s own header states the same rule for company
identifiers). Every concrete domain below is therefore `TBC-Conductor`: a named,
structured slot for a value only a future, network-capable, Conductor-supervised
assembly pass may fill in — never a placeholder this packet quietly resolves itself.

**What Session 1 already approved, and what it did not:** per §6, Session 1 approved
the redirect *mechanism and rules only* — a redirect is permitted solely from an
already-approved official IR page, never to a freestanding new domain, and any
destination not on an approved list is quarantined as `Link pending (unknown
vendor)` per amendment §8.4. Session 1 did NOT approve any specific domain; that
approval is exactly the async gate this document's assembled list, once filled in,
returns to the Conductor for.

**What this document is not:** it is not `earnings_calendar.py`'s own deliverable.
That adapter (this packet's other main deliverable) is EDGAR-only per D-PO-019 and
never constructs a request against any IR/webcast domain — see that module's own
docstring, point 3. Populating this list and fetching against it is P-KE-3B's job
(`sec_edgar.py` for filing enrichment, plus a future IR/webcast resolver), and P-KE-3B
is itself explicitly blocked on this gate landing first (`PHASE0_PLAN.md`'s P-KE-3B
row: "blocked on P-KE-3A's vendor-domain-list approval landing first — no live
redirect fetch before that gate clears").

---

## 2. Structure — one slot per roster company

For every company migration 00026 seeds (the D-PO-019 roster, `PHASE0_ROSTER.md`
§3 — 13 `roster_status='confirmed'` companies today, plus the 9-company
`wgmi_candidate_pool` once the Conductor picks its final five), the assembled list
must eventually carry one row of this shape:

| Field | Meaning | Source of truth | Status in this document |
|---|---|---|---|
| `company_id` | Matches `ke_companies.company_id` | Migration 00017/00026 | Known today (this doc lists all 22 below) |
| `ir_root_url` | The company's own official investor-relations root URL | Official company site, verified by a human or a Conductor-supervised fetch — never guessed | **TBC-Conductor** |
| `ir_root_verified_as_of_date` | When `ir_root_url` was last confirmed reachable and official | Same verification pass | **TBC-Conductor** |
| `webcast_vendor_domain(s)` | The domain(s) `ir_root_url` is observed to redirect to for live/replay webcast links (e.g. a third-party IR-webcast platform) | Observed during the same verification pass — a redirect target is recorded, not assumed | **TBC-Conductor** (zero or more per company; a company may use more than one vendor across event types, or none if it hosts its own webcast) |
| `redirect_rule_note` | Free text: any company-specific redirect quirk (e.g. "webcast subdomain differs from IR root subdomain") | Verification pass | **TBC-Conductor** |
| `approval_status` | `pending` \| `approved` \| `rejected` | Conductor, at the named gate (§4) | `pending` for every row until the Conductor approval lands |

This table's row count is bounded by construction: exactly the roster's own
company count (D-PO-019's own bounded-roster rationale, `PHASE0_ROSTER.md` §2),
never an open-ended crawl of arbitrary IR pages. A `webcast_vendor_domain` value is
a bare registrable domain (e.g. `investor.example-vendor.com`), matching the
granularity `_HostConfinedRedirectHandler`-style host comparisons already use
elsewhere in this codebase (`podcasts.py`/`youtube.py`/`earnings_calendar.py`'s own
`_extract_host`) — not a full URL, not a wildcard.

### 2.1 Roster company slots (company_id only — every other column TBC-Conductor)

**Group A — nasdaq100_top10 (confirmed):** `ke-company-nvda`, `ke-company-aapl`,
`ke-company-googl`, `ke-company-msft`, `ke-company-amzn`, `ke-company-avgo`,
`ke-company-meta`, `ke-company-tsla`, `ke-company-asml`, `ke-company-nflx`.

**Group B — crypto_native_top3 (confirmed):** `ke-company-coin`, `ke-company-mstr`,
`ke-company-crcl`.

**Group C — wgmi_candidate_pool (candidate; slot reserved, not yet roster-confirmed):**
`ke-company-cifr`, `ke-company-hut`, `ke-company-iren`,
`ke-company-keel-infrastructure`, `ke-company-mara`, `ke-company-hive`,
`ke-company-clsk`, `ke-company-riot`, `ke-company-btdr`. Per §9.4's "no company is
promoted automatically," a Group C row's `ir_root_url` should not be assembled and
verified ahead of that company's own roster confirmation — assembling IR-vendor
data for a company that never makes the final five would be wasted verification
effort against a company Lane D may never actually poll. The recommended order is:
roster confirmation first (a separate, already-described Conductor gate,
`PHASE0_ROSTER.md` §6), IR-root assembly for that company second.

---

## 3. Verification recipe — how a future assembly pass fills in §2's TBC slots

This is the recipe, not its execution. Every step below requires live network
access this packet does not have and must be run by a Conductor-supervised session,
mirroring `PACKET_3A_EARNINGS_SUPERVISED_SMOKE.md`'s own supervision discipline:

1. **Locate the official IR root.** For each company, identify the investor-relations
   root URL from the company's own primary domain (e.g. navigating from the
   company's known corporate homepage to its "Investors" section) — never from an
   unverified search result alone. Record the URL and the date it was confirmed
   reachable.
2. **Identify the webcast mechanism.** From the IR root, locate the events/webcast
   page (amendment §8.4's link-hierarchy items 2–3: "official company event detail
   page," "official investor-relations events page"). If that page's live/replay
   webcast link redirects to a different registrable domain than the IR root itself,
   record that domain as a `webcast_vendor_domain` candidate. If it does not redirect
   (the company hosts its own webcast), record zero vendor domains for that company
   — this is a valid, expected outcome, not a gap.
3. **Cross-check, don't single-source.** Where practical, confirm a vendor-domain
   observation against more than one company's IR page redirecting to the same
   vendor (a small number of third-party IR-webcast platforms serve most public
   companies) — this raises confidence the domain is a real recurring vendor rather
   than a one-off observation artifact, without requiring an exhaustive survey.
4. **Record, don't approve.** The assembly pass populates §2's table and sets every
   row's `approval_status` to `pending`. It does NOT flip any row to `approved` —
   that is exclusively the Conductor's action, at the named gate below.
5. **Return to the Conductor as one batch.** Per §6's own "never silent or
   automatic" framing (the same discipline the §10.3 source/channel allowlist and
   the roster quarterly-refresh procedure already use), the assembled table is
   presented to the Conductor as a single reviewable batch, not approved
   piecemeal or in the background.

---

## 4. The named approval gate — "Packet 3A vendor-domain-list approval"

This is the async, human-in-the-loop checkpoint `PHASE0_PLAN.md`'s P-KE-3A row and
`PHASE0_PROVIDERS_AND_ACCESS.md` §6 both name explicitly. Gate language, restated
here as the operative rule for every future packet that reads this document:

- **What is approved:** each individual `(ir_root_url, webcast_vendor_domain)` pair
  in §2's assembled table, one row's `approval_status` at a time (or as an explicit
  reviewed batch) — never the whole list implicitly because the assembly pass
  "looked reasonable."
- **What approval unlocks:** P-KE-3B's redirect-following resolver may fetch from an
  `approved` row's `webcast_vendor_domain` (subject to Session 1's already-approved
  redirect mechanism/rules — same-host-or-approved-vendor-only, HTTPS-only, no
  arbitrary new domain). A `pending` or `rejected` row is quarantined as `Link
  pending (unknown vendor)` exactly as amendment §8.4 specifies, and stays
  quarantined until its own row is explicitly approved.
- **Who approves:** the Conductor (Chris), not any packet builder — identical
  authority pattern to the roster confirmation gate (`PHASE0_ROSTER.md` §7) and the
  §10.3 source/channel allowlist gate.
- **This packet's own status against that gate:** **not requested, because there is
  nothing to approve yet.** This document ships the frame; §2's table has zero
  filled `ir_root_url`/`webcast_vendor_domain` values for the Conductor to review.
  The gate itself remains open and unexercised until a future assembly pass (§3)
  produces something concrete to bring to it.

---

## 5. What is explicitly out of scope for this document and this packet

- No domain in §2 is fetched, resolved, or redirect-followed by anything in this
  packet. `earnings_calendar.py` never imports or references this document's data —
  it is EDGAR-only (see that module's own docstring, point 3).
- No new redirect mechanism or rule is proposed here beyond what Session 1 already
  approved (§1) — this document assembles a *domain list* against an *already-
  approved mechanism*, it does not renegotiate the mechanism itself.
- No company's IR root is assumed reachable, official, or stable — §9.3's own
  "names and identifiers must not be assumed to remain static" applies to IR URLs
  exactly as it does to tickers/CIKs.
