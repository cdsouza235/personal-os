"""P-KE-2A: live podcast RSS/Atom rail adapter.

No real network call is ever made in this suite: every gate-isolation test injects a
fake `client` (bypassing `urllib` entirely, mirroring `test_rails_todoist.py`'s
`_RecordingFakeClient`), and the HTTP-mechanics tests inject a fake `opener` into
`PodcastFeedHttpClient` (mirroring that same file's `_RecordingOpener`/
`_FailingOpener`) so the real request-construction path is proven without ever
touching a socket.
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
import urllib.error
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.rails.knowledge_edge.podcasts import (
    DEFAULT_LANE_A_FEATURE_MODE,
    LANE_A_FEATURE_MODES,
    PODCAST_RAIL_CREDENTIAL_ENV_VAR,
    STATUS_BLOCKED_CREDENTIAL_EMPTY,
    STATUS_BLOCKED_CREDENTIAL_MISSING,
    STATUS_BLOCKED_ENDPOINT_INSECURE_SCHEME,
    STATUS_BLOCKED_FEATURE_MODE,
    STATUS_BLOCKED_NO_ENDPOINT,
    STATUS_BLOCKED_SOURCE_NOT_FOUND,
    STATUS_BLOCKED_SOURCE_NOT_VERIFIED,
    STATUS_FETCH_MALFORMED_FEED,
    STATUS_FETCH_REDIRECT_QUARANTINED,
    STATUS_FETCH_RESPONSE_TOO_LARGE,
    STATUS_FETCH_TRANSPORT_FAILED,
    LivePodcastFeedAdapter,
    MalformedFeedError,
    PodcastFeedHttpClient,
    PodcastFeedRedirectQuarantined,
    PodcastFeedResponseTooLarge,
    _extract_host,
    _HostConfinedRedirectHandler,
    _parse_feed_document,
    validate_lane_a_feature_mode,
)

NOW = datetime(2026, 7, 16, tzinfo=UTC)
FAKE_USER_AGENT = "PersonalOS-KnowledgeEdge-Test/1.0 (test@example.com)"  # not a real credential

RSS_FEED_BASIC = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
<channel>
<title>Test Podcast</title>
<item>
  <title>Episode One</title>
  <link>https://feeds.example.com/ep-1</link>
  <guid>guid-ep-1</guid>
  <pubDate>Mon, 01 Jun 2026 10:00:00 +0000</pubDate>
  <description>First episode description.</description>
  <itunes:duration>32:15</itunes:duration>
  <itunes:episode>1</itunes:episode>
  <enclosure url="https://feeds.example.com/ep-1.mp3" type="audio/mpeg" length="123"/>
</item>
<item>
  <title>Episode Two</title>
  <link>https://feeds.example.com/ep-2</link>
  <guid>guid-ep-2</guid>
  <pubDate>Mon, 08 Jun 2026 10:00:00 +0000</pubDate>
  <description>Second episode description.</description>
  <itunes:duration>45:00</itunes:duration>
  <itunes:episode>2</itunes:episode>
  <enclosure url="https://feeds.example.com/ep-2.mp3" type="audio/mpeg" length="123"/>
</item>
<item>
  <title>Episode Two (Corrected)</title>
  <link>https://feeds.example.com/ep-2-corrected</link>
  <guid>guid-ep-2-corrected</guid>
  <pubDate>Tue, 09 Jun 2026 09:00:00 +0000</pubDate>
  <description>Corrected re-upload of episode two.</description>
  <itunes:duration>44:50</itunes:duration>
  <itunes:episode>2</itunes:episode>
  <enclosure url="https://feeds.example.com/ep-2-corrected.mp3" type="audio/mpeg" length="123"/>
</item>
</channel>
</rss>
"""

RSS_FEED_VIDEO_ENCLOSURE = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
<channel>
<item>
  <title>Video Episode</title>
  <link>https://feeds.example.com/vid-1</link>
  <guid>guid-vid-1</guid>
  <pubDate>Mon, 01 Jun 2026 10:00:00 +0000</pubDate>
  <description>A video episode.</description>
  <enclosure url="https://feeds.example.com/vid-1.mp4" type="video/mp4" length="456"/>
</item>
</channel>
</rss>
"""

RSS_FEED_DUPLICATE_GUID = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<item>
  <title>Episode One</title>
  <link>https://feeds.example.com/ep-1</link>
  <guid>guid-dupe</guid>
  <pubDate>Mon, 01 Jun 2026 10:00:00 +0000</pubDate>
</item>
<item>
  <title>Episode One (repeated guid)</title>
  <link>https://feeds.example.com/ep-1-again</link>
  <guid>guid-dupe</guid>
  <pubDate>Tue, 02 Jun 2026 10:00:00 +0000</pubDate>
</item>
</channel>
</rss>
"""

RSS_FEED_MISSING_FIELDS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<item>
  <title>Missing guid</title>
  <link>https://feeds.example.com/no-guid</link>
  <pubDate>Mon, 01 Jun 2026 10:00:00 +0000</pubDate>
</item>
<item>
  <guid>guid-no-title</guid>
  <link>https://feeds.example.com/no-title</link>
  <pubDate>Mon, 01 Jun 2026 10:00:00 +0000</pubDate>
</item>
<item>
  <title>Missing pubDate</title>
  <link>https://feeds.example.com/no-pubdate</link>
  <guid>guid-no-pubdate</guid>
</item>
</channel>
</rss>
"""

ATOM_FEED_BASIC = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title>Test Atom Podcast</title>
<entry>
  <id>atom-guid-1</id>
  <title>Atom Episode One</title>
  <link href="https://feeds.example.com/atom-ep-1" rel="alternate"/>
  <published>2026-06-01T10:00:00Z</published>
  <summary>Atom summary text.</summary>
</entry>
</feed>
"""

MALFORMED_NOT_XML = b"not xml at all {{{"
MALFORMED_DOCTYPE = (
    b'<?xml version="1.0"?><!DOCTYPE rss ['
    b'<!ENTITY xxe SYSTEM "file:///etc/passwd">]><rss><channel></channel></rss>'
)
MALFORMED_UNSUPPORTED_ROOT = b'<?xml version="1.0"?><foo></foo>'
MALFORMED_RSS_NO_CHANNEL = b'<?xml version="1.0"?><rss version="2.0"></rss>'


class _FakePodcastClient:
    """Bypass client (no urllib at all) used by the gate-isolation tests."""

    def __init__(self, *, body: bytes = RSS_FEED_BASIC, error: Exception | None = None) -> None:
        self.calls: list[tuple[str, str]] = []
        self._body = body
        self._error = error

    def fetch(self, url: str, *, user_agent: str) -> bytes:
        self.calls.append((url, user_agent))
        if self._error is not None:
            raise self._error
        return self._body


class _RecordingOpener:
    def __init__(self, *, body: bytes = RSS_FEED_BASIC) -> None:
        self.requests: list = []
        self._body = body

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        return _FakeHTTPResponse(self._body)


class _FailingOpener:
    def __call__(self, request, timeout=None):
        raise urllib.error.URLError("simulated network failure")


class _FakeHTTPResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self, amt: int | None = None) -> bytes:
        return self._body if amt is None else self._body[:amt]

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False


class ParseFeedDocumentTest(unittest.TestCase):
    def test_parses_rss_basic_feed_in_document_order(self) -> None:
        episodes = _parse_feed_document(RSS_FEED_BASIC)
        self.assertEqual([episode.guid for episode in episodes], ["guid-ep-1", "guid-ep-2", "guid-ep-2-corrected"])
        first = episodes[0]
        self.assertEqual(first.title, "Episode One")
        self.assertEqual(first.canonical_url, "https://feeds.example.com/ep-1")
        self.assertEqual(first.duration_seconds, 32 * 60 + 15)
        self.assertEqual(first.underlying_id, "1")
        self.assertEqual(first.media_type, "podcast_episode")
        self.assertEqual(first.published_at, "2026-06-01T10:00:00+00:00")

    def test_corrected_reissue_shares_underlying_id_but_has_distinct_guid(self) -> None:
        episodes = _parse_feed_document(RSS_FEED_BASIC)
        original = episodes[1]
        corrected = episodes[2]
        self.assertNotEqual(original.guid, corrected.guid)
        self.assertEqual(original.underlying_id, corrected.underlying_id)
        self.assertNotEqual(original.title, corrected.title)

    def test_video_enclosure_sets_video_media_type(self) -> None:
        episodes = _parse_feed_document(RSS_FEED_VIDEO_ENCLOSURE)
        self.assertEqual(episodes[0].media_type, "video_interview")

    def test_items_missing_required_fields_are_skipped_not_fatal(self) -> None:
        episodes = _parse_feed_document(RSS_FEED_MISSING_FIELDS)
        self.assertEqual(episodes, [])

    def test_atom_feed_parses(self) -> None:
        episodes = _parse_feed_document(ATOM_FEED_BASIC)
        self.assertEqual(len(episodes), 1)
        entry = episodes[0]
        self.assertEqual(entry.guid, "atom-guid-1")
        self.assertEqual(entry.canonical_url, "https://feeds.example.com/atom-ep-1")
        self.assertEqual(entry.published_at, "2026-06-01T10:00:00+00:00")
        self.assertEqual(entry.description_excerpt, "Atom summary text.")

    def test_not_well_formed_xml_raises_malformed_feed_error(self) -> None:
        with self.assertRaises(MalformedFeedError):
            _parse_feed_document(MALFORMED_NOT_XML)

    def test_doctype_declaration_is_refused(self) -> None:
        with self.assertRaises(MalformedFeedError):
            _parse_feed_document(MALFORMED_DOCTYPE)

    def test_unsupported_root_element_raises_malformed_feed_error(self) -> None:
        with self.assertRaises(MalformedFeedError):
            _parse_feed_document(MALFORMED_UNSUPPORTED_ROOT)

    def test_rss_without_channel_raises_malformed_feed_error(self) -> None:
        with self.assertRaises(MalformedFeedError):
            _parse_feed_document(MALFORMED_RSS_NO_CHANNEL)


class ValidateLaneAFeatureModeTest(unittest.TestCase):
    def test_accepts_every_documented_mode(self) -> None:
        for mode in LANE_A_FEATURE_MODES:
            self.assertEqual(validate_lane_a_feature_mode(mode), mode)

    def test_rejects_unknown_mode(self) -> None:
        with self.assertRaises(ValueError):
            validate_lane_a_feature_mode("live")


class ExtractHostTest(unittest.TestCase):
    def test_plain_host(self) -> None:
        self.assertEqual(_extract_host("https://feeds.example.com/feed.xml"), "feeds.example.com")

    def test_host_with_port_and_userinfo_and_case(self) -> None:
        self.assertEqual(_extract_host("HTTPS://User:Pw@Feeds.Example.com:443/feed.xml"), "feeds.example.com")


class HostConfinedRedirectHandlerTest(unittest.TestCase):
    def test_same_host_redirect_is_not_quarantined(self) -> None:
        handler = _HostConfinedRedirectHandler("feeds.example.com")
        # super().redirect_request builds a plain GET Request for the new URL when the
        # method/code combination permits it; no network I/O happens here.
        result = handler.redirect_request(
            _FakeRequest(), None, 302, "Found", {}, "https://feeds.example.com/feed-new.xml"
        )
        self.assertEqual(result.full_url, "https://feeds.example.com/feed-new.xml")

    def test_cross_host_redirect_is_quarantined(self) -> None:
        handler = _HostConfinedRedirectHandler("feeds.example.com")
        with self.assertRaises(PodcastFeedRedirectQuarantined):
            handler.redirect_request(
                _FakeRequest(), None, 302, "Found", {}, "https://evil.example.net/feed.xml"
            )


class _FakeRequest:
    """Minimal stand-in for `urllib.request.Request`, enough for
    `HTTPRedirectHandler.redirect_request`'s own logic to run without a real request."""

    def __init__(self) -> None:
        self.full_url = "https://feeds.example.com/feed.xml"
        self.headers: dict[str, str] = {}
        self.unredirected_hdrs: dict[str, str] = {}
        self.origin_req_host = "feeds.example.com"
        self.unverifiable = False

    def get_method(self) -> str:
        return "GET"

    def has_header(self, name: str) -> bool:
        return name in self.headers

    def get_full_url(self) -> str:
        return self.full_url


class PodcastFeedHttpClientTest(unittest.TestCase):
    def test_fetch_sends_expected_request_shape(self) -> None:
        opener = _RecordingOpener()
        client = PodcastFeedHttpClient(opener=opener)
        body = client.fetch("https://feeds.example.com/feed.xml", user_agent=FAKE_USER_AGENT)

        self.assertEqual(body, RSS_FEED_BASIC)
        self.assertEqual(len(opener.requests), 1)
        sent = opener.requests[0]
        self.assertEqual(sent.full_url, "https://feeds.example.com/feed.xml")
        self.assertEqual(sent.get_method(), "GET")
        self.assertEqual(sent.get_header("User-agent"), FAKE_USER_AGENT)

    def test_fetch_converts_transport_failure(self) -> None:
        client = PodcastFeedHttpClient(opener=_FailingOpener())
        with self.assertRaises(urllib.error.URLError):
            client.fetch("https://feeds.example.com/feed.xml", user_agent=FAKE_USER_AGENT)

    def test_fetch_enforces_response_size_cap(self) -> None:
        big_body = b"x" * 100
        opener = _RecordingOpener(body=big_body)
        client = PodcastFeedHttpClient(opener=opener, max_response_bytes=10)
        with self.assertRaises(PodcastFeedResponseTooLarge):
            client.fetch("https://feeds.example.com/feed.xml", user_agent=FAKE_USER_AGENT)


class LivePodcastFeedAdapterGateTest(unittest.TestCase):
    def test_disabled_feature_mode_refuses_before_touching_db_or_client(self) -> None:
        with _migrated_test_connection() as connection:
            client = _FakePodcastClient(error=AssertionError("client must not be called"))
            adapter = LivePodcastFeedAdapter(
                connection, feature_mode="disabled", client=client
            )
            with mock.patch.dict("os.environ", {PODCAST_RAIL_CREDENTIAL_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_episodes(source_id="ke-source-dwarkesh-podcast", cursor=None, now=NOW)

            self.assertFalse(result.healthy)
            self.assertIn(STATUS_BLOCKED_FEATURE_MODE, result.error_summary)
            self.assertEqual(client.calls, [])

    def test_fixture_feature_mode_also_refuses(self) -> None:
        with _migrated_test_connection() as connection:
            client = _FakePodcastClient(error=AssertionError("client must not be called"))
            adapter = LivePodcastFeedAdapter(connection, feature_mode="fixture", client=client)
            with mock.patch.dict("os.environ", {PODCAST_RAIL_CREDENTIAL_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_episodes(source_id="ke-source-dwarkesh-podcast", cursor=None, now=NOW)

            self.assertFalse(result.healthy)
            self.assertIn(STATUS_BLOCKED_FEATURE_MODE, result.error_summary)
            self.assertEqual(client.calls, [])

    def test_default_constructor_feature_mode_is_disabled(self) -> None:
        self.assertEqual(DEFAULT_LANE_A_FEATURE_MODE, "disabled")
        with _migrated_test_connection() as connection:
            adapter = LivePodcastFeedAdapter(connection)
            with mock.patch.dict("os.environ", {PODCAST_RAIL_CREDENTIAL_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_episodes(source_id="ke-source-dwarkesh-podcast", cursor=None, now=NOW)
            self.assertFalse(result.healthy)
            self.assertIn(STATUS_BLOCKED_FEATURE_MODE, result.error_summary)

    def test_missing_credential_env_var_refuses(self) -> None:
        with _migrated_test_connection() as connection:
            client = _FakePodcastClient(error=AssertionError("client must not be called"))
            adapter = LivePodcastFeedAdapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {}, clear=False):
                import os

                os.environ.pop(PODCAST_RAIL_CREDENTIAL_ENV_VAR, None)
                result = adapter.fetch_episodes(source_id="ke-source-dwarkesh-podcast", cursor=None, now=NOW)

            self.assertFalse(result.healthy)
            self.assertIn(STATUS_BLOCKED_CREDENTIAL_MISSING, result.error_summary)
            self.assertEqual(client.calls, [])

    def test_empty_credential_env_var_refuses(self) -> None:
        with _migrated_test_connection() as connection:
            client = _FakePodcastClient(error=AssertionError("client must not be called"))
            adapter = LivePodcastFeedAdapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {PODCAST_RAIL_CREDENTIAL_ENV_VAR: "   "}):
                result = adapter.fetch_episodes(source_id="ke-source-dwarkesh-podcast", cursor=None, now=NOW)

            self.assertFalse(result.healthy)
            self.assertIn(STATUS_BLOCKED_CREDENTIAL_EMPTY, result.error_summary)
            self.assertEqual(client.calls, [])

    def test_unknown_source_id_refuses(self) -> None:
        with _migrated_test_connection() as connection:
            client = _FakePodcastClient(error=AssertionError("client must not be called"))
            adapter = LivePodcastFeedAdapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {PODCAST_RAIL_CREDENTIAL_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_episodes(source_id="ke-source-does-not-exist", cursor=None, now=NOW)

            self.assertFalse(result.healthy)
            self.assertIn(STATUS_BLOCKED_SOURCE_NOT_FOUND, result.error_summary)
            self.assertEqual(client.calls, [])

    def test_trial_source_with_no_endpoint_verification_refuses_and_names_it(self) -> None:
        # migration 00022/00023's actual seeded state: 'trial' status, endpoint present
        # but endpoint_verified_at is NULL. This is the real, current state of every
        # one of the 9 launch feeds today -- nothing can fetch from any of them yet.
        with _migrated_test_connection() as connection:
            client = _FakePodcastClient(error=AssertionError("client must not be called"))
            adapter = LivePodcastFeedAdapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {PODCAST_RAIL_CREDENTIAL_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_episodes(
                    source_id="ke-source-dwarkesh-podcast", cursor=None, now=NOW
                )

            self.assertFalse(result.healthy)
            self.assertIn(STATUS_BLOCKED_SOURCE_NOT_VERIFIED, result.error_summary)
            self.assertIn("trial", result.error_summary)
            self.assertIn("endpoint_verified_at", result.error_summary)
            self.assertEqual(client.calls, [])

    def test_source_with_no_active_endpoint_refuses(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_source(connection, source_id="src-no-endpoint", status="active")
            client = _FakePodcastClient(error=AssertionError("client must not be called"))
            adapter = LivePodcastFeedAdapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {PODCAST_RAIL_CREDENTIAL_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_episodes(source_id="src-no-endpoint", cursor=None, now=NOW)

            self.assertFalse(result.healthy)
            self.assertIn(STATUS_BLOCKED_NO_ENDPOINT, result.error_summary)

    def test_verified_at_set_but_verified_by_empty_refuses(self) -> None:
        # Codex iteration-3 audit condition 2: a timestamp alone is not a completed
        # verification record -- an empty/blank verifier must refuse exactly like the
        # both-NULL case, never treated as "close enough".
        with _migrated_test_connection() as connection:
            _seed_verified_source(
                connection,
                source_id="src-verified-by-empty",
                url="https://feeds.example.com/feed.xml",
                endpoint_verified_at="2026-07-16T00:00:00+00:00",
                verified_by="   ",
            )
            client = _FakePodcastClient(error=AssertionError("client must not be called"))
            adapter = LivePodcastFeedAdapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {PODCAST_RAIL_CREDENTIAL_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_episodes(
                    source_id="src-verified-by-empty", cursor=None, now=NOW
                )

            self.assertFalse(result.healthy)
            self.assertIn(STATUS_BLOCKED_SOURCE_NOT_VERIFIED, result.error_summary)
            self.assertEqual(client.calls, [])

    def test_malformed_verification_timestamp_refuses(self) -> None:
        # A non-empty verifier with an unparseable timestamp must not be trusted as a
        # completed supervised-smoke record.
        with _migrated_test_connection() as connection:
            _seed_verified_source(
                connection,
                source_id="src-malformed-timestamp",
                url="https://feeds.example.com/feed.xml",
                endpoint_verified_at="not-a-timestamp",
                verified_by="tests",
            )
            client = _FakePodcastClient(error=AssertionError("client must not be called"))
            adapter = LivePodcastFeedAdapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {PODCAST_RAIL_CREDENTIAL_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_episodes(
                    source_id="src-malformed-timestamp", cursor=None, now=NOW
                )

            self.assertFalse(result.healthy)
            self.assertIn(STATUS_BLOCKED_SOURCE_NOT_VERIFIED, result.error_summary)
            self.assertIn("not a parseable timestamp", result.error_summary)
            self.assertEqual(client.calls, [])

    def test_http_endpoint_refuses_even_when_fully_verified(self) -> None:
        # Codex iteration-3 audit condition 2: https:// is enforced independently of
        # verification state -- a fully-verified http:// endpoint still refuses.
        with _migrated_test_connection() as connection:
            _seed_verified_source(
                connection,
                source_id="src-insecure-scheme",
                url="http://feeds.example.com/feed.xml",
            )
            client = _FakePodcastClient(error=AssertionError("client must not be called"))
            adapter = LivePodcastFeedAdapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {PODCAST_RAIL_CREDENTIAL_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_episodes(
                    source_id="src-insecure-scheme", cursor=None, now=NOW
                )

            self.assertFalse(result.healthy)
            self.assertIn(STATUS_BLOCKED_ENDPOINT_INSECURE_SCHEME, result.error_summary)
            self.assertIn("http://feeds.example.com/feed.xml", result.error_summary)
            self.assertEqual(client.calls, [])

    def test_active_source_with_verified_endpoint_reaches_client_and_parses(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_source(
                connection, source_id="src-verified", url="https://feeds.example.com/feed.xml"
            )
            client = _FakePodcastClient(body=RSS_FEED_BASIC)
            adapter = LivePodcastFeedAdapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {PODCAST_RAIL_CREDENTIAL_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_episodes(source_id="src-verified", cursor=None, now=NOW)

            self.assertTrue(result.healthy)
            self.assertEqual(len(client.calls), 1)
            called_url, called_user_agent = client.calls[0]
            self.assertEqual(called_url, "https://feeds.example.com/feed.xml")
            self.assertEqual(called_user_agent, FAKE_USER_AGENT)
            self.assertEqual(len(result.items), 3)
            self.assertEqual(result.items[0].source_id, "src-verified")
            self.assertEqual(result.items[0].feed_guid, result.items[0].source_specific_id)
            self.assertEqual(result.next_cursor_value, result.items[-1].cursor_value)

    def test_active_read_only_and_obsidian_modes_also_admit_live_fetch(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_source(
                connection, source_id="src-verified", url="https://feeds.example.com/feed.xml"
            )
            for mode in ("active_read_only", "active_with_obsidian_handoff"):
                client = _FakePodcastClient(body=RSS_FEED_BASIC)
                adapter = LivePodcastFeedAdapter(connection, feature_mode=mode, client=client)
                with mock.patch.dict("os.environ", {PODCAST_RAIL_CREDENTIAL_ENV_VAR: FAKE_USER_AGENT}):
                    result = adapter.fetch_episodes(source_id="src-verified", cursor=None, now=NOW)
                self.assertTrue(result.healthy, msg=f"mode={mode}")
                self.assertEqual(len(client.calls), 1, msg=f"mode={mode}")

    def test_cursor_filters_out_already_seen_items(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_source(
                connection, source_id="src-verified", url="https://feeds.example.com/feed.xml"
            )
            client = _FakePodcastClient(body=RSS_FEED_BASIC)
            adapter = LivePodcastFeedAdapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {PODCAST_RAIL_CREDENTIAL_ENV_VAR: FAKE_USER_AGENT}):
                first = adapter.fetch_episodes(source_id="src-verified", cursor=None, now=NOW)
                second = adapter.fetch_episodes(
                    source_id="src-verified", cursor=first.next_cursor_value, now=NOW
                )

            self.assertEqual(second.items, ())
            self.assertEqual(second.next_cursor_value, first.next_cursor_value)

    def test_max_items_per_fetch_bounds_batch_and_advances_cursor_partially(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_source(
                connection, source_id="src-verified", url="https://feeds.example.com/feed.xml"
            )
            client = _FakePodcastClient(body=RSS_FEED_BASIC)
            adapter = LivePodcastFeedAdapter(
                connection, feature_mode="shadow_live", client=client, max_items_per_fetch=2
            )
            with mock.patch.dict("os.environ", {PODCAST_RAIL_CREDENTIAL_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_episodes(source_id="src-verified", cursor=None, now=NOW)

            self.assertEqual(len(result.items), 2)
            self.assertEqual(result.next_cursor_value, result.items[-1].cursor_value)

    def test_duplicate_guid_within_one_feed_is_deduped_to_first_seen(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_source(
                connection, source_id="src-verified", url="https://feeds.example.com/feed.xml"
            )
            client = _FakePodcastClient(body=RSS_FEED_DUPLICATE_GUID)
            adapter = LivePodcastFeedAdapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {PODCAST_RAIL_CREDENTIAL_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_episodes(source_id="src-verified", cursor=None, now=NOW)

            self.assertTrue(result.healthy)
            self.assertEqual(len(result.items), 1)
            self.assertEqual(result.items[0].title, "Episode One")

    def test_malformed_feed_response_fails_closed_without_advancing_cursor(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_source(
                connection, source_id="src-verified", url="https://feeds.example.com/feed.xml"
            )
            client = _FakePodcastClient(body=MALFORMED_NOT_XML)
            adapter = LivePodcastFeedAdapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {PODCAST_RAIL_CREDENTIAL_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_episodes(source_id="src-verified", cursor="prior-cursor", now=NOW)

            self.assertFalse(result.healthy)
            self.assertIn(STATUS_FETCH_MALFORMED_FEED, result.error_summary)
            self.assertEqual(result.items, ())
            self.assertEqual(result.next_cursor_value, "prior-cursor")

    def test_transport_failure_fails_closed_without_advancing_cursor(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_source(
                connection, source_id="src-verified", url="https://feeds.example.com/feed.xml"
            )
            client = _FakePodcastClient(error=urllib.error.URLError("simulated"))
            adapter = LivePodcastFeedAdapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {PODCAST_RAIL_CREDENTIAL_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_episodes(source_id="src-verified", cursor="prior-cursor", now=NOW)

            self.assertFalse(result.healthy)
            self.assertIn(STATUS_FETCH_TRANSPORT_FAILED, result.error_summary)
            self.assertEqual(result.next_cursor_value, "prior-cursor")

    def test_redirect_quarantine_failure_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_source(
                connection, source_id="src-verified", url="https://feeds.example.com/feed.xml"
            )
            client = _FakePodcastClient(
                error=PodcastFeedRedirectQuarantined("refusing redirect to a different host")
            )
            adapter = LivePodcastFeedAdapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {PODCAST_RAIL_CREDENTIAL_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_episodes(source_id="src-verified", cursor=None, now=NOW)

            self.assertFalse(result.healthy)
            self.assertIn(STATUS_FETCH_REDIRECT_QUARANTINED, result.error_summary)

    def test_response_too_large_failure_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_source(
                connection, source_id="src-verified", url="https://feeds.example.com/feed.xml"
            )
            client = _FakePodcastClient(
                error=PodcastFeedResponseTooLarge("feed response exceeded the byte cap")
            )
            adapter = LivePodcastFeedAdapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {PODCAST_RAIL_CREDENTIAL_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_episodes(source_id="src-verified", cursor=None, now=NOW)

            self.assertFalse(result.healthy)
            self.assertIn(STATUS_FETCH_RESPONSE_TOO_LARGE, result.error_summary)

    def test_no_credential_value_ever_appears_in_result(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_source(
                connection, source_id="src-verified", url="https://feeds.example.com/feed.xml"
            )
            client = _FakePodcastClient(body=RSS_FEED_BASIC)
            adapter = LivePodcastFeedAdapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {PODCAST_RAIL_CREDENTIAL_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_episodes(source_id="src-verified", cursor=None, now=NOW)

            self.assertNotIn(FAKE_USER_AGENT, repr(result))


def _seed_source(
    connection: sqlite3.Connection,
    *,
    source_id: str,
    status: str,
    lane: str = "curated_podcasts",
) -> None:
    now = "2026-07-16T00:00:00+00:00"
    connection.execute(
        """
        INSERT INTO ke_sources (source_id, source_type, lane, name, status, notes, created_at, updated_at)
        VALUES (?, 'podcast_feed', ?, ?, ?, '', ?, ?)
        """,
        (source_id, lane, source_id, status, now, now),
    )
    connection.commit()


def _seed_verified_source(
    connection: sqlite3.Connection,
    *,
    source_id: str,
    url: str,
    endpoint_verified_at: str | None = "2026-07-16T00:00:00+00:00",
    verified_by: str | None = "tests",
) -> None:
    """Seeds a source in the one state that lets the adapter's gates all pass:
    status='active' and an rss endpoint with endpoint_verified_at recorded -- the
    exact state none of the 9 real launch feeds are in yet (see
    docs/knowledge_edge/PACKET_2A_PODCAST_SUPERVISED_SMOKE.md). The
    `endpoint_verified_at`/`verified_by` overrides let tests build the otherwise-fully-
    seeded-but-for-one-field states the hardened gate must still refuse."""
    _seed_source(connection, source_id=source_id, status="active")
    now = "2026-07-16T00:00:00+00:00"
    connection.execute(
        """
        INSERT INTO ke_source_endpoints (
            source_endpoint_id, source_id, endpoint_type, url, is_primary, status,
            endpoint_verified_at, verified_by, created_at, updated_at
        )
        VALUES (?, ?, 'rss', ?, 1, 'active', ?, ?, ?, ?)
        """,
        (f"{source_id}-endpoint", source_id, url, endpoint_verified_at, verified_by, now, now),
    )
    connection.commit()


@contextmanager
def _migrated_test_connection() -> Iterator[sqlite3.Connection]:
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir) / "runtime"
        config = PersonalOSConfig(
            environment=Environment.TEST,
            timezone=DEFAULT_TIMEZONE,
            database_path=runtime_dir / "test" / "personalos.sqlite3",
        )
        connection = connect_sqlite(config, runtime_dir=runtime_dir)
        apply_migrations(connection)
        try:
            yield connection
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
