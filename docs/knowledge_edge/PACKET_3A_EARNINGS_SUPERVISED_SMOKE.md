# Knowledge Edge — Packet 3A EDGAR Earnings-Calendar Supervised Smoke Procedure

Status: proposed procedure, for execution post-merge under direct Conductor-session
supervision only. Owner: Builder (P-KE-3A) · Date: 2026-07-17
Zero network requests, zero credentials touched in producing this document (hard
constraint) — this is a plan to be executed later, by a human-supervised session, not
a script run by this packet. Mirrors
`docs/knowledge_edge/PACKET_2A_PODCAST_SUPERVISED_SMOKE.md` and
`PACKET_2B_YOUTUBE_SUPERVISED_SMOKE.md`'s structure and STOP-rule discipline, applied
to `src/personalos/rails/knowledge_edge/earnings_calendar.py`'s single EDGAR
submissions mechanism.

---

## 1. Why this document exists

Migration `00026_knowledge_edge_edgar_company_identifiers.sql` seeds one
`ke_sources` row (`ke-source-sec-edgar-submissions`, `source_type='calendar_provider'`,
`lane='earnings_events'`) and one `ke_source_endpoints` row (`endpoint_type=
'api_endpoint'`, `url='https://data.sec.gov/submissions/'`) representing the EDGAR
submissions mechanism the D-PO-019 roster's earnings coverage runs on
(`docs/knowledge_edge/PHASE0_ROSTER.md`). Per this project's own hard constraint,
seeding the mechanism is not the same as verifying it: the source stays
`status='trial'` and the endpoint's `endpoint_verified_at`/`verified_by` stay `NULL`
after that migration runs.
`earnings_calendar.py`'s own gating (`LiveEarningsCalendarAdapter.
_evaluate_source_gates`) refuses to fetch anything until this exact procedure runs
and a Conductor session records its result — independent of, and prior to, the
additional per-company gate the same adapter also applies (a company must be
`roster_status='confirmed'` with an `identifier_status='confirmed'`
`ke_company_edgar_identifiers` row; see that module's own docstring point 1).

This procedure verifies the MECHANISM only — one representative company's
submissions endpoint responds the way this adapter expects. It does not, and cannot,
verify all ~21 roster companies individually (see §3's bound); per-company coverage
is validated continuously afterward through ordinary scan runs and coverage
reporting (§10.5), not by this one-time smoke.

---

## 2. Execution constraints (non-negotiable)

- **Who runs this:** the Conductor session, directly and supervised, in real time.
  **Not any packet builder, and not scheduled** — no automation, no cron, no
  unattended run.
- **When:** post-merge of this packet only.
- **Scope:** read-only; shadow-scope (no production database, no production
  writes); requests identified via the `PERSONALOS_RAIL_KE_EDGAR_USER_AGENT` string
  already approved at Session 1 (D-PO-018 item 4) and already probed once by
  `PHASE0_PROBE_PLAN.md` §3 — this smoke does not re-open that approval, it exercises
  the same mechanism against the same header from within `earnings_calendar.py`
  itself for the first time.
- **Rate:** this adapter self-limits to ≤2 requests/second
  (`MIN_SECONDS_BETWEEN_REQUESTS`), itself well under SEC's published 10
  requests/second fair-access ceiling; this smoke's own request count (§3) is far
  below either bound and is not attempting to characterize it.
- **Transcript:** results (request URL, response status, and a short summary of what
  parsed — not the full raw JSON body) saved under `audits/knowledge-edge/` by the
  supervising session itself, not by this packet, mirroring the 0C/2A/2B
  transcripts' format.
- **STOP rule, no exceptions:** any non-200 response, any redirect to a host other
  than `data.sec.gov` (the exact thing `earnings_calendar.py`'s
  `_HostConfinedRedirectHandler` refuses to follow silently), or any response that
  does not parse as the expected `filings.recent` JSON shape **halts the smoke
  immediately**. No retries.

---

## 3. Procedure — exactly one GET, one company

**Target company:** Apple Inc. (`ke-company-aapl`, CIK `0000320193`) — the same
company `PHASE0_PROBE_PLAN.md` §3 already probed successfully pre-merge, chosen
again here for continuity: it is unambiguous, large, and files standard 10-K/10-Q
forms (unlike ASML's 20-F/6-K path, which this smoke does not separately probe —
see §5).

```
GET https://data.sec.gov/submissions/CIK0000320193.json
User-Agent: <PERSONALOS_RAIL_KE_EDGAR_USER_AGENT from .env.local>
```

**Success criteria (all must hold):**

1. HTTP 200 response, no redirect to a host other than `data.sec.gov`.
2. Response body parses as valid JSON with a top-level `filings.recent` object
   containing parallel `form`/`filingDate`/`accessionNumber` arrays (the same shape
   `earnings_calendar.py`'s `_parse_submissions_document` requires).
3. The declared `cik` field, once normalized, matches `320193` (the same
   cross-check `_parse_submissions_document` itself performs on every real fetch).

**Bound:** exactly one GET. This is a mechanism check, not a roster sweep — it does
not attempt to verify any of the other ~20 roster companies' endpoints
individually; per-company reachability is exactly the same URL pattern against a
different CIK, and this procedure's PASS is evidence the pattern itself works, not
a per-company guarantee.

---

## 4. Recording a PASS — the only path from `trial` to `active`

A smoke that meets all three success criteria is recorded by the supervising
Conductor session, via a direct, ordinary write using the existing state-layer
helpers (no new script):

1. Call `personalos.knowledge_edge.state.record_endpoint_verification` for
   `source_id='ke-source-sec-edgar-submissions'`,
   `endpoint_url='https://data.sec.gov/submissions/'`, the UTC timestamp of the
   successful smoke GET, and an identifying `verified_by` string for the session
   (e.g. `"conductor:2026-07-17"`).
2. Call `personalos.knowledge_edge.state.update_source_status` to flip
   `ke-source-sec-edgar-submissions` from `trial` to `active`.
3. Append a row to this packet's smoke transcript
   (`audits/knowledge-edge/<date>-packet-3a-earnings-smoke-transcript.md`, mirroring
   the 0C/2A/2B transcripts' format) recording the request, response status, and
   what parsed.

Until both step 1 and step 2 land, `LiveEarningsCalendarAdapter` continues to
refuse every fetch attempt, independent of feature_mode and independent of any
company's own `ke_company_edgar_identifiers` status — seeding the mechanism (this
packet) and running this smoke (this procedure) are each necessary but neither is
sufficient on its own.

---

## 5. What this smoke deliberately does NOT cover

- **ASML's 20-F/6-K path.** The migration seeds `ke-company-asml`'s
  `filer_form_family='foreign_private_issuer'`, but this smoke's one GET targets
  Apple's standard 10-K/10-Q path only. A future, separate smoke (or simply the
  first real scan run's coverage report, §10.5) is where the 20-F/6-K path first
  gets a live-data check; nothing in this procedure blocks that from happening
  later under the same mechanism-level verification this smoke records.
- **The IR/webcast vendor-domain list.** Entirely out of scope for this adapter and
  this smoke — see `docs/knowledge_edge/PACKET_3A_VENDOR_DOMAIN_LIST.md`. Nothing
  this smoke verifies authorizes any fetch against any IR/webcast domain.
- **Per-company `ke_company_edgar_identifiers` accuracy.** This smoke does not
  re-verify the 21 CIKs migration 00026 seeded (those were supplied pre-verified,
  per that migration's own header) — it verifies only that the submissions
  mechanism itself, called the way this adapter calls it, behaves as expected for
  one of them.

---

## 6. Combined STOP conditions

One GET, one company, one shot. A STOP leaves the source exactly as seeded
(`trial`, `endpoint_verified_at` still `NULL`) — not retried within the same
session. A PASS is recorded per §4 before the supervising session ends.
