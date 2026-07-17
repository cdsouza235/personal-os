"""P-KE-2C: paired grades-file tests (personalos.knowledge_edge.sample_grades).

Covers the two-artifact freeze/grade redesign: the frozen sample is immutable and
hashed once at freeze; this suite proves the *separate* grades file is validated
against that fixed checksum and against exactly the frozen sample's own item ids,
with no network and no dependency on a real shadow scan.
"""

from __future__ import annotations

import hashlib
import json
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
from personalos.knowledge_edge.adapters.contracts import DiscoveredMediaItem
from personalos.knowledge_edge.adapters.fixtures import (
    FixtureChannelVideoAdapter,
    FixtureEarningsEventAdapter,
    FixtureFilingsAdapter,
    FixturePodcastFeedAdapter,
)
from personalos.knowledge_edge.ground_truth_sample import build_ground_truth_sample
from personalos.knowledge_edge.sample_grades import (
    SampleGradingError,
    parse_grades_file,
    render_blank_grades_file,
    require_paired_grades,
)
from personalos.knowledge_edge.scan_orchestrator import run_scan

NOW = datetime(2026, 7, 30, 21, 0, 0, tzinfo=UTC)
WINDOW_START = "2026-07-01"
WINDOW_END = "2026-07-14"


@contextmanager
def _migrated_connection() -> Iterator[sqlite3.Connection]:
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


def _frozen_json_text() -> str:
    with _migrated_connection() as connection:
        ke.create_source(
            connection, source_id="src-a", source_type="podcast_feed", lane="curated_podcasts", name="Podcast A"
        )
        items = tuple(
            DiscoveredMediaItem(
                source_id="src-a",
                source_specific_id=f"ep-{index}",
                canonical_url=f"https://example.com/ep-{index}",
                title=f"Episode {index}",
                media_type="podcast_episode",
                source_precedence="official",
                format_hint="original_podcast_guest",
                published_at=f"2026-07-{(index % 10) + 1:02d}T09:00:00+00:00",
                duration_seconds=3600,
                cursor_value=f"2026-07-{(index % 10) + 1:02d}T09:00:00+00:00",
            )
            for index in range(3)
        )
        run_scan(
            connection,
            scan_run_id="run-a",
            run_type="full_scan",
            triggered_by="scheduler",
            now=NOW,
            queue_date="2026-07-14",
            podcast_adapter=FixturePodcastFeedAdapter({"src-a": items}),
            channel_adapter=FixtureChannelVideoAdapter({}),
            earnings_adapter=FixtureEarningsEventAdapter({}),
            filings_adapter=FixtureFilingsAdapter({}),
        )
        sample = build_ground_truth_sample(
            connection, window_start=WINDOW_START, window_end=WINDOW_END, generated_at=NOW.isoformat()
        )
    return sample.canonical_json()


class RenderBlankGradesFileTest(unittest.TestCase):
    def test_precision_verdicts_cover_exactly_the_frozen_item_ids(self) -> None:
        frozen_json_text = _frozen_json_text()
        sample_dict = json.loads(frozen_json_text)
        expected_ids = {item["media_item_id"] for item in sample_dict["lane_a_precision_check"]}

        grades_text = render_blank_grades_file(frozen_json_text)
        grades = json.loads(grades_text)

        self.assertEqual(set(grades["precision_verdicts"].keys()), expected_ids)
        self.assertTrue(all(value is None for value in grades["precision_verdicts"].values()))
        self.assertEqual(grades["lane_b_recall_check"], [])
        self.assertEqual(grades["lane_c_recall_check"], [])

    def test_frozen_checksum_matches_the_source_file(self) -> None:
        frozen_json_text = _frozen_json_text()
        grades = json.loads(render_blank_grades_file(frozen_json_text))
        expected = hashlib.sha256(frozen_json_text.encode("utf-8")).hexdigest()
        self.assertEqual(grades["frozen_checksum_sha256"], expected)

    def test_render_is_deterministic(self) -> None:
        frozen_json_text = _frozen_json_text()
        self.assertEqual(
            render_blank_grades_file(frozen_json_text), render_blank_grades_file(frozen_json_text)
        )

    def test_malformed_frozen_json_is_refused(self) -> None:
        with self.assertRaises(SampleGradingError):
            render_blank_grades_file("not json")


class ParseGradesFileTest(unittest.TestCase):
    def test_malformed_json_is_refused(self) -> None:
        with self.assertRaises(SampleGradingError):
            parse_grades_file("not json")

    def test_non_object_json_is_refused(self) -> None:
        with self.assertRaises(SampleGradingError):
            parse_grades_file("[1, 2, 3]")


class RequirePairedGradesTest(unittest.TestCase):
    def _frozen_and_checksum(self) -> tuple[str, str]:
        frozen_json_text = _frozen_json_text()
        checksum = hashlib.sha256(frozen_json_text.encode("utf-8")).hexdigest()
        return frozen_json_text, checksum

    def test_blank_skeleton_grades_pass_pairing(self) -> None:
        frozen_json_text, checksum = self._frozen_and_checksum()
        grades_text = render_blank_grades_file(frozen_json_text)
        paired = require_paired_grades(
            frozen_json_text=frozen_json_text,
            acknowledged_checksum=checksum,
            grades_json_text=grades_text,
        )
        self.assertEqual(paired.lane_b_recall_check, [])
        self.assertEqual(paired.lane_c_recall_check, [])
        self.assertEqual(len(paired.precision_verdicts), 3)

    def test_graded_verdicts_still_pass_pairing(self) -> None:
        """The whole point of the redesign: grading (editing the GRADES file, never
        the frozen file) must not invalidate pairing."""
        frozen_json_text, checksum = self._frozen_and_checksum()
        grades = json.loads(render_blank_grades_file(frozen_json_text))
        for item_id in grades["precision_verdicts"]:
            grades["precision_verdicts"][item_id] = "confirmed"
        grades["graded_by"] = "chris"
        paired = require_paired_grades(
            frozen_json_text=frozen_json_text,
            acknowledged_checksum=checksum,
            grades_json_text=json.dumps(grades),
        )
        self.assertTrue(all(v == "confirmed" for v in paired.precision_verdicts.values()))

    def test_wrong_frozen_checksum_in_grades_file_is_refused(self) -> None:
        frozen_json_text, checksum = self._frozen_and_checksum()
        grades = json.loads(render_blank_grades_file(frozen_json_text))
        grades["frozen_checksum_sha256"] = "0" * 64
        with self.assertRaises(SampleGradingError):
            require_paired_grades(
                frozen_json_text=frozen_json_text,
                acknowledged_checksum=checksum,
                grades_json_text=json.dumps(grades),
            )

    def test_stale_acknowledged_checksum_is_refused(self) -> None:
        """Even if the grades file's own checksum is internally self-consistent, a
        caller passing a stale acknowledged_checksum (e.g. from a re-frozen sample)
        must still be refused."""
        frozen_json_text, checksum = self._frozen_and_checksum()
        grades_text = render_blank_grades_file(frozen_json_text)
        with self.assertRaises(SampleGradingError):
            require_paired_grades(
                frozen_json_text=frozen_json_text,
                acknowledged_checksum="1" * 64,
                grades_json_text=grades_text,
            )

    def test_missing_item_id_is_refused(self) -> None:
        frozen_json_text, checksum = self._frozen_and_checksum()
        grades = json.loads(render_blank_grades_file(frozen_json_text))
        del grades["precision_verdicts"][next(iter(grades["precision_verdicts"]))]
        with self.assertRaises(SampleGradingError) as ctx:
            require_paired_grades(
                frozen_json_text=frozen_json_text,
                acknowledged_checksum=checksum,
                grades_json_text=json.dumps(grades),
            )
        self.assertIn("missing", str(ctx.exception))

    def test_extra_item_id_is_refused(self) -> None:
        frozen_json_text, checksum = self._frozen_and_checksum()
        grades = json.loads(render_blank_grades_file(frozen_json_text))
        grades["precision_verdicts"]["not-a-real-item-id"] = "confirmed"
        with self.assertRaises(SampleGradingError) as ctx:
            require_paired_grades(
                frozen_json_text=frozen_json_text,
                acknowledged_checksum=checksum,
                grades_json_text=json.dumps(grades),
            )
        self.assertIn("extra", str(ctx.exception))

    def test_missing_precision_verdicts_key_is_refused(self) -> None:
        frozen_json_text, checksum = self._frozen_and_checksum()
        grades = json.loads(render_blank_grades_file(frozen_json_text))
        del grades["precision_verdicts"]
        with self.assertRaises(SampleGradingError):
            require_paired_grades(
                frozen_json_text=frozen_json_text,
                acknowledged_checksum=checksum,
                grades_json_text=json.dumps(grades),
            )

    def test_non_list_recall_arrays_are_refused(self) -> None:
        frozen_json_text, checksum = self._frozen_and_checksum()
        grades = json.loads(render_blank_grades_file(frozen_json_text))
        grades["lane_b_recall_check"] = "not-a-list"
        with self.assertRaises(SampleGradingError):
            require_paired_grades(
                frozen_json_text=frozen_json_text,
                acknowledged_checksum=checksum,
                grades_json_text=json.dumps(grades),
            )

    def test_malformed_grades_json_is_refused(self) -> None:
        frozen_json_text, checksum = self._frozen_and_checksum()
        with self.assertRaises(SampleGradingError):
            require_paired_grades(
                frozen_json_text=frozen_json_text,
                acknowledged_checksum=checksum,
                grades_json_text="not json",
            )


if __name__ == "__main__":
    unittest.main()
