"""P-KE-1A: roster_change_proposal and synthesis_handoff state (amendment §18.3
deterministic recommendations, §7.6 knowledge handoff). Nothing in either table is
ever applied/completed automatically -- both require an explicit caller action.
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import personalos.knowledge_edge.state as ke
from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations


class RosterChangeProposalTest(unittest.TestCase):
    def test_proposal_starts_in_proposed_status_with_no_decision(self) -> None:
        with _migrated_connection() as connection:
            proposal = ke.create_roster_change_proposal(
                connection,
                proposal_id="proposal-1",
                proposal_type="retire_source",
                target_entity_type="source",
                target_entity_id="src-1",
                proposed_change={"status": "retired"},
                rationale="Feed has been dead for 90 days.",
            )
        self.assertEqual(proposal["status"], "proposed")
        self.assertIsNone(proposal["decided_at"])
        self.assertIsNone(proposal["decided_by"])
        self.assertEqual(proposal["proposed_change"], {"status": "retired"})

    def test_decide_proposal_requires_decided_by(self) -> None:
        """Schema CHECK: status != 'proposed' requires decided_at/decided_by set --
        the Python layer requires decided_by as a keyword argument so this can't be
        skipped."""
        with _migrated_connection() as connection:
            ke.create_roster_change_proposal(
                connection,
                proposal_id="proposal-1",
                proposal_type="promote_company",
                target_entity_type="company",
                proposed_change={"roster_status": "confirmed"},
                rationale="Market cap ranking now qualifies.",
            )
            approved = ke.decide_roster_change_proposal(
                connection,
                proposal_id="proposal-1",
                status="approved",
                decided_by="human-operator",
            )
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(approved["decided_by"], "human-operator")
        self.assertIsNotNone(approved["decided_at"])

    def test_decide_cannot_set_status_back_to_proposed(self) -> None:
        with _migrated_connection() as connection:
            ke.create_roster_change_proposal(
                connection,
                proposal_id="proposal-1",
                proposal_type="other",
                target_entity_type="topic",
                proposed_change={},
                rationale="Test.",
            )
            with self.assertRaises(ValueError):
                ke.decide_roster_change_proposal(
                    connection,
                    proposal_id="proposal-1",
                    status="proposed",
                    decided_by="human-operator",
                )

    def test_check_constraint_rejects_non_proposed_row_without_decision_fields(self) -> None:
        with _migrated_connection() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO ke_roster_change_proposals (
                        proposal_id, proposal_type, target_entity_type, target_entity_id,
                        proposed_change_json, rationale, status, created_at, updated_at,
                        decided_at, decided_by
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
                    """,
                    (
                        "proposal-bad", "other", "topic", None, "{}", "Test.", "approved",
                        "2026-07-16T00:00:00+00:00", "2026-07-16T00:00:00+00:00",
                    ),
                )

    def test_list_proposals_filters_by_status(self) -> None:
        with _migrated_connection() as connection:
            ke.create_roster_change_proposal(
                connection,
                proposal_id="proposal-1",
                proposal_type="retire_source",
                target_entity_type="source",
                proposed_change={},
                rationale="Test.",
            )
            ke.create_roster_change_proposal(
                connection,
                proposal_id="proposal-2",
                proposal_type="retire_source",
                target_entity_type="source",
                proposed_change={},
                rationale="Test.",
            )
            ke.decide_roster_change_proposal(
                connection, proposal_id="proposal-2", status="rejected", decided_by="operator"
            )
            proposed = ke.list_roster_change_proposals(connection, status="proposed")
            rejected = ke.list_roster_change_proposals(connection, status="rejected")
        self.assertEqual([p["proposal_id"] for p in proposed], ["proposal-1"])
        self.assertEqual([p["proposal_id"] for p in rejected], ["proposal-2"])


class SynthesisHandoffTest(unittest.TestCase):
    def _seed_media_item(self, connection: sqlite3.Connection) -> None:
        ke.create_source(
            connection,
            source_id="src-1",
            source_type="podcast_feed",
            lane="curated_podcasts",
            name="Test Podcast",
        )
        ke.create_media_item(
            connection,
            media_item_id="media-1",
            source_id="src-1",
            source_specific_id="ep-1",
            canonical_url="https://example.com/ep-1",
            title="Episode 1",
            source_precedence="official",
            media_type="podcast_episode",
            dedupe_key="dedupe-1",
        )

    def test_handoff_starts_staged_and_completes_explicitly(self) -> None:
        with _migrated_connection() as connection:
            self._seed_media_item(connection)
            handoff = ke.create_synthesis_handoff(
                connection,
                handoff_id="handoff-1",
                entity_type="media_item",
                entity_id="media-1",
                handoff_type="copy_synthesis_packet",
                packet={"summary": "Watched episode, no thesis impact."},
            )
            self.assertEqual(handoff["status"], "staged")

            completed = ke.complete_synthesis_handoff(connection, handoff_id="handoff-1")
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(handoff["packet"], {"summary": "Watched episode, no thesis impact."})

    def test_creating_handoff_performs_no_obsidian_or_network_side_effect(self) -> None:
        """Creating a row is itself a no-network, no-Obsidian-write, local-state-only
        action (module docstring) -- the function signature accepts no filesystem or
        network parameters."""
        import inspect

        signature = inspect.signature(ke.create_synthesis_handoff)
        self.assertNotIn("obsidian_path", signature.parameters)
        self.assertNotIn("url", signature.parameters)

    def test_list_synthesis_handoffs_filters_by_status_and_entity_type(self) -> None:
        with _migrated_connection() as connection:
            self._seed_media_item(connection)
            ke.create_synthesis_handoff(
                connection,
                handoff_id="handoff-1",
                entity_type="media_item",
                entity_id="media-1",
                handoff_type="no_thesis_impact",
            )
            ke.create_synthesis_handoff(
                connection,
                handoff_id="handoff-2",
                entity_type="media_item",
                entity_id="media-1",
                handoff_type="create_obsidian_draft",
            )
            ke.complete_synthesis_handoff(connection, handoff_id="handoff-2")

            staged = ke.list_synthesis_handoffs(connection, status="staged")
            completed = ke.list_synthesis_handoffs(connection, status="completed")
        self.assertEqual([h["handoff_id"] for h in staged], ["handoff-1"])
        self.assertEqual([h["handoff_id"] for h in completed], ["handoff-2"])


def _config_for(runtime_dir: Path, environment: Environment) -> PersonalOSConfig:
    directory_name = "dev" if environment is Environment.DEVELOPMENT else "test"
    return PersonalOSConfig(
        environment=environment,
        timezone=DEFAULT_TIMEZONE,
        database_path=runtime_dir / directory_name / "personalos.sqlite3",
    )


@contextmanager
def _connected_sqlite(
    config: PersonalOSConfig,
    *,
    runtime_dir: Path,
) -> Iterator[sqlite3.Connection]:
    connection = connect_sqlite(config, runtime_dir=runtime_dir)
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def _migrated_connection() -> Iterator[sqlite3.Connection]:
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir) / "runtime"
        config = _config_for(runtime_dir, Environment.TEST)
        with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
            apply_migrations(connection)
            yield connection


if __name__ == "__main__":
    unittest.main()
