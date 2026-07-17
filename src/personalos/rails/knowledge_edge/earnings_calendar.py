"""Live SEC EDGAR earnings-calendar Lane D rail adapter (P-KE-3A) -- inert until a
later, G5-gated packet admits `shadow_live` for Lane D (amendment Sec14.4; Session 2),
exactly the same posture `rails/knowledge_edge/podcasts.py` (P-KE-2A) and
`youtube.py` (P-KE-2B) shipped under. Read those two modules first -- gating order,
host-confined redirects, coverage-honesty dropped-item counting, and refusal-
taxonomy conventions are the house pattern this module extends, not reinvents.

**This is NOT an FMP client.** Per D-PO-019 (`docs/knowledge_edge/PHASE0_ROSTER.md`),
the amendment's original §10.4 paid-calendar-vendor framing was rejected at Session 1
("not down with that") and replaced with a bounded, Conductor-ratified company
roster (~21 names, `PHASE0_ROSTER.md` §3) whose earnings dates are discovered for
free via SEC EDGAR's public `data.sec.gov/submissions/CIK{10}.json` endpoint -- no
API key, identified via the same fair-access `PERSONALOS_RAIL_KE_EDGAR_USER_AGENT`
header D-PO-018 item 4 already approved and `PHASE0_PROBE_PLAN.md` §3 already probed
the mechanism for. IR/webcast link resolution is explicitly out of scope here -- see
point 3 below.

Three differences from `podcasts.py`/`youtube.py`, each explained where it happens:

1. **One `ke_sources` row admits a fetch across many companies, not one row per
   feed/channel.** Migration 00026 seeds exactly one row
   (`ke-source-sec-edgar-submissions`, `source_type='calendar_provider'` -- matching
   `EarningsEventAdapter`'s existing orchestrator routing, see that migration's own
   header) representing the EDGAR submissions mechanism itself; the per-company CIK
   targeting lives in `ke_company_edgar_identifiers` (same migration), read via
   `personalos.knowledge_edge.state.edgar_identifiers`. This module therefore adds a
   SECOND, per-company gate inside the fetch loop, evaluated only after the usual
   source-level feature_mode -> credential -> source/endpoint verification gate
   passes: a company must have `ke_companies.status='active'`,
   `ke_companies.roster_status='confirmed'` (amendment §9.4: "no company is promoted
   automatically" -- the WGMI candidate-pool nine, migration 00026, are NOT polled
   until a future Conductor gate picks the final five), and
   `ke_company_edgar_identifiers.identifier_status='confirmed'` (today: every company
   except Keel Infrastructure, whose CIK is TBC -- migration 00026's header). A
   company failing any of these is skipped and counted via `AdapterFetchResult.
   dropped_items`, exactly like a malformed feed item is counted rather than
   silently absorbed -- it never fails the whole fetch, and a transport/parse
   failure fetching one company's submissions document likewise only drops that
   company's events, never the whole batch (unlike `podcasts.py`, where one feed IS
   the whole batch).
2. **Rate-limited across that per-company loop.** SEC's own published fair-access
   ceiling is 10 requests/second per identifying User-Agent
   (`PHASE0_PROBE_PLAN.md` §3); this module enforces a self-imposed ceiling of at
   most 2 requests/second (`MIN_SECONDS_BETWEEN_REQUESTS`), well under SEC's limit,
   via an injectable clock/sleep pair (`_RateLimiter`) so tests can assert the
   enforced spacing without ever sleeping in real time and without ever touching a
   socket.
3. **EDGAR reports what WAS filed, never a future date.** This packet's own hard
   honesty requirement (no inferred date may ever be presented as confirmed) means
   every event this adapter emits is exactly one of two schedule-confidence shapes,
   both required by amendment §8.4:
     - `confirmed_official` -- derived directly from an already-filed 8-K carrying
       Item 2.02 ("Results of Operations and Financial Condition"), a 10-Q/10-K, or
       (ASML's foreign-private-issuer path, `filer_form_family='foreign_private_
       issuer'`) a 6-K/20-F that already appears in EDGAR's submissions feed -- the
       filing itself IS the official record, so a fresh scheduled-event row anchored
       to it is as confirmed as this lane gets without a live IR page.
     - `estimated` -- at most one inferred "next expected filing" projection per
       company per fetch, derived only from the gap between that company's own two
       most recent quarterly-cadence filings (10-Q, or 6-K for the foreign-private-
       issuer path) -- never labeled confirmed, no matter how regular the company's
       filing history looks, and never given an exact time (`time_precision=
       'date_only'` unconditionally; EDGAR carries no time-of-day).
   Every event this module creates has `live_webcast_url=None`,
   `official_event_page_url=None`, `replay_url=None` -- those fields, plus true IR/
   webcast link resolution, are explicitly P-KE-3B's job
   (`sec_edgar.py`'s `FilingsAdapter` implementation, gated behind the named
   "Packet 3A vendor-domain-list approval" -- see
   `docs/knowledge_edge/PACKET_3A_VENDOR_DOMAIN_LIST.md`), never this module's, and
   never by mutating an event this module already created --
   `scan_orchestrator.py`'s own documented gap 1 (events cannot be updated after
   creation this packet) applies here unchanged. `filing_urls` DOES get one link per
   confirmed event -- the EDGAR filing index URL itself, constructed from the
   filing's own accession number, which is exactly the kind of "link, don't ingest"
   primary-material reference §8.4 asks for and needs no IR-vendor-domain approval
   because it never leaves `sec.gov`.

`LANE_D_FEATURE_MODES` adds `shadow_live` (and the two Session-3 rungs) to Lane D's
own config vocabulary, per amendment Sec14.4 -- vocabulary only, exactly like the two
sibling modules: nothing in this repo constructs
`LiveEarningsCalendarAdapter(feature_mode="shadow_live")` outside this module's own
tests, and this packet does not wire this adapter into `scan_orchestrator.py` or
`cli/knowledge_edge.py` (both still only construct the Packet 1B fixtures) -- that
wiring is a later packet's job, exactly like `podcasts.py`/`youtube.py`'s own
"structurally reachable, not actually reached" posture. Independently of
feature_mode, migration 00026 seeds `ke-source-sec-edgar-submissions` with
`status='trial'` and `endpoint_verified_at IS NULL` -- the source/endpoint
verification gate below refuses every fetch today regardless of feature_mode, until
`docs/knowledge_edge/PACKET_3A_EARNINGS_SUPERVISED_SMOKE.md` records a verification.

Network stack is stdlib-only (`urllib.request`/`urllib.error`, `json`) -- no
third-party HTTP or JSON library, matching the two sibling rails and this repo's
zero-dependency posture. `urllib.parse` is not imported here (that carve-out is
scoped to `engine/canonicalize.py` only); host extraction reuses the same
plain-string technique `podcasts.py`/`youtube.py` already use.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Protocol

import personalos.knowledge_edge.state as ke
from personalos.knowledge_edge.adapters.contracts import AdapterFetchResult, DiscoveredEvent

# ------------------------------------------------------------------ shared vocabulary

EDGAR_USER_AGENT_ENV_VAR = "PERSONALOS_RAIL_KE_EDGAR_USER_AGENT"

LANE_D_FEATURE_MODES = (
    "disabled",
    "fixture",
    "shadow_live",
    "active_read_only",
    "active_with_obsidian_handoff",
)
DEFAULT_LANE_D_FEATURE_MODE = "disabled"
_LANE_D_LIVE_ADMITTING_MODES = frozenset(
    {"shadow_live", "active_read_only", "active_with_obsidian_handoff"}
)

REQUEST_TIMEOUT_SECONDS = 10.0
# No live measurement exists for this cap yet (this packet is fully inert -- no real
# request has ever been made). Reasoned bound, not a measured one, unlike podcasts.py's
# P-KE-2D-retuned cap: EDGAR's documented `submissions/CIK{10}.json` shape holds only
# `filings.recent` (a bounded recent-activity window; a filer with a long history
# paginates older filings into separate `filings.files` documents this adapter never
# fetches), so even a high-filing-volume issuer's response is expected well under 1 MB.
# 5 MB gives generous headroom while still bounding a pathological/misrouted response.
MAX_RESPONSE_BYTES_PER_COMPANY = 5_000_000
MAX_ITEMS_PER_FETCH = 200
# SEC's own published fair-access ceiling is 10 requests/second per identifying
# User-Agent (PHASE0_PROBE_PLAN.md §3); this adapter self-limits to well under that.
MIN_SECONDS_BETWEEN_REQUESTS = 0.5
# Bounds how many confirmed (already-filed) events this adapter creates per company
# per relevant form type in one fetch -- roughly a year of quarterlies -- so a
# first-ever run against a company with a long EDGAR history does not flood the
# queue with old, already-past events.
MAX_CONFIRMED_FILINGS_PER_FORM = 4
# The cadence inference (schedule_confidence='estimated') is refused outside this
# band: a same-day or multi-year gap between two "quarterly" filings is more likely a
# data anomaly (amended filing, restatement, missed year) than a usable cadence
# signal, and this adapter would rather emit nothing than an obviously wrong estimate.
_MIN_PLAUSIBLE_CADENCE_DAYS = 60
_MAX_PLAUSIBLE_CADENCE_DAYS = 200

EIGHT_K_EARNINGS_ITEM_CODE = "2.02"
FILER_FORM_FAMILY_RELEVANT_FORMS: dict[str, frozenset[str]] = {
    "us_domestic": frozenset({"10-Q", "10-K", "8-K"}),
    "foreign_private_issuer": frozenset({"20-F", "6-K"}),
}
# Which relevant forms carry cadence-usable quarterly signal (used for the
# 'estimated' next-event inference) -- annual forms and non-earnings 8-Ks are
# excluded from the cadence calculation even though 10-K/20-F are still eligible for
# their own confirmed_official annual_results event.
_CADENCE_FORMS: dict[str, frozenset[str]] = {
    "us_domestic": frozenset({"10-Q"}),
    "foreign_private_issuer": frozenset({"6-K"}),
}

STATUS_BLOCKED_FEATURE_MODE = "earnings_calendar_rail_live_fetch_blocked_feature_mode_not_live"
STATUS_BLOCKED_CREDENTIAL_MISSING = "earnings_calendar_rail_live_fetch_blocked_credential_env_var_missing"
STATUS_BLOCKED_CREDENTIAL_EMPTY = "earnings_calendar_rail_live_fetch_blocked_credential_env_var_empty"
STATUS_BLOCKED_SOURCE_NOT_FOUND = "earnings_calendar_rail_live_fetch_blocked_source_not_found"
STATUS_BLOCKED_NO_ENDPOINT = "earnings_calendar_rail_live_fetch_blocked_no_active_endpoint"
STATUS_BLOCKED_SOURCE_NOT_VERIFIED = "earnings_calendar_rail_live_fetch_blocked_source_not_verified"
STATUS_BLOCKED_ENDPOINT_INSECURE_SCHEME = "earnings_calendar_rail_live_fetch_blocked_endpoint_insecure_scheme"

# Per-company drop reasons (F1, mirroring podcasts.py/youtube.py): a company skipped
# for any of these reasons is counted, never silently absent from coverage reporting.
DROP_REASON_COMPANY_NOT_ACTIVE = "company_not_active"
DROP_REASON_COMPANY_ROSTER_STATUS_NOT_CONFIRMED = "company_roster_status_not_confirmed"
DROP_REASON_COMPANY_EDGAR_IDENTIFIER_MISSING = "company_edgar_identifier_missing"
DROP_REASON_COMPANY_EDGAR_IDENTIFIER_TBC = "company_edgar_identifier_tbc"
DROP_REASON_COMPANY_FETCH_TRANSPORT_FAILED = "company_fetch_transport_failed"
DROP_REASON_COMPANY_FETCH_REDIRECT_QUARANTINED = "company_fetch_redirect_quarantined"
DROP_REASON_COMPANY_FETCH_RESPONSE_TOO_LARGE = "company_fetch_response_too_large"
DROP_REASON_COMPANY_FETCH_MALFORMED_RESPONSE = "company_fetch_malformed_response"


def validate_lane_d_feature_mode(value: str) -> str:
    if value not in LANE_D_FEATURE_MODES:
        allowed = ", ".join(LANE_D_FEATURE_MODES)
        raise ValueError(f"Lane D feature mode must be one of: {allowed}")
    return value


class EarningsCalendarFetchError(Exception):
    """Base class for adapter-raised (non-transport) fetch failures."""


class EarningsCalendarRedirectQuarantined(EarningsCalendarFetchError):
    """A submissions response's HTTP redirect pointed at a different host than the
    request's own -- refused."""


class EarningsCalendarResponseTooLarge(EarningsCalendarFetchError):
    """The submissions response exceeded MAX_RESPONSE_BYTES_PER_COMPANY -- refused
    before it was fully buffered."""


class MalformedSubmissionsResponseError(Exception):
    """The fetched document could not be parsed as a well-formed EDGAR submissions
    JSON document, or its declared `cik` did not match the company being fetched."""


def _extract_host(url: str) -> str:
    """Lowercased host, extracted with plain string ops -- no `urllib.parse` import
    (that carve-out is scoped to `engine/canonicalize.py` only); mirrors
    `podcasts.py`/`youtube.py`'s identical technique."""
    remainder = url.split("://", 1)[-1]
    host = remainder.split("/", 1)[0]
    return host.rsplit("@", 1)[-1].split(":", 1)[0].lower()


class _HostConfinedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follows a redirect only when it stays on the request's own host and stays
    https:// -- identical logic to the two sibling rails' handler of the same name,
    duplicated rather than imported so this module stays independent
    (`PHASE0_ARCHITECTURE_DECISIONS.md` AD-1's per-module independence)."""

    def __init__(self, allowed_host: str) -> None:
        super().__init__()
        self._allowed_host = allowed_host

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        if not newurl.startswith("https://"):
            raise EarningsCalendarRedirectQuarantined(
                f"refusing redirect from {req.full_url!r} to a non-https:// target "
                f"({newurl!r}): HTTPS->HTTP downgrade is never followed"
            )
        redirect_host = _extract_host(newurl)
        if redirect_host != self._allowed_host:
            raise EarningsCalendarRedirectQuarantined(
                f"refusing redirect from host {self._allowed_host!r} to a different "
                f"host {redirect_host!r} ({newurl!r})"
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class EdgarSubmissionsHttpClientProtocol(Protocol):
    def fetch(self, url: str, *, user_agent: str) -> bytes: ...


class EdgarSubmissionsHttpClient:
    """Thin stdlib-only HTTPS client for one company's EDGAR submissions document.
    Mirrors `podcasts.py`'s `PodcastFeedHttpClient` exactly, including the P-KE-2D
    Content-Length preflight refusal -- see that module for the full reasoning."""

    def __init__(
        self,
        *,
        timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
        max_response_bytes: int = MAX_RESPONSE_BYTES_PER_COMPANY,
        opener: Any | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._max_response_bytes = max_response_bytes
        self._opener = opener

    def fetch(self, url: str, *, user_agent: str) -> bytes:
        request = urllib.request.Request(url, method="GET", headers={"User-Agent": user_agent})
        opener = self._opener
        if opener is None:
            redirect_handler = _HostConfinedRedirectHandler(_extract_host(url))
            opener = urllib.request.build_opener(redirect_handler).open
        with opener(request, timeout=self._timeout_seconds) as response:
            content_length = response.headers.get("Content-Length")
            if content_length is not None:
                try:
                    declared_bytes = int(content_length)
                except ValueError:
                    declared_bytes = None
                if declared_bytes is not None and declared_bytes > self._max_response_bytes:
                    raise EarningsCalendarResponseTooLarge(
                        f"submissions response at {url!r} declared Content-Length "
                        f"{declared_bytes} bytes, exceeding the {self._max_response_bytes}-byte "
                        "cap; refusing before reading the body"
                    )
            raw = response.read(self._max_response_bytes + 1)
        if len(raw) > self._max_response_bytes:
            raise EarningsCalendarResponseTooLarge(
                f"submissions response at {url!r} exceeded the {self._max_response_bytes}-byte cap"
            )
        return raw


class _RateLimiter:
    """Enforces at most one request per `min_interval_seconds`, with an injectable
    clock/sleep pair so tests can assert the enforced spacing deterministically and
    without ever sleeping in real time (this packet's own "zero live requests in
    build/tests" hard constraint applies equally to accidental real sleeps)."""

    def __init__(
        self,
        *,
        min_interval_seconds: float,
        monotonic_fn: Callable[[], float] = time.monotonic,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._min_interval_seconds = min_interval_seconds
        self._monotonic_fn = monotonic_fn
        self._sleep_fn = sleep_fn
        self._last_request_at: float | None = None

    def wait(self) -> None:
        if self._last_request_at is not None:
            elapsed = self._monotonic_fn() - self._last_request_at
            remaining = self._min_interval_seconds - elapsed
            if remaining > 0:
                self._sleep_fn(remaining)
        self._last_request_at = self._monotonic_fn()


@dataclass(frozen=True)
class _ParsedFiling:
    form: str
    filing_date: str
    report_date: str | None
    accession_number: str
    primary_document: str
    items: tuple[str, ...] = ()


def _edgar_filing_index_url(*, cik: str, accession_number: str, primary_document: str) -> str:
    cik_numeric = str(int(cik))
    accession_no_dashes = accession_number.replace("-", "")
    if not primary_document:
        return f"https://www.sec.gov/Archives/edgar/data/{cik_numeric}/{accession_no_dashes}/"
    return f"https://www.sec.gov/Archives/edgar/data/{cik_numeric}/{accession_no_dashes}/{primary_document}"


def _parse_submissions_document(raw: bytes, *, expected_cik: str) -> list[_ParsedFiling]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as parse_error:
        raise MalformedSubmissionsResponseError(
            f"submissions response is not valid JSON: {parse_error}"
        ) from parse_error

    if not isinstance(payload, dict):
        raise MalformedSubmissionsResponseError("submissions response is not a JSON object")

    declared_cik = payload.get("cik")
    if declared_cik is not None:
        # EDGAR's own `cik` field is an unpadded numeric string (e.g. "320193"); the
        # zero-padded 10-digit form is this repo's storage convention (migration
        # 00026). Compare on the normalized integer value so a well-formed response
        # is never rejected over padding, while a genuinely misrouted response (a
        # different company's document served for this URL) still fails the check.
        try:
            if int(str(declared_cik)) != int(expected_cik):
                raise MalformedSubmissionsResponseError(
                    f"submissions response declared cik={declared_cik!r}, expected {expected_cik!r}"
                )
        except ValueError as parse_error:
            raise MalformedSubmissionsResponseError(
                f"submissions response cik field is not numeric: {declared_cik!r}"
            ) from parse_error

    filings = payload.get("filings")
    if not isinstance(filings, dict) or not isinstance(filings.get("recent"), dict):
        raise MalformedSubmissionsResponseError(
            "submissions response is missing a top-level filings.recent object"
        )
    recent = filings["recent"]

    forms = recent.get("form")
    filing_dates = recent.get("filingDate")
    if not isinstance(forms, list) or not isinstance(filing_dates, list):
        raise MalformedSubmissionsResponseError(
            "filings.recent is missing required 'form'/'filingDate' arrays"
        )
    report_dates = recent.get("reportDate") if isinstance(recent.get("reportDate"), list) else None
    accession_numbers = (
        recent.get("accessionNumber") if isinstance(recent.get("accessionNumber"), list) else None
    )
    primary_documents = (
        recent.get("primaryDocument") if isinstance(recent.get("primaryDocument"), list) else None
    )
    items_lists = recent.get("items") if isinstance(recent.get("items"), list) else None

    count = len(forms)
    if len(filing_dates) != count:
        raise MalformedSubmissionsResponseError(
            "filings.recent arrays have mismatched lengths"
        )

    parsed: list[_ParsedFiling] = []
    for index in range(count):
        form = forms[index]
        filing_date = filing_dates[index]
        if not isinstance(form, str) or not form:
            continue
        if not isinstance(filing_date, str):
            continue
        try:
            date.fromisoformat(filing_date)
        except ValueError:
            continue

        report_date = report_dates[index] if report_dates and index < len(report_dates) else None
        if isinstance(report_date, str) and report_date:
            try:
                date.fromisoformat(report_date)
            except ValueError:
                report_date = None
        else:
            report_date = None

        accession_number = (
            accession_numbers[index] if accession_numbers and index < len(accession_numbers) else None
        )
        if not isinstance(accession_number, str) or not accession_number:
            # A filing with no stable accession number cannot be turned into a
            # deterministic, idempotent event_id_hint -- skip it rather than invent one.
            continue

        primary_document = (
            primary_documents[index]
            if primary_documents and index < len(primary_documents)
            else ""
        )
        if not isinstance(primary_document, str):
            primary_document = ""

        raw_items = items_lists[index] if items_lists and index < len(items_lists) else ""
        item_codes = (
            tuple(code.strip() for code in raw_items.split(",") if code.strip())
            if isinstance(raw_items, str) and raw_items
            else ()
        )

        parsed.append(
            _ParsedFiling(
                form=form,
                filing_date=filing_date,
                report_date=report_date,
                accession_number=accession_number,
                primary_document=primary_document,
                items=item_codes,
            )
        )

    return parsed


def _event_type_for_form(form: str) -> str | None:
    if form in ("10-K", "20-F"):
        return "annual_results"
    if form in ("10-Q", "6-K"):
        return "quarterly_earnings"
    if form == "8-K":
        return "quarterly_earnings"
    return None


def _derive_confirmed_events(
    *, company_id: str, cik: str, filer_form_family: str, filings: Sequence[_ParsedFiling]
) -> list[DiscoveredEvent]:
    relevant_forms = FILER_FORM_FAMILY_RELEVANT_FORMS[filer_form_family]
    candidates = [
        filing
        for filing in filings
        if filing.form in relevant_forms
        and (filing.form != "8-K" or EIGHT_K_EARNINGS_ITEM_CODE in filing.items)
    ]

    events: list[DiscoveredEvent] = []
    by_form: dict[str, list[_ParsedFiling]] = {}
    for filing in candidates:
        by_form.setdefault(filing.form, []).append(filing)

    for form, form_filings in by_form.items():
        event_type = _event_type_for_form(form)
        if event_type is None:
            continue
        ordered = sorted(form_filings, key=lambda filing: filing.filing_date, reverse=True)
        for filing in ordered[:MAX_CONFIRMED_FILINGS_PER_FORM]:
            # The event date is when EDGAR says the filing happened, not the fiscal
            # period it covers -- a 10-Q filed 2026-05-01 reporting on Q1 (period end
            # 2026-03-31) is a 2026-05-01 event. report_date is preserved separately
            # below as fiscal_period.
            scheduled_date = filing.filing_date
            filing_url = _edgar_filing_index_url(
                cik=cik, accession_number=filing.accession_number, primary_document=filing.primary_document
            )
            events.append(
                DiscoveredEvent(
                    source_id="",  # filled in by the caller once the batch is built
                    company_id=company_id,
                    event_id_hint=f"{form}-{filing.accession_number}",
                    event_type=event_type,
                    scheduled_date=scheduled_date,
                    time_precision="date_only",
                    schedule_confidence="confirmed_official",
                    schedule_source=f"sec_edgar_submissions:{form}:{filing.accession_number}",
                    fiscal_period=filing.report_date,
                    earnings_release_url=filing_url if form == "8-K" else None,
                    filing_urls=(filing_url,),
                    cursor_value=f"{filing.filing_date}|{company_id}|{filing.accession_number}",
                )
            )
    return events


def _derive_inferred_next_event(
    *, company_id: str, filer_form_family: str, filings: Sequence[_ParsedFiling]
) -> DiscoveredEvent | None:
    cadence_forms = _CADENCE_FORMS[filer_form_family]
    cadence_filings = sorted(
        (filing for filing in filings if filing.form in cadence_forms),
        key=lambda filing: filing.filing_date,
        reverse=True,
    )
    if len(cadence_filings) < 2:
        return None

    latest, previous = cadence_filings[0], cadence_filings[1]
    latest_date = date.fromisoformat(latest.filing_date)
    previous_date = date.fromisoformat(previous.filing_date)
    gap_days = (latest_date - previous_date).days
    if not (_MIN_PLAUSIBLE_CADENCE_DAYS <= gap_days <= _MAX_PLAUSIBLE_CADENCE_DAYS):
        return None

    projected_date = latest_date + timedelta(days=gap_days)
    return DiscoveredEvent(
        source_id="",
        company_id=company_id,
        event_id_hint=f"inferred-next-after-{latest.accession_number}",
        event_type="quarterly_earnings",
        scheduled_date=projected_date.isoformat(),
        time_precision="date_only",
        schedule_confidence="estimated",
        schedule_source="sec_edgar_submissions:inferred_from_history",
        cursor_value=f"{projected_date.isoformat()}|{company_id}|inferred",
    )


def _derive_events_for_company(
    *, company_id: str, cik: str, filer_form_family: str, filings: Sequence[_ParsedFiling]
) -> tuple[DiscoveredEvent, ...]:
    """Every event this adapter can honestly report for one company's filings:
    zero or more `confirmed_official` events (one per relevant already-filed
    document, per §8.4's launch event types) plus at most one `estimated`
    next-event projection derived only from filing-cadence history. Never returns
    anything else -- see module docstring point 3."""
    confirmed = _derive_confirmed_events(
        company_id=company_id, cik=cik, filer_form_family=filer_form_family, filings=filings
    )
    inferred = _derive_inferred_next_event(
        company_id=company_id, filer_form_family=filer_form_family, filings=filings
    )
    return tuple(confirmed) + ((inferred,) if inferred is not None else ())


def _with_source_id(event: DiscoveredEvent, *, source_id: str) -> DiscoveredEvent:
    return DiscoveredEvent(
        source_id=source_id,
        company_id=event.company_id,
        event_id_hint=event.event_id_hint,
        event_type=event.event_type,
        scheduled_date=event.scheduled_date,
        time_precision=event.time_precision,
        schedule_confidence=event.schedule_confidence,
        schedule_source=event.schedule_source,
        start_time_utc=event.start_time_utc,
        end_time_utc=event.end_time_utc,
        source_timezone=event.source_timezone,
        timing_label=event.timing_label,
        fiscal_period=event.fiscal_period,
        official_event_page_url=event.official_event_page_url,
        live_webcast_url=event.live_webcast_url,
        replay_url=event.replay_url,
        earnings_release_url=event.earnings_release_url,
        filing_urls=event.filing_urls,
        slides_url=event.slides_url,
        shareholder_letter_url=event.shareholder_letter_url,
        prepared_remarks_url=event.prepared_remarks_url,
        cursor_value=event.cursor_value,
    )


def _unhealthy(source_id: str, cursor: str | None, error_summary: str) -> AdapterFetchResult:
    return AdapterFetchResult(
        source_id=source_id,
        items=(),
        next_cursor_value=cursor,
        healthy=False,
        error_summary=error_summary,
    )


def _resolve_primary_api_endpoint(
    connection: sqlite3.Connection, *, source_id: str
) -> dict[str, Any] | None:
    endpoints = [
        endpoint
        for endpoint in ke.list_source_endpoints(connection, source_id=source_id)
        if endpoint["endpoint_type"] == "api_endpoint" and endpoint["status"] == "active"
    ]
    if not endpoints:
        return None
    primary = [endpoint for endpoint in endpoints if endpoint["is_primary"]]
    return primary[0] if primary else endpoints[0]


def _parse_iso8601_to_iso_utc(text: str) -> str | None:
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat()


def _merge_counts(*counters: dict[str, int]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for counter in counters:
        for reason, count in counter.items():
            merged[reason] = merged.get(reason, 0) + count
    return merged


class LiveEarningsCalendarAdapter:
    """Live implementation of `EarningsEventAdapter`
    (`personalos.knowledge_edge.adapters.contracts`): `fetch_events(source_id=...,
    cursor=..., now=...)`, same shape as `FixtureEarningsEventAdapter`. One call
    polls every gate-admissible roster company (see module docstring point 1), not
    just the one `source_id` -- the D-PO-019 roster IS this source's scope.
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
        *,
        feature_mode: str = DEFAULT_LANE_D_FEATURE_MODE,
        credential_env_var: str = EDGAR_USER_AGENT_ENV_VAR,
        client: EdgarSubmissionsHttpClientProtocol | None = None,
        max_items_per_fetch: int = MAX_ITEMS_PER_FETCH,
        min_seconds_between_requests: float = MIN_SECONDS_BETWEEN_REQUESTS,
        monotonic_fn: Callable[[], float] = time.monotonic,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._connection = connection
        self._feature_mode = validate_lane_d_feature_mode(feature_mode)
        self._credential_env_var = credential_env_var
        self._client = client if client is not None else EdgarSubmissionsHttpClient()
        self._max_items_per_fetch = max_items_per_fetch
        self._rate_limiter = _RateLimiter(
            min_interval_seconds=min_seconds_between_requests,
            monotonic_fn=monotonic_fn,
            sleep_fn=sleep_fn,
        )

    def fetch_events(
        self, *, source_id: str, cursor: str | None, now: datetime
    ) -> AdapterFetchResult:
        del now  # every date this adapter reports comes from EDGAR's own declared
        # filingDate/reportDate (confirmed) or a filing-cadence projection derived
        # from those same declared dates (estimated) -- never the wall clock.

        error, endpoint_url, user_agent = self._evaluate_source_gates(source_id=source_id)
        if error is not None:
            return _unhealthy(source_id, cursor, error)

        admissible, dropped = self._admissible_companies()

        all_items: list[DiscoveredEvent] = []
        for company, edgar_row in admissible:
            cik = edgar_row["cik"]
            url = f"{endpoint_url}CIK{cik}.json"
            self._rate_limiter.wait()
            try:
                raw = self._client.fetch(url, user_agent=user_agent)
            except EarningsCalendarRedirectQuarantined:
                dropped[DROP_REASON_COMPANY_FETCH_REDIRECT_QUARANTINED] = (
                    dropped.get(DROP_REASON_COMPANY_FETCH_REDIRECT_QUARANTINED, 0) + 1
                )
                continue
            except EarningsCalendarResponseTooLarge:
                dropped[DROP_REASON_COMPANY_FETCH_RESPONSE_TOO_LARGE] = (
                    dropped.get(DROP_REASON_COMPANY_FETCH_RESPONSE_TOO_LARGE, 0) + 1
                )
                continue
            except (OSError, urllib.error.URLError):
                dropped[DROP_REASON_COMPANY_FETCH_TRANSPORT_FAILED] = (
                    dropped.get(DROP_REASON_COMPANY_FETCH_TRANSPORT_FAILED, 0) + 1
                )
                continue

            try:
                filings = _parse_submissions_document(raw, expected_cik=cik)
            except MalformedSubmissionsResponseError:
                dropped[DROP_REASON_COMPANY_FETCH_MALFORMED_RESPONSE] = (
                    dropped.get(DROP_REASON_COMPANY_FETCH_MALFORMED_RESPONSE, 0) + 1
                )
                continue

            events = _derive_events_for_company(
                company_id=company["company_id"],
                cik=cik,
                filer_form_family=edgar_row["filer_form_family"],
                filings=filings,
            )
            all_items.extend(_with_source_id(event, source_id=source_id) for event in events)

        due = tuple(item for item in all_items if cursor is None or item.cursor_value > cursor)
        due_sorted = tuple(sorted(due, key=lambda item: item.cursor_value))
        due_sorted = due_sorted[: self._max_items_per_fetch]
        next_cursor = due_sorted[-1].cursor_value if due_sorted else cursor
        return AdapterFetchResult(
            source_id=source_id,
            items=due_sorted,
            next_cursor_value=next_cursor,
            healthy=True,
            dropped_items=dropped,
        )

    def _admissible_companies(
        self,
    ) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], dict[str, int]]:
        """Every roster company (`ke_companies`, every group/status), partitioned
        into `(company, edgar_row)` pairs this adapter may poll and a `dropped`
        counter for every company it may not -- see module docstring point 1 for the
        three gates applied here, in order."""
        dropped: dict[str, int] = {}
        admissible: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for company in ke.list_companies(self._connection):
            if company["status"] != "active":
                dropped[DROP_REASON_COMPANY_NOT_ACTIVE] = dropped.get(DROP_REASON_COMPANY_NOT_ACTIVE, 0) + 1
                continue
            if company["roster_status"] != "confirmed":
                dropped[DROP_REASON_COMPANY_ROSTER_STATUS_NOT_CONFIRMED] = (
                    dropped.get(DROP_REASON_COMPANY_ROSTER_STATUS_NOT_CONFIRMED, 0) + 1
                )
                continue
            edgar_row = ke.get_edgar_identifier(self._connection, company_id=company["company_id"])
            if edgar_row is None:
                dropped[DROP_REASON_COMPANY_EDGAR_IDENTIFIER_MISSING] = (
                    dropped.get(DROP_REASON_COMPANY_EDGAR_IDENTIFIER_MISSING, 0) + 1
                )
                continue
            if edgar_row["identifier_status"] != "confirmed":
                dropped[DROP_REASON_COMPANY_EDGAR_IDENTIFIER_TBC] = (
                    dropped.get(DROP_REASON_COMPANY_EDGAR_IDENTIFIER_TBC, 0) + 1
                )
                continue
            admissible.append((company, edgar_row))

        admissible.sort(key=lambda pair: pair[0]["company_id"])
        return admissible, dropped

    def _evaluate_source_gates(
        self, *, source_id: str
    ) -> tuple[str | None, str | None, str | None]:
        """Returns `(error, endpoint_url, user_agent)`. `error` is `None` only once
        every gate has passed, in the fixed order feature_mode -> credentials ->
        source/endpoint verification -- identical order to `podcasts.py`/
        `youtube.py`'s own `_evaluate_gates` (AD-3: a read-only discovery adapter
        does not get the full four-gate write pattern)."""
        if self._feature_mode not in _LANE_D_LIVE_ADMITTING_MODES:
            return (
                f"{STATUS_BLOCKED_FEATURE_MODE}: feature_mode {self._feature_mode!r} does not "
                "admit a live Lane D fetch ('disabled'/'fixture' never fetch live)",
                None,
                None,
            )

        if self._credential_env_var not in os.environ:
            return (
                f"{STATUS_BLOCKED_CREDENTIAL_MISSING}: credential env var is not set: "
                f"{self._credential_env_var}",
                None,
                None,
            )
        user_agent = os.environ[self._credential_env_var]
        if not user_agent.strip():
            return (
                f"{STATUS_BLOCKED_CREDENTIAL_EMPTY}: credential env var is set but empty: "
                f"{self._credential_env_var}",
                None,
                None,
            )

        source = ke.get_source(self._connection, source_id)
        if source is None:
            return (
                f"{STATUS_BLOCKED_SOURCE_NOT_FOUND}: no ke_sources row for {source_id!r}",
                None,
                None,
            )

        endpoint = _resolve_primary_api_endpoint(self._connection, source_id=source_id)
        if endpoint is None:
            return (
                f"{STATUS_BLOCKED_NO_ENDPOINT}: no active api_endpoint on file for "
                f"{source_id!r}",
                None,
                None,
            )

        verified_at = endpoint["endpoint_verified_at"]
        verified_by = endpoint["verified_by"]
        verified_by_present = verified_by is not None and str(verified_by).strip() != ""
        if source["status"] != "active" or verified_at is None or not verified_by_present:
            return (
                f"{STATUS_BLOCKED_SOURCE_NOT_VERIFIED}: source status is {source['status']!r} "
                f"(endpoint_verified_at={verified_at!r}, verified_by={verified_by!r}); refusing "
                "until the Conductor-supervised smoke records a verification (see "
                "docs/knowledge_edge/PACKET_3A_EARNINGS_SUPERVISED_SMOKE.md)",
                None,
                None,
            )
        if _parse_iso8601_to_iso_utc(str(verified_at)) is None:
            return (
                f"{STATUS_BLOCKED_SOURCE_NOT_VERIFIED}: endpoint_verified_at={verified_at!r} is "
                "not a parseable timestamp; refusing rather than trusting a malformed "
                "verification record (see docs/knowledge_edge/PACKET_3A_EARNINGS_SUPERVISED_SMOKE.md)",
                None,
                None,
            )

        endpoint_url = endpoint["url"]
        if not endpoint_url.startswith("https://"):
            return (
                f"{STATUS_BLOCKED_ENDPOINT_INSECURE_SCHEME}: endpoint url {endpoint_url!r} is "
                "not https://; refusing to construct a live request over an insecure scheme",
                None,
                None,
            )

        return (None, endpoint_url, user_agent)
