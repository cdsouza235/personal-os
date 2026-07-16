"""Deduplication / canonical grouping (amendment §11.4).

Pure functions only: no I/O, no clock reads. Operates on plain mappings so it has
no dependency on the adapter contracts or the state layer's row shape beyond the
handful of keys documented below.

Every function here only *evaluates* evidence; nothing suppresses anything by
itself -- the scan orchestrator is responsible for acting on the returned verdicts
(recording a ``canonical_group`` membership, or attaching a ``suspected_duplicate``
note without suppressing).

Expected keys on a "candidate" mapping (subset of ``ke_media_items`` fields plus the
adapter-only fields that never reach the database):

- ``media_item_id`` (existing rows only)
- ``dedupe_key``
- ``feed_guid`` (nullable)
- ``underlying_id`` (nullable) -- a stable ID shared by audio/video/clip/repost
  versions of literally the same recorded content
- ``is_replay_of_underlying_id`` (nullable) -- explicit adapter signal that this
  item is the official replay of the live item carrying that ``underlying_id``
- ``title``
- ``matched_person_id`` (nullable)
- ``published_at`` (nullable ISO-8601 string)
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from personalos.knowledge_edge.state.media import CANONICAL_GROUP_DEDUPE_RULES

SUSPECTED_DUPLICATE_WINDOW_HOURS = 48


@dataclass(frozen=True)
class DuplicateEvidence:
    rule: str
    existing_media_item_id: str


def find_duplicate_evidence(
    *, new_item: Mapping, existing_items: Sequence[Mapping]
) -> DuplicateEvidence | None:
    """Return the first deterministic-evidence duplicate match, or ``None``.

    Evidence rules are evaluated in a fixed priority order so the result is
    reproducible even when more than one rule could technically apply. Weaker,
    non-deterministic similarity never appears here -- see
    :func:`find_suspected_duplicate` for that.
    """
    feed_guid = new_item.get("feed_guid")
    underlying_id = new_item.get("underlying_id")
    replay_of = new_item.get("is_replay_of_underlying_id")

    if feed_guid is not None:
        for existing in existing_items:
            if existing.get("feed_guid") == feed_guid and existing["dedupe_key"] != new_item["dedupe_key"]:
                return DuplicateEvidence(rule="shared_feed_guid", existing_media_item_id=existing["media_item_id"])

    if replay_of is not None:
        for existing in existing_items:
            if existing.get("underlying_id") == replay_of:
                return DuplicateEvidence(
                    rule="live_and_official_replay", existing_media_item_id=existing["media_item_id"]
                )

    if underlying_id is not None:
        for existing in existing_items:
            if existing.get("underlying_id") != underlying_id:
                continue
            if existing["dedupe_key"] == new_item["dedupe_key"]:
                continue
            if existing.get("title") != new_item.get("title"):
                return DuplicateEvidence(
                    rule="same_underlying_id_title_change", existing_media_item_id=existing["media_item_id"]
                )
            return DuplicateEvidence(
                rule="same_channel_video_id", existing_media_item_id=existing["media_item_id"]
            )

    return None


def find_suspected_duplicate(
    *,
    new_item: Mapping,
    existing_items: Sequence[Mapping],
    window_hours: int = SUSPECTED_DUPLICATE_WINDOW_HOURS,
) -> str | None:
    """Return a human-readable reason for a *weak* duplicate signal, or ``None``.

    Weak signals never suppress anything (§11.4: "grouped visually, never silently
    suppressed") -- callers attach the reason as a visible note only. A weak signal
    is: same normalized title, same matched person, published within
    ``window_hours`` of each other, but no deterministic identifier in common
    (otherwise :func:`find_duplicate_evidence` would already have matched it).
    """
    new_title = (new_item.get("title") or "").strip().lower()
    new_person = new_item.get("matched_person_id")
    new_published = new_item.get("published_at")
    if not new_title or new_person is None or new_published is None:
        return None
    new_published_dt = datetime.fromisoformat(new_published)

    for existing in existing_items:
        if existing["dedupe_key"] == new_item["dedupe_key"]:
            continue
        if (existing.get("title") or "").strip().lower() != new_title:
            continue
        if existing.get("matched_person_id") != new_person:
            continue
        existing_published = existing.get("published_at")
        if existing_published is None:
            continue
        existing_published_dt = datetime.fromisoformat(existing_published)
        delta_hours = abs((new_published_dt - existing_published_dt).total_seconds()) / 3600.0
        if delta_hours <= window_hours:
            return (
                f"suspected_duplicate: same title/person as {existing['media_item_id']} "
                f"within {window_hours}h, no deterministic identifier shared"
            )
    return None


assert set(CANONICAL_GROUP_DEDUPE_RULES) >= {
    "shared_feed_guid",
    "same_channel_video_id",
    "same_underlying_id_title_change",
    "live_and_official_replay",
}
