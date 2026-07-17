"""Knowledge Edge SEC EDGAR company-identifier state (P-KE-3A, migration 00026).

Backs `personalos.rails.knowledge_edge.earnings_calendar`'s per-company admission
gate against `ke_company_edgar_identifiers`: a company is only ever polled for
submissions data when its row here has `identifier_status='confirmed'` (a CIK is on
file). `identifier_status='tbc'` (today: Keel Infrastructure only, see migration
00026's header) is a real, first-class row -- present so a caller iterating every
roster company's EDGAR status sees it explicitly, not as a silent absence -- but
never admits a live fetch.

Mirrors this package's existing state/rails split (AD-1): this module persists rows
and validates their shape; `earnings_calendar.py` decides what a row means for gating
and gets no import back the other way.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from personalos.knowledge_edge.state._shared import (
    _count_rows,
    _utc_now,
    _validate_enum,
    _validate_optional_iso_date,
    _validate_optional_text,
    _validate_required_text,
    _validate_text,
)

EDGAR_IDENTIFIER_STATUSES = ("confirmed", "tbc")
EDGAR_FILER_FORM_FAMILIES = ("us_domestic", "foreign_private_issuer")


def validate_edgar_identifier_status(value: str) -> str:
    return _validate_enum("identifier_status", value, EDGAR_IDENTIFIER_STATUSES)


def validate_edgar_filer_form_family(value: str) -> str:
    return _validate_enum("filer_form_family", value, EDGAR_FILER_FORM_FAMILIES)


def create_edgar_identifier(
    connection: sqlite3.Connection,
    *,
    company_id: str,
    identifier_status: str,
    cik: str | None = None,
    sec_entity_title: str | None = None,
    sec_ticker: str | None = None,
    filer_form_family: str | None = None,
    verified_as_of_date: str | None = None,
    source: str = "",
    notes: str = "",
) -> dict[str, Any]:
    """Insert one `ke_company_edgar_identifiers` row. Mirrors the migration 00026
    seed shape so a future roster refresh (a new confirmed company, or Keel finally
    getting a CIK) can add a row through this helper instead of hand-written SQL --
    the same "no new script, use the existing state-layer helpers" discipline
    `registries.update_source_status`'s docstring already documents for this
    package.
    """
    company_id = _validate_required_text("company_id", company_id)
    identifier_status = validate_edgar_identifier_status(identifier_status)
    cik = _validate_optional_text("cik", cik)
    if identifier_status == "confirmed" and cik is None:
        raise ValueError("cik must be supplied when identifier_status is 'confirmed'")
    if cik is not None and len(cik) != 10:
        raise ValueError("cik must be a 10-digit, zero-padded SEC identifier")
    sec_entity_title = _validate_optional_text("sec_entity_title", sec_entity_title)
    sec_ticker = _validate_optional_text("sec_ticker", sec_ticker)
    if filer_form_family is not None:
        filer_form_family = validate_edgar_filer_form_family(filer_form_family)
    verified_as_of_date = _validate_optional_iso_date("verified_as_of_date", verified_as_of_date)
    source = _validate_text("source", source)
    notes = _validate_text("notes", notes)
    now = _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO ke_company_edgar_identifiers (
                company_id, cik, sec_entity_title, sec_ticker, filer_form_family,
                identifier_status, verified_as_of_date, source, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company_id, cik, sec_entity_title, sec_ticker, filer_form_family,
                identifier_status, verified_as_of_date, source, notes, now, now,
            ),
        )

    row = get_edgar_identifier(connection, company_id=company_id)
    if row is None:
        raise RuntimeError(
            f"EDGAR identifier was not persisted for company_id: {company_id}"
        )
    return row


def get_edgar_identifier(
    connection: sqlite3.Connection, *, company_id: str
) -> dict[str, Any] | None:
    company_id = _validate_required_text("company_id", company_id)
    row = connection.execute(
        "SELECT * FROM ke_company_edgar_identifiers WHERE company_id = ?", (company_id,)
    ).fetchone()
    return dict(row) if row is not None else None


def list_edgar_identifiers(
    connection: sqlite3.Connection, *, identifier_status: str | None = None
) -> list[dict[str, Any]]:
    if identifier_status is None:
        rows = connection.execute(
            "SELECT * FROM ke_company_edgar_identifiers ORDER BY company_id"
        ).fetchall()
    else:
        identifier_status = validate_edgar_identifier_status(identifier_status)
        rows = connection.execute(
            "SELECT * FROM ke_company_edgar_identifiers WHERE identifier_status = ? ORDER BY company_id",
            (identifier_status,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_confirmed_edgar_identifiers(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    """Every company whose EDGAR identifier is usable today -- the exact set
    `earnings_calendar.py` is allowed to construct a live submissions URL for."""
    return list_edgar_identifiers(connection, identifier_status="confirmed")


def count_edgar_identifiers(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "ke_company_edgar_identifiers")
