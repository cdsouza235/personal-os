"""P-KE-1B: engine.ranking -- amendment §11.5 deterministic ranking + queue-section
assignment/cap enforcement (the scan-time portion; see module docstring)."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from personalos.knowledge_edge.engine import ranking
from personalos.knowledge_edge.engine.matching import TopicMatch


class ComputePriorityScoreTest(unittest.TestCase):
    def test_pinned_short_circuits_to_fixed_bonus(self) -> None:
        result = ranking.compute_priority_score(
            directness_class="commentary_about",
            source_precedence="broad_search",
            company_roster_group=None,
            topic_matches=(),
            published_at=None,
            now=datetime(2026, 7, 16, tzinfo=UTC),
            duration_seconds=None,
            is_suspected_duplicate=True,
            pinned=True,
            prior_decision_state=None,
        )
        self.assertEqual(result.score, ranking.PINNED_BONUS)

    def test_prior_skip_short_circuits_to_fixed_penalty(self) -> None:
        result = ranking.compute_priority_score(
            directness_class="direct_primary",
            source_precedence="official",
            company_roster_group="nasdaq100_top10",
            topic_matches=(),
            published_at=None,
            now=datetime(2026, 7, 16, tzinfo=UTC),
            duration_seconds=None,
            is_suspected_duplicate=False,
            pinned=False,
            prior_decision_state="skip",
        )
        self.assertEqual(result.score, -ranking.PRIOR_SKIP_PENALTY)

    def test_higher_directness_scores_higher_all_else_equal(self) -> None:
        now = datetime(2026, 7, 16, tzinfo=UTC)
        kwargs = dict(
            source_precedence="official",
            company_roster_group=None,
            topic_matches=(),
            published_at=None,
            now=now,
            duration_seconds=None,
            is_suspected_duplicate=False,
            pinned=False,
            prior_decision_state=None,
        )
        direct = ranking.compute_priority_score(directness_class="direct_primary", **kwargs)
        commentary = ranking.compute_priority_score(directness_class="commentary_about", **kwargs)
        self.assertGreater(direct.score, commentary.score)

    def test_suspected_duplicate_penalizes_score(self) -> None:
        now = datetime(2026, 7, 16, tzinfo=UTC)
        kwargs = dict(
            directness_class="direct_primary",
            source_precedence="official",
            company_roster_group=None,
            topic_matches=(),
            published_at=None,
            now=now,
            duration_seconds=None,
            pinned=False,
            prior_decision_state=None,
        )
        clean = ranking.compute_priority_score(is_suspected_duplicate=False, **kwargs)
        suspect = ranking.compute_priority_score(is_suspected_duplicate=True, **kwargs)
        self.assertEqual(clean.score - suspect.score, ranking.SUSPECTED_DUPLICATE_PENALTY)

    def test_more_recent_publish_scores_higher(self) -> None:
        now = datetime(2026, 7, 16, tzinfo=UTC)
        kwargs = dict(
            directness_class="direct_primary",
            source_precedence="official",
            company_roster_group=None,
            topic_matches=(),
            now=now,
            duration_seconds=None,
            is_suspected_duplicate=False,
            pinned=False,
            prior_decision_state=None,
        )
        recent = ranking.compute_priority_score(published_at=(now - timedelta(hours=1)).isoformat(), **kwargs)
        stale = ranking.compute_priority_score(published_at=(now - timedelta(days=30)).isoformat(), **kwargs)
        self.assertGreater(recent.score, stale.score)

    def test_long_duration_penalized_relative_to_short(self) -> None:
        now = datetime(2026, 7, 16, tzinfo=UTC)
        kwargs = dict(
            directness_class="direct_primary",
            source_precedence="official",
            company_roster_group=None,
            topic_matches=(),
            published_at=None,
            now=now,
            is_suspected_duplicate=False,
            pinned=False,
            prior_decision_state=None,
        )
        short = ranking.compute_priority_score(duration_seconds=600, **kwargs)
        long = ranking.compute_priority_score(duration_seconds=10800, **kwargs)
        self.assertGreater(short.score, long.score)

    def test_thesis_entity_match_outweighs_keyword_match(self) -> None:
        now = datetime(2026, 7, 16, tzinfo=UTC)
        kwargs = dict(
            directness_class="direct_primary",
            source_precedence="official",
            company_roster_group=None,
            published_at=None,
            now=now,
            duration_seconds=None,
            is_suspected_duplicate=False,
            pinned=False,
            prior_decision_state=None,
        )
        entity = ranking.compute_priority_score(
            topic_matches=(TopicMatch(topic_id="t", strength="entity", reason="x"),), **kwargs
        )
        keyword = ranking.compute_priority_score(
            topic_matches=(TopicMatch(topic_id="t", strength="keyword", reason="x"),), **kwargs
        )
        self.assertGreater(entity.score, keyword.score)

    def test_explanation_is_nonempty_and_deterministic(self) -> None:
        now = datetime(2026, 7, 16, tzinfo=UTC)
        kwargs = dict(
            directness_class="direct_primary",
            source_precedence="official",
            company_roster_group="nasdaq100_top10",
            topic_matches=(),
            published_at=now.isoformat(),
            now=now,
            duration_seconds=300,
            is_suspected_duplicate=False,
            pinned=False,
            prior_decision_state=None,
        )
        first = ranking.compute_priority_score(**kwargs)
        second = ranking.compute_priority_score(**kwargs)
        self.assertTrue(first.explanation)
        self.assertEqual(first.explanation, second.explanation)
        self.assertEqual(first.score, second.score)


class OrderAndSelectTest(unittest.TestCase):
    def test_order_candidates_descending_score_tiebreak_by_entity_id(self) -> None:
        candidates = [
            {"entity_id": "b", "priority_score": 10.0},
            {"entity_id": "a", "priority_score": 10.0},
            {"entity_id": "c", "priority_score": 20.0},
        ]
        ordered = ranking.order_candidates(candidates)
        self.assertEqual([c["entity_id"] for c in ordered], ["c", "a", "b"])

    def test_select_promoted_no_cap_promotes_all(self) -> None:
        ordered = [{"entity_id": "a", "priority_score": 1}, {"entity_id": "b", "priority_score": 0}]
        promoted, overflow = ranking.select_promoted(ordered, cap=None)
        self.assertEqual(promoted, ["a", "b"])
        self.assertEqual(overflow, [])

    def test_select_promoted_respects_cap_and_reports_overflow(self) -> None:
        ordered = [{"entity_id": str(i), "priority_score": -i} for i in range(5)]
        promoted, overflow = ranking.select_promoted(ordered, cap=2)
        self.assertEqual(promoted, ["0", "1"])
        self.assertEqual(overflow, ["2", "3", "4"])


class AssignQueueSectionTest(unittest.TestCase):
    def test_skip_and_watched_never_return_a_section(self) -> None:
        for decision_state in ("skip", "watched"):
            self.assertIsNone(ranking.assign_queue_section(lane="curated_podcasts", decision_state=decision_state))

    def test_save_for_later_always_saved_section_regardless_of_lane(self) -> None:
        for lane in ("curated_podcasts", "market_voices", "consequential_leaders"):
            self.assertEqual(
                ranking.assign_queue_section(lane=lane, decision_state="save_for_later"), "saved_to_reconsider"
            )

    def test_lane_maps_to_expected_section(self) -> None:
        self.assertEqual(ranking.assign_queue_section(lane="curated_podcasts", decision_state="undecided"), "p1_core_podcasts")
        self.assertEqual(ranking.assign_queue_section(lane="market_voices", decision_state="undecided"), "p2_market_voices")
        self.assertEqual(
            ranking.assign_queue_section(lane="consequential_leaders", decision_state="undecided"),
            "p0_consequential_leaders",
        )

    def test_unknown_lane_returns_none(self) -> None:
        self.assertIsNone(ranking.assign_queue_section(lane="earnings_events", decision_state="undecided"))


class ExpiryTest(unittest.TestCase):
    def test_saved_item_expires_after_14_days(self) -> None:
        now = datetime(2026, 7, 16, tzinfo=UTC)
        old = (now - timedelta(days=15)).isoformat()
        recent = (now - timedelta(days=1)).isoformat()
        self.assertTrue(ranking.is_saved_item_expired(decided_at=old, now=now, pinned=False))
        self.assertFalse(ranking.is_saved_item_expired(decided_at=recent, now=now, pinned=False))

    def test_pinned_saved_item_never_expires(self) -> None:
        now = datetime(2026, 7, 16, tzinfo=UTC)
        old = (now - timedelta(days=365)).isoformat()
        self.assertFalse(ranking.is_saved_item_expired(decided_at=old, now=now, pinned=True))

    def test_replay_item_expires_after_7_days(self) -> None:
        now = datetime(2026, 7, 16, tzinfo=UTC)
        old = (now - timedelta(days=8)).isoformat()
        recent = (now - timedelta(days=6)).isoformat()
        self.assertTrue(ranking.is_replay_item_expired(ended_at=old, now=now, pinned=False))
        self.assertFalse(ranking.is_replay_item_expired(ended_at=recent, now=now, pinned=False))


class ResurfaceTest(unittest.TestCase):
    def test_selects_at_most_two_highest_scoring(self) -> None:
        candidates = [{"entity_id": str(i), "priority_score": i} for i in range(5)]
        selected = ranking.select_resurfaced_saved_items(candidates)
        self.assertEqual(selected, ["4", "3"])
        self.assertLessEqual(len(selected), ranking.SAVED_RESURFACE_MAX_PER_DAY)


if __name__ == "__main__":
    unittest.main()
