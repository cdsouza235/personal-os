"""P-KE-1A: registry state round-trips, seed-data provenance, and effective-dated
role/affiliation query semantics (amendment §8.1-8.3, §9.3, §9.4).

Seed data provenance: exactly two ratified authorities per the packet brief --
governance/living/agent-writable/DECISIONS.md D-PO-018 item 5 (role appendix) and
docs/knowledge_edge/PHASE0_ROSTER.md (company roster). These tests assert the seeded
rows match those authorities' stated values and dates, and that the launch role
appendix's central point -- effective-dated occupancy, not hard-coded officeholders --
actually resolves correctly across the succession boundary.
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


class RoleAppendixSeedDataTest(unittest.TestCase):
    """D-PO-018 item 5: 5 role seats, occupants, effective dates."""

    def test_five_role_seats_are_seeded(self) -> None:
        with _migrated_connection() as connection:
            roles = ke.list_roles(connection)
        role_names = {role["role_name"] for role in roles}
        self.assertEqual(
            role_names,
            {
                "Federal Reserve Chair",
                "U.S. Treasury Secretary",
                "SEC Chair",
                "CFTC Chair",
                "Apple CEO",
            },
        )

    def test_fed_chair_occupant_transitions_on_effective_date(self) -> None:
        with _migrated_connection() as connection:
            before = ke.get_role_occupant_as_of(
                connection, role_id="ke-role-fed-chair", as_of_date="2026-05-21"
            )
            on_date = ke.get_role_occupant_as_of(
                connection, role_id="ke-role-fed-chair", as_of_date="2026-05-22"
            )
            after = ke.get_role_occupant_as_of(
                connection, role_id="ke-role-fed-chair", as_of_date="2026-05-23"
            )

        # No occupancy is seeded for whoever held the seat before 2026-05-22: the seed
        # authority gives no effective start date for that occupant, and the packet does
        # not invent one (see migration 00017 comment). Only Warsh's dated occupancy exists.
        self.assertIsNone(before)
        self.assertEqual(on_date["person"]["display_name"], "Kevin Warsh")
        self.assertEqual(after["person"]["display_name"], "Kevin Warsh")

    def test_apple_ceo_succession_is_effective_dated_not_hard_coded(self) -> None:
        """Amendment §8.3: "model the scheduled succession, it is the whole point of
        effective-dating" -- Tim Cook through 2026-08-31, John Ternus from 2026-09-01."""
        with _migrated_connection() as connection:
            before = ke.get_role_occupant_as_of(
                connection, role_id="ke-role-apple-ceo", as_of_date="2026-08-31"
            )
            on_date = ke.get_role_occupant_as_of(
                connection, role_id="ke-role-apple-ceo", as_of_date="2026-09-01"
            )
            after = ke.get_role_occupant_as_of(
                connection, role_id="ke-role-apple-ceo", as_of_date="2026-10-15"
            )

        self.assertEqual(before["person"]["display_name"], "Tim Cook")
        self.assertEqual(on_date["person"]["display_name"], "John Ternus")
        self.assertEqual(after["person"]["display_name"], "John Ternus")

    def test_treasury_secretary_bessent_effective_january_2025(self) -> None:
        with _migrated_connection() as connection:
            occupant = ke.get_role_occupant_as_of(
                connection, role_id="ke-role-treasury-secretary", as_of_date="2026-07-16"
            )
        self.assertEqual(occupant["person"]["display_name"], "Scott Bessent")
        self.assertEqual(occupant["effective_start_date"], "2025-01-01")
        self.assertEqual(occupant["date_precision"], "month")

    def test_sec_chair_atkins_effective_2025_04_21(self) -> None:
        with _migrated_connection() as connection:
            before = ke.get_role_occupant_as_of(
                connection, role_id="ke-role-sec-chair", as_of_date="2025-04-20"
            )
            on_date = ke.get_role_occupant_as_of(
                connection, role_id="ke-role-sec-chair", as_of_date="2025-04-21"
            )
        self.assertIsNone(before)
        self.assertEqual(on_date["person"]["display_name"], "Paul Atkins")

    def test_cftc_chair_selig_seeded_with_estimated_precision(self) -> None:
        with _migrated_connection() as connection:
            occupant = ke.get_role_occupant_as_of(
                connection, role_id="ke-role-cftc-chair", as_of_date="2026-07-16"
            )
        self.assertEqual(occupant["person"]["display_name"], "Michael Selig")
        self.assertEqual(occupant["effective_start_date"], "2025-12-18")
        self.assertEqual(occupant["date_precision"], "estimated")

    def test_no_officeholders_beyond_the_seed_authority_are_seeded(self) -> None:
        with _migrated_connection() as connection:
            people = ke.list_people(connection, category="role_occupant")
        names = {person["display_name"] for person in people}
        self.assertEqual(
            names,
            {
                "Kevin Warsh",
                "Scott Bessent",
                "Paul Atkins",
                "Michael Selig",
                "Tim Cook",
                "John Ternus",
            },
        )


class CompanyRosterSeedDataTest(unittest.TestCase):
    """D-PO-019 / PHASE0_ROSTER.md: NDX-10 and crypto-3 confirmed, WGMI 9-company pool
    candidate-only."""

    def test_nasdaq100_top10_group_is_confirmed_with_ten_members(self) -> None:
        with _migrated_connection() as connection:
            companies = ke.list_companies(
                connection, roster_group="nasdaq100_top10", roster_status="confirmed"
            )
        self.assertEqual(len(companies), 10)
        tickers = {c["display_name"] for c in companies}
        self.assertIn("NVIDIA", tickers)
        self.assertIn("Apple", tickers)
        self.assertIn("ASML", tickers)

    def test_crypto_native_top3_group_is_confirmed_with_three_members(self) -> None:
        with _migrated_connection() as connection:
            companies = ke.list_companies(
                connection, roster_group="crypto_native_top3", roster_status="confirmed"
            )
        self.assertEqual(len(companies), 3)
        names = {c["display_name"] for c in companies}
        self.assertEqual(names, {"Coinbase", "Strategy (MicroStrategy)", "Circle"})

    def test_wgmi_candidate_pool_has_nine_members_all_candidate_status(self) -> None:
        with _migrated_connection() as connection:
            pool = ke.list_companies(connection, roster_group="wgmi_candidate_pool")
        self.assertEqual(len(pool), 9)
        self.assertTrue(all(c["roster_status"] == "candidate" for c in pool))

    def test_candidate_pool_is_never_returned_as_confirmed(self) -> None:
        """Amendment §9.4: no company is promoted out of a candidate pool automatically."""
        with _migrated_connection() as connection:
            confirmed = ke.list_confirmed_companies(connection)
        confirmed_groups = {c["roster_group"] for c in confirmed}
        self.assertNotIn("wgmi_candidate_pool", confirmed_groups)

        with _migrated_connection() as connection:
            confirmed_wgmi = ke.list_companies(
                connection, roster_group="wgmi_candidate_pool", roster_status="confirmed"
            )
        self.assertEqual(confirmed_wgmi, [])

    def test_total_confirmed_company_count_is_thirteen(self) -> None:
        with _migrated_connection() as connection:
            confirmed = ke.list_confirmed_companies(connection)
        self.assertEqual(len(confirmed), 13)

    def test_get_company_by_ticker_resolves_seeded_identifiers(self) -> None:
        with _migrated_connection() as connection:
            company = ke.get_company_by_ticker(connection, "NVDA")
        self.assertIsNotNone(company)
        self.assertEqual(company["company_id"], "ke-company-nvda")

    def test_candidate_pool_ranked_by_fund_weight_not_market_cap(self) -> None:
        with _migrated_connection() as connection:
            pool = ke.list_companies(connection, roster_group="wgmi_candidate_pool")
        for company in pool:
            self.assertEqual(company["roster_group_rank_basis"], "fund_weight")
            self.assertIsNone(company["market_cap_display"])

    def test_no_roster_membership_dates_are_invented(self) -> None:
        """Neither seed authority records a dated ratification event for roster
        membership itself; added/removed_effective_date must stay NULL for every seeded
        row rather than a fabricated date."""
        with _migrated_connection() as connection:
            companies = ke.list_companies(connection)
        for company in companies:
            self.assertIsNone(company["added_effective_date"])
            self.assertIsNone(company["removed_effective_date"])


class RegistryRoundTripTest(unittest.TestCase):
    def test_create_and_get_source(self) -> None:
        with _migrated_connection() as connection:
            created = ke.create_source(
                connection,
                source_id="src-1",
                source_type="podcast_feed",
                lane="curated_podcasts",
                name="Test Podcast",
                cadence_expectation_days=7,
            )
            fetched = ke.get_source(connection, "src-1")
        self.assertEqual(created, fetched)
        self.assertEqual(fetched["status"], "active")

    def test_create_person_alias_round_trip(self) -> None:
        with _migrated_connection() as connection:
            ke.create_person_alias(
                connection,
                alias_id="alias-1",
                person_id="ke-person-kevin-warsh",
                alias="Kevin M. Warsh",
                alias_type="spelling_variant",
            )
            aliases = ke.list_person_aliases(connection, person_id="ke-person-kevin-warsh")
        self.assertEqual(len(aliases), 1)
        self.assertEqual(aliases[0]["alias"], "Kevin M. Warsh")

    def test_affiliation_as_of_resolves_effective_dated_row(self) -> None:
        with _migrated_connection() as connection:
            ke.create_affiliation(
                connection,
                affiliation_id="aff-1",
                person_id="ke-person-kevin-warsh",
                organization="Hoover Institution",
                title="Fellow",
                effective_start_date="2020-01-01",
                effective_end_date="2026-05-22",
            )
            during = ke.get_affiliation_as_of(
                connection, person_id="ke-person-kevin-warsh", as_of_date="2023-01-01"
            )
            after = ke.get_affiliation_as_of(
                connection, person_id="ke-person-kevin-warsh", as_of_date="2026-06-01"
            )
        self.assertIsNotNone(during)
        self.assertIsNone(after)

    def test_role_occupancy_end_date_must_be_after_start_date(self) -> None:
        with _migrated_connection() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO ke_role_occupancies (
                        occupancy_id, role_id, person_id, effective_start_date,
                        effective_end_date, date_precision, occupancy_source, notes,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "occ-bad-dates", "ke-role-fed-chair", "ke-person-kevin-warsh",
                        "2026-06-01", "2026-01-01", "exact", "test", "",
                        "2026-07-16T00:00:00+00:00", "2026-07-16T00:00:00+00:00",
                    ),
                )

    def test_company_removed_before_added_is_rejected_at_python_validation(self) -> None:
        with _migrated_connection() as connection:
            with self.assertRaises(ValueError):
                ke.create_company(
                    connection,
                    company_id="company-bad-dates",
                    legal_name="Bad Co",
                    display_name="Bad Co",
                    roster_group="nasdaq100_top10",
                    roster_status="candidate",
                    added_effective_date="2026-06-01",
                    removed_effective_date="2026-01-01",
                )

    def test_invalid_enum_values_are_rejected(self) -> None:
        with _migrated_connection() as connection:
            with self.assertRaises(ValueError):
                ke.create_source(
                    connection,
                    source_id="src-bad",
                    source_type="not_a_real_type",
                    lane="curated_podcasts",
                    name="Bad source",
                )


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
