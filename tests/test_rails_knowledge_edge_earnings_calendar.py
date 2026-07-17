"""P-KE-3A: live SEC EDGAR earnings-calendar rail adapter (D-PO-019 roster/EDGAR path
-- NOT an FMP client, see PHASE0_ROSTER.md).

No real network call is ever made in this suite: every gate-isolation test injects a
fake `client` (bypassing `urllib` entirely, mirroring
`test_rails_knowledge_edge_podcasts.py`'s `_FakePodcastClient`), and the rate-limiter
tests inject fake `monotonic_fn`/`sleep_fn` callables so enforced request spacing is
asserted without ever sleeping in real time.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
import urllib.error
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
import personalos.knowledge_edge.state as ke
from personalos.rails.knowledge_edge.earnings_calendar import (
    DEFAULT_LANE_D_FEATURE_MODE,
    DROP_REASON_COMPANY_EDGAR_IDENTIFIER_MISSING,
    DROP_REASON_COMPANY_EDGAR_IDENTIFIER_TBC,
    DROP_REASON_COMPANY_FETCH_MALFORMED_RESPONSE,
    DROP_REASON_COMPANY_FETCH_REDIRECT_QUARANTINED,
    DROP_REASON_COMPANY_FETCH_RESPONSE_TOO_LARGE,
    DROP_REASON_COMPANY_FETCH_TRANSPORT_FAILED,
    DROP_REASON_COMPANY_NOT_ACTIVE,
    DROP_REASON_COMPANY_ROSTER_STATUS_NOT_CONFIRMED,
    EDGAR_USER_AGENT_ENV_VAR,
    LANE_D_FEATURE_MODES,
    MIN_SECONDS_BETWEEN_REQUESTS,
    STATUS_BLOCKED_CREDENTIAL_EMPTY,
    STATUS_BLOCKED_CREDENTIAL_MISSING,
    STATUS_BLOCKED_ENDPOINT_INSECURE_SCHEME,
    STATUS_BLOCKED_FEATURE_MODE,
    STATUS_BLOCKED_NO_ENDPOINT,
    STATUS_BLOCKED_SOURCE_NOT_FOUND,
    STATUS_BLOCKED_SOURCE_NOT_VERIFIED,
    EarningsCalendarRedirectQuarantined,
    EarningsCalendarResponseTooLarge,
    LiveEarningsCalendarAdapter,
    MalformedSubmissionsResponseError,
    _edgar_filing_index_url,
    _extract_host,
    _HostConfinedRedirectHandler,
    _derive_events_for_company,
    _parse_submissions_document,
    _RateLimiter,
    validate_lane_d_feature_mode,
)

NOW = datetime(2026, 7, 17, tzinfo=UTC)
FAKE_USER_AGENT = "PersonalOS-KnowledgeEdge-Test/1.0 (test@example.com)"  # not a real credential
EDGAR_SOURCE_ID = "ke-source-sec-edgar-submissions"
EDGAR_ENDPOINT_URL = "https://data.sec.gov/submissions/"


def _submissions_json(
    *,
    cik: str = "0000320193",
    forms: list[str],
    filing_dates: list[str],
    report_dates: list[str] | None = None,
    accession_numbers: list[str] | None = None,
    primary_documents: list[str] | None = None,
    items: list[str] | None = None,
) -> bytes:
    n = len(forms)
    payload = {
        "cik": str(int(cik)),
        "filings": {
            "recent": {
                "form": forms,
                "filingDate": filing_dates,
                "reportDate": report_dates if report_dates is not None else [""] * n,
                "accessionNumber": (
                    accession_numbers
                    if accession_numbers is not None
                    else [f"0000000000-26-{i:06d}" for i in range(n)]
                ),
                "primaryDocument": (
                    primary_documents if primary_documents is not None else [f"doc{i}.htm" for i in range(n)]
                ),
                "items": items if items is not None else [""] * n,
            }
        },
    }
    return json.dumps(payload).encode()


AAPL_SUBMISSIONS = _submissions_json(
    cik="0000320193",
    forms=["10-Q", "10-Q", "10-Q", "8-K", "8-K", "10-K"],
    filing_dates=["2026-05-01", "2026-02-01", "2025-11-01", "2026-05-01", "2026-04-15", "2025-11-15"],
    report_dates=["2026-03-31", "2025-12-31", "2025-09-30", "", "", "2025-09-30"],
    accession_numbers=[
        "0000320193-26-000010",
        "0000320193-26-000005",
        "0000320193-25-000090",
        "0000320193-26-000011",
        "0000320193-26-000009",
        "0000320193-25-000095",
    ],
    primary_documents=["aapl-10q.htm"] * 3 + ["aapl-8k.htm", "aapl-8k-other.htm", "aapl-10k.htm"],
    items=["", "", "", "2.02,9.01", "5.02", ""],
)

ASML_SUBMISSIONS = _submissions_json(
    cik="0000937966",
    forms=["6-K", "6-K", "20-F"],
    filing_dates=["2026-04-16", "2026-01-16", "2026-02-28"],
    report_dates=["2026-03-31", "2025-12-31", "2025-12-31"],
    accession_numbers=["0000937966-26-000004", "0000937966-26-000001", "0000937966-26-000002"],
    primary_documents=["asml-6k.htm", "asml-6k.htm", "asml-20f.htm"],
)

EMPTY_SUBMISSIONS = _submissions_json(cik="0000000001", forms=[], filing_dates=[])


class ParseSubmissionsDocumentTest(unittest.TestCase):
    def test_parses_well_formed_document(self) -> None:
        filings = _parse_submissions_document(AAPL_SUBMISSIONS, expected_cik="0000320193")
        self.assertEqual(len(filings), 6)
        self.assertEqual(filings[0].form, "10-Q")
        self.assertEqual(filings[0].accession_number, "0000320193-26-000010")

    def test_cik_mismatch_raises(self) -> None:
        with self.assertRaises(MalformedSubmissionsResponseError):
            _parse_submissions_document(AAPL_SUBMISSIONS, expected_cik="0000000001")

    def test_cik_padding_difference_does_not_raise(self) -> None:
        # EDGAR's own `cik` field is unpadded ("320193"); this repo's storage
        # convention is zero-padded to 10 digits -- the check must normalize, not
        # string-compare.
        filings = _parse_submissions_document(AAPL_SUBMISSIONS, expected_cik="0000320193")
        self.assertTrue(filings)

    def test_not_json_raises(self) -> None:
        with self.assertRaises(MalformedSubmissionsResponseError):
            _parse_submissions_document(b"not json at all", expected_cik="0000320193")

    def test_missing_filings_recent_raises(self) -> None:
        with self.assertRaises(MalformedSubmissionsResponseError):
            _parse_submissions_document(json.dumps({"cik": "320193"}).encode(), expected_cik="0000320193")

    def test_mismatched_array_lengths_raises(self) -> None:
        payload = {
            "cik": "320193",
            "filings": {"recent": {"form": ["10-Q", "10-K"], "filingDate": ["2026-05-01"]}},
        }
        with self.assertRaises(MalformedSubmissionsResponseError):
            _parse_submissions_document(json.dumps(payload).encode(), expected_cik="0000320193")

    def test_filing_missing_accession_number_is_skipped_not_fatal(self) -> None:
        payload = {
            "cik": "320193",
            "filings": {
                "recent": {
                    "form": ["10-Q", "10-Q"],
                    "filingDate": ["2026-05-01", "2026-02-01"],
                    "accessionNumber": ["0000320193-26-000010", None],
                }
            },
        }
        filings = _parse_submissions_document(json.dumps(payload).encode(), expected_cik="0000320193")
        self.assertEqual(len(filings), 1)
        self.assertEqual(filings[0].filing_date, "2026-05-01")

    def test_unparseable_filing_date_is_skipped_not_fatal(self) -> None:
        payload = {
            "cik": "320193",
            "filings": {
                "recent": {
                    "form": ["10-Q", "10-Q"],
                    "filingDate": ["2026-05-01", "not-a-date"],
                    "accessionNumber": ["0000320193-26-000010", "0000320193-26-000005"],
                }
            },
        }
        filings = _parse_submissions_document(json.dumps(payload).encode(), expected_cik="0000320193")
        self.assertEqual(len(filings), 1)

    def test_item_codes_are_split_and_stripped(self) -> None:
        filings = _parse_submissions_document(AAPL_SUBMISSIONS, expected_cik="0000320193")
        eight_k_earnings = [f for f in filings if f.form == "8-K" and f.accession_number == "0000320193-26-000011"]
        self.assertEqual(eight_k_earnings[0].items, ("2.02", "9.01"))

    def test_empty_recent_arrays_parse_to_empty_list(self) -> None:
        filings = _parse_submissions_document(EMPTY_SUBMISSIONS, expected_cik="0000000001")
        self.assertEqual(filings, [])


class DeriveEventsForCompanyTest(unittest.TestCase):
    def test_us_domestic_confirmed_events_both_directions_of_confidence(self) -> None:
        # "Both directions" (checkpoint-history discipline): a confirmed-by-filing
        # event must never be 'estimated', and the inferred event must never be
        # 'confirmed_official' -- assert both explicitly in one test.
        filings = _parse_submissions_document(AAPL_SUBMISSIONS, expected_cik="0000320193")
        events = _derive_events_for_company(
            company_id="ke-company-aapl", cik="0000320193", filer_form_family="us_domestic", filings=filings
        )
        confirmed = [e for e in events if e.schedule_source.startswith("sec_edgar_submissions:10")]
        estimated = [e for e in events if e.schedule_confidence == "estimated"]
        self.assertTrue(confirmed)
        for event in confirmed:
            self.assertEqual(event.schedule_confidence, "confirmed_official")
        self.assertEqual(len(estimated), 1)
        self.assertNotEqual(estimated[0].schedule_confidence, "confirmed_official")

    def test_eight_k_without_item_202_is_excluded(self) -> None:
        filings = _parse_submissions_document(AAPL_SUBMISSIONS, expected_cik="0000320193")
        events = _derive_events_for_company(
            company_id="ke-company-aapl", cik="0000320193", filer_form_family="us_domestic", filings=filings
        )
        hints = [e.event_id_hint for e in events]
        self.assertIn("8-K-0000320193-26-000011", hints)  # has item 2.02
        self.assertNotIn("8-K-0000320193-26-000009", hints)  # item 5.02 only

    def test_ten_k_maps_to_annual_results_ten_q_maps_to_quarterly(self) -> None:
        filings = _parse_submissions_document(AAPL_SUBMISSIONS, expected_cik="0000320193")
        events = {e.event_id_hint: e for e in _derive_events_for_company(
            company_id="ke-company-aapl", cik="0000320193", filer_form_family="us_domestic", filings=filings
        )}
        self.assertEqual(events["10-K-0000320193-25-000095"].event_type, "annual_results")
        self.assertEqual(events["10-Q-0000320193-26-000010"].event_type, "quarterly_earnings")

    def test_scheduled_date_prefers_report_date_over_filing_date(self) -> None:
        filings = _parse_submissions_document(AAPL_SUBMISSIONS, expected_cik="0000320193")
        events = {e.event_id_hint: e for e in _derive_events_for_company(
            company_id="ke-company-aapl", cik="0000320193", filer_form_family="us_domestic", filings=filings
        )}
        self.assertEqual(events["10-Q-0000320193-26-000010"].scheduled_date, "2026-03-31")

    def test_eight_k_falls_back_to_filing_date_when_no_report_date(self) -> None:
        filings = _parse_submissions_document(AAPL_SUBMISSIONS, expected_cik="0000320193")
        events = {e.event_id_hint: e for e in _derive_events_for_company(
            company_id="ke-company-aapl", cik="0000320193", filer_form_family="us_domestic", filings=filings
        )}
        self.assertEqual(events["8-K-0000320193-26-000011"].scheduled_date, "2026-05-01")

    def test_time_precision_is_always_date_only(self) -> None:
        filings = _parse_submissions_document(AAPL_SUBMISSIONS, expected_cik="0000320193")
        events = _derive_events_for_company(
            company_id="ke-company-aapl", cik="0000320193", filer_form_family="us_domestic", filings=filings
        )
        for event in events:
            self.assertEqual(event.time_precision, "date_only")
            self.assertIsNone(event.start_time_utc)
            self.assertIsNone(event.live_webcast_url)
            self.assertIsNone(event.official_event_page_url)
            self.assertIsNone(event.replay_url)

    def test_confirmed_events_carry_an_edgar_filing_url(self) -> None:
        filings = _parse_submissions_document(AAPL_SUBMISSIONS, expected_cik="0000320193")
        events = {e.event_id_hint: e for e in _derive_events_for_company(
            company_id="ke-company-aapl", cik="0000320193", filer_form_family="us_domestic", filings=filings
        )}
        event = events["10-K-0000320193-25-000095"]
        self.assertEqual(len(event.filing_urls), 1)
        self.assertTrue(event.filing_urls[0].startswith("https://www.sec.gov/Archives/edgar/data/320193/"))

    def test_asml_foreign_private_issuer_path_uses_20f_6k(self) -> None:
        filings = _parse_submissions_document(ASML_SUBMISSIONS, expected_cik="0000937966")
        events = {e.event_id_hint: e for e in _derive_events_for_company(
            company_id="ke-company-asml", cik="0000937966", filer_form_family="foreign_private_issuer", filings=filings
        )}
        self.assertEqual(events["20-F-0000937966-26-000002"].event_type, "annual_results")
        self.assertEqual(events["6-K-0000937966-26-000004"].event_type, "quarterly_earnings")
        # 6-K cadence: 2026-04-16 minus 2026-01-16 is a plausible ~90-day gap.
        estimated = [e for e in events.values() if e.schedule_confidence == "estimated"]
        self.assertEqual(len(estimated), 1)

    def test_asml_10k_10q_forms_are_not_recognized_under_foreign_private_issuer(self) -> None:
        # A foreign private issuer's relevant-forms set is 20-F/6-K only -- a
        # (hypothetical) stray 10-Q in the feed must not be treated as relevant.
        filings = _parse_submissions_document(
            _submissions_json(cik="0000937966", forms=["10-Q"], filing_dates=["2026-05-01"]),
            expected_cik="0000937966",
        )
        events = _derive_events_for_company(
            company_id="ke-company-asml", cik="0000937966", filer_form_family="foreign_private_issuer", filings=filings
        )
        self.assertEqual(events, ())

    def test_cadence_gap_outside_plausible_band_yields_no_inferred_event(self) -> None:
        filings = _parse_submissions_document(
            _submissions_json(
                cik="0000320193",
                forms=["10-Q", "10-Q"],
                filing_dates=["2026-05-01", "2026-04-20"],  # 11-day gap, implausible
                accession_numbers=["0000320193-26-000010", "0000320193-26-000009"],
            ),
            expected_cik="0000320193",
        )
        events = _derive_events_for_company(
            company_id="ke-company-aapl", cik="0000320193", filer_form_family="us_domestic", filings=filings
        )
        self.assertEqual([e for e in events if e.schedule_confidence == "estimated"], [])

    def test_single_quarterly_filing_yields_no_inferred_event(self) -> None:
        filings = _parse_submissions_document(
            _submissions_json(cik="0000320193", forms=["10-Q"], filing_dates=["2026-05-01"]),
            expected_cik="0000320193",
        )
        events = _derive_events_for_company(
            company_id="ke-company-aapl", cik="0000320193", filer_form_family="us_domestic", filings=filings
        )
        self.assertEqual([e for e in events if e.schedule_confidence == "estimated"], [])

    def test_no_filings_yields_no_events(self) -> None:
        events = _derive_events_for_company(
            company_id="ke-company-aapl", cik="0000320193", filer_form_family="us_domestic", filings=()
        )
        self.assertEqual(events, ())

    def test_confirmed_filings_per_form_are_capped(self) -> None:
        forms = ["10-Q"] * 6
        filing_dates = [f"2026-0{i}-01" for i in range(1, 7)]
        accessions = [f"0000320193-26-00{i:04d}" for i in range(6)]
        filings = _parse_submissions_document(
            _submissions_json(
                cik="0000320193", forms=forms, filing_dates=filing_dates, accession_numbers=accessions
            ),
            expected_cik="0000320193",
        )
        events = _derive_events_for_company(
            company_id="ke-company-aapl", cik="0000320193", filer_form_family="us_domestic", filings=filings
        )
        confirmed_10q = [e for e in events if e.event_id_hint.startswith("10-Q-")]
        self.assertEqual(len(confirmed_10q), 4)  # MAX_CONFIRMED_FILINGS_PER_FORM

    def test_event_id_hints_are_deterministic_and_idempotent(self) -> None:
        filings = _parse_submissions_document(AAPL_SUBMISSIONS, expected_cik="0000320193")
        first = _derive_events_for_company(
            company_id="ke-company-aapl", cik="0000320193", filer_form_family="us_domestic", filings=filings
        )
        second = _derive_events_for_company(
            company_id="ke-company-aapl", cik="0000320193", filer_form_family="us_domestic", filings=filings
        )
        self.assertEqual([e.event_id_hint for e in first], [e.event_id_hint for e in second])


class EdgarFilingIndexUrlTest(unittest.TestCase):
    def test_strips_dashes_from_accession_and_zero_padding_from_cik(self) -> None:
        url = _edgar_filing_index_url(
            cik="0000320193", accession_number="0000320193-26-000010", primary_document="aapl-10q.htm"
        )
        self.assertEqual(
            url, "https://www.sec.gov/Archives/edgar/data/320193/000032019326000010/aapl-10q.htm"
        )

    def test_empty_primary_document_falls_back_to_index_directory(self) -> None:
        url = _edgar_filing_index_url(
            cik="0000320193", accession_number="0000320193-26-000010", primary_document=""
        )
        self.assertEqual(url, "https://www.sec.gov/Archives/edgar/data/320193/000032019326000010/")


class RateLimiterTest(unittest.TestCase):
    def test_first_call_never_waits(self) -> None:
        sleeps: list[float] = []
        limiter = _RateLimiter(
            min_interval_seconds=0.5, monotonic_fn=lambda: 100.0, sleep_fn=sleeps.append
        )
        limiter.wait()
        self.assertEqual(sleeps, [])

    def test_second_call_within_interval_sleeps_the_remainder(self) -> None:
        clock = [100.0]

        def monotonic_fn() -> float:
            return clock[0]

        sleeps: list[float] = []
        limiter = _RateLimiter(min_interval_seconds=0.5, monotonic_fn=monotonic_fn, sleep_fn=sleeps.append)
        limiter.wait()
        clock[0] = 100.1  # only 0.1s elapsed, less than the 0.5s minimum
        limiter.wait()
        self.assertEqual(len(sleeps), 1)
        self.assertAlmostEqual(sleeps[0], 0.4)

    def test_call_after_interval_elapsed_does_not_sleep(self) -> None:
        clock = [100.0]

        def monotonic_fn() -> float:
            return clock[0]

        sleeps: list[float] = []
        limiter = _RateLimiter(min_interval_seconds=0.5, monotonic_fn=monotonic_fn, sleep_fn=sleeps.append)
        limiter.wait()
        clock[0] = 100.6
        limiter.wait()
        self.assertEqual(sleeps, [])


class ValidateLaneDFeatureModeTest(unittest.TestCase):
    def test_accepts_every_documented_mode(self) -> None:
        for mode in LANE_D_FEATURE_MODES:
            self.assertEqual(validate_lane_d_feature_mode(mode), mode)

    def test_rejects_unknown_mode(self) -> None:
        with self.assertRaises(ValueError):
            validate_lane_d_feature_mode("live")


class ExtractHostTest(unittest.TestCase):
    def test_plain_host(self) -> None:
        self.assertEqual(_extract_host("https://data.sec.gov/submissions/CIK0000320193.json"), "data.sec.gov")


class HostConfinedRedirectHandlerTest(unittest.TestCase):
    def test_cross_host_redirect_is_quarantined(self) -> None:
        handler = _HostConfinedRedirectHandler("data.sec.gov")
        with self.assertRaises(EarningsCalendarRedirectQuarantined):
            handler.redirect_request(
                _FakeRequest(), None, 302, "Found", {}, "https://evil.example.net/CIK0000320193.json"
            )

    def test_https_to_http_downgrade_is_quarantined(self) -> None:
        handler = _HostConfinedRedirectHandler("data.sec.gov")
        with self.assertRaises(EarningsCalendarRedirectQuarantined):
            handler.redirect_request(
                _FakeRequest(), None, 302, "Found", {}, "http://data.sec.gov/CIK0000320193.json"
            )

    def test_same_host_https_redirect_is_followed(self) -> None:
        handler = _HostConfinedRedirectHandler("data.sec.gov")
        result = handler.redirect_request(
            _FakeRequest(), None, 302, "Found", {}, "https://data.sec.gov/CIK0000320193-2.json"
        )
        self.assertEqual(result.full_url, "https://data.sec.gov/CIK0000320193-2.json")


class _FakeRequest:
    full_url = "https://data.sec.gov/submissions/CIK0000320193.json"
    unredirected_hdrs: dict = {}
    headers: dict = {}
    origin_req_host = "data.sec.gov"
    unverifiable = False

    def get_method(self) -> str:
        return "GET"

    def has_header(self, name: str) -> bool:
        return False

    def get_full_url(self) -> str:
        return self.full_url


# ------------------------------------------------------------------- gate isolation


class _FakeEdgarClient:
    """Bypass client (no urllib at all) used by the gate-isolation tests.

    Default behavior (no `body`/`bodies_by_cik` match) synthesizes an empty-but-
    cik-correct submissions document for whichever CIK the URL requests --
    `_parse_submissions_document`'s own cik cross-check (module docstring point 3;
    a real, deliberate integrity check) would otherwise flag every company except
    one as a "misrouted response" if this fixture served the same static body
    (with its own fixed cik) to every URL. `body=` remains available as an
    explicit override for tests that want every call to return the exact same
    (possibly deliberately CIK-mismatched) bytes."""

    def __init__(
        self,
        *,
        body: bytes | None = None,
        bodies_by_cik: dict[str, bytes] | None = None,
        error: Exception | None = None,
        errors_by_cik: dict[str, Exception] | None = None,
    ) -> None:
        self.calls: list[tuple[str, str]] = []
        self._body = body
        self._bodies_by_cik = bodies_by_cik or {}
        self._error = error
        self._errors_by_cik = errors_by_cik or {}

    def fetch(self, url: str, *, user_agent: str) -> bytes:
        self.calls.append((url, user_agent))
        cik = url.rsplit("CIK", 1)[-1].split(".json")[0]
        if cik in self._errors_by_cik:
            raise self._errors_by_cik[cik]
        if self._error is not None:
            raise self._error
        if cik in self._bodies_by_cik:
            return self._bodies_by_cik[cik]
        if self._body is not None:
            return self._body
        return _submissions_json(cik=cik, forms=[], filing_dates=[])


def _no_sleep_adapter(connection: sqlite3.Connection, **kwargs) -> LiveEarningsCalendarAdapter:
    kwargs.setdefault("sleep_fn", lambda seconds: None)
    kwargs.setdefault("monotonic_fn", lambda: 0.0)
    return LiveEarningsCalendarAdapter(connection, **kwargs)


class LiveEarningsCalendarAdapterGateTest(unittest.TestCase):
    def test_disabled_feature_mode_refuses_before_touching_db_or_client(self) -> None:
        with _migrated_test_connection() as connection:
            client = _FakeEdgarClient(error=AssertionError("client must not be called"))
            adapter = _no_sleep_adapter(connection, feature_mode="disabled", client=client)
            with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_events(source_id=EDGAR_SOURCE_ID, cursor=None, now=NOW)

            self.assertFalse(result.healthy)
            self.assertIn(STATUS_BLOCKED_FEATURE_MODE, result.error_summary)
            self.assertEqual(client.calls, [])

    def test_fixture_feature_mode_also_refuses(self) -> None:
        with _migrated_test_connection() as connection:
            client = _FakeEdgarClient(error=AssertionError("client must not be called"))
            adapter = _no_sleep_adapter(connection, feature_mode="fixture", client=client)
            with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_events(source_id=EDGAR_SOURCE_ID, cursor=None, now=NOW)

            self.assertFalse(result.healthy)
            self.assertIn(STATUS_BLOCKED_FEATURE_MODE, result.error_summary)
            self.assertEqual(client.calls, [])

    def test_default_constructor_feature_mode_is_disabled(self) -> None:
        self.assertEqual(DEFAULT_LANE_D_FEATURE_MODE, "disabled")
        with _migrated_test_connection() as connection:
            adapter = _no_sleep_adapter(connection)
            with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_events(source_id=EDGAR_SOURCE_ID, cursor=None, now=NOW)
            self.assertFalse(result.healthy)
            self.assertIn(STATUS_BLOCKED_FEATURE_MODE, result.error_summary)

    def test_missing_credential_env_var_refuses(self) -> None:
        with _migrated_test_connection() as connection:
            client = _FakeEdgarClient(error=AssertionError("client must not be called"))
            adapter = _no_sleep_adapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {}, clear=False):
                import os

                os.environ.pop(EDGAR_USER_AGENT_ENV_VAR, None)
                result = adapter.fetch_events(source_id=EDGAR_SOURCE_ID, cursor=None, now=NOW)

            self.assertFalse(result.healthy)
            self.assertIn(STATUS_BLOCKED_CREDENTIAL_MISSING, result.error_summary)
            self.assertEqual(client.calls, [])

    def test_empty_credential_env_var_refuses(self) -> None:
        with _migrated_test_connection() as connection:
            client = _FakeEdgarClient(error=AssertionError("client must not be called"))
            adapter = _no_sleep_adapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: "   "}):
                result = adapter.fetch_events(source_id=EDGAR_SOURCE_ID, cursor=None, now=NOW)

            self.assertFalse(result.healthy)
            self.assertIn(STATUS_BLOCKED_CREDENTIAL_EMPTY, result.error_summary)
            self.assertEqual(client.calls, [])

    def test_unknown_source_id_refuses(self) -> None:
        with _migrated_test_connection() as connection:
            client = _FakeEdgarClient(error=AssertionError("client must not be called"))
            adapter = _no_sleep_adapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_events(source_id="ke-source-does-not-exist", cursor=None, now=NOW)

            self.assertFalse(result.healthy)
            self.assertIn(STATUS_BLOCKED_SOURCE_NOT_FOUND, result.error_summary)
            self.assertEqual(client.calls, [])

    def test_trial_source_with_no_verification_refuses_and_names_it(self) -> None:
        # migration 00026's actual seeded state: 'trial' status, endpoint present but
        # endpoint_verified_at is NULL -- nothing can fetch until the supervised
        # smoke (PACKET_3A_EARNINGS_SUPERVISED_SMOKE.md) records a verification.
        with _migrated_test_connection() as connection:
            client = _FakeEdgarClient(error=AssertionError("client must not be called"))
            adapter = _no_sleep_adapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_events(source_id=EDGAR_SOURCE_ID, cursor=None, now=NOW)

            self.assertFalse(result.healthy)
            self.assertIn(STATUS_BLOCKED_SOURCE_NOT_VERIFIED, result.error_summary)
            self.assertIn("trial", result.error_summary)
            self.assertEqual(client.calls, [])

    def test_source_with_no_active_endpoint_refuses(self) -> None:
        with _migrated_test_connection() as connection:
            ke.create_source(
                connection, source_id="src-no-endpoint", source_type="calendar_provider",
                lane="earnings_events", name="test", status="active",
            )
            client = _FakeEdgarClient(error=AssertionError("client must not be called"))
            adapter = _no_sleep_adapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_events(source_id="src-no-endpoint", cursor=None, now=NOW)

            self.assertFalse(result.healthy)
            self.assertIn(STATUS_BLOCKED_NO_ENDPOINT, result.error_summary)

    def test_malformed_verification_timestamp_refuses(self) -> None:
        with _migrated_test_connection() as connection:
            connection.execute(
                "UPDATE ke_source_endpoints SET endpoint_verified_at = ?, verified_by = ? "
                "WHERE source_id = ?",
                ("not-a-timestamp", "tests", EDGAR_SOURCE_ID),
            )
            connection.commit()
            ke.update_source_status(connection, source_id=EDGAR_SOURCE_ID, new_status="active")
            client = _FakeEdgarClient(error=AssertionError("client must not be called"))
            adapter = _no_sleep_adapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_events(source_id=EDGAR_SOURCE_ID, cursor=None, now=NOW)

            self.assertFalse(result.healthy)
            self.assertIn(STATUS_BLOCKED_SOURCE_NOT_VERIFIED, result.error_summary)
            self.assertIn("not a parseable timestamp", result.error_summary)
            self.assertEqual(client.calls, [])

    def test_http_endpoint_refuses_even_when_fully_verified(self) -> None:
        with _migrated_test_connection() as connection:
            _verify_edgar_source(connection)
            connection.execute(
                "UPDATE ke_source_endpoints SET url = ? WHERE source_id = ?",
                ("http://data.sec.gov/submissions/", EDGAR_SOURCE_ID),
            )
            connection.commit()
            client = _FakeEdgarClient(error=AssertionError("client must not be called"))
            adapter = _no_sleep_adapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_events(source_id=EDGAR_SOURCE_ID, cursor=None, now=NOW)

            self.assertFalse(result.healthy)
            self.assertIn(STATUS_BLOCKED_ENDPOINT_INSECURE_SCHEME, result.error_summary)
            self.assertEqual(client.calls, [])

    def test_verified_source_reaches_client_for_every_confirmed_company(self) -> None:
        with _migrated_test_connection() as connection:
            _verify_edgar_source(connection)
            client = _FakeEdgarClient()
            adapter = _no_sleep_adapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_events(source_id=EDGAR_SOURCE_ID, cursor=None, now=NOW)

            self.assertTrue(result.healthy)
            # 13 roster_status='confirmed' companies (10 nasdaq100_top10 + 3
            # crypto_native_top3); the 9 wgmi_candidate_pool rows are not confirmed.
            self.assertEqual(len(client.calls), 13)
            for _url, user_agent in client.calls:
                self.assertEqual(user_agent, FAKE_USER_AGENT)

    def test_active_read_only_and_obsidian_modes_also_admit_live_fetch(self) -> None:
        with _migrated_test_connection() as connection:
            _verify_edgar_source(connection)
            for mode in ("active_read_only", "active_with_obsidian_handoff"):
                client = _FakeEdgarClient()
                adapter = _no_sleep_adapter(connection, feature_mode=mode, client=client)
                with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: FAKE_USER_AGENT}):
                    result = adapter.fetch_events(source_id=EDGAR_SOURCE_ID, cursor=None, now=NOW)
                self.assertTrue(result.healthy, msg=f"mode={mode}")
                self.assertEqual(len(client.calls), 13, msg=f"mode={mode}")


class PerCompanyGatingTest(unittest.TestCase):
    def test_wgmi_candidate_pool_companies_are_skipped_and_counted(self) -> None:
        with _migrated_test_connection() as connection:
            _verify_edgar_source(connection)
            client = _FakeEdgarClient()
            adapter = _no_sleep_adapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_events(source_id=EDGAR_SOURCE_ID, cursor=None, now=NOW)

            self.assertEqual(result.dropped_items[DROP_REASON_COMPANY_ROSTER_STATUS_NOT_CONFIRMED], 9)
            called_ciks = {url.rsplit("CIK", 1)[-1].split(".json")[0] for url, _ in client.calls}
            self.assertNotIn("0001819989", called_ciks)  # CIFR (candidate pool)

    def test_keel_infrastructure_tbc_identifier_is_never_polled(self) -> None:
        with _migrated_test_connection() as connection:
            _verify_edgar_source(connection)
            # Promote Keel to roster_status='confirmed' to isolate the identifier
            # gate from the roster-status gate -- it should still be refused because
            # its ke_company_edgar_identifiers row is identifier_status='tbc'.
            connection.execute(
                "UPDATE ke_companies SET roster_status = 'confirmed' WHERE company_id = ?",
                ("ke-company-keel-infrastructure",),
            )
            connection.commit()
            client = _FakeEdgarClient()
            adapter = _no_sleep_adapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_events(source_id=EDGAR_SOURCE_ID, cursor=None, now=NOW)

            self.assertEqual(result.dropped_items.get(DROP_REASON_COMPANY_EDGAR_IDENTIFIER_TBC), 1)
            self.assertEqual(len(client.calls), 13)  # unchanged: Keel still not polled

    def test_paused_company_is_skipped_and_counted(self) -> None:
        with _migrated_test_connection() as connection:
            _verify_edgar_source(connection)
            connection.execute(
                "UPDATE ke_companies SET status = 'paused' WHERE company_id = ?", ("ke-company-nvda",)
            )
            connection.commit()
            client = _FakeEdgarClient()
            adapter = _no_sleep_adapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_events(source_id=EDGAR_SOURCE_ID, cursor=None, now=NOW)

            self.assertEqual(result.dropped_items.get(DROP_REASON_COMPANY_NOT_ACTIVE), 1)
            self.assertEqual(len(client.calls), 12)

    def test_missing_edgar_identifier_row_is_skipped_and_counted(self) -> None:
        with _migrated_test_connection() as connection:
            _verify_edgar_source(connection)
            connection.execute("DELETE FROM ke_company_edgar_identifiers WHERE company_id = ?", ("ke-company-nvda",))
            connection.commit()
            client = _FakeEdgarClient()
            adapter = _no_sleep_adapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_events(source_id=EDGAR_SOURCE_ID, cursor=None, now=NOW)

            self.assertEqual(result.dropped_items.get(DROP_REASON_COMPANY_EDGAR_IDENTIFIER_MISSING), 1)
            self.assertEqual(len(client.calls), 12)


class PerCompanyFailureIsolationTest(unittest.TestCase):
    def test_one_companys_transport_failure_does_not_fail_the_whole_batch(self) -> None:
        with _migrated_test_connection() as connection:
            _verify_edgar_source(connection)
            client = _FakeEdgarClient(
                errors_by_cik={"0001045810": urllib.error.URLError("boom")},  # NVDA
            )
            adapter = _no_sleep_adapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_events(source_id=EDGAR_SOURCE_ID, cursor=None, now=NOW)

            self.assertTrue(result.healthy)
            self.assertEqual(result.dropped_items.get(DROP_REASON_COMPANY_FETCH_TRANSPORT_FAILED), 1)
            self.assertEqual(len(client.calls), 13)  # every company still attempted

    def test_one_companys_redirect_quarantine_does_not_fail_the_whole_batch(self) -> None:
        with _migrated_test_connection() as connection:
            _verify_edgar_source(connection)
            client = _FakeEdgarClient(
                errors_by_cik={"0001045810": EarningsCalendarRedirectQuarantined("boom")},
            )
            adapter = _no_sleep_adapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_events(source_id=EDGAR_SOURCE_ID, cursor=None, now=NOW)

            self.assertTrue(result.healthy)
            self.assertEqual(result.dropped_items.get(DROP_REASON_COMPANY_FETCH_REDIRECT_QUARANTINED), 1)

    def test_one_companys_oversized_response_does_not_fail_the_whole_batch(self) -> None:
        with _migrated_test_connection() as connection:
            _verify_edgar_source(connection)
            client = _FakeEdgarClient(
                errors_by_cik={"0001045810": EarningsCalendarResponseTooLarge("boom")},
            )
            adapter = _no_sleep_adapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_events(source_id=EDGAR_SOURCE_ID, cursor=None, now=NOW)

            self.assertTrue(result.healthy)
            self.assertEqual(result.dropped_items.get(DROP_REASON_COMPANY_FETCH_RESPONSE_TOO_LARGE), 1)

    def test_one_companys_malformed_response_does_not_fail_the_whole_batch(self) -> None:
        with _migrated_test_connection() as connection:
            _verify_edgar_source(connection)
            client = _FakeEdgarClient(
                bodies_by_cik={"0001045810": b"not json"},
            )
            adapter = _no_sleep_adapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_events(source_id=EDGAR_SOURCE_ID, cursor=None, now=NOW)

            self.assertTrue(result.healthy)
            self.assertEqual(result.dropped_items.get(DROP_REASON_COMPANY_FETCH_MALFORMED_RESPONSE), 1)


class FetchEventsEndToEndTest(unittest.TestCase):
    def test_events_are_created_for_the_matching_company_only(self) -> None:
        with _migrated_test_connection() as connection:
            _verify_edgar_source(connection)
            client = _FakeEdgarClient(bodies_by_cik={"0000320193": AAPL_SUBMISSIONS})
            adapter = _no_sleep_adapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_events(source_id=EDGAR_SOURCE_ID, cursor=None, now=NOW)

            aapl_events = [item for item in result.items if item.company_id == "ke-company-aapl"]
            other_events = [item for item in result.items if item.company_id != "ke-company-aapl"]
            self.assertTrue(aapl_events)
            self.assertEqual(other_events, [])
            for item in result.items:
                self.assertEqual(item.source_id, EDGAR_SOURCE_ID)

    def test_cursor_filters_out_already_seen_items(self) -> None:
        with _migrated_test_connection() as connection:
            _verify_edgar_source(connection)
            client = _FakeEdgarClient(bodies_by_cik={"0000320193": AAPL_SUBMISSIONS})
            adapter = _no_sleep_adapter(connection, feature_mode="shadow_live", client=client)
            with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: FAKE_USER_AGENT}):
                first = adapter.fetch_events(source_id=EDGAR_SOURCE_ID, cursor=None, now=NOW)
                second = adapter.fetch_events(
                    source_id=EDGAR_SOURCE_ID, cursor=first.next_cursor_value, now=NOW
                )

            self.assertEqual(second.items, ())
            self.assertEqual(second.next_cursor_value, first.next_cursor_value)

    def test_max_items_per_fetch_bounds_batch(self) -> None:
        with _migrated_test_connection() as connection:
            _verify_edgar_source(connection)
            client = _FakeEdgarClient(bodies_by_cik={"0000320193": AAPL_SUBMISSIONS})
            adapter = _no_sleep_adapter(
                connection, feature_mode="shadow_live", client=client, max_items_per_fetch=2
            )
            with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: FAKE_USER_AGENT}):
                result = adapter.fetch_events(source_id=EDGAR_SOURCE_ID, cursor=None, now=NOW)

            self.assertLessEqual(len(result.items), 2)

    def test_rate_limiter_is_invoked_once_per_company(self) -> None:
        with _migrated_test_connection() as connection:
            _verify_edgar_source(connection)
            client = _FakeEdgarClient()
            waits: list[int] = []

            class _CountingSleep:
                def __call__(self, seconds: float) -> None:
                    waits.append(1)

            adapter = LiveEarningsCalendarAdapter(
                connection,
                feature_mode="shadow_live",
                client=client,
                min_seconds_between_requests=1000.0,  # force every call after the first to "wait"
                monotonic_fn=lambda: 0.0,
                sleep_fn=_CountingSleep(),
            )
            with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: FAKE_USER_AGENT}):
                adapter.fetch_events(source_id=EDGAR_SOURCE_ID, cursor=None, now=NOW)

            # 13 confirmed companies, 12 of the 13 calls should have had to wait
            # (the first call never waits -- _RateLimiter.wait's own contract).
            self.assertEqual(len(waits), 12)

    def test_default_constructor_rate_limits_at_the_module_constant(self) -> None:
        # SEC's fair-access ceiling is 10 req/s (PHASE0_PROBE_PLAN.md §3); this
        # adapter self-limits well under it -- assert the default constructor
        # actually wires MIN_SECONDS_BETWEEN_REQUESTS through, not just some other
        # hardcoded value.
        with _migrated_test_connection() as connection:
            _verify_edgar_source(connection)
            requested_intervals: list[float] = []
            clock = [0.0]

            def monotonic_fn() -> float:
                return clock[0]

            def sleep_fn(seconds: float) -> None:
                requested_intervals.append(seconds)
                clock[0] += seconds

            adapter = LiveEarningsCalendarAdapter(
                connection,
                feature_mode="shadow_live",
                client=_FakeEdgarClient(),
                monotonic_fn=monotonic_fn,
                sleep_fn=sleep_fn,
            )
            with mock.patch.dict("os.environ", {EDGAR_USER_AGENT_ENV_VAR: FAKE_USER_AGENT}):
                adapter.fetch_events(source_id=EDGAR_SOURCE_ID, cursor=None, now=NOW)

            self.assertTrue(requested_intervals)
            for interval in requested_intervals:
                self.assertAlmostEqual(interval, MIN_SECONDS_BETWEEN_REQUESTS)


def _verify_edgar_source(connection: sqlite3.Connection) -> None:
    ke.record_endpoint_verification(
        connection,
        source_id=EDGAR_SOURCE_ID,
        endpoint_url=EDGAR_ENDPOINT_URL,
        verified_at="2026-07-17T00:00:00+00:00",
        verified_by="conductor:2026-07-17",
    )
    ke.update_source_status(connection, source_id=EDGAR_SOURCE_ID, new_status="active")


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
