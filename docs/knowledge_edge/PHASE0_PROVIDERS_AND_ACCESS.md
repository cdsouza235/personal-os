# Knowledge Edge — Packet 0B: Provider Evaluation and External-Access Bundle

Status: proposed, for Session 1 approval. Owner: Builder (Packet 0B) · Date: 2026-07-15
**Amended 2026-07-16 (P-KE-00C): §2's Financial Modeling Prep evaluation was superseded
at Session 1 — see the disposition banner at the top of §2 and D-PO-019. §2 is retained
as the evaluation record; it is no longer a live spec. Nothing else in this document is
changed by that amendment.**
Zero credentials created, zero live network requests, zero live pricing/rate-limit pages
fetched in producing this document (hard constraint, amendment §0). Every figure that
would normally require live external confirmation is marked **TBC — verify at Session 1**
rather than invented; this is deliberate, per this packet's own instructions, not an
oversight. D-PO-016 originally fixed the earnings-calendar provider (Financial Modeling
Prep); §2 below evaluates that decision against the amendment's criteria — see the §2
disposition banner for how that choice was subsequently reversed by D-PO-019.

---

## 1. Evaluation criteria (applied to every candidate provider below)

Per amendment §19 Packet 0B: **cost, rate limits, licensing, data-retention obligations,
reliability, coverage.** Applied as a fixed rubric so each provider section below answers
the same six questions in the same order.

---

## 2. Earnings-calendar provider — Financial Modeling Prep (decided, D-PO-016) — **REJECTED at Session 1 (D-PO-019, 2026-07-15)**

> **Disposition banner (2026-07-15):** At Session 1 credential creation, Chris verified
> FMP's actual pricing: earnings/corporate-events access requires a ~$50/month tier — the
> figure this section explicitly could not confirm when D-PO-016 chose paid-FMP-over-
> scrapers. Chris rejected it as over budget ("not down with that") — see **D-PO-019** in
> `governance/living/agent-writable/DECISIONS.md`. **FMP is out entirely; the FMP key
> created at Session 1 is inert (commented out in `.env.local`; Chris may cancel the
> account).** The replacement is a bounded, rule-defined company roster sourced from SEC
> EDGAR + official IR pages — see `PHASE0_ROSTER.md`. The section below is **retained
> as-is as the evaluation record** (it is why FMP was rejected once real pricing was
> known, not despite that record); the entitlement-artifact list in this section (items
> 1-6 below) is **no longer applicable** — no entitlement artifact will ever be captured
> for FMP, since no plan is being purchased. Do not build against this section; it is
> history, not a live spec.

| Criterion | Finding |
|---|---|
| Cost | Paid tier required (Chris's explicit choice, D-PO-016 item 3: "keeps it cleaner" vs. ~20-40 per-company IR-page scrapers). **Exact current plan name and monthly price: TBC — verify at Session 1** against `https://site.financialmodelingprep.com/developer/docs/stable/earnings-calendar` and FMP's own pricing page at credential-creation time. D-PO-016 itself records that automated fetching of FMP's pricing page was blocked when tried, and only unauthoritative third-party-sourced numbers were available — those are explicitly not repeated here as if confirmed. |
| Rate limits | **Exact current per-minute/per-day call cap for the selected plan: TBC — verify at Session 1.** Design the adapter (Packet 3A) to read the plan's documented limit from the entitlement artifact (below), not from an assumed number. |
| Licensing | Vendor-supplied structured calendar data, single-user local research use. The amendment's own §10.4 disposition (R2-17): FMP's display restrictions target third-party redistribution, not single-user local display — but this reading must be confirmed against the actual plan terms, not assumed; see entitlement artifact requirement below. |
| Data-retention obligations | **TBC — verify at Session 1**: whether the plan's terms impose any refresh/deletion cycle on cached fields (unlike the YouTube Data API's documented 30-day rule, FMP's retention terms are not established in any source available to this packet). Until confirmed, treat FMP-sourced display fields (company name, date, time) with the same TTL-cache discipline as YouTube provider metadata (§10.4) as a conservative default. |
| Reliability | Documented, actively maintained REST API (per the amendment's own §25 reference link); the amendment names it as the recommended structured provider specifically to avoid the reliability risk of ~20-40 bespoke IR-page scrapers breaking on redesigns. No live uptime data available to this packet. |
| Coverage | Structured earnings-calendar data is FMP's core product category; expected to cover the Tier A/B company universe (§9) as US-listed equities. Non-US-listed Tier A names (e.g. Taiwan Semiconductor Manufacturing Company, ASML) may have partial or ADR-only coverage — **verify per-company coverage during Packet 3A's company-identifier verification step**, not assumed here. |

### Candidate tier/plan structure (framework, not invented numbers)

FMP publishes multiple tiers (commonly a free tier plus several paid tiers of increasing
call volume/endpoint access — exact current tier names, prices, and per-tier endpoint
gating are **TBC, verify at Session 1**). The adapter design must not hardcode a tier
name; it should read the entitlement artifact (below) to know which endpoints and rate
limits apply, so a future plan change does not require a code change.

### Entitlement artifacts Session 1 must capture (per amendment §0 Session 1 bundle + R2-17)

**No longer applicable (D-PO-019, 2026-07-15) — FMP is not adopted, so no entitlement
artifact is ever captured against it.** Retained below unedited as the evaluation record
of what *would* have been required had FMP been adopted.

A named, dated record (screenshot or saved terms excerpt, referenced from — not
necessarily committed verbatim into — the repo, since raw vendor terms text may itself
carry redistribution restrictions) confirming, at minimum:

1. **Plan/tier name and billing cadence** actually purchased.
2. **Permitted fields** — which returned fields (company, date, time, confirmed status,
   etc.) the plan allows an application to display, cache, and act on.
3. **Retention** — how long returned data may be cached/stored before requiring refresh
   or deletion.
4. **Derived use** — whether permitted fields may feed a deterministic ranking/priority
   score (Lane D's "event proximity"/"company tier" ranking factors, §11.5) — this is a
   real question because "derived use" restrictions in vendor terms sometimes target
   redistribution/resale, not single-user internal scoring, but that distinction must be
   confirmed in FMP's actual terms, not assumed by analogy to the YouTube case.
5. **Local display rights** — whether displaying event name/date/time/link cards in a
   localhost-only, single-user application is within the plan's terms (expected yes, but
   named explicitly since R2-17 flagged licensing evidence, not just a licensing posture,
   as the requirement).
6. **Test-fixture rights** — whether a sample response may be converted into a synthetic,
   provider-policy-safe golden fixture (Packet 0C) for use in the repo's committed test
   suite; if the plan's terms are silent or restrictive, default to structurally-similar
   *invented* fixture data (not derived from a real captured response) for that adapter's
   tests instead.

If any of 2-6 comes back restrictive or unconfirmed by the time Packet 3A needs to build
against it, the fallback is **FMP link-only mode** (display the official IR/company link,
not FMP's own displayed schedule fields) — exactly the amendment's own §10.4 fallback
("absent that evidence, use link-only data").

---

## 3. Broad person-search provider — recommend deferral, with coverage impact

The amendment permits either a recommendation or a documented deferral (§19 Packet 0B).
**This document recommends deferral at launch.** Reasoning:

- No live provider research (pricing/licensing comparison across candidate podcast/video
  search indexes) is possible inside this packet's hard constraints (no network requests).
  A genuine, evidence-based recommendation of a *specific* vendor would require exactly
  the kind of live research this packet is barred from doing — producing one anyway would
  mean guessing a vendor name and inventing plausible-sounding terms, which is the
  fabrication this packet's own instructions forbid.
- The D-YT decision (§4 below) already selects **RSS-first (Option 1)** as the launch
  YouTube-sourcing mechanism, which covers Lane A entirely (podcast RSS/Atom, no video
  search involved) and covers Lane B/C for any tracked person's *own or approved-network*
  channel uploads via channel RSS/upload-playlist polling. What a broad person-search
  provider would additionally buy is coverage of a tracked person's appearance on a
  channel *not* on the approved allowlist (§10.3) — e.g., a Market Voice interviewed on a
  smaller or regional business-news channel that was never added to the roster.
- Given launch already accepts "coverage honesty" over "coverage completeness" as a
  product principle (§6 principle 10, §10.5), deferring a broad-search provider and
  reporting the resulting gap as a named coverage limitation is consistent with the
  amendment's own philosophy, rather than a corner cut.

**Coverage impact, stated explicitly:** at launch, Lane B (Market Voices) and Lane C
(Consequential Leaders) discovery is bounded to (a) the approved official/network channel
allowlist (§10.3) via RSS/playlist polling, and (b) YouTube Data API `search.list` person
queries restricted to stable-identifier use only (D-YT option 1's Data-API carve-out,
not full transcript/derived classification). An appearance on a non-allowlisted channel
that is never uploaded to (or is uploaded late to) an allowlisted channel will not be
discovered until/unless that channel is separately added to the allowlist through the
existing source-verification/roster-approval path (§10.3), or a broad-search provider is
evaluated and approved in a later phase. This is reported in the coverage dashboard
(§10.5) as an "unapproved-channel" gap, not silently absorbed.

**Revisit trigger:** if Phase 2C's shadow-mode measurement (frozen ground-truth sample,
`PHASE0_THESIS_MATCHING.md`) shows person-appearance recall meaningfully below the
Session-2 threshold specifically because of missed non-allowlisted-channel appearances
(as opposed to classification errors on already-discovered items), that is the concrete,
data-backed trigger to bring a specific broad-search provider recommendation back for a
new Session-gated decision — not a launch-blocking requirement now.

---

## 4. D-YT — YouTube sourcing decision (amendment §10.4)

Three options were laid out in the amendment; option 3 (documented deviation) was already
rejected in Revision 1.3 (R3-01) as unable to satisfy any launch acceptance criterion.
**Recommendation: Option 1, RSS-first**, matching the amendment's own "default
recommendation" framing.

| | Option 1 — RSS-first (recommended) | Option 2 — third-party person search | Option 3 — documented deviation |
|---|---|---|---|
| Mechanism | Channel RSS/upload-playlist polling for allowlisted channels (outside YouTube Data API terms entirely); Data API restricted to person-search only, minimal stable-identifier storage | Route person/appearance search through a licensed third-party provider whose terms permit derived classification | Keep Data API with derived classification (directness class, confidence, priority score) despite the terms prohibiting derived/aggregated use |
| Terms compliance | Compliant — RSS/playlist polling is outside API Services terms; Data API use is narrowed to the one use (person search, stable IDs only) that does not require derived-metric rights | Compliant, contingent on the specific vendor's terms permitting derived use (must be confirmed per-vendor before adoption) | **Non-compliant by the amendment's own reading** — rejected in R3-01; cannot satisfy any launch acceptance criterion |
| Cost/quota | Zero quota cost for RSS/playlist polling; Data API quota bounded to person-search calls only (§5 below) | Depends on deferred provider (§3 above — not adopted at launch) | N/A (rejected) |
| Coverage | Full for allowlisted channels; gap for non-allowlisted-channel appearances (§3) | Would close the non-allowlisted-channel gap, if adopted | N/A (rejected) |
| Decision | **Selected for launch** | Not adopted at launch (§3 deferral) | Rejected (R3-01) |

**Storage/cache implications of Option 1:** provider display metadata sourced from the
Data API (titles, descriptions, channel names, for the person-search use only) lives in a
TTL-controlled refreshable cache with expiry, refresh, and deletion tests (§10.4,
§13.4) — audit history never archives this provider display metadata, only stable
identifiers and internal/user-authored facts persist indefinitely. RSS/playlist-sourced
fields (used for the bulk of Lane A/B/C discovery) are not subject to the Data API's
30-day refresh rule at all, since they are not sourced from the Data API — this is a
real, material benefit of the RSS-first choice beyond terms compliance alone.

---

## 5. Worst-case quota budget (R2-16)

Framework and worked formula; the two flagged inputs are widely-documented historical
YouTube Data API values, not this packet's invention, but are still marked **TBC —
reconfirm at Session 1** per this packet's own instruction to verify current external
rate limits rather than assert them from training-data recall.

**Budget components** (all bounded to the *person-search* use only, since Option 1 keeps
channel polling on RSS, which is quota-free):

| Component | Worst-case count (launch rosters) |
|---|---|
| Tracked people needing person-search (Lane B: 8, Lane C named individuals: ~13, Lane C role-based watches: up to the Session 1 launch role appendix's roster cap — provisionally ≤8 roles) | ≤29 distinct search subjects |
| Aliases per person (spelling variants, e.g. Mohamed/Mohammed El-Erian) | ~2-3 alias variants each → ≤3x multiplier |
| Pagination pages per search (only if a search returns more results than one page) | 1-2 pages typical; budget for 2 |
| Overlap-window re-checks (scan cursor overlap, §11.1) | re-search on 6:15am refresh may re-touch the same-day window; budget 2 calls/day/subject worst case (4:30pm scan + 6:15am refresh) |
| Retries (transient-failure backoff, bounded per §17.2) | up to 3 retries per call, only on failure — not counted in the steady-state budget, reserved headroom |
| Manual "Scan now" | user-triggered, rate-limited by the same single-instance lock as scheduled scans; budget as one additional full-subject pass per manual invocation |
| Soak traffic (Packet 6A, 7 consecutive days) | steady-state daily cost x 7, no additional multiplier |

**Worked formula (steady-state, one calendar day, no manual scans, no retries):**

```
daily_search_calls = subjects (≤29) × alias_variants (≤3) × pagination (≤2) × daily_runs (2)
                   = 29 × 3 × 2 × 2 = 348 calls/day, worst case
```

**Per-call quota cost — TBC, reconfirm at Session 1:** `search.list` has historically cost
100 quota units per call against a default project quota of 10,000 units/day (widely
documented in third-party and archived Google API references available to this packet's
training data, but not independently re-verified live here per this packet's hard
constraint). If that figure is still current: `348 calls × 100 units = 34,800 units/day`,
which **would exceed** a 10,000-unit default daily quota by more than 3x. This is the
concrete number that makes the RSS-first choice non-optional rather than a preference:
even a modest person-search-only Data API usage pattern is quota-tight against the
commonly-cited default project quota, and channel-polling (which Option 1 explicitly
avoids putting on the Data API) would make the budget considerably worse.

**Required action before Packet 2B builds against this:** confirm at Session 1 (a) the
current `search.list` unit cost, (b) the current default daily project quota, and (c)
whether a quota extension request is realistic/needed given (a) and (b) — per the
amendment's own instruction, "requiring an approved quota extension before any design
that exceeds the reserve is accepted." If the reconfirmed numbers make the 348-call
worst case infeasible, the fallback is to reduce alias-variant coverage or batch multiple
people per query (YouTube's `search.list` supports a single `q` query string, so some
alias consolidation is possible) — a Packet 2B design detail, not decided here.

---

## 6. External-access bundle — Session 1 consolidated checklist

Every item Session 1 must approve, in one place, expanded from the amendment's own §0
Session 1 bullet:

- [x] **Financial Modeling Prep API key** — env var `PERSONALOS_RAIL_KE_FMP_API_KEY`.
      **NOT ADOPTED (D-PO-019, 2026-07-15)** — rejected at real price (~$50/month tier)
      once verified at Session 1. The key created at Session 1 is **inert** (commented
      out in `.env.local`; Chris may cancel the account). No entitlement artifact will be
      captured against it. Superseded by the roster-source item below.
- [x] **Earnings-coverage roster source (EDGAR + IR pages)** — replacement for the item
      above per D-PO-019. Two sources, both already approved, **no credential
      required**: (1) SEC EDGAR (`data.sec.gov`), approved Session 1 with the
      `PERSONALOS_RAIL_KE_EDGAR_USER_AGENT` string per D-PO-018 item 4 — no API key; (2)
      the companies' official investor-relations pages, already admitted by the §10.3
      allowlist below as "official company/investor-relations channels" — no separate
      approval needed. Roster membership rule, candidate seed list, and quarterly
      refresh procedure: `PHASE0_ROSTER.md`.
- [ ] **YouTube Data API key** — env var `PERSONALOS_RAIL_KE_YOUTUBE_API_KEY`. Scope:
      `search.list` for person-search only (D-YT option 1); no channel-listing/upload
      polling through this key (that path uses RSS/playlist URLs, no key required).
- [ ] **Broad person-search provider credential** — **not requested at Session 1**
      (§3 deferral). No credential to approve.
- [ ] **Source/channel allowlist** — the podcast RSS roster (amendment §8.1, 9 feeds) +
      the video/network allowlist (§10.3: CNBC Television + tracked-show feeds,
      Bloomberg Television, Bloomberg Technology, Yahoo Finance, official
      company/IR/executive channels, official conference/event-organizer channels,
      official U.S. government/central-bank channels for the role-based watches) —
      Session 1 approves this list as the launch-time allowlist. Any addition later
      re-runs the same source-verification step **and requires an explicit Conductor
      acknowledgment of the specific added source before it is fetched from** — the
      verification step establishes the source is legitimate, but only a human
      acknowledgment closes the gate for that specific addition; no source is ever
      fetched from solely because it passed an automated verification step. This does
      not require re-convening a full Session (a lightweight Conductor sign-off
      suffices, consistent with the roster-cap/gate design elsewhere in the amendment),
      but it is never silent or automatic.
- [ ] **IR/webcast vendor-domain list** — **TBC, populated at Packet 3A** when Tier A/B
      company IR roots are verified (amendment §9.3's own requirement that identifiers/
      URLs be verified "from official sources during the live-adapter planning phase,"
      not assumed static here). The amendment's own §0 Session 1 bullet places "the
      approved IR/webcast vendor-domain list and redirect rules" *inside* the Session 1
      approval bundle — so the concrete list cannot be approved by this packet (it does
      not exist yet, and this packet has zero network access to derive it), and it
      cannot self-extend under today's Session 1 approval either, because that would let
      Packet 3A's own findings authorize themselves, which is exactly the gap Session 1
      exists to prevent. The resolution moves the approval's *timing*, not its
      requirement:
      - **Session 1 approves now:** the redirect *mechanism and rules only* — bounded
        redirects are permitted solely from an already-approved official IR page (never
        a freestanding new domain), and any destination not on an approved list is
        quarantined as `Link pending (unknown vendor)` per §8.4 and is not fetched or
        displayed as verified.
      - **Packet 3A assembles and verifies** the concrete Tier A/B IR-root and
        redirect-target domain list against official sources, as its own deliverable.
      - **The assembled list then returns to the Conductor as its own explicit,
        named approval gate — "Packet 3A vendor-domain-list approval" — before any live
        fetch is made against any domain on it.** This is an asynchronous approval (it
        does not require reconvening the full Session 1 meeting), but it is a mandatory,
        named, human-in-the-loop checkpoint distinct from and in addition to Session 1's
        mechanism approval — not an automatic extension of it. `PHASE0_PLAN.md`'s P-KE-3A
        packet row and Phase 3 acceptance criteria name this gate explicitly so it is not
        lost as an implicit assumption.
      - Until that Packet 3A approval lands, every redirect destination is treated as
        unknown and quarantined as `Link pending (unknown vendor)` — no domain is ever
        fetched from on the strength of Session 1's mechanism approval alone.
- [ ] **SEC EDGAR user-agent string** — SEC's fair-access rules require an identifying
      `User-Agent` header (typically `AppName ContactEmail`). **Exact contact
      identity/email to use: TBC — this is Chris's own identifying information, to be
      supplied and confirmed at Session 1**, not invented by this packet.
- [ ] **Scope limits** (apply to every credential/endpoint above): read-only access only;
      named endpoints and approved vendor domains only; isolated shadow database path
      only (`~/.personalos/shadow/personalos-shadow.sqlite3` as of the P-KE-2E amendment,
      2026-07-17; originally `var/shadow/personalos-shadow.sqlite3` — AD-4 in
      `PHASE0_ARCHITECTURE_DECISIONS.md`) — no production database writes before
      Session 3; no production notifications; no Obsidian writes; no scheduler
      installation or loading before Session 2 (shadow) / Session 3 (production).
- [x] **Provider entitlement artifacts** — FMP's: **not applicable, FMP not adopted
      (D-PO-019)**, no artifact will be captured; YouTube Data API's derived-data policy
      is already documented in the amendment itself (§10.4) and does not need a separate
      captured artifact, since Option 1 avoids the derived-use path entirely.
- [ ] **Launch role appendix** — role, initial occupant, effective date, and roster cap
      for every "configured" role named in amendment §8.3 (Federal Reserve Chair, U.S.
      Treasury Secretary, SEC Chair, CFTC Chair, Apple CEO, configured frontier-lab
      heads, configured AI-accelerator/semiconductor-platform heads). **Not populated by
      this packet** — Session 1 itself is where Chris supplies and ratifies this list,
      per the amendment's own §0 description of what Session 1 approves; Packet 1A seeds
      roles from that appendix, not from the amendment's prose list alone.
