# Knowledge Edge — Packet 2F Lane B/C Source Supervised Smoke Procedure

Status: proposed procedure, for execution post-merge under direct Conductor-session
supervision only. Owner: Builder (P-KE-2F) · Date: 2026-07-17
Zero network requests, zero credentials touched in producing this document (hard
constraint) — this is a plan to be executed later, by a human-supervised session, not
a script run by this packet. Mirrors `docs/knowledge_edge/
PACKET_2A_PODCAST_SUPERVISED_SMOKE.md`, `PACKET_2B_YOUTUBE_SUPERVISED_SMOKE.md`, and
`PACKET_3A_EARNINGS_SUPERVISED_SMOKE.md`'s structure and STOP-rule discipline, applied
to the five rows migration `00027_knowledge_edge_lane_bc_source_seeding.sql` seeds.

---

## 1. Why this document exists

Migration `00027` seeds four `youtube_channel` `ke_sources` rows (the amendment
§10.3 launch video/network allowlist's general-news class: CNBC Television,
Bloomberg Television, Bloomberg Technology, Yahoo Finance) with their `channel_id`
endpoints, plus the one `person_search_provider` row
(`ke-source-youtube-person-search`, matching `rails/knowledge_edge/youtube.py`'s
`DEFAULT_PERSON_SEARCH_SOURCE_ID`) with its `api_endpoint` row. Per this project's
own hard constraint, seeding a row is not the same as verifying it: all five sources
stay `status='trial'` and every one of their endpoints'
`endpoint_verified_at`/`verified_by` stays `NULL` after that migration runs.
`youtube.py`'s own gating (`LiveYoutubeChannelAdapter._evaluate_gates` and
`LiveYoutubePersonSearchClient._evaluate_gates`, both unmodified by this packet —
see `tests/test_knowledge_edge_lane_bc_source_seeding.py`'s
`ChannelAdapterGatingTest`/`PersonSearchGatingTest`, which confirm this against the
real seeded rows with fake, in-process HTTP clients) refuses to fetch from any of
these five sources until this exact procedure runs and a Conductor session records
its result.

This is also the step `PHASE0_PROVIDERS_AND_ACCESS.md` §6 names explicitly: seeding
these four channel identities via a Conductor-verified migration (this packet) is
necessary but not sufficient — "any addition later ... requires an explicit
Conductor acknowledgment of the specific added source before it is fetched from."
This document is that acknowledgment's execution procedure, not the acknowledgment
itself.

---

## 2. Execution constraints (non-negotiable)

- **Who runs this:** the Conductor session, directly and supervised, in real time.
  **Not any packet builder, and not scheduled** — no automation, no cron, no
  unattended run.
- **When:** post-merge of this packet only, and only after the explicit Conductor
  acknowledgment of these four specific channel identities that this packet's own
  handoff flags as still pending.
- **Scope:** read-only; shadow-scope (no production database, no production
  writes); one plain `GET` per channel feed, no API key (RSS/playlist polling is
  outside the YouTube Data API Services terms entirely, D-YT option 1) — see §3.
- **Transcript:** results (request URL, response status, and a short summary of what
  parsed — not the full raw feed body) saved under `audits/knowledge-edge/` by the
  supervising session itself, not by this packet, mirroring the 0C/2A/2B/3A
  transcripts' format.
- **STOP rule, no exceptions:** any non-200 response, any redirect to a host other
  than `www.youtube.com` (the exact thing `youtube.py`'s
  `_HostConfinedRedirectHandler` refuses to follow silently), or any response that
  does not parse as well-formed Atom `<feed>` **halts that channel's smoke
  immediately**. No retries. Each channel's smoke is independent — one channel's
  failure does not block attempting the next.

---

## 3. Channel-upload RSS polling — one GET per channel, 4 GETs total ceiling

For each of the 4 rows migration `00027` seeds (`ke-source-cnbc-television`,
`ke-source-bloomberg-television`, `ke-source-bloomberg-technology`,
`ke-source-yahoo-finance`):

```
GET https://www.youtube.com/feeds/videos.xml?channel_id=<that row's channel_id>
User-Agent: PersonalOS-KnowledgeEdge-YoutubeChannelPoll/1.0
```

| Source | channel_id |
|---|---|
| ke-source-cnbc-television | UCrp_UI8XtuYfpiqluWLD7Lw |
| ke-source-bloomberg-television | UCIALMKvObZNtJ6AmdCLP7Lg |
| ke-source-bloomberg-technology | UCrM7B7SL_g1edFOnmj-SDKg |
| ke-source-yahoo-finance | UCEAZeUIeJs0IjQiqTCdVSIg |

**Success criteria (all must hold, mirroring the 2B doc's own three):**

1. HTTP 200 response, no redirect to a different host than `www.youtube.com`.
2. Response body parses as well-formed Atom `<feed>` with at least one `<entry>`.
3. At least one entry carries a non-empty `yt:videoId` and `<title>`.

**Bound:** exactly one GET per channel; 4 GETs is the hard ceiling for this section,
not a target to reach. A channel that fails its smoke is left exactly as seeded
(`trial`, `endpoint_verified_at` still `NULL`) — it is not retried within the same
session.

**Recording a PASS** (the only path from `trial` to `active`, via the existing
state-layer helpers `personalos.knowledge_edge.state.record_endpoint_verification`
and `personalos.knowledge_edge.state.update_source_status`):

1. `record_endpoint_verification(connection, source_id=<source_id>,
   endpoint_url=<channel_id>, verified_at=<UTC timestamp of the successful GET>,
   verified_by=<identifying session string, e.g. "conductor:2026-07-17">)` —
   `endpoint_url` here is the raw `channel_id` value itself, since that is what
   `ke_source_endpoints.url` holds for a `channel_id`-type endpoint (migration
   `00027`'s own header explains why; `youtube.py`'s module docstring is the
   original source of that convention).
2. `update_source_status(connection, source_id=<source_id>, new_status="active")`.
3. Append a row to this packet's own smoke transcript
   (`audits/knowledge-edge/<date>-packet-2f-youtube-lane-bc-smoke-transcript.md`,
   mirroring the 2A/3A transcripts' format) recording the request, response status,
   and what parsed.

Until both steps 1 and 2 land for a given channel, `LiveYoutubeChannelAdapter`
continues to refuse every fetch attempt against it.

---

## 4. `search.list` person search — the row flip only, no new live call

**This section requires no new live `search.list` call.** The mechanism itself
(request shape, response shape, key validity) was already live-fire verified once,
pre-existing this packet: one `search.list` call (`q=Mohamed El-Erian`,
`maxResults=5`) returned HTTP 200 with 5 on-target items, recorded in the "YouTube
verification (per PACKET_2B_YOUTUBE_SUPERVISED_SMOKE.md)" section of
`audits/knowledge-edge/2026-07-16-packet-2a-podcast-smoke-transcript.md` (Session
#2 addendum). That call predates `ke-source-youtube-person-search`'s own existence
(migration `00027` is what first seeds that row — see that migration's own header
and `PACKET_2B_YOUTUBE_SUPERVISED_SMOKE.md` §0's prerequisite this document
closes), so it is evidence the mechanism works, not itself a verification record
against this specific source row.

**What this section does instead:** the Conductor session records that
already-passed call as this row's own verification, via the same two sanctioned
helpers as §3, applied once:

1. `record_endpoint_verification(connection,
   source_id="ke-source-youtube-person-search",
   endpoint_url="https://www.googleapis.com/youtube/v3/search",
   verified_at=<the 2A transcript's own recorded timestamp for that call, or a
   fresh UTC timestamp if the session prefers to re-run one confirming call before
   flipping — either is acceptable; re-running is not required>,
   verified_by="conductor:2026-07-17-packet-2f")`.
2. `update_source_status(connection, source_id="ke-source-youtube-person-search",
   new_status="active")`.
3. Append a row to this packet's smoke transcript citing the 2A transcript's
   YouTube verification section by path, plus a note recording the flip itself.

**Still open, carried unchanged from the 2A/2B transcripts:** the Google Cloud
Console quota screenshot that closes `PHASE0_PROVIDERS_AND_ACCESS.md` §5's TBC
(per-call `search.list` unit cost, project default daily quota). Nothing in this
packet or this procedure resolves that; it remains a Conductor action independent
of this row's flip.

Until both steps 1 and 2 land, `LiveYoutubePersonSearchClient` continues to refuse
every fetch attempt against `ke-source-youtube-person-search` — seeding the row
(migration `00027`) and recording this flip (this procedure) are each necessary but
neither is sufficient on its own.

---

## 5. Combined STOP conditions

Each of the 4 channel smokes (§3) halts independently of the others and of §4 on
its own first failure; a failure on one channel never blocks attempting the next or
recording §4's flip. §4 itself has no live-fire STOP condition of its own (no new
call is made) — its only failure mode is the Conductor session declining to record
the flip, which simply leaves the source exactly as seeded. All results are saved
to a transcript before the supervising session ends. No channel is fetched from
again inside the same session after either a PASS (recorded, done) or a STOP (left
exactly as seeded, not retried).
