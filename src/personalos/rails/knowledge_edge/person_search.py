"""Lane B/C: broad third-party person-search provider -- deferred at launch.

Per `docs/knowledge_edge/PHASE0_PROVIDERS_AND_ACCESS.md` §3 (D-YT option 2), Session 1
approved *deferring* adoption of a broad, licensed third-party person/appearance
search provider rather than selecting one: no live provider research was possible
inside that packet's own no-network-requests constraint, and Lane B/C's launch
coverage is already carried by `youtube.py`'s two mechanisms -- official channel-
upload RSS/playlist polling (§10.3 allowlist) and the narrowed `search.list`
person-search client. What a broad-search provider would additionally buy is
coverage of a tracked person's appearance on a channel that is not on the approved
allowlist; §3 states that gap explicitly as a named, reported coverage limitation
("unapproved-channel gap") rather than something to silently absorb or route through
an unapproved credential.

This module intentionally contains no adapter, no client, no credential, and no
network-capable import. It exists purely as the named placeholder
`PHASE0_ARCHITECTURE_DECISIONS.md` AD-1's module layout already calls for
(`rails/knowledge_edge/person_search.py`, "currently: deferred, module stubs only"),
so a future packet that acts on §3's own "revisit trigger" (a Phase 2C shadow-mode
measurement showing person-appearance recall meaningfully hurt specifically by missed
non-allowlisted-channel appearances) has an obvious, pre-named location to build in --
not a reason to retrofit a new file into this package later. Nothing in this repo may
construct a live broad-search client until that trigger is met and a new
Session-gated decision selects and approves a specific vendor.
"""

from __future__ import annotations

BROAD_PERSON_SEARCH_PROVIDER_STATUS = "deferred_at_launch"


def is_broad_person_search_available() -> bool:
    """Always `False`. See module docstring: no broad third-party person-search
    provider is selected or approved, so nothing in this repo may treat one as
    available -- there is no vendor name, credential, or client to construct."""
    return False
