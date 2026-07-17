"""P-KE-2F: `ke_sources`/`ke_source_endpoints` seed data migration 00027 adds --
the four amendment §10.3 launch video/network channels (CNBC Television, Bloomberg
Television, Bloomberg Technology, Yahoo Finance) and the
`rails/knowledge_edge/youtube.py` person-search mechanism's own
`ke-source-youtube-person-search` row. Covers the migration's seeded data (byte-exact
source_id/channel_id/endpoint-url pinning, trial/NULL-verification posture) and
confirms `youtube.py`'s existing gating (`LiveYoutubeChannelAdapter`,
`LiveYoutubePersonSearchClient`) admits these exact rows once flipped to
active+verified through the sanctioned `state.registries` helpers, with no adapter
code change. Zero network requests anywhere in this file: every adapter exercised
below is constructed with a fake, in-process HTTP client.
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import personalos.knowledge_edge.state as ke
from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.rails.knowledge_edge.youtube import (
    DEFAULT_PERSON_SEARCH_SOURCE_ID,
    STATUS_CHANNEL_BLOCKED_SOURCE_NOT_VERIFIED,
    STATUS_SEARCH_BLOCKED_SOURCE_NOT_VERIFIED,
    YOUTUBE_CHANNEL_FEED_BASE_URL,
    YOUTUBE_SEARCH_ENDPOINT_URL,
    LiveYoutubeChannelAdapter,
    LiveYoutubePersonSearchClient,
)

NOW = datetime(2026, 7, 17, tzinfo=UTC)

# Channel identities Conductor-verified 2026-07-17 (YouTube channels.list forHandle
# lookups) -- the same table migration 00027's own header restates in prose. Kept
# here as an independent, hand-typed copy (not imported from the migration file)
# so a single mistyped character on either side of that duplication fails this test.
EXPECTED_CHANNEL_ID_BY_SOURCE_ID = {
    "ke-source-cnbc-television": "UCrp_UI8XtuYfpiqluWLD7Lw",
    "ke-source-bloomberg-television": "UCIALMKvObZNtJ6AmdCLP7Lg",
    "ke-source-bloomberg-technology": "UCrM7B7SL_g1edFOnmj-SDKg",
    "ke-source-yahoo-finance": "UCEAZeUIeJs0IjQiqTCdVSIg",
}

EXPECTED_CHANNEL_NAME_BY_SOURCE_ID = {
    "ke-source-cnbc-television": "CNBC Television",
    "ke-source-bloomberg-television": "Bloomberg Television",
    "ke-source-bloomberg-technology": "Bloomberg Technology",
    "ke-source-yahoo-finance": "Yahoo Finance",
}


class SeedDataTest(unittest.TestCase):
    def test_four_youtube_channel_sources_are_seeded_trial(self) -> None:
        with _migrated_connection() as connection:
            sources = {
                source["source_id"]: source
                for source in ke.list_sources(connection, lane="market_voices")
                if source["source_type"] == "youtube_channel"
            }
        self.assertEqual(set(sources), set(EXPECTED_CHANNEL_ID_BY_SOURCE_ID))
        for source_id, source in sources.items():
            self.assertEqual(source["status"], "trial")
            self.assertEqual(source["source_type"], "youtube_channel")
            self.assertEqual(source["lane"], "market_voices")
            self.assertEqual(source["name"], EXPECTED_CHANNEL_NAME_BY_SOURCE_ID[source_id])

    def test_channel_ids_are_byte_exact_pinned_to_the_verified_table(self) -> None:
        """Full source_id->channel_id mapping equality, not a per-row spot check --
        so a single mistyped character in any of the 4 channel IDs fails this test
        (house pattern: test_lane_a_endpoint_urls_are_byte_exact_pinned_to_the_
        ratified_table in tests/test_knowledge_edge_registries.py,
        test_specific_cik_values_are_byte_exact in
        tests/test_knowledge_edge_edgar_identifiers.py)."""
        with _migrated_connection() as connection:
            actual: dict[str, str] = {}
            for source_id in EXPECTED_CHANNEL_ID_BY_SOURCE_ID:
                endpoints = ke.list_source_endpoints(connection, source_id=source_id)
                self.assertEqual(len(endpoints), 1)
                endpoint = endpoints[0]
                self.assertEqual(endpoint["endpoint_type"], "channel_id")
                self.assertTrue(endpoint["is_primary"])
                self.assertEqual(endpoint["status"], "active")
                self.assertIsNone(endpoint["endpoint_verified_at"])
                self.assertIsNone(endpoint["verified_by"])
                actual[source_id] = endpoint["url"]

        self.assertEqual(actual, EXPECTED_CHANNEL_ID_BY_SOURCE_ID)

    def test_channel_endpoint_url_is_the_raw_channel_id_not_the_full_rss_url(self) -> None:
        """`youtube.py`'s own gating contract (`_evaluate_gates` comment,
        `_resolve_primary_channel_endpoint`'s `endpoint_type == 'channel_id'`
        filter): a `channel_id`-type endpoint's `url` column holds the bare
        identifier, and the adapter builds the RSS URL itself. A row that
        accidentally stored the full RSS URL here would silently defeat that
        filter (`STATUS_CHANNEL_BLOCKED_NO_ENDPOINT` forever, even once active)."""
        with _migrated_connection() as connection:
            for source_id, channel_id in EXPECTED_CHANNEL_ID_BY_SOURCE_ID.items():
                endpoint = ke.list_source_endpoints(connection, source_id=source_id)[0]
                self.assertEqual(endpoint["url"], channel_id)
                self.assertFalse(endpoint["url"].startswith("http"))
                constructed = f"{YOUTUBE_CHANNEL_FEED_BASE_URL}{endpoint['url']}"
                self.assertEqual(
                    constructed,
                    f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}",
                )

    def test_person_search_source_is_seeded_trial_matching_default_source_id(self) -> None:
        with _migrated_connection() as connection:
            source = ke.get_source(connection, DEFAULT_PERSON_SEARCH_SOURCE_ID)
            endpoints = ke.list_source_endpoints(
                connection, source_id=DEFAULT_PERSON_SEARCH_SOURCE_ID
            )

        self.assertEqual(DEFAULT_PERSON_SEARCH_SOURCE_ID, "ke-source-youtube-person-search")
        self.assertIsNotNone(source)
        self.assertEqual(source["status"], "trial")
        self.assertEqual(source["source_type"], "person_search_provider")
        self.assertEqual(source["lane"], "market_voices")

        self.assertEqual(len(endpoints), 1)
        endpoint = endpoints[0]
        self.assertEqual(endpoint["endpoint_type"], "api_endpoint")
        self.assertEqual(endpoint["url"], YOUTUBE_SEARCH_ENDPOINT_URL)
        self.assertEqual(endpoint["url"], "https://www.googleapis.com/youtube/v3/search")
        self.assertTrue(endpoint["is_primary"])
        self.assertEqual(endpoint["status"], "active")
        self.assertIsNone(endpoint["endpoint_verified_at"])
        self.assertIsNone(endpoint["verified_by"])

    def test_exactly_five_new_rows_no_scope_creep(self) -> None:
        """This packet's own hard constraint: nothing beyond the five rows (four
        youtube_channel sources + the one person_search_provider source)."""
        with _migrated_connection() as connection:
            channel_sources = [
                s for s in ke.list_sources(connection) if s["source_type"] == "youtube_channel"
            ]
            search_sources = [
                s for s in ke.list_sources(connection) if s["source_type"] == "person_search_provider"
            ]
        self.assertEqual(len(channel_sources), 4)
        self.assertEqual(len(search_sources), 1)


class ChannelAdapterGatingTest(unittest.TestCase):
    """Deliverable 3: confirm the existing (unmodified) `youtube.py` gating admits
    these exact seeded rows once a Conductor-supervised smoke flips them to
    active+verified through the sanctioned `state.registries` helpers -- and
    continues to refuse them beforehand. No fake client ever has its `fetch`
    invoked before verification (asserted via an error-raising fake), and after
    verification the fake response is fabricated in-process -- no real HTTP call
    is made anywhere in this test."""

    def test_seeded_trial_channel_source_refuses_before_conductor_verification(self) -> None:
        with _migrated_connection() as connection:
            client = _RefusingClient()
            adapter = LiveYoutubeChannelAdapter(connection, feature_mode="shadow_live", client=client)
            result = adapter.fetch_uploads(
                source_id="ke-source-cnbc-television", cursor=None, now=NOW
            )
        self.assertFalse(result.healthy)
        self.assertIn(STATUS_CHANNEL_BLOCKED_SOURCE_NOT_VERIFIED, result.error_summary)
        self.assertEqual(client.calls, [])

    def test_sanctioned_verification_helpers_admit_the_channel_source_no_adapter_change(
        self,
    ) -> None:
        with _migrated_connection() as connection:
            ke.record_endpoint_verification(
                connection,
                source_id="ke-source-cnbc-television",
                endpoint_url="UCrp_UI8XtuYfpiqluWLD7Lw",
                verified_at="2026-07-17T12:00:00+00:00",
                verified_by="conductor:2026-07-17-packet-2f-smoke",
            )
            ke.update_source_status(
                connection, source_id="ke-source-cnbc-television", new_status="active"
            )

            client = _FakeChannelClient(body=_CHANNEL_FEED_ONE_ENTRY)
            adapter = LiveYoutubeChannelAdapter(connection, feature_mode="shadow_live", client=client)
            result = adapter.fetch_uploads(
                source_id="ke-source-cnbc-television", cursor=None, now=NOW
            )

        self.assertTrue(result.healthy)
        self.assertEqual(len(client.calls), 1)
        self.assertIn("channel_id=UCrp_UI8XtuYfpiqluWLD7Lw", client.calls[0])
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].source_id, "ke-source-cnbc-television")

    def test_all_four_channel_sources_admit_once_verified(self) -> None:
        with _migrated_connection() as connection:
            for source_id, channel_id in EXPECTED_CHANNEL_ID_BY_SOURCE_ID.items():
                ke.record_endpoint_verification(
                    connection,
                    source_id=source_id,
                    endpoint_url=channel_id,
                    verified_at="2026-07-17T12:00:00+00:00",
                    verified_by="conductor:2026-07-17-packet-2f-smoke",
                )
                ke.update_source_status(connection, source_id=source_id, new_status="active")

            for source_id, channel_id in EXPECTED_CHANNEL_ID_BY_SOURCE_ID.items():
                client = _FakeChannelClient(body=_CHANNEL_FEED_ONE_ENTRY)
                adapter = LiveYoutubeChannelAdapter(
                    connection, feature_mode="shadow_live", client=client
                )
                result = adapter.fetch_uploads(source_id=source_id, cursor=None, now=NOW)
                self.assertTrue(result.healthy, msg=source_id)
                self.assertIn(f"channel_id={channel_id}", client.calls[0])


class PersonSearchGatingTest(unittest.TestCase):
    """Deliverable 1/3 combined: migration 00027 closes the 2B smoke's own
    `STATUS_SEARCH_BLOCKED_SOURCE_NOT_FOUND` block (see
    docs/knowledge_edge/PACKET_2B_YOUTUBE_SUPERVISED_SMOKE.md Sec0) -- the row now
    exists, so the gate that fires pre-verification is
    `STATUS_SEARCH_BLOCKED_SOURCE_NOT_VERIFIED`, not source-not-found."""

    def test_source_not_found_block_is_closed(self) -> None:
        with _migrated_connection() as connection:
            source = ke.get_source(connection, DEFAULT_PERSON_SEARCH_SOURCE_ID)
        self.assertIsNotNone(source)

    def test_seeded_trial_search_source_refuses_before_conductor_verification(self) -> None:
        with _migrated_connection() as connection:
            client = _RefusingClient()
            with _env_var_set("PERSONALOS_RAIL_KE_YOUTUBE_API_KEY", "fake-key-not-real"):
                search_client = LiveYoutubePersonSearchClient(
                    connection, feature_mode="shadow_live", client=client
                )
                outcome = search_client.search_person(person_id="ke-person-kevin-warsh", query="Kevin Warsh", now=NOW)

        self.assertFalse(outcome.healthy)
        self.assertIn(STATUS_SEARCH_BLOCKED_SOURCE_NOT_VERIFIED, outcome.error_summary)
        self.assertEqual(client.calls, [])

    def test_sanctioned_verification_helpers_admit_the_search_source_no_adapter_change(
        self,
    ) -> None:
        with _migrated_connection() as connection:
            ke.record_endpoint_verification(
                connection,
                source_id=DEFAULT_PERSON_SEARCH_SOURCE_ID,
                endpoint_url="https://www.googleapis.com/youtube/v3/search",
                verified_at="2026-07-17T12:00:00+00:00",
                verified_by="conductor:2026-07-17-packet-2f-smoke",
            )
            ke.update_source_status(
                connection, source_id=DEFAULT_PERSON_SEARCH_SOURCE_ID, new_status="active"
            )

            client = _FakeSearchClient(body=_SEARCH_RESPONSE_ONE_ITEM)
            with _env_var_set("PERSONALOS_RAIL_KE_YOUTUBE_API_KEY", "fake-key-not-real"):
                search_client = LiveYoutubePersonSearchClient(
                    connection, feature_mode="shadow_live", client=client
                )
                outcome = search_client.search_person(
                    person_id="ke-person-kevin-warsh", query="Kevin Warsh", now=NOW
                )

        self.assertTrue(outcome.healthy)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(len(outcome.results), 1)


class _RefusingClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def fetch(self, url: str) -> bytes:
        self.calls.append(url)
        raise AssertionError("client must not be called before Conductor verification")


class _FakeChannelClient:
    def __init__(self, *, body: bytes) -> None:
        self.calls: list[str] = []
        self._body = body

    def fetch(self, url: str) -> bytes:
        self.calls.append(url)
        return self._body


class _FakeSearchClient:
    def __init__(self, *, body: bytes) -> None:
        self.calls: list[str] = []
        self._body = body

    def fetch(self, url: str) -> bytes:
        self.calls.append(url)
        return self._body


_CHANNEL_FEED_ONE_ENTRY = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns:media="http://search.yahoo.com/mrss/" xmlns="http://www.w3.org/2005/Atom">
<entry>
  <id>yt:video:vid-1</id>
  <yt:videoId>vid-1</yt:videoId>
  <title>Test Video</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=vid-1"/>
  <published>2026-06-01T10:00:00+00:00</published>
</entry>
</feed>
"""

_SEARCH_RESPONSE_ONE_ITEM = (
    b'{"items": [{"id": {"videoId": "vid-1"}, "snippet": {"title": "Kevin Warsh remarks", '
    b'"channelId": "UCabc123", "channelTitle": "Some Channel", "publishedAt": '
    b'"2026-06-01T10:00:00Z", "description": "desc"}}]}'
)


@contextmanager
def _env_var_set(name: str, value: str) -> Iterator[None]:
    import os

    previous = os.environ.get(name)
    os.environ[name] = value
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous


def _config_for(runtime_dir: Path, environment: Environment) -> PersonalOSConfig:
    directory_name = "dev" if environment is Environment.DEVELOPMENT else "test"
    return PersonalOSConfig(
        environment=environment,
        timezone=DEFAULT_TIMEZONE,
        database_path=runtime_dir / directory_name / "personalos.sqlite3",
    )


@contextmanager
def _migrated_connection() -> Iterator[sqlite3.Connection]:
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir) / "runtime"
        config = _config_for(runtime_dir, Environment.TEST)
        connection = connect_sqlite(config, runtime_dir=runtime_dir)
        try:
            apply_migrations(connection)
            yield connection
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
