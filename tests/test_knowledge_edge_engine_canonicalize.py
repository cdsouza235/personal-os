"""P-KE-1B: engine.canonicalize (amendment §11.2)."""

from __future__ import annotations

import unittest

from personalos.knowledge_edge.engine import canonicalize


class NormalizeUrlTest(unittest.TestCase):
    def test_strips_tracking_params(self) -> None:
        url = "https://Example.com/watch?v=abc&utm_source=newsletter&utm_campaign=x"
        self.assertEqual(canonicalize.normalize_url(url), "https://example.com/watch?v=abc")

    def test_strips_trailing_slash(self) -> None:
        self.assertEqual(canonicalize.normalize_url("https://example.com/path/"), "https://example.com/path")

    def test_root_slash_preserved(self) -> None:
        self.assertEqual(canonicalize.normalize_url("https://example.com/"), "https://example.com/")

    def test_idempotent(self) -> None:
        url = "https://example.com/watch?v=abc&si=xyz"
        once = canonicalize.normalize_url(url)
        twice = canonicalize.normalize_url(once)
        self.assertEqual(once, twice)

    def test_query_params_sorted_for_stability(self) -> None:
        first = canonicalize.normalize_url("https://example.com/x?b=2&a=1")
        second = canonicalize.normalize_url("https://example.com/x?a=1&b=2")
        self.assertEqual(first, second)


class NormalizeIdentifierTest(unittest.TestCase):
    def test_strips_and_collapses_whitespace(self) -> None:
        self.assertEqual(canonicalize.normalize_identifier("  abc   123  "), "abc 123")

    def test_preserves_case(self) -> None:
        self.assertEqual(canonicalize.normalize_identifier("dQw4w9WgXcQ"), "dQw4w9WgXcQ")


class ResolveAliasTest(unittest.TestCase):
    def test_resolves_case_insensitive_alias(self) -> None:
        alias_map = {"Mohammed El-Erian": "ke-person-el-erian"}
        self.assertEqual(canonicalize.resolve_alias("mohammed el-erian", alias_map), "ke-person-el-erian")

    def test_returns_none_when_no_alias_matches(self) -> None:
        self.assertIsNone(canonicalize.resolve_alias("nobody", {"Tom Lee": "ke-person-tom-lee"}))


class TimestampNormalizationTest(unittest.TestCase):
    def test_naive_timestamp_uses_source_timezone(self) -> None:
        result = canonicalize.normalize_timestamp_to_utc("2026-07-16T09:00:00", source_timezone="America/Chicago")
        self.assertEqual(result, "2026-07-16T14:00:00+00:00")

    def test_offset_aware_timestamp_converted_to_utc(self) -> None:
        result = canonicalize.normalize_timestamp_to_utc("2026-07-16T09:00:00-05:00", source_timezone="UTC")
        self.assertEqual(result, "2026-07-16T14:00:00+00:00")

    def test_to_display_timezone_round_trip(self) -> None:
        display = canonicalize.to_display_timezone("2026-07-16T14:00:00+00:00", display_timezone="America/Chicago")
        self.assertEqual(display, "2026-07-16T09:00:00-05:00")


class BuildDedupeKeyTest(unittest.TestCase):
    def test_deterministic_for_same_inputs(self) -> None:
        first = canonicalize.build_dedupe_key(source_id="src-1", stable_id="ep-42")
        second = canonicalize.build_dedupe_key(source_id="src-1", stable_id="ep-42")
        self.assertEqual(first, second)

    def test_differs_for_different_stable_id(self) -> None:
        first = canonicalize.build_dedupe_key(source_id="src-1", stable_id="ep-42")
        second = canonicalize.build_dedupe_key(source_id="src-1", stable_id="ep-43")
        self.assertNotEqual(first, second)


class NormalizeDurationSecondsTest(unittest.TestCase):
    def test_none_passthrough(self) -> None:
        self.assertIsNone(canonicalize.normalize_duration_seconds(None))

    def test_rejects_negative(self) -> None:
        with self.assertRaises(ValueError):
            canonicalize.normalize_duration_seconds(-1)


if __name__ == "__main__":
    unittest.main()
