"""P-KE-1B: engine.dedup -- amendment §11.4 deterministic-evidence dedup rules."""

from __future__ import annotations

import unittest

from personalos.knowledge_edge.engine.dedup import find_duplicate_evidence, find_suspected_duplicate


def _item(**overrides):
    base = {
        "media_item_id": "existing-1",
        "dedupe_key": "src:existing-1",
        "feed_guid": None,
        "underlying_id": None,
        "is_replay_of_underlying_id": None,
        "title": "Some Title",
        "matched_person_id": None,
        "published_at": None,
    }
    base.update(overrides)
    return base


class SharedFeedGuidTest(unittest.TestCase):
    def test_matches_on_shared_feed_guid_different_dedupe_key(self) -> None:
        existing = _item(feed_guid="guid-123")
        new_item = _item(dedupe_key="src:new-1", feed_guid="guid-123")
        evidence = find_duplicate_evidence(new_item=new_item, existing_items=[existing])
        self.assertIsNotNone(evidence)
        self.assertEqual(evidence.rule, "shared_feed_guid")
        self.assertEqual(evidence.existing_media_item_id, "existing-1")

    def test_no_match_when_feed_guid_differs(self) -> None:
        existing = _item(feed_guid="guid-123")
        new_item = _item(dedupe_key="src:new-1", feed_guid="guid-999")
        self.assertIsNone(find_duplicate_evidence(new_item=new_item, existing_items=[existing]))

    def test_same_dedupe_key_is_not_a_duplicate_match(self) -> None:
        # Same occurrence re-processed -- caught upstream by get_media_item_by_dedupe_key,
        # not by this evidence function; guard that it doesn't also self-match.
        existing = _item(feed_guid="guid-123", dedupe_key="src:existing-1")
        new_item = _item(dedupe_key="src:existing-1", feed_guid="guid-123")
        self.assertIsNone(find_duplicate_evidence(new_item=new_item, existing_items=[existing]))


class ReplayEvidenceTest(unittest.TestCase):
    def test_replay_matches_underlying_id_of_live_item(self) -> None:
        live = _item(underlying_id="video-live-1")
        replay = _item(dedupe_key="src:replay-1", is_replay_of_underlying_id="video-live-1")
        evidence = find_duplicate_evidence(new_item=replay, existing_items=[live])
        self.assertEqual(evidence.rule, "live_and_official_replay")


class UnderlyingIdEvidenceTest(unittest.TestCase):
    def test_title_change_on_same_underlying_id(self) -> None:
        original = _item(underlying_id="vid-1", title="Original Title")
        corrected = _item(dedupe_key="src:new-1", underlying_id="vid-1", title="Corrected Title")
        evidence = find_duplicate_evidence(new_item=corrected, existing_items=[original])
        self.assertEqual(evidence.rule, "same_underlying_id_title_change")

    def test_same_underlying_id_same_title_is_channel_video_id_rule(self) -> None:
        audio = _item(underlying_id="ep-1", title="Episode 1")
        video = _item(dedupe_key="src:video-1", underlying_id="ep-1", title="Episode 1")
        evidence = find_duplicate_evidence(new_item=video, existing_items=[audio])
        self.assertEqual(evidence.rule, "same_channel_video_id")

    def test_no_underlying_id_no_match(self) -> None:
        existing = _item(underlying_id=None)
        new_item = _item(dedupe_key="src:new-1", underlying_id=None)
        self.assertIsNone(find_duplicate_evidence(new_item=new_item, existing_items=[existing]))


class RulePriorityTest(unittest.TestCase):
    def test_feed_guid_rule_takes_priority_over_underlying_id_rule(self) -> None:
        existing = _item(feed_guid="guid-1", underlying_id="vid-1", title="A")
        new_item = _item(dedupe_key="src:new-1", feed_guid="guid-1", underlying_id="vid-2", title="B")
        evidence = find_duplicate_evidence(new_item=new_item, existing_items=[existing])
        self.assertEqual(evidence.rule, "shared_feed_guid")


class SuspectedDuplicateTest(unittest.TestCase):
    def test_weak_signal_never_returned_by_find_duplicate_evidence(self) -> None:
        existing = _item(title="Tom Lee on Bitcoin", matched_person_id="ke-person-tom-lee", published_at="2026-07-16T10:00:00+00:00")
        new_item = _item(
            dedupe_key="src:new-1",
            title="Tom Lee on Bitcoin",
            matched_person_id="ke-person-tom-lee",
            published_at="2026-07-16T12:00:00+00:00",
        )
        self.assertIsNone(find_duplicate_evidence(new_item=new_item, existing_items=[existing]))
        reason = find_suspected_duplicate(new_item=new_item, existing_items=[existing])
        self.assertIsNotNone(reason)
        self.assertIn("suspected_duplicate", reason)

    def test_no_suspicion_when_outside_window(self) -> None:
        existing = _item(title="Tom Lee on Bitcoin", matched_person_id="ke-person-tom-lee", published_at="2026-07-01T10:00:00+00:00")
        new_item = _item(
            dedupe_key="src:new-1",
            title="Tom Lee on Bitcoin",
            matched_person_id="ke-person-tom-lee",
            published_at="2026-07-16T12:00:00+00:00",
        )
        self.assertIsNone(find_suspected_duplicate(new_item=new_item, existing_items=[existing], window_hours=48))

    def test_no_suspicion_when_person_differs(self) -> None:
        existing = _item(title="Same Title", matched_person_id="person-a", published_at="2026-07-16T10:00:00+00:00")
        new_item = _item(
            dedupe_key="src:new-1", title="Same Title", matched_person_id="person-b", published_at="2026-07-16T11:00:00+00:00"
        )
        self.assertIsNone(find_suspected_duplicate(new_item=new_item, existing_items=[existing]))

    def test_no_suspicion_without_person_or_published_at(self) -> None:
        existing = _item(title="Same Title")
        new_item = _item(dedupe_key="src:new-1", title="Same Title")
        self.assertIsNone(find_suspected_duplicate(new_item=new_item, existing_items=[existing]))


if __name__ == "__main__":
    unittest.main()
