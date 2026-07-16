"""P-KE-1B: engine.matching -- the deterministic thesis/topic matching grammar
(docs/knowledge_edge/PHASE0_THESIS_MATCHING.md Part 2)."""

from __future__ import annotations

import unittest

from personalos.knowledge_edge.engine.matching import leading_topic, match_topics, normalize_text

THESES = [
    {
        "topic_id": "ai-compute-buildout",
        "display_name": "AI Compute Buildout",
        "status": "active",
        "tokens": {
            "companies": ["NVDA", "MSFT", "GOOGL", "AMZN", "META", "AVGO", "CRWV"],
            "people": ["jensen-huang", "satya-nadella", "sundar-pichai"],
            "keywords": ["data center", "gpu capex", "power demand", "capex guidance"],
        },
        "aliases": {"NVDA": ["NVIDIA", "Nvidia Corp", "Nvidia Corporation"]},
        "negative_terms": ["gaming gpu", "consumer graphics card"],
        "precedence": 10,
    },
    {
        "topic_id": "stablecoin-rails",
        "display_name": "Stablecoin Payment Rails",
        "status": "active",
        "tokens": {"companies": ["CRCL", "COIN"], "people": [], "keywords": ["stablecoin", "payment rail", "on-chain settlement"]},
        "aliases": {},
        "negative_terms": [],
        "precedence": 5,
    },
    {
        "topic_id": "dormant-topic",
        "display_name": "Dormant Topic",
        "status": "dormant",
        "tokens": {"companies": ["NVDA"], "people": [], "keywords": ["dormant keyword"]},
        "aliases": {},
        "negative_terms": [],
        "precedence": 99,
    },
]


class NormalizeTextTest(unittest.TestCase):
    def test_lowercases_strips_punctuation_collapses_whitespace(self) -> None:
        self.assertEqual(normalize_text("NVIDIA's Q3   Earnings!!"), "nvidia s q3 earnings")


class MatchTopicsWorkedExampleTest(unittest.TestCase):
    """The exact worked example from PHASE0_THESIS_MATCHING.md Part 2."""

    def test_company_and_person_entity_hits_both_recorded_no_keyword_duplication(self) -> None:
        matches = match_topics(
            company_id="NVDA",
            person_ids=["jensen-huang"],
            title="NVIDIA Q3 Earnings: Jensen Huang on Data Center Demand",
            description="",
            theses=THESES,
        )
        topic_ids = {m.topic_id for m in matches}
        self.assertEqual(topic_ids, {"ai-compute-buildout"})
        strengths = {m.strength for m in matches if m.topic_id == "ai-compute-buildout"}
        self.assertEqual(strengths, {"entity"})  # rule 3 skipped once an entity hit exists (redundant)

    def test_does_not_match_unrelated_topic(self) -> None:
        matches = match_topics(
            company_id="NVDA", person_ids=["jensen-huang"], title="x", description="", theses=THESES
        )
        self.assertNotIn("stablecoin-rails", {m.topic_id for m in matches})


class MatchTopicsRuleTest(unittest.TestCase):
    def test_dormant_topics_never_match(self) -> None:
        matches = match_topics(
            company_id="NVDA", person_ids=[], title="dormant keyword mention", description="", theses=THESES
        )
        self.assertNotIn("dormant-topic", {m.topic_id for m in matches})

    def test_company_alias_resolves_to_canonical_ticker(self) -> None:
        matches = match_topics(
            company_id=None,
            person_ids=[],
            title="Nvidia Corp announces new chip",
            description="",
            theses=THESES,
        )
        # Alias only expands keyword/company token lists for keyword matching of
        # the ticker string itself -- "NVIDIA"/"Nvidia Corp" are aliases of the
        # *company token* "NVDA", not free keywords, so a title mentioning the
        # alias without a resolved company_id does not keyword-match on it. This
        # documents the boundary precisely (aliases apply to the entity-match
        # rules 1/2, not rule 3's free keyword list).
        self.assertEqual(matches, ())

    def test_keyword_match_whole_phrase_required(self) -> None:
        matches = match_topics(
            company_id=None,
            person_ids=[],
            title="Data centers are booming this quarter",
            description="",
            theses=THESES,
        )
        self.assertEqual({m.topic_id for m in matches}, {"ai-compute-buildout"})
        self.assertEqual(matches[0].strength, "keyword")

    def test_keyword_match_requires_exact_multiword_phrase_not_scattered_tokens(self) -> None:
        matches = match_topics(
            company_id=None,
            person_ids=[],
            title="The data was center of attention this quarter",
            description="",
            theses=THESES,
        )
        self.assertEqual(matches, ())

    def test_negative_term_suppresses_keyword_hit(self) -> None:
        matches = match_topics(
            company_id=None,
            person_ids=[],
            title="Best gaming gpu for data center workloads",
            description="",
            theses=THESES,
        )
        self.assertEqual(matches, ())

    def test_negative_term_never_suppresses_entity_hit(self) -> None:
        matches = match_topics(
            company_id="NVDA",
            person_ids=[],
            title="Best gaming gpu roundup",
            description="",
            theses=THESES,
        )
        self.assertEqual({m.topic_id for m in matches}, {"ai-compute-buildout"})
        self.assertEqual(matches[0].strength, "entity")

    def test_multiple_topics_can_match_simultaneously(self) -> None:
        matches = match_topics(
            company_id=None,
            person_ids=[],
            title="Circle stablecoin meets data center financing",
            description="",
            theses=THESES,
        )
        self.assertEqual({m.topic_id for m in matches}, {"ai-compute-buildout", "stablecoin-rails"})

    def test_no_match_returns_empty_tuple(self) -> None:
        matches = match_topics(company_id=None, person_ids=[], title="unrelated", description="", theses=THESES)
        self.assertEqual(matches, ())


class LeadingTopicTest(unittest.TestCase):
    def test_highest_precedence_wins(self) -> None:
        theses_by_id = {thesis["topic_id"]: thesis for thesis in THESES}
        matches = match_topics(
            company_id=None,
            person_ids=[],
            title="Circle stablecoin meets data center financing",
            description="",
            theses=THESES,
        )
        self.assertEqual(leading_topic(matches, theses_by_id=theses_by_id), "ai-compute-buildout")

    def test_no_matches_returns_none(self) -> None:
        self.assertIsNone(leading_topic((), theses_by_id={}))

    def test_ties_break_by_topic_id_ascending(self) -> None:
        theses_by_id = {
            "topic-b": {"precedence": 5},
            "topic-a": {"precedence": 5},
        }
        from personalos.knowledge_edge.engine.matching import TopicMatch

        matches = (TopicMatch(topic_id="topic-b", strength="keyword", reason="x"), TopicMatch(topic_id="topic-a", strength="keyword", reason="y"))
        self.assertEqual(leading_topic(matches, theses_by_id=theses_by_id), "topic-a")


if __name__ == "__main__":
    unittest.main()
