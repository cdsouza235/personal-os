"""P-KE-2B: live YouTube Lane B/C rail adapter -- channel-upload RSS polling
(`LiveYoutubeChannelAdapter`) and the `search.list` person-search client
(`LiveYoutubePersonSearchClient`).

No real network call is ever made in this suite: every gate-isolation test injects a
fake client (bypassing `urllib` entirely), and the HTTP-mechanics tests inject a fake
`opener` into the two `*HttpClient` classes -- mirroring
`test_rails_knowledge_edge_podcasts.py`'s own conventions exactly.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
import urllib.error
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.rails.knowledge_edge.youtube import (
    DEFAULT_LANE_BC_FEATURE_MODE,
    DEFAULT_PERSON_SEARCH_SOURCE_ID,
    LANE_BC_FEATURE_MODES,
    YOUTUBE_API_KEY_ENV_VAR,
    STATUS_CHANNEL_BLOCKED_FEATURE_MODE,
    STATUS_CHANNEL_BLOCKED_NO_ENDPOINT,
    STATUS_CHANNEL_BLOCKED_SOURCE_NOT_FOUND,
    STATUS_CHANNEL_BLOCKED_SOURCE_NOT_VERIFIED,
    STATUS_CHANNEL_FETCH_MALFORMED_FEED,
    STATUS_CHANNEL_FETCH_REDIRECT_QUARANTINED,
    STATUS_CHANNEL_FETCH_RESPONSE_TOO_LARGE,
    STATUS_CHANNEL_FETCH_TRANSPORT_FAILED,
    STATUS_SEARCH_BLOCKED_BUDGET_EXHAUSTED,
    STATUS_SEARCH_BLOCKED_CREDENTIAL_EMPTY,
    STATUS_SEARCH_BLOCKED_CREDENTIAL_MISSING,
    STATUS_SEARCH_BLOCKED_ENDPOINT_INSECURE_SCHEME,
    STATUS_SEARCH_BLOCKED_FEATURE_MODE,
    STATUS_SEARCH_BLOCKED_NO_ENDPOINT,
    STATUS_SEARCH_BLOCKED_SOURCE_NOT_FOUND,
    STATUS_SEARCH_BLOCKED_SOURCE_NOT_VERIFIED,
    STATUS_SEARCH_FETCH_MALFORMED_RESPONSE,
    STATUS_SEARCH_FETCH_REDIRECT_QUARANTINED,
    STATUS_SEARCH_FETCH_RESPONSE_TOO_LARGE,
    STATUS_SEARCH_FETCH_TRANSPORT_FAILED,
    InMemoryPersonSearchCache,
    LiveYoutubeChannelAdapter,
    LiveYoutubePersonSearchClient,
    MalformedChannelFeedError,
    MalformedSearchResponseError,
    PersonSearchCacheEntry,
    PersonSearchResult,
    YoutubeChannelFeedHttpClient,
    YoutubeRailRedirectQuarantined,
    YoutubeRailResponseTooLarge,
    YoutubeSearchHttpClient,
    _build_search_url,
    _extract_host,
    _HostConfinedRedirectHandler,
    _parse_channel_feed_document,
    _parse_search_response,
    _percent_encode_query_value,
    validate_lane_bc_feature_mode,
)

NOW = datetime(2026, 7, 17, tzinfo=UTC)
FAKE_API_KEY = "fake-search-api-key-not-real"  # not a real credential

CHANNEL_FEED_BASIC = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns:media="http://search.yahoo.com/mrss/" xmlns="http://www.w3.org/2005/Atom">
<link rel="self" href="https://www.youtube.com/feeds/videos.xml?channel_id=UCabc123"/>
<yt:channelId>UCabc123</yt:channelId>
<title>Test Channel</title>
<entry>
  <id>yt:video:vid-1</id>
  <yt:videoId>vid-1</yt:videoId>
  <yt:channelId>UCabc123</yt:channelId>
  <title>Video One</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=vid-1"/>
  <published>2026-06-01T10:00:00+00:00</published>
  <updated>2026-06-01T10:05:00+00:00</updated>
  <media:group>
    <media:title>Video One</media:title>
    <media:description>First video description.</media:description>
  </media:group>
</entry>
<entry>
  <id>yt:video:vid-2</id>
  <yt:videoId>vid-2</yt:videoId>
  <yt:channelId>UCabc123</yt:channelId>
  <title>Video Two</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=vid-2"/>
  <published>2026-06-08T10:00:00+00:00</published>
  <updated>2026-06-08T10:05:00+00:00</updated>
  <media:group>
    <media:title>Video Two</media:title>
    <media:description>Second video description.</media:description>
  </media:group>
</entry>
</feed>
"""

CHANNEL_FEED_DUPLICATE_VIDEO_ID = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns="http://www.w3.org/2005/Atom">
<entry>
  <yt:videoId>vid-dupe</yt:videoId>
  <title>First Occurrence</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=vid-dupe"/>
  <published>2026-06-01T10:00:00+00:00</published>
</entry>
<entry>
  <yt:videoId>vid-dupe</yt:videoId>
  <title>Repeated videoId</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=vid-dupe-2"/>
  <published>2026-06-02T10:00:00+00:00</published>
</entry>
</feed>
"""

CHANNEL_FEED_MISSING_FIELDS = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns="http://www.w3.org/2005/Atom">
<entry>
  <title>Missing videoId</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=no-id"/>
  <published>2026-06-01T10:00:00+00:00</published>
</entry>
<entry>
  <yt:videoId>vid-no-title</yt:videoId>
  <link rel="alternate" href="https://www.youtube.com/watch?v=vid-no-title"/>
  <published>2026-06-01T10:00:00+00:00</published>
</entry>
<entry>
  <yt:videoId>vid-no-link</yt:videoId>
  <title>Missing link</title>
  <published>2026-06-01T10:00:00+00:00</published>
</entry>
<entry>
  <yt:videoId>vid-no-published</yt:videoId>
  <title>Missing published</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=vid-no-published"/>
</entry>
</feed>
"""

MALFORMED_NOT_XML = b"not xml at all {{{"
MALFORMED_DOCTYPE = (
    b'<?xml version="1.0"?><!DOCTYPE feed ['
    b'<!ENTITY xxe SYSTEM "file:///etc/passwd">]><feed></feed>'
)
MALFORMED_UNSUPPORTED_ROOT = b'<?xml version="1.0"?><rss version="2.0"><channel></channel></rss>'

SEARCH_RESPONSE_BASIC = json.dumps(
    {
        "items": [
            {
                "id": {"kind": "youtube#video", "videoId": "search-vid-1"},
                "snippet": {
                    "publishedAt": "2026-06-01T10:00:00Z",
                    "channelId": "UCsearch1",
                    "title": "Search Result One",
                    "description": "First search result description.",
                    "channelTitle": "Some News Channel",
                },
            },
            {
                "id": {"kind": "youtube#video", "videoId": "search-vid-2"},
                "snippet": {
                    "publishedAt": "2026-06-02T10:00:00Z",
                    "channelId": "UCsearch2",
                    "title": "Search Result Two",
                    "description": "Second search result description.",
                    "channelTitle": "Another Channel",
                },
            },
        ]
    }
).encode("utf-8")

SEARCH_RESPONSE_DUPLICATE_VIDEO_ID = json.dumps(
    {
        "items": [
            {
                "id": {"videoId": "dupe-vid"},
                "snippet": {"title": "First", "channelId": "UCx", "channelTitle": "X"},
            },
            {
                "id": {"videoId": "dupe-vid"},
                "snippet": {"title": "Repeated", "channelId": "UCx", "channelTitle": "X"},
            },
        ]
    }
).encode("utf-8")

SEARCH_RESPONSE_MISSING_ITEMS_KEY = json.dumps({"kind": "youtube#searchListResponse"}).encode("utf-8")
SEARCH_RESPONSE_NOT_JSON = b"not json at all {{{"


class _FakeChannelClient:
    def __init__(self, *, body: bytes = CHANNEL_FEED_BASIC, error: Exception | None = None) -> None:
        self.calls: list[str] = []
        self._body = body
        self._error = error

    def fetch(self, url: str) -> bytes:
        self.calls.append(url)
        if self._error is not None:
            raise self._error
        return self._body


class _FakeSearchClient:
    def __init__(self, *, body: bytes = SEARCH_RESPONSE_BASIC, error: Exception | None = None) -> None:
        self.calls: list[str] = []
        self._body = body
        self._error = error

    def fetch(self, url: str) -> bytes:
        self.calls.append(url)
        if self._error is not None:
            raise self._error
        return self._body


class _RecordingOpener:
    def __init__(self, *, body: bytes = CHANNEL_FEED_BASIC) -> None:
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


class _FakeRequest:
    def __init__(self, url: str = "https://www.youtube.com/feeds/videos.xml?channel_id=UCabc123") -> None:
        self.full_url = url
        self.headers: dict[str, str] = {}
        self.unredirected_hdrs: dict[str, str] = {}
        self.origin_req_host = _extract_host(url)
        self.unverifiable = False

    def get_method(self) -> str:
        return "GET"

    def has_header(self, name: str) -> bool:
        return name in self.headers

    def get_full_url(self) -> str:
        return self.full_url


class ExtractHostTest(unittest.TestCase):
    def test_plain_host(self) -> None:
        self.assertEqual(_extract_host("https://www.youtube.com/feeds/videos.xml"), "www.youtube.com")

    def test_host_with_port_and_userinfo_and_case(self) -> None:
        self.assertEqual(
            _extract_host("HTTPS://User:Pw@WWW.Youtube.com:443/feeds/videos.xml"), "www.youtube.com"
        )


class HostConfinedRedirectHandlerTest(unittest.TestCase):
    def test_cross_host_redirect_is_quarantined(self) -> None:
        handler = _HostConfinedRedirectHandler("www.youtube.com")
        with self.assertRaises(YoutubeRailRedirectQuarantined):
            handler.redirect_request(
                _FakeRequest(), None, 302, "Found", {}, "https://evil.example.net/feed.xml"
            )

    def test_https_to_http_downgrade_is_quarantined(self) -> None:
        handler = _HostConfinedRedirectHandler("www.youtube.com")
        with self.assertRaises(YoutubeRailRedirectQuarantined):
            handler.redirect_request(
                _FakeRequest(), None, 302, "Found", {}, "http://www.youtube.com/feeds/videos.xml"
            )

    def test_same_host_https_redirect_is_followed(self) -> None:
        handler = _HostConfinedRedirectHandler("www.youtube.com")
        result = handler.redirect_request(
            _FakeRequest(), None, 302, "Found", {}, "https://www.youtube.com/feeds/videos.xml?channel_id=UCnew"
        )
        self.assertEqual(result.full_url, "https://www.youtube.com/feeds/videos.xml?channel_id=UCnew")


class ValidateLaneBcFeatureModeTest(unittest.TestCase):
    def test_accepts_every_documented_mode(self) -> None:
        for mode in LANE_BC_FEATURE_MODES:
            self.assertEqual(validate_lane_bc_feature_mode(mode), mode)

    def test_rejects_unknown_mode(self) -> None:
        with self.assertRaises(ValueError):
            validate_lane_bc_feature_mode("live")


class PercentEncodeQueryValueTest(unittest.TestCase):
    def test_unreserved_characters_pass_through(self) -> None:
        self.assertEqual(_percent_encode_query_value("Kevin-Warsh_1.0~"), "Kevin-Warsh_1.0~")

    def test_space_and_special_characters_are_encoded(self) -> None:
        self.assertEqual(_percent_encode_query_value("a b"), "a%20b")
        self.assertEqual(_percent_encode_query_value("&"), "%26")
        self.assertEqual(_percent_encode_query_value("O'Brien"), "O%27Brien")

    def test_unicode_characters_are_utf8_percent_encoded(self) -> None:
        self.assertEqual(_percent_encode_query_value("é"), "%C3%A9")


class BuildSearchUrlTest(unittest.TestCase):
    def test_builds_expected_query_string(self) -> None:
        url = _build_search_url(
            base_url="https://www.googleapis.com/youtube/v3/search",
            query="Kevin Warsh",
            api_key=FAKE_API_KEY,
            max_results=5,
        )
        self.assertTrue(url.startswith("https://www.googleapis.com/youtube/v3/search?"))
        self.assertIn("q=Kevin%20Warsh", url)
        self.assertIn(f"key={FAKE_API_KEY}", url)
        self.assertIn("part=snippet", url)
        self.assertIn("type=video", url)
        self.assertIn("maxResults=5", url)


class ParseChannelFeedDocumentTest(unittest.TestCase):
    def test_parses_basic_feed_in_document_order(self) -> None:
        uploads, dropped = _parse_channel_feed_document(CHANNEL_FEED_BASIC, expected_channel_id="UCabc123")
        self.assertEqual([u.video_id for u in uploads], ["vid-1", "vid-2"])
        self.assertEqual(dropped, {})
        first = uploads[0]
        self.assertEqual(first.title, "Video One")
        self.assertEqual(first.canonical_url, "https://www.youtube.com/watch?v=vid-1")
        self.assertEqual(first.published_at, "2026-06-01T10:00:00+00:00")
        self.assertEqual(first.channel_id, "UCabc123")
        self.assertEqual(first.description_excerpt, "First video description.")

    def test_items_missing_required_fields_are_skipped_and_counted_by_reason(self) -> None:
        uploads, dropped = _parse_channel_feed_document(
            CHANNEL_FEED_MISSING_FIELDS, expected_channel_id="UCabc123"
        )
        self.assertEqual(uploads, [])
        self.assertEqual(
            dropped,
            {
                "missing_video_id": 1,
                "missing_title": 1,
                "missing_canonical_url": 1,
                "missing_or_unparseable_published_at": 1,
            },
        )

    def test_not_well_formed_xml_raises_malformed_feed_error(self) -> None:
        with self.assertRaises(MalformedChannelFeedError):
            _parse_channel_feed_document(MALFORMED_NOT_XML, expected_channel_id="UCabc123")

    def test_doctype_declaration_is_refused(self) -> None:
        with self.assertRaises(MalformedChannelFeedError):
            _parse_channel_feed_document(MALFORMED_DOCTYPE, expected_channel_id="UCabc123")

    def test_unsupported_root_element_raises_malformed_feed_error(self) -> None:
        with self.assertRaises(MalformedChannelFeedError):
            _parse_channel_feed_document(MALFORMED_UNSUPPORTED_ROOT, expected_channel_id="UCabc123")


class ParseSearchResponseTest(unittest.TestCase):
    def test_parses_basic_response(self) -> None:
        results = _parse_search_response(SEARCH_RESPONSE_BASIC)
        self.assertEqual(len(results), 2)
        first = results[0]
        self.assertEqual(first.video_id, "search-vid-1")
        self.assertEqual(first.channel_id, "UCsearch1")
        self.assertEqual(first.title, "Search Result One")
        self.assertEqual(first.channel_title, "Some News Channel")
        self.assertEqual(first.published_at, "2026-06-01T10:00:00Z")

    def test_duplicate_video_id_in_one_response_is_deduped(self) -> None:
        results = _parse_search_response(SEARCH_RESPONSE_DUPLICATE_VIDEO_ID)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "First")

    def test_not_json_raises_malformed_response_error(self) -> None:
        with self.assertRaises(MalformedSearchResponseError):
            _parse_search_response(SEARCH_RESPONSE_NOT_JSON)

    def test_missing_items_key_raises_malformed_response_error(self) -> None:
        with self.assertRaises(MalformedSearchResponseError):
            _parse_search_response(SEARCH_RESPONSE_MISSING_ITEMS_KEY)


class ChannelFeedHttpClientTest(unittest.TestCase):
    def test_fetch_sends_expected_request_shape(self) -> None:
        opener = _RecordingOpener()
        client = YoutubeChannelFeedHttpClient(opener=opener)
        body = client.fetch("https://www.youtube.com/feeds/videos.xml?channel_id=UCabc123")

        self.assertEqual(body, CHANNEL_FEED_BASIC)
        self.assertEqual(len(opener.requests), 1)
        sent = opener.requests[0]
        self.assertEqual(sent.get_method(), "GET")
        self.assertTrue(sent.get_header("User-agent"))

    def test_fetch_converts_transport_failure(self) -> None:
        client = YoutubeChannelFeedHttpClient(opener=_FailingOpener())
        with self.assertRaises(urllib.error.URLError):
            client.fetch("https://www.youtube.com/feeds/videos.xml?channel_id=UCabc123")

    def test_fetch_enforces_response_size_cap(self) -> None:
        opener = _RecordingOpener(body=b"x" * 100)
        client = YoutubeChannelFeedHttpClient(opener=opener, max_response_bytes=10)
        with self.assertRaises(YoutubeRailResponseTooLarge):
            client.fetch("https://www.youtube.com/feeds/videos.xml?channel_id=UCabc123")


class SearchHttpClientTest(unittest.TestCase):
    def test_fetch_sends_expected_request_shape(self) -> None:
        opener = _RecordingOpener(body=SEARCH_RESPONSE_BASIC)
        client = YoutubeSearchHttpClient(opener=opener)
        body = client.fetch("https://www.googleapis.com/youtube/v3/search?key=abc")

        self.assertEqual(body, SEARCH_RESPONSE_BASIC)
        self.assertEqual(opener.requests[0].get_method(), "GET")

    def test_fetch_enforces_response_size_cap(self) -> None:
        opener = _RecordingOpener(body=b"x" * 100)
        client = YoutubeSearchHttpClient(opener=opener, max_response_bytes=10)
        with self.assertRaises(YoutubeRailResponseTooLarge):
            client.fetch("https://www.googleapis.com/youtube/v3/search?key=abc")


class LiveYoutubeChannelAdapterGateTest(unittest.TestCase):
    def test_disabled_feature_mode_refuses_before_touching_client(self) -> None:
        with _migrated_test_connection() as connection:
            client = _FakeChannelClient(error=AssertionError("client must not be called"))
            adapter = LiveYoutubeChannelAdapter(connection, feature_mode="disabled", client=client)
            result = adapter.fetch_uploads(source_id="src-does-not-matter", cursor=None, now=NOW)
            self.assertFalse(result.healthy)
            self.assertIn(STATUS_CHANNEL_BLOCKED_FEATURE_MODE, result.error_summary)
            self.assertEqual(client.calls, [])

    def test_default_constructor_feature_mode_is_disabled(self) -> None:
        self.assertEqual(DEFAULT_LANE_BC_FEATURE_MODE, "disabled")
        with _migrated_test_connection() as connection:
            adapter = LiveYoutubeChannelAdapter(connection)
            result = adapter.fetch_uploads(source_id="src-x", cursor=None, now=NOW)
            self.assertFalse(result.healthy)
            self.assertIn(STATUS_CHANNEL_BLOCKED_FEATURE_MODE, result.error_summary)

    def test_unknown_source_id_refuses(self) -> None:
        with _migrated_test_connection() as connection:
            client = _FakeChannelClient(error=AssertionError("client must not be called"))
            adapter = LiveYoutubeChannelAdapter(connection, feature_mode="shadow_live", client=client)
            result = adapter.fetch_uploads(source_id="ke-source-does-not-exist", cursor=None, now=NOW)
            self.assertFalse(result.healthy)
            self.assertIn(STATUS_CHANNEL_BLOCKED_SOURCE_NOT_FOUND, result.error_summary)
            self.assertEqual(client.calls, [])

    def test_source_with_no_endpoint_refuses(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_channel_source(connection, source_id="src-no-endpoint", status="active")
            client = _FakeChannelClient(error=AssertionError("client must not be called"))
            adapter = LiveYoutubeChannelAdapter(connection, feature_mode="shadow_live", client=client)
            result = adapter.fetch_uploads(source_id="src-no-endpoint", cursor=None, now=NOW)
            self.assertFalse(result.healthy)
            self.assertIn(STATUS_CHANNEL_BLOCKED_NO_ENDPOINT, result.error_summary)

    def test_trial_source_with_no_endpoint_verification_refuses_and_names_it(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_channel_source(connection, source_id="src-trial", status="trial")
            connection.execute(
                """
                INSERT INTO ke_source_endpoints (
                    source_endpoint_id, source_id, endpoint_type, url, is_primary, status,
                    endpoint_verified_at, verified_by, created_at, updated_at
                )
                VALUES ('src-trial-endpoint', 'src-trial', 'channel_id', 'UCabc123', 1, 'active',
                        NULL, NULL, '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00')
                """
            )
            connection.commit()
            client = _FakeChannelClient(error=AssertionError("client must not be called"))
            adapter = LiveYoutubeChannelAdapter(connection, feature_mode="shadow_live", client=client)
            result = adapter.fetch_uploads(source_id="src-trial", cursor=None, now=NOW)
            self.assertFalse(result.healthy)
            self.assertIn(STATUS_CHANNEL_BLOCKED_SOURCE_NOT_VERIFIED, result.error_summary)
            self.assertIn("trial", result.error_summary)
            self.assertIn("endpoint_verified_at", result.error_summary)
            self.assertEqual(client.calls, [])

    def test_malformed_verification_timestamp_refuses(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_channel_source(
                connection, source_id="src-bad-ts", channel_id="UCabc123",
                endpoint_verified_at="not-a-timestamp",
            )
            client = _FakeChannelClient(error=AssertionError("client must not be called"))
            adapter = LiveYoutubeChannelAdapter(connection, feature_mode="shadow_live", client=client)
            result = adapter.fetch_uploads(source_id="src-bad-ts", cursor=None, now=NOW)
            self.assertFalse(result.healthy)
            self.assertIn(STATUS_CHANNEL_BLOCKED_SOURCE_NOT_VERIFIED, result.error_summary)
            self.assertIn("not a parseable timestamp", result.error_summary)

    def test_active_source_with_verified_endpoint_reaches_client_and_parses(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_channel_source(connection, source_id="src-verified", channel_id="UCabc123")
            client = _FakeChannelClient(body=CHANNEL_FEED_BASIC)
            adapter = LiveYoutubeChannelAdapter(connection, feature_mode="shadow_live", client=client)
            result = adapter.fetch_uploads(source_id="src-verified", cursor=None, now=NOW)

            self.assertTrue(result.healthy)
            self.assertEqual(len(client.calls), 1)
            self.assertIn("channel_id=UCabc123", client.calls[0])
            self.assertEqual(len(result.items), 2)
            self.assertEqual(result.items[0].source_id, "src-verified")
            self.assertEqual(result.items[0].channel_id, "UCabc123")
            self.assertEqual(result.items[0].format_hint, "mentioned_only_appearance")
            self.assertEqual(result.next_cursor_value, result.items[-1].cursor_value)

    def test_active_read_only_and_obsidian_modes_also_admit_live_fetch(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_channel_source(connection, source_id="src-verified", channel_id="UCabc123")
            for mode in ("active_read_only", "active_with_obsidian_handoff"):
                client = _FakeChannelClient(body=CHANNEL_FEED_BASIC)
                adapter = LiveYoutubeChannelAdapter(connection, feature_mode=mode, client=client)
                result = adapter.fetch_uploads(source_id="src-verified", cursor=None, now=NOW)
                self.assertTrue(result.healthy, msg=f"mode={mode}")

    def test_cursor_filters_out_already_seen_items(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_channel_source(connection, source_id="src-verified", channel_id="UCabc123")
            client = _FakeChannelClient(body=CHANNEL_FEED_BASIC)
            adapter = LiveYoutubeChannelAdapter(connection, feature_mode="shadow_live", client=client)
            first = adapter.fetch_uploads(source_id="src-verified", cursor=None, now=NOW)
            second = adapter.fetch_uploads(source_id="src-verified", cursor=first.next_cursor_value, now=NOW)
            self.assertEqual(second.items, ())

    def test_max_items_per_fetch_bounds_batch(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_channel_source(connection, source_id="src-verified", channel_id="UCabc123")
            client = _FakeChannelClient(body=CHANNEL_FEED_BASIC)
            adapter = LiveYoutubeChannelAdapter(
                connection, feature_mode="shadow_live", client=client, max_items_per_fetch=1
            )
            result = adapter.fetch_uploads(source_id="src-verified", cursor=None, now=NOW)
            self.assertEqual(len(result.items), 1)

    def test_duplicate_video_id_within_one_feed_is_deduped_and_counted(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_channel_source(connection, source_id="src-verified", channel_id="UCabc123")
            client = _FakeChannelClient(body=CHANNEL_FEED_DUPLICATE_VIDEO_ID)
            adapter = LiveYoutubeChannelAdapter(connection, feature_mode="shadow_live", client=client)
            result = adapter.fetch_uploads(source_id="src-verified", cursor=None, now=NOW)
            self.assertTrue(result.healthy)
            self.assertEqual(len(result.items), 1)
            self.assertEqual(result.items[0].title, "First Occurrence")
            self.assertEqual(result.dropped_items, {"duplicate_video_id_in_batch": 1})

    def test_missing_field_items_are_dropped_and_counted_by_reason(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_channel_source(connection, source_id="src-verified", channel_id="UCabc123")
            client = _FakeChannelClient(body=CHANNEL_FEED_MISSING_FIELDS)
            adapter = LiveYoutubeChannelAdapter(connection, feature_mode="shadow_live", client=client)
            result = adapter.fetch_uploads(source_id="src-verified", cursor=None, now=NOW)
            self.assertTrue(result.healthy)
            self.assertEqual(result.items, ())
            self.assertEqual(
                result.dropped_items,
                {
                    "missing_video_id": 1,
                    "missing_title": 1,
                    "missing_canonical_url": 1,
                    "missing_or_unparseable_published_at": 1,
                },
            )

    def test_malformed_feed_fails_closed_without_advancing_cursor(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_channel_source(connection, source_id="src-verified", channel_id="UCabc123")
            client = _FakeChannelClient(body=MALFORMED_NOT_XML)
            adapter = LiveYoutubeChannelAdapter(connection, feature_mode="shadow_live", client=client)
            result = adapter.fetch_uploads(source_id="src-verified", cursor="prior-cursor", now=NOW)
            self.assertFalse(result.healthy)
            self.assertIn(STATUS_CHANNEL_FETCH_MALFORMED_FEED, result.error_summary)
            self.assertEqual(result.next_cursor_value, "prior-cursor")

    def test_transport_failure_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_channel_source(connection, source_id="src-verified", channel_id="UCabc123")
            client = _FakeChannelClient(error=urllib.error.URLError("simulated"))
            adapter = LiveYoutubeChannelAdapter(connection, feature_mode="shadow_live", client=client)
            result = adapter.fetch_uploads(source_id="src-verified", cursor="prior-cursor", now=NOW)
            self.assertFalse(result.healthy)
            self.assertIn(STATUS_CHANNEL_FETCH_TRANSPORT_FAILED, result.error_summary)
            self.assertEqual(result.next_cursor_value, "prior-cursor")

    def test_redirect_quarantine_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_channel_source(connection, source_id="src-verified", channel_id="UCabc123")
            client = _FakeChannelClient(error=YoutubeRailRedirectQuarantined("refused"))
            adapter = LiveYoutubeChannelAdapter(connection, feature_mode="shadow_live", client=client)
            result = adapter.fetch_uploads(source_id="src-verified", cursor=None, now=NOW)
            self.assertFalse(result.healthy)
            self.assertIn(STATUS_CHANNEL_FETCH_REDIRECT_QUARANTINED, result.error_summary)

    def test_response_too_large_fails_closed_and_is_not_a_parse_failure(self) -> None:
        # The podcast smoke lesson this packet closes: an oversized response must be
        # counted as a refusal (STATUS_CHANNEL_FETCH_RESPONSE_TOO_LARGE), never routed
        # through the XML parser and reported as a malformed-feed failure instead.
        with _migrated_test_connection() as connection:
            _seed_verified_channel_source(connection, source_id="src-verified", channel_id="UCabc123")
            client = _FakeChannelClient(error=YoutubeRailResponseTooLarge("exceeded cap"))
            adapter = LiveYoutubeChannelAdapter(connection, feature_mode="shadow_live", client=client)
            result = adapter.fetch_uploads(source_id="src-verified", cursor=None, now=NOW)
            self.assertFalse(result.healthy)
            self.assertIn(STATUS_CHANNEL_FETCH_RESPONSE_TOO_LARGE, result.error_summary)
            self.assertNotIn(STATUS_CHANNEL_FETCH_MALFORMED_FEED, result.error_summary)

    def test_empty_default_format_hint_is_rejected_at_construction(self) -> None:
        with _migrated_test_connection() as connection:
            with self.assertRaises(ValueError):
                LiveYoutubeChannelAdapter(connection, default_format_hint="   ")


class LiveYoutubePersonSearchClientGateTest(unittest.TestCase):
    def test_disabled_feature_mode_refuses_before_touching_cache_or_client(self) -> None:
        with _migrated_test_connection() as connection:
            client = _FakeSearchClient(error=AssertionError("client must not be called"))
            search_client = LiveYoutubePersonSearchClient(
                connection, feature_mode="disabled", client=client
            )
            with mock.patch.dict("os.environ", {YOUTUBE_API_KEY_ENV_VAR: FAKE_API_KEY}):
                outcome = search_client.search_person(person_id="p1", query="Kevin Warsh", now=NOW)
            self.assertFalse(outcome.healthy)
            self.assertIn(STATUS_SEARCH_BLOCKED_FEATURE_MODE, outcome.error_summary)
            self.assertEqual(client.calls, [])

    def test_missing_credential_env_var_refuses(self) -> None:
        with _migrated_test_connection() as connection:
            client = _FakeSearchClient(error=AssertionError("client must not be called"))
            search_client = LiveYoutubePersonSearchClient(
                connection, feature_mode="shadow_live", client=client
            )
            with mock.patch.dict("os.environ", {}, clear=False):
                import os

                os.environ.pop(YOUTUBE_API_KEY_ENV_VAR, None)
                outcome = search_client.search_person(person_id="p1", query="Kevin Warsh", now=NOW)
            self.assertFalse(outcome.healthy)
            self.assertIn(STATUS_SEARCH_BLOCKED_CREDENTIAL_MISSING, outcome.error_summary)
            self.assertEqual(client.calls, [])

    def test_empty_credential_env_var_refuses(self) -> None:
        with _migrated_test_connection() as connection:
            client = _FakeSearchClient(error=AssertionError("client must not be called"))
            search_client = LiveYoutubePersonSearchClient(
                connection, feature_mode="shadow_live", client=client
            )
            with mock.patch.dict("os.environ", {YOUTUBE_API_KEY_ENV_VAR: "   "}):
                outcome = search_client.search_person(person_id="p1", query="Kevin Warsh", now=NOW)
            self.assertFalse(outcome.healthy)
            self.assertIn(STATUS_SEARCH_BLOCKED_CREDENTIAL_EMPTY, outcome.error_summary)

    def test_unseeded_default_source_refuses(self) -> None:
        # No migration in this packet seeds DEFAULT_PERSON_SEARCH_SOURCE_ID -- this is
        # the expected, permanent (until a future packet's migration) state.
        with _migrated_test_connection() as connection:
            client = _FakeSearchClient(error=AssertionError("client must not be called"))
            search_client = LiveYoutubePersonSearchClient(
                connection, feature_mode="shadow_live", client=client
            )
            with mock.patch.dict("os.environ", {YOUTUBE_API_KEY_ENV_VAR: FAKE_API_KEY}):
                outcome = search_client.search_person(person_id="p1", query="Kevin Warsh", now=NOW)
            self.assertFalse(outcome.healthy)
            self.assertIn(STATUS_SEARCH_BLOCKED_SOURCE_NOT_FOUND, outcome.error_summary)
            self.assertIn(DEFAULT_PERSON_SEARCH_SOURCE_ID, outcome.error_summary)
            self.assertEqual(client.calls, [])

    def test_source_with_no_endpoint_refuses(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_search_source(connection, source_id="src-search-no-endpoint", status="active")
            client = _FakeSearchClient(error=AssertionError("client must not be called"))
            search_client = LiveYoutubePersonSearchClient(
                connection, feature_mode="shadow_live", client=client, source_id="src-search-no-endpoint"
            )
            with mock.patch.dict("os.environ", {YOUTUBE_API_KEY_ENV_VAR: FAKE_API_KEY}):
                outcome = search_client.search_person(person_id="p1", query="Kevin Warsh", now=NOW)
            self.assertFalse(outcome.healthy)
            self.assertIn(STATUS_SEARCH_BLOCKED_NO_ENDPOINT, outcome.error_summary)

    def test_trial_source_refuses_and_names_it(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_search_source(connection, source_id="src-search-trial", status="trial")
            connection.execute(
                """
                INSERT INTO ke_source_endpoints (
                    source_endpoint_id, source_id, endpoint_type, url, is_primary, status,
                    endpoint_verified_at, verified_by, created_at, updated_at
                )
                VALUES ('src-search-trial-endpoint', 'src-search-trial', 'api_endpoint',
                        'https://www.googleapis.com/youtube/v3/search', 1, 'active',
                        NULL, NULL, '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00')
                """
            )
            connection.commit()
            client = _FakeSearchClient(error=AssertionError("client must not be called"))
            search_client = LiveYoutubePersonSearchClient(
                connection, feature_mode="shadow_live", client=client, source_id="src-search-trial"
            )
            with mock.patch.dict("os.environ", {YOUTUBE_API_KEY_ENV_VAR: FAKE_API_KEY}):
                outcome = search_client.search_person(person_id="p1", query="Kevin Warsh", now=NOW)
            self.assertFalse(outcome.healthy)
            self.assertIn(STATUS_SEARCH_BLOCKED_SOURCE_NOT_VERIFIED, outcome.error_summary)
            self.assertIn("trial", outcome.error_summary)

    def test_insecure_endpoint_scheme_refuses_even_when_fully_verified(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_search_source(
                connection, source_id="src-search-insecure", url="http://www.googleapis.com/youtube/v3/search"
            )
            client = _FakeSearchClient(error=AssertionError("client must not be called"))
            search_client = LiveYoutubePersonSearchClient(
                connection, feature_mode="shadow_live", client=client, source_id="src-search-insecure"
            )
            with mock.patch.dict("os.environ", {YOUTUBE_API_KEY_ENV_VAR: FAKE_API_KEY}):
                outcome = search_client.search_person(person_id="p1", query="Kevin Warsh", now=NOW)
            self.assertFalse(outcome.healthy)
            self.assertIn(STATUS_SEARCH_BLOCKED_ENDPOINT_INSECURE_SCHEME, outcome.error_summary)

    def test_active_verified_source_reaches_client_and_caches_result(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_search_source(connection, source_id="src-search-verified")
            client = _FakeSearchClient(body=SEARCH_RESPONSE_BASIC)
            search_client = LiveYoutubePersonSearchClient(
                connection, feature_mode="shadow_live", client=client, source_id="src-search-verified"
            )
            with mock.patch.dict("os.environ", {YOUTUBE_API_KEY_ENV_VAR: FAKE_API_KEY}):
                outcome = search_client.search_person(person_id="p1", query="Kevin Warsh", now=NOW)

            self.assertTrue(outcome.healthy)
            self.assertEqual(outcome.calls_made, 1)
            self.assertFalse(outcome.served_from_cache)
            self.assertEqual(len(outcome.results), 2)
            self.assertEqual(len(client.calls), 1)
            self.assertIn(f"key={FAKE_API_KEY}", client.calls[0])

    def test_second_call_is_served_from_cache_without_a_new_http_call(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_search_source(connection, source_id="src-search-verified")
            client = _FakeSearchClient(body=SEARCH_RESPONSE_BASIC)
            search_client = LiveYoutubePersonSearchClient(
                connection, feature_mode="shadow_live", client=client, source_id="src-search-verified"
            )
            with mock.patch.dict("os.environ", {YOUTUBE_API_KEY_ENV_VAR: FAKE_API_KEY}):
                first = search_client.search_person(person_id="p1", query="Kevin Warsh", now=NOW)
                second = search_client.search_person(person_id="p1", query="Kevin Warsh", now=NOW)

            self.assertEqual(len(client.calls), 1)
            self.assertTrue(second.healthy)
            self.assertTrue(second.served_from_cache)
            self.assertEqual(second.calls_made, 0)
            self.assertEqual(second.results, first.results)

    def test_expired_cache_entry_triggers_a_fresh_call(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_search_source(connection, source_id="src-search-verified")
            client = _FakeSearchClient(body=SEARCH_RESPONSE_BASIC)
            search_client = LiveYoutubePersonSearchClient(
                connection, feature_mode="shadow_live", client=client, source_id="src-search-verified"
            )
            with mock.patch.dict("os.environ", {YOUTUBE_API_KEY_ENV_VAR: FAKE_API_KEY}):
                search_client.search_person(person_id="p1", query="Kevin Warsh", now=NOW)
                later = NOW + timedelta(days=31)
                second = search_client.search_person(person_id="p1", query="Kevin Warsh", now=later)

            self.assertEqual(len(client.calls), 2)
            self.assertFalse(second.served_from_cache)

    def test_per_scan_budget_exhaustion_refuses_further_calls(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_search_source(connection, source_id="src-search-verified")
            client = _FakeSearchClient(body=SEARCH_RESPONSE_BASIC)
            search_client = LiveYoutubePersonSearchClient(
                connection,
                feature_mode="shadow_live",
                client=client,
                source_id="src-search-verified",
                max_calls_per_scan=1,
            )
            with mock.patch.dict("os.environ", {YOUTUBE_API_KEY_ENV_VAR: FAKE_API_KEY}):
                first = search_client.search_person(person_id="p1", query="Kevin Warsh", now=NOW)
                second = search_client.search_person(person_id="p2", query="Someone Else", now=NOW)

            self.assertTrue(first.healthy)
            self.assertFalse(second.healthy)
            self.assertIn(STATUS_SEARCH_BLOCKED_BUDGET_EXHAUSTED, second.error_summary)
            self.assertEqual(len(client.calls), 1)

    def test_malformed_response_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_search_source(connection, source_id="src-search-verified")
            client = _FakeSearchClient(body=SEARCH_RESPONSE_NOT_JSON)
            search_client = LiveYoutubePersonSearchClient(
                connection, feature_mode="shadow_live", client=client, source_id="src-search-verified"
            )
            with mock.patch.dict("os.environ", {YOUTUBE_API_KEY_ENV_VAR: FAKE_API_KEY}):
                outcome = search_client.search_person(person_id="p1", query="Kevin Warsh", now=NOW)
            self.assertFalse(outcome.healthy)
            self.assertIn(STATUS_SEARCH_FETCH_MALFORMED_RESPONSE, outcome.error_summary)

    def test_transport_failure_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_search_source(connection, source_id="src-search-verified")
            client = _FakeSearchClient(error=urllib.error.URLError("simulated"))
            search_client = LiveYoutubePersonSearchClient(
                connection, feature_mode="shadow_live", client=client, source_id="src-search-verified"
            )
            with mock.patch.dict("os.environ", {YOUTUBE_API_KEY_ENV_VAR: FAKE_API_KEY}):
                outcome = search_client.search_person(person_id="p1", query="Kevin Warsh", now=NOW)
            self.assertFalse(outcome.healthy)
            self.assertIn(STATUS_SEARCH_FETCH_TRANSPORT_FAILED, outcome.error_summary)

    def test_redirect_quarantine_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_search_source(connection, source_id="src-search-verified")
            client = _FakeSearchClient(error=YoutubeRailRedirectQuarantined("refused"))
            search_client = LiveYoutubePersonSearchClient(
                connection, feature_mode="shadow_live", client=client, source_id="src-search-verified"
            )
            with mock.patch.dict("os.environ", {YOUTUBE_API_KEY_ENV_VAR: FAKE_API_KEY}):
                outcome = search_client.search_person(person_id="p1", query="Kevin Warsh", now=NOW)
            self.assertFalse(outcome.healthy)
            self.assertIn(STATUS_SEARCH_FETCH_REDIRECT_QUARANTINED, outcome.error_summary)

    def test_response_too_large_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_search_source(connection, source_id="src-search-verified")
            client = _FakeSearchClient(error=YoutubeRailResponseTooLarge("exceeded cap"))
            search_client = LiveYoutubePersonSearchClient(
                connection, feature_mode="shadow_live", client=client, source_id="src-search-verified"
            )
            with mock.patch.dict("os.environ", {YOUTUBE_API_KEY_ENV_VAR: FAKE_API_KEY}):
                outcome = search_client.search_person(person_id="p1", query="Kevin Warsh", now=NOW)
            self.assertFalse(outcome.healthy)
            self.assertIn(STATUS_SEARCH_FETCH_RESPONSE_TOO_LARGE, outcome.error_summary)

    def test_no_derived_fields_on_person_search_result(self) -> None:
        # D-YT option 1: no derived classification persisted from Data API fields --
        # PersonSearchResult carries only stable identifiers + display metadata.
        fields = set(PersonSearchResult.__dataclass_fields__)
        self.assertEqual(
            fields,
            {"video_id", "channel_id", "title", "channel_title", "published_at", "description_excerpt"},
        )

    def test_no_credential_value_ever_appears_in_any_outcome(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_verified_search_source(connection, source_id="src-search-verified")
            client = _FakeSearchClient(body=SEARCH_RESPONSE_BASIC)
            search_client = LiveYoutubePersonSearchClient(
                connection, feature_mode="shadow_live", client=client, source_id="src-search-verified"
            )
            with mock.patch.dict("os.environ", {YOUTUBE_API_KEY_ENV_VAR: FAKE_API_KEY}):
                outcome = search_client.search_person(person_id="p1", query="Kevin Warsh", now=NOW)
                missing_credential_outcome = LiveYoutubePersonSearchClient(
                    connection, feature_mode="shadow_live", client=client, source_id="does-not-exist"
                ).search_person(person_id="p1", query="Kevin Warsh", now=NOW)

            self.assertNotIn(FAKE_API_KEY, repr(outcome))
            self.assertNotIn(FAKE_API_KEY, repr(missing_credential_outcome))


class InMemoryPersonSearchCacheTest(unittest.TestCase):
    def test_get_returns_none_when_absent(self) -> None:
        cache = InMemoryPersonSearchCache()
        self.assertIsNone(cache.get(person_id="p1", query="q"))

    def test_put_then_get_round_trips(self) -> None:
        cache = InMemoryPersonSearchCache()
        entry = PersonSearchCacheEntry(
            person_id="p1",
            query="Kevin Warsh",
            results=(),
            fetched_at=NOW.isoformat(),
            expires_at=(NOW + timedelta(days=30)).isoformat(),
        )
        cache.put(entry)
        self.assertEqual(cache.get(person_id="p1", query="Kevin Warsh"), entry)

    def test_put_replaces_prior_entry_for_the_same_key(self) -> None:
        # "deleted-video" handling (§10.4): a refreshed search result set fully
        # replaces the prior one rather than accumulating stale rows, so a video no
        # longer returned by a fresh search is naturally dropped from the cache.
        cache = InMemoryPersonSearchCache()
        stale_result = PersonSearchResult(
            video_id="stale", channel_id="c", title="t", channel_title="ct",
            published_at=None, description_excerpt="",
        )
        fresh_result = PersonSearchResult(
            video_id="fresh", channel_id="c", title="t2", channel_title="ct",
            published_at=None, description_excerpt="",
        )
        cache.put(PersonSearchCacheEntry(
            person_id="p1", query="q", results=(stale_result,),
            fetched_at=NOW.isoformat(), expires_at=(NOW + timedelta(days=30)).isoformat(),
        ))
        cache.put(PersonSearchCacheEntry(
            person_id="p1", query="q", results=(fresh_result,),
            fetched_at=NOW.isoformat(), expires_at=(NOW + timedelta(days=30)).isoformat(),
        ))
        entry = cache.get(person_id="p1", query="q")
        self.assertEqual(entry.results, (fresh_result,))

    def test_delete_removes_entry(self) -> None:
        cache = InMemoryPersonSearchCache()
        entry = PersonSearchCacheEntry(
            person_id="p1", query="q", results=(),
            fetched_at=NOW.isoformat(), expires_at=(NOW + timedelta(days=30)).isoformat(),
        )
        cache.put(entry)
        cache.delete(person_id="p1", query="q")
        self.assertIsNone(cache.get(person_id="p1", query="q"))

    def test_purge_expired_removes_only_expired_entries(self) -> None:
        cache = InMemoryPersonSearchCache()
        expired = PersonSearchCacheEntry(
            person_id="p1", query="q-old", results=(),
            fetched_at=NOW.isoformat(), expires_at=(NOW - timedelta(days=1)).isoformat(),
        )
        fresh = PersonSearchCacheEntry(
            person_id="p1", query="q-new", results=(),
            fetched_at=NOW.isoformat(), expires_at=(NOW + timedelta(days=1)).isoformat(),
        )
        cache.put(expired)
        cache.put(fresh)
        removed = cache.purge_expired(now=NOW)
        self.assertEqual(removed, 1)
        self.assertIsNone(cache.get(person_id="p1", query="q-old"))
        self.assertIsNotNone(cache.get(person_id="p1", query="q-new"))


def _seed_channel_source(
    connection: sqlite3.Connection, *, source_id: str, status: str, lane: str = "market_voices"
) -> None:
    now = "2026-07-17T00:00:00+00:00"
    connection.execute(
        """
        INSERT INTO ke_sources (source_id, source_type, lane, name, status, notes, created_at, updated_at)
        VALUES (?, 'youtube_channel', ?, ?, ?, '', ?, ?)
        """,
        (source_id, lane, source_id, status, now, now),
    )
    connection.commit()


def _seed_verified_channel_source(
    connection: sqlite3.Connection,
    *,
    source_id: str,
    channel_id: str,
    endpoint_verified_at: str | None = "2026-07-17T00:00:00+00:00",
    verified_by: str | None = "tests",
) -> None:
    _seed_channel_source(connection, source_id=source_id, status="active")
    now = "2026-07-17T00:00:00+00:00"
    connection.execute(
        """
        INSERT INTO ke_source_endpoints (
            source_endpoint_id, source_id, endpoint_type, url, is_primary, status,
            endpoint_verified_at, verified_by, created_at, updated_at
        )
        VALUES (?, ?, 'channel_id', ?, 1, 'active', ?, ?, ?, ?)
        """,
        (f"{source_id}-endpoint", source_id, channel_id, endpoint_verified_at, verified_by, now, now),
    )
    connection.commit()


def _seed_search_source(connection: sqlite3.Connection, *, source_id: str, status: str) -> None:
    now = "2026-07-17T00:00:00+00:00"
    connection.execute(
        """
        INSERT INTO ke_sources (source_id, source_type, lane, name, status, notes, created_at, updated_at)
        VALUES (?, 'person_search_provider', 'market_voices', ?, ?, '', ?, ?)
        """,
        (source_id, source_id, status, now, now),
    )
    connection.commit()


def _seed_verified_search_source(
    connection: sqlite3.Connection,
    *,
    source_id: str,
    url: str = "https://www.googleapis.com/youtube/v3/search",
    endpoint_verified_at: str | None = "2026-07-17T00:00:00+00:00",
    verified_by: str | None = "tests",
) -> None:
    _seed_search_source(connection, source_id=source_id, status="active")
    now = "2026-07-17T00:00:00+00:00"
    connection.execute(
        """
        INSERT INTO ke_source_endpoints (
            source_endpoint_id, source_id, endpoint_type, url, is_primary, status,
            endpoint_verified_at, verified_by, created_at, updated_at
        )
        VALUES (?, ?, 'api_endpoint', ?, 1, 'active', ?, ?, ?, ?)
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
