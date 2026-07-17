"""P-KE-2B: the §3-deferral stub (rails/knowledge_edge/person_search.py). Documents
that no broad third-party person-search provider is selected or reachable at launch
(docs/knowledge_edge/PHASE0_PROVIDERS_AND_ACCESS.md §3)."""

from __future__ import annotations

import unittest

from personalos.rails.knowledge_edge.person_search import (
    BROAD_PERSON_SEARCH_PROVIDER_STATUS,
    is_broad_person_search_available,
)


class PersonSearchDeferralTest(unittest.TestCase):
    def test_broad_person_search_is_never_available(self) -> None:
        self.assertFalse(is_broad_person_search_available())

    def test_status_constant_records_the_deferral(self) -> None:
        self.assertEqual(BROAD_PERSON_SEARCH_PROVIDER_STATUS, "deferred_at_launch")


if __name__ == "__main__":
    unittest.main()
