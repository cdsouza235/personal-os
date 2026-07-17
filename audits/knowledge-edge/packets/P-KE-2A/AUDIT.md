schema_version: "1"
run_id: "codex-audit-2026-07-17T00:00:00Z"
packet_id: "P-KE-2A"
producer_role: "auditor"
artifact_type: "build_audit_report"
status: "completed"
base_sha: "unknown_git_unavailable"
head_sha: "unknown_git_unavailable"
changed_files:
  - "src/personalos/rails/knowledge_edge/podcasts.py"
  - "migrations/00023_knowledge_edge_lane_a_endpoints.sql"
  - "migrations/00024_knowledge_edge_media_cross_run_identity.sql"
  - "src/personalos/knowledge_edge/adapters/contracts.py"
  - "src/personalos/knowledge_edge/scan_orchestrator.py"
  - "src/personalos/knowledge_edge/state/media.py"
  - "src/personalos/knowledge_edge/state/registries.py"
  - "tests/test_rails_knowledge_edge_podcasts.py"
  - "tests/test_knowledge_edge_registries.py"
  - "tests/test_knowledge_edge_scan_orchestrator.py"
  - "tests/test_knowledge_edge_migrations.py"
  - "docs/knowledge_edge/PACKET_2A_PODCAST_SUPERVISED_SMOKE.md"
timestamp: "2026-07-17T00:00:00Z"
recommendation: "accept_with_conditions"
issues_found: 1
summary: >-
  No reject-level live-fetch reachability was found by source inspection. At merge,
  the nine Lane A podcast sources remain trial via migration 00022/00023, their
  endpoint_verified_at and verified_by fields are NULL, and run_scan only iterates
  active sources. Direct use of LivePodcastFeedAdapter is also gated before fetch by
  feature mode, credential presence, source existence, active source status, verifier
  identity, parseable verification timestamp, and https endpoint scheme. Network
  mechanics are tested with injected fake clients/openers rather than live network.
  Migration 00024 and the minimal media persistence changes are treated as in scope
  under the user-provided Conductor amendment and appear aligned with §8.1 corrected
  episode handling.
findings:
  - id: "P-KE-2A-F1"
    file: "docs/knowledge_edge/PACKET_2A_PODCAST_SUPERVISED_SMOKE.md"
    location: "lines 81-99; related code at src/personalos/knowledge_edge/state/registries.py:128-257"
    severity: "medium"
    what: >-
      The supervised smoke procedure says passing feeds should be promoted by
      updating ke_source_endpoints.endpoint_verified_at, ke_source_endpoints.verified_by,
      and ke_sources.status via existing state-layer helpers, but the registry state
      module currently exposes create/get/list helpers only; no update helper exists
      for endpoint verification or source status promotion.
    why: >-
      This does not make live fetch reachable at merge, so it is not a G5 inertness
      failure. It is still a gate condition before executing the smoke: the documented
      post-merge procedure either cannot be followed as written or would push the
      Conductor toward raw SQL/state mutation, which conflicts with the project rule
      that state writes go through core APIs.
    fix: >-
      Before running the supervised smoke or flipping any Lane A source active, add
      or cite a state-layer API that records endpoint verification and source status
      promotion one feed at a time, with validation and tests; then update the smoke
      procedure to name that API exactly.
evidence_reviewed:
  - "Read governance/living/agent-writable/STATUS.md and governance/ROADMAP.md per session-start instructions."
  - "git and rg were unavailable in this sandbox; base/head SHA and exact git diff are unknown. File list is inferred from the P-KE-2A implementation surface reviewed."
  - "python3 was unavailable, so tests could not be executed locally; this is environment-limited and not counted as a packet failure per the task note."
  - "src/personalos/rails/knowledge_edge/podcasts.py:270-275 calls client.fetch only after _evaluate_gates returns no error."
  - "src/personalos/rails/knowledge_edge/podcasts.py:311-389 refuses disabled/fixture mode, missing/empty credential, unknown source, missing endpoint, non-active or unverified source, malformed verification timestamp, and non-https endpoint."
  - "src/personalos/rails/knowledge_edge/podcasts.py:193-225 enforces GET, timeout, max response bytes, and same-host redirect handler construction for the real client path."
  - "src/personalos/rails/knowledge_edge/podcasts.py:483-519 and 557-655 reject malformed documents, count malformed items by reason, parse RSS/Atom, and avoid silent garbage acceptance."
  - "src/personalos/knowledge_edge/scan_orchestrator.py:145 lists only status='active' sources, so the seeded trial Lane A sources are skipped before adapter dispatch."
  - "src/personalos/knowledge_edge/scan_orchestrator.py:300-358 and 501-582 implement cross-run corrected-episode handling via underlying_id lookup, identity update, content-status transition, decision history, and discovery occurrence."
  - "src/personalos/knowledge_edge/state/media.py:258-335 provides underlying_id lookup and identity update helpers for the amended migration 00024 path."
  - "migrations/00023_knowledge_edge_lane_a_endpoints.sql:26-42 adds endpoint verification columns and exactly nine Lane A endpoint rows with endpoint_verified_at and verified_by NULL."
  - "migrations/00024_knowledge_edge_media_cross_run_identity.sql:23-27 additively adds feed_guid, underlying_id, and an index for cross-run identity."
  - "tests/test_knowledge_edge_registries.py:221-282 asserts Lane A sources remain trial, endpoints remain NULL-verified, and the source_id-to-URL mapping is byte-exact for all nine rows."
  - "tests/test_rails_knowledge_edge_podcasts.py:379-727 covers refusal paths, fake-client no-network behavior, redirect quarantine, size cap, transport failure, malformed feed failure, dropped-item counts, duplicate GUID handling, cursor filtering, and the verified-source positive path with an injected client."
  - "tests/test_knowledge_edge_migrations.py:230-279 preserves the no-network-import guard for the knowledge_edge package root; the new live rail is outside that package and is covered by dedicated fake-client tests."
  - "docs/knowledge_edge/PACKET_2A_PODCAST_SUPERVISED_SMOKE.md:28-78 documents post-merge supervised execution only, no packet-run network, one GET per feed ceiling, no cross-host redirect, and independent per-feed STOP behavior."
  - "grep found no production caller outside tests constructing LivePodcastFeedAdapter with shadow_live/active modes."
  - "No GOVERNANCE_MANIFEST.yaml edit was made by this audit; governance files were read only."
