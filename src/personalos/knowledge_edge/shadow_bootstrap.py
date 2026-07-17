"""P-KE-2C: idempotent shadow-database bootstrap (amendment Sec14.4 shadow_live;
Phase 2 acceptance Sec19; PHASE0_ARCHITECTURE_DECISIONS.md AD-4/AD-5).

Two responsibilities, run in order by `bootstrap_shadow_database`:

1. Apply every pending schema migration -- the same additive migrations every other
   environment uses (`personalos.db.migrations.apply_migrations`).
2. Re-apply the nine Lane A verification flips recorded by the Conductor-supervised
   podcast smoke
   (`audits/knowledge-edge/2026-07-16-packet-2a-podcast-smoke-transcript.md`) as
   LITERAL config -- no re-fetching, no live network -- via the same
   single-write-path helpers (`state.update_source_status`,
   `state.record_endpoint_verification`) the smoke itself used, so the shadow
   registry ends up byte-equivalent to the dev registry's sources/endpoints for
   these nine rows.

Idempotent: calling this twice against an already-bootstrapped connection makes no
further status/verification writes on the second call -- each flip only applies if
the source is still `trial`/unverified. This makes it safe to run as a routine
"bring the shadow DB up to the latest migrations" step during the supervised
procedure, not solely a one-time first action.

Deliberately narrow: this module knows about Lane A (curated podcasts) only, because
that is the one lane the smoke transcript actually verified end to end. Lane B/C
(YouTube channel polling, person search) and Lane D (earnings/EDGAR) have no
Conductor-verified sources to re-apply yet -- migration 00023 seeded only the 9 Lane
A endpoints, and `rails/knowledge_edge/youtube.py`'s own module docstring records
that no `youtube_channel` source or person-search source row exists in this repo's
migrations. Extending this bootstrap to other lanes is a future packet's job, once
their own supervised smokes produce a transcript to re-apply from.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

import personalos.knowledge_edge.state as ke
from personalos.db.migrations import apply_migrations

# Literal config, copied verbatim from the smoke transcript and migration 00023 --
# no re-fetching. `verified_at` uses each session's own recorded execution
# timestamp (Session #1: the four original PASSes; Session #2: the five re-smoked
# large feeds), `verified_by` is the transcript's own recorded actor string.
_TRANSCRIPT_VERIFIED_BY = "conductor:2026-07-16-supervised-smoke"
_SESSION_1_VERIFIED_AT = "2026-07-17T01:38:00+00:00"
_SESSION_2_VERIFIED_AT = "2026-07-17T03:52:00+00:00"


class ShadowBootstrapError(RuntimeError):
    """Raised when the shadow registry does not match this bootstrap's expected
    pre-state (e.g. migrations did not produce the expected 9 Lane A sources)."""


@dataclass(frozen=True)
class ShadowVerificationFlip:
    source_id: str
    endpoint_url: str
    verified_at: str
    verified_by: str


# Endpoint URLs copied verbatim from migration 00023_knowledge_edge_lane_a_endpoints.sql.
LANE_A_SHADOW_VERIFICATION_FLIPS: tuple[ShadowVerificationFlip, ...] = (
    ShadowVerificationFlip(
        source_id="ke-source-dwarkesh-podcast",
        endpoint_url="https://apple.dwarkesh-podcast.workers.dev/feed.rss",
        verified_at=_SESSION_1_VERIFIED_AT,
        verified_by=_TRANSCRIPT_VERIFIED_BY,
    ),
    ShadowVerificationFlip(
        source_id="ke-source-no-priors",
        endpoint_url="https://feeds.megaphone.fm/nopriors",
        verified_at=_SESSION_1_VERIFIED_AT,
        verified_by=_TRANSCRIPT_VERIFIED_BY,
    ),
    ShadowVerificationFlip(
        source_id="ke-source-forward-guidance",
        endpoint_url="https://feeds.megaphone.fm/forwardguidance",
        verified_at=_SESSION_1_VERIFIED_AT,
        verified_by=_TRANSCRIPT_VERIFIED_BY,
    ),
    ShadowVerificationFlip(
        source_id="ke-source-macro-voices",
        endpoint_url="https://feed.podbean.com/macrovoices/feed.xml",
        verified_at=_SESSION_1_VERIFIED_AT,
        verified_by=_TRANSCRIPT_VERIFIED_BY,
    ),
    ShadowVerificationFlip(
        source_id="ke-source-latent-space",
        endpoint_url="https://api.substack.com/feed/podcast/1084089.rss",
        verified_at=_SESSION_2_VERIFIED_AT,
        verified_by=_TRANSCRIPT_VERIFIED_BY,
    ),
    ShadowVerificationFlip(
        source_id="ke-source-unchained",
        endpoint_url="https://feeds.megaphone.fm/LSHML4761942757",
        verified_at=_SESSION_2_VERIFIED_AT,
        verified_by=_TRANSCRIPT_VERIFIED_BY,
    ),
    ShadowVerificationFlip(
        source_id="ke-source-bankless",
        endpoint_url="https://feeds.flightcast.com/p83fuj0y0u58o82l41xei7zo.xml",
        verified_at=_SESSION_2_VERIFIED_AT,
        verified_by=_TRANSCRIPT_VERIFIED_BY,
    ),
    ShadowVerificationFlip(
        source_id="ke-source-odd-lots",
        endpoint_url=(
            "https://www.omnycontent.com/d/playlist/e73c998e-6e60-432f-8610-ae210140c5b1/"
            "8a94442e-5a74-4fa2-8b8d-ae27003a8d6b/982f5071-765c-403d-969d-ae27003a8d83/podcast.rss"
        ),
        verified_at=_SESSION_2_VERIFIED_AT,
        verified_by=_TRANSCRIPT_VERIFIED_BY,
    ),
    ShadowVerificationFlip(
        source_id="ke-source-compound-and-friends",
        endpoint_url="https://feeds.megaphone.fm/TCP4771071679",
        verified_at=_SESSION_2_VERIFIED_AT,
        verified_by=_TRANSCRIPT_VERIFIED_BY,
    ),
)


@dataclass(frozen=True)
class ShadowBootstrapResult:
    migrations_applied: tuple[str, ...]
    sources_flipped_to_active: tuple[str, ...]
    endpoints_verified: tuple[str, ...]
    already_bootstrapped: tuple[str, ...]


def bootstrap_shadow_database(connection: sqlite3.Connection) -> ShadowBootstrapResult:
    """Apply pending migrations, then re-apply the nine Lane A verification flips.
    Safe to call repeatedly against the same connection -- the second call applies
    zero migrations (already recorded in `schema_migrations`) and zero flips
    (already `active`/verified), reporting those nine source_ids under
    `already_bootstrapped` instead.
    """
    applied = apply_migrations(connection)

    flipped: list[str] = []
    verified: list[str] = []
    already: list[str] = []
    for flip in LANE_A_SHADOW_VERIFICATION_FLIPS:
        source = ke.get_source(connection, flip.source_id)
        if source is None:
            raise ShadowBootstrapError(
                f"no ke_sources row for {flip.source_id!r} after migrations -- expected "
                "migrations 00022/00023 to have seeded the 9 Lane A launch sources"
            )
        if source["status"] == "trial":
            ke.update_source_status(connection, source_id=flip.source_id, new_status="active")
            flipped.append(flip.source_id)
        elif source["status"] == "active":
            already.append(flip.source_id)
        else:
            raise ShadowBootstrapError(
                f"{flip.source_id!r} is in unexpected status {source['status']!r}; this "
                "bootstrap only knows how to move trial -> active"
            )

        endpoints = ke.list_source_endpoints(connection, source_id=flip.source_id)
        matching = [endpoint for endpoint in endpoints if endpoint["url"] == flip.endpoint_url]
        if not matching:
            raise ShadowBootstrapError(
                f"no ke_source_endpoints row for source_id={flip.source_id!r}, "
                f"url={flip.endpoint_url!r}"
            )
        endpoint = matching[0]
        if endpoint["endpoint_verified_at"] is None:
            ke.record_endpoint_verification(
                connection,
                source_id=flip.source_id,
                endpoint_url=flip.endpoint_url,
                verified_at=flip.verified_at,
                verified_by=flip.verified_by,
            )
            verified.append(flip.source_id)

    return ShadowBootstrapResult(
        migrations_applied=tuple(migration.version for migration in applied),
        sources_flipped_to_active=tuple(flipped),
        endpoints_verified=tuple(verified),
        already_bootstrapped=tuple(already),
    )
