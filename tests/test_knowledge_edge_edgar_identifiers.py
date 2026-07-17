"""P-KE-3A: `ke_company_edgar_identifiers` (migration 00026) /
`personalos.knowledge_edge.state.edgar_identifiers` -- the SEC EDGAR company-
identifier registry `earnings_calendar.py`'s per-company admission gate reads.
Covers the migration's seeded data (all 21 confirmed CIKs, the two recorded SEC
entity-title renames, Keel Infrastructure's TBC row, ASML's foreign-private-issuer
form family) and the state module's own CRUD/validation surface.
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


class SeedDataTest(unittest.TestCase):
    def test_twenty_two_roster_companies_have_an_edgar_identifier_row(self) -> None:
        with _migrated_connection() as connection:
            rows = ke.list_edgar_identifiers(connection)
        self.assertEqual(len(rows), 22)

    def test_twenty_one_companies_are_confirmed_with_a_ten_digit_cik(self) -> None:
        with _migrated_connection() as connection:
            confirmed = ke.list_confirmed_edgar_identifiers(connection)
        self.assertEqual(len(confirmed), 21)
        for row in confirmed:
            self.assertIsNotNone(row["cik"])
            self.assertEqual(len(row["cik"]), 10)

    def test_keel_infrastructure_is_tbc_with_no_cik(self) -> None:
        with _migrated_connection() as connection:
            row = ke.get_edgar_identifier(connection, company_id="ke-company-keel-infrastructure")
        self.assertIsNotNone(row)
        self.assertEqual(row["identifier_status"], "tbc")
        self.assertIsNone(row["cik"])
        self.assertIsNone(row["sec_entity_title"])
        self.assertIsNone(row["filer_form_family"])

    def test_keel_is_excluded_from_confirmed_list(self) -> None:
        with _migrated_connection() as connection:
            confirmed_ids = {row["company_id"] for row in ke.list_confirmed_edgar_identifiers(connection)}
        self.assertNotIn("ke-company-keel-infrastructure", confirmed_ids)

    def test_asml_is_the_only_foreign_private_issuer(self) -> None:
        with _migrated_connection() as connection:
            rows = ke.list_confirmed_edgar_identifiers(connection)
        foreign = [row for row in rows if row["filer_form_family"] == "foreign_private_issuer"]
        self.assertEqual([row["company_id"] for row in foreign], ["ke-company-asml"])
        us_domestic = [row for row in rows if row["filer_form_family"] == "us_domestic"]
        self.assertEqual(len(us_domestic), 20)

    def test_mstr_and_cifr_have_recorded_sec_title_renames(self) -> None:
        with _migrated_connection() as connection:
            mstr = ke.get_edgar_identifier(connection, company_id="ke-company-mstr")
            cifr = ke.get_edgar_identifier(connection, company_id="ke-company-cifr")
        self.assertEqual(mstr["sec_entity_title"], "Strategy Inc")
        self.assertEqual(cifr["sec_entity_title"], "Cipher Digital Inc.")

    def test_no_other_company_has_a_guessed_sec_title(self) -> None:
        # House discipline (PHASE0_ROSTER.md's own header): a title is recorded only
        # when it was explicitly supplied, never filled in from training-data recall.
        # Only the two Conductor-flagged renames were supplied verbatim.
        with _migrated_connection() as connection:
            rows = ke.list_edgar_identifiers(connection)
        titled = {row["company_id"] for row in rows if row["sec_entity_title"] is not None}
        self.assertEqual(titled, {"ke-company-mstr", "ke-company-cifr"})

    def test_specific_cik_values_are_byte_exact(self) -> None:
        with _migrated_connection() as connection:
            nvda = ke.get_edgar_identifier(connection, company_id="ke-company-nvda")
            aapl = ke.get_edgar_identifier(connection, company_id="ke-company-aapl")
        self.assertEqual(nvda["cik"], "0001045810")
        self.assertEqual(aapl["cik"], "0000320193")

    def test_generic_company_identifiers_table_also_has_cik_rows(self) -> None:
        # ke_company_identifiers (migration 00017) already reserves identifier_type=
        # 'cik' in its CHECK constraint; migration 00026 is what actually populates it.
        with _migrated_connection() as connection:
            idents = ke.list_company_identifiers(connection, company_id="ke-company-aapl")
        cik_idents = [i for i in idents if i["identifier_type"] == "cik"]
        self.assertEqual(len(cik_idents), 1)
        self.assertEqual(cik_idents[0]["identifier_value"], "0000320193")

    def test_no_generic_cik_row_for_keel(self) -> None:
        with _migrated_connection() as connection:
            idents = ke.list_company_identifiers(connection, company_id="ke-company-keel-infrastructure")
        self.assertEqual([i for i in idents if i["identifier_type"] == "cik"], [])

    def test_edgar_source_and_endpoint_are_seeded_unverified(self) -> None:
        with _migrated_connection() as connection:
            source = ke.get_source(connection, "ke-source-sec-edgar-submissions")
            endpoints = ke.list_source_endpoints(connection, source_id="ke-source-sec-edgar-submissions")
        self.assertIsNotNone(source)
        self.assertEqual(source["status"], "trial")
        self.assertEqual(source["source_type"], "calendar_provider")
        self.assertEqual(source["lane"], "earnings_events")
        self.assertEqual(len(endpoints), 1)
        self.assertEqual(endpoints[0]["url"], "https://data.sec.gov/submissions/")
        self.assertIsNone(endpoints[0]["endpoint_verified_at"])
        self.assertIsNone(endpoints[0]["verified_by"])


class ValidationTest(unittest.TestCase):
    def test_validate_edgar_identifier_status_accepts_known_values(self) -> None:
        for value in ke.EDGAR_IDENTIFIER_STATUSES:
            self.assertEqual(ke.validate_edgar_identifier_status(value), value)

    def test_validate_edgar_identifier_status_rejects_unknown(self) -> None:
        with self.assertRaises(ValueError):
            ke.validate_edgar_identifier_status("verified")

    def test_validate_edgar_filer_form_family_rejects_unknown(self) -> None:
        with self.assertRaises(ValueError):
            ke.validate_edgar_filer_form_family("domestic")


class CreateEdgarIdentifierTest(unittest.TestCase):
    def test_confirmed_row_requires_a_cik(self) -> None:
        with _migrated_connection() as connection:
            with self.assertRaises(ValueError):
                ke.create_edgar_identifier(
                    connection, company_id="ke-company-nvda", identifier_status="confirmed", cik=None
                )

    def test_cik_must_be_ten_digits(self) -> None:
        with _migrated_connection() as connection:
            with self.assertRaises(ValueError):
                ke.create_edgar_identifier(
                    connection,
                    company_id="ke-company-nvda",
                    identifier_status="confirmed",
                    cik="123",
                )

    def test_tbc_row_round_trips_without_a_cik(self) -> None:
        with _migrated_connection() as connection:
            ke.create_company(
                connection,
                company_id="ke-company-test-newco",
                legal_name="Test NewCo",
                display_name="Test NewCo",
                roster_group="wgmi_candidate_pool",
                roster_status="candidate",
            )
            row = ke.create_edgar_identifier(
                connection, company_id="ke-company-test-newco", identifier_status="tbc"
            )
        self.assertEqual(row["identifier_status"], "tbc")
        self.assertIsNone(row["cik"])

    def test_confirmed_row_with_valid_cik_round_trips(self) -> None:
        with _migrated_connection() as connection:
            ke.create_company(
                connection,
                company_id="ke-company-test-newco2",
                legal_name="Test NewCo2",
                display_name="Test NewCo2",
                roster_group="nasdaq100_top10",
                roster_status="confirmed",
            )
            row = ke.create_edgar_identifier(
                connection,
                company_id="ke-company-test-newco2",
                identifier_status="confirmed",
                cik="0009999999",
                filer_form_family="us_domestic",
                source="test",
            )
        self.assertEqual(row["cik"], "0009999999")
        self.assertEqual(row["filer_form_family"], "us_domestic")

    def test_unique_cik_constraint_rejects_duplicate(self) -> None:
        with _migrated_connection() as connection:
            ke.create_company(
                connection,
                company_id="ke-company-test-dupcik",
                legal_name="Test DupCik",
                display_name="Test DupCik",
                roster_group="nasdaq100_top10",
                roster_status="confirmed",
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO ke_company_edgar_identifiers (
                        company_id, cik, identifier_status, source, notes, created_at, updated_at
                    ) VALUES ('ke-company-test-dupcik', ?, 'confirmed', '', '', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00')
                    """,
                    ("0001045810",),  # already used by ke-company-nvda
                )


class ForeignKeyTest(unittest.TestCase):
    def test_foreign_keys_reject_orphan_edgar_identifier_company(self) -> None:
        with _migrated_connection() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO ke_company_edgar_identifiers (
                        company_id, cik, identifier_status, source, notes, created_at, updated_at
                    ) VALUES ('missing-company', '0001111111', 'confirmed', '', '', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00')
                    """
                )


def _config_for(runtime_dir: Path, environment: Environment) -> PersonalOSConfig:
    directory_name = "dev" if environment is Environment.DEVELOPMENT else "test"
    return PersonalOSConfig(
        environment=environment,
        timezone=DEFAULT_TIMEZONE,
        database_path=runtime_dir / directory_name / "personalos.sqlite3",
    )


@contextmanager
def _migrated_connection() -> Iterator[sqlite3.Connection]:
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir) / "runtime"
        config = _config_for(runtime_dir, Environment.TEST)
        connection = connect_sqlite(config, runtime_dir=runtime_dir)
        try:
            apply_migrations(connection)
            yield connection
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
