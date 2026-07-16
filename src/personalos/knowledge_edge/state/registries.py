"""Knowledge Edge registry state: source, person, role, role_occupancy, affiliation,
company, company_identifier, topic (amendment §13.1, §8.1-8.3, §9.3).
"""

from __future__ import annotations

import sqlite3
from typing import Any

from personalos.knowledge_edge.state._shared import (
    _count_rows,
    _deserialize_json_array,
    _serialize_json,
    _utc_now,
    _validate_bool,
    _validate_enum,
    _validate_optional_iso_date,
    _validate_optional_text,
    _validate_required_text,
    _validate_text,
)

SOURCE_TYPES = (
    "podcast_feed",
    "youtube_channel",
    "network_program",
    "ir_page",
    "calendar_provider",
    "sec_edgar",
    "person_search_provider",
    "manual_link",
)
SOURCE_LANES = (
    "curated_podcasts",
    "market_voices",
    "consequential_leaders",
    "earnings_events",
)
SOURCE_STATUSES = ("active", "trial", "paused", "retired")
SOURCE_ENDPOINT_TYPES = ("rss", "atom", "channel_id", "api_endpoint", "page_url")
SOURCE_ENDPOINT_STATUSES = ("active", "retired")

PERSON_CATEGORIES = ("market_voice", "consequential_leader", "role_occupant")
PERSON_STATUSES = ("active", "retired")
PERSON_ALIAS_TYPES = ("exact", "spelling_variant")

ROLE_CATEGORIES = ("government", "frontier_ai_lab", "semiconductor_platform", "corporate")
ROLE_OCCUPANCY_DATE_PRECISIONS = ("exact", "month", "estimated", "unknown_predates_tracking")

COMPANY_ROSTER_GROUPS = ("nasdaq100_top10", "crypto_native_top3", "wgmi_candidate_pool")
COMPANY_ROSTER_STATUSES = ("confirmed", "candidate")
COMPANY_ROSTER_RANK_BASES = ("market_cap", "fund_weight")
COMPANY_PRIORITY_TIERS = ("tier_a", "tier_b")
COMPANY_STATUSES = ("active", "paused", "retired")
COMPANY_IDENTIFIER_TYPES = ("ticker", "cik", "isin")


# --------------------------------------------------------------------------- validators


def validate_source_type(value: str) -> str:
    return _validate_enum("source_type", value, SOURCE_TYPES)


def validate_source_lane(value: str) -> str:
    return _validate_enum("lane", value, SOURCE_LANES)


def validate_source_status(value: str) -> str:
    return _validate_enum("status", value, SOURCE_STATUSES)


def validate_source_endpoint_type(value: str) -> str:
    return _validate_enum("endpoint_type", value, SOURCE_ENDPOINT_TYPES)


def validate_source_endpoint_status(value: str) -> str:
    return _validate_enum("status", value, SOURCE_ENDPOINT_STATUSES)


def validate_person_category(value: str) -> str:
    return _validate_enum("category", value, PERSON_CATEGORIES)


def validate_person_status(value: str) -> str:
    return _validate_enum("status", value, PERSON_STATUSES)


def validate_person_alias_type(value: str) -> str:
    return _validate_enum("alias_type", value, PERSON_ALIAS_TYPES)


def validate_role_category(value: str) -> str:
    return _validate_enum("role_category", value, ROLE_CATEGORIES)


def validate_role_occupancy_date_precision(value: str) -> str:
    return _validate_enum("date_precision", value, ROLE_OCCUPANCY_DATE_PRECISIONS)


def validate_company_roster_group(value: str) -> str:
    return _validate_enum("roster_group", value, COMPANY_ROSTER_GROUPS)


def validate_company_roster_status(value: str) -> str:
    return _validate_enum("roster_status", value, COMPANY_ROSTER_STATUSES)


def validate_company_roster_rank_basis(value: str) -> str:
    return _validate_enum("roster_group_rank_basis", value, COMPANY_ROSTER_RANK_BASES)


def validate_company_priority_tier(value: str) -> str:
    return _validate_enum("priority_tier", value, COMPANY_PRIORITY_TIERS)


def validate_company_status(value: str) -> str:
    return _validate_enum("status", value, COMPANY_STATUSES)


def validate_company_identifier_type(value: str) -> str:
    return _validate_enum("identifier_type", value, COMPANY_IDENTIFIER_TYPES)


# ------------------------------------------------------------------------------ sources


def create_source(
    connection: sqlite3.Connection,
    *,
    source_id: str,
    source_type: str,
    lane: str,
    name: str,
    topic_group: str | None = None,
    status: str = "active",
    cadence_expectation_days: int | None = None,
    notes: str = "",
) -> dict[str, Any]:
    source_id = _validate_required_text("source_id", source_id)
    source_type = validate_source_type(source_type)
    lane = validate_source_lane(lane)
    name = _validate_required_text("name", name)
    topic_group = _validate_optional_text("topic_group", topic_group)
    status = validate_source_status(status)
    if cadence_expectation_days is not None and cadence_expectation_days <= 0:
        raise ValueError("cadence_expectation_days must be positive")
    notes = _validate_text("notes", notes)
    now = _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO ke_sources (
                source_id, source_type, lane, topic_group, name, status,
                cadence_expectation_days, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id, source_type, lane, topic_group, name, status,
                cadence_expectation_days, notes, now, now,
            ),
        )

    source = get_source(connection, source_id)
    if source is None:
        raise RuntimeError(f"Source was not persisted for source_id: {source_id}")
    return source


def get_source(connection: sqlite3.Connection, source_id: str) -> dict[str, Any] | None:
    source_id = _validate_required_text("source_id", source_id)
    row = connection.execute(
        "SELECT * FROM ke_sources WHERE source_id = ?", (source_id,)
    ).fetchone()
    return dict(row) if row is not None else None


def list_sources(
    connection: sqlite3.Connection,
    *,
    lane: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if lane is not None:
        clauses.append("lane = ?")
        params.append(validate_source_lane(lane))
    if status is not None:
        clauses.append("status = ?")
        params.append(validate_source_status(status))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = connection.execute(
        f"SELECT * FROM ke_sources {where} ORDER BY name, source_id", params
    ).fetchall()
    return [dict(row) for row in rows]


def count_sources(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "ke_sources")


def create_source_endpoint(
    connection: sqlite3.Connection,
    *,
    source_endpoint_id: str,
    source_id: str,
    endpoint_type: str,
    url: str,
    is_primary: bool = True,
    status: str = "active",
) -> dict[str, Any]:
    source_endpoint_id = _validate_required_text("source_endpoint_id", source_endpoint_id)
    source_id = _validate_required_text("source_id", source_id)
    endpoint_type = validate_source_endpoint_type(endpoint_type)
    url = _validate_required_text("url", url)
    is_primary = _validate_bool("is_primary", is_primary)
    status = validate_source_endpoint_status(status)
    now = _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO ke_source_endpoints (
                source_endpoint_id, source_id, endpoint_type, url, is_primary, status,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_endpoint_id, source_id, endpoint_type, url, int(is_primary),
                status, now, now,
            ),
        )

    row = connection.execute(
        "SELECT * FROM ke_source_endpoints WHERE source_endpoint_id = ?",
        (source_endpoint_id,),
    ).fetchone()
    if row is None:
        raise RuntimeError(
            f"Source endpoint was not persisted for source_endpoint_id: {source_endpoint_id}"
        )
    return _endpoint_row_to_dict(row)


def list_source_endpoints(
    connection: sqlite3.Connection, *, source_id: str
) -> list[dict[str, Any]]:
    source_id = _validate_required_text("source_id", source_id)
    rows = connection.execute(
        "SELECT * FROM ke_source_endpoints WHERE source_id = ? ORDER BY source_endpoint_id",
        (source_id,),
    ).fetchall()
    return [_endpoint_row_to_dict(row) for row in rows]


def _endpoint_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["is_primary"] = bool(item["is_primary"])
    return item


# ------------------------------------------------------------------------------- people


def create_person(
    connection: sqlite3.Connection,
    *,
    person_id: str,
    display_name: str,
    category: str,
    status: str = "active",
    notes: str = "",
) -> dict[str, Any]:
    person_id = _validate_required_text("person_id", person_id)
    display_name = _validate_required_text("display_name", display_name)
    category = validate_person_category(category)
    status = validate_person_status(status)
    notes = _validate_text("notes", notes)
    now = _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO ke_people (
                person_id, display_name, category, status, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (person_id, display_name, category, status, notes, now, now),
        )

    person = get_person(connection, person_id)
    if person is None:
        raise RuntimeError(f"Person was not persisted for person_id: {person_id}")
    return person


def get_person(connection: sqlite3.Connection, person_id: str) -> dict[str, Any] | None:
    person_id = _validate_required_text("person_id", person_id)
    row = connection.execute(
        "SELECT * FROM ke_people WHERE person_id = ?", (person_id,)
    ).fetchone()
    return dict(row) if row is not None else None


def list_people(
    connection: sqlite3.Connection, *, category: str | None = None
) -> list[dict[str, Any]]:
    if category is None:
        rows = connection.execute(
            "SELECT * FROM ke_people ORDER BY display_name, person_id"
        ).fetchall()
    else:
        category = validate_person_category(category)
        rows = connection.execute(
            "SELECT * FROM ke_people WHERE category = ? ORDER BY display_name, person_id",
            (category,),
        ).fetchall()
    return [dict(row) for row in rows]


def count_people(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "ke_people")


def create_person_alias(
    connection: sqlite3.Connection,
    *,
    alias_id: str,
    person_id: str,
    alias: str,
    alias_type: str = "exact",
) -> dict[str, Any]:
    alias_id = _validate_required_text("alias_id", alias_id)
    person_id = _validate_required_text("person_id", person_id)
    alias = _validate_required_text("alias", alias)
    alias_type = validate_person_alias_type(alias_type)
    now = _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO ke_person_aliases (alias_id, person_id, alias, alias_type, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (alias_id, person_id, alias, alias_type, now),
        )

    row = connection.execute(
        "SELECT * FROM ke_person_aliases WHERE alias_id = ?", (alias_id,)
    ).fetchone()
    if row is None:
        raise RuntimeError(f"Person alias was not persisted for alias_id: {alias_id}")
    return dict(row)


def list_person_aliases(
    connection: sqlite3.Connection, *, person_id: str
) -> list[dict[str, Any]]:
    person_id = _validate_required_text("person_id", person_id)
    rows = connection.execute(
        "SELECT * FROM ke_person_aliases WHERE person_id = ? ORDER BY alias_id",
        (person_id,),
    ).fetchall()
    return [dict(row) for row in rows]


# -------------------------------------------------------------------------------- roles


def create_role(
    connection: sqlite3.Connection,
    *,
    role_id: str,
    role_name: str,
    role_category: str,
    roster_cap: int = 1,
    notes: str = "",
) -> dict[str, Any]:
    role_id = _validate_required_text("role_id", role_id)
    role_name = _validate_required_text("role_name", role_name)
    role_category = validate_role_category(role_category)
    if type(roster_cap) is not int or roster_cap <= 0:
        raise ValueError("roster_cap must be a positive integer")
    notes = _validate_text("notes", notes)
    now = _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO ke_roles (
                role_id, role_name, role_category, roster_cap, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (role_id, role_name, role_category, roster_cap, notes, now, now),
        )

    role = get_role(connection, role_id)
    if role is None:
        raise RuntimeError(f"Role was not persisted for role_id: {role_id}")
    return role


def get_role(connection: sqlite3.Connection, role_id: str) -> dict[str, Any] | None:
    role_id = _validate_required_text("role_id", role_id)
    row = connection.execute(
        "SELECT * FROM ke_roles WHERE role_id = ?", (role_id,)
    ).fetchone()
    return dict(row) if row is not None else None


def get_role_by_name(connection: sqlite3.Connection, role_name: str) -> dict[str, Any] | None:
    role_name = _validate_required_text("role_name", role_name)
    row = connection.execute(
        "SELECT * FROM ke_roles WHERE role_name = ?", (role_name,)
    ).fetchone()
    return dict(row) if row is not None else None


def list_roles(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute("SELECT * FROM ke_roles ORDER BY role_name, role_id").fetchall()
    return [dict(row) for row in rows]


def count_roles(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "ke_roles")


def create_role_occupancy(
    connection: sqlite3.Connection,
    *,
    occupancy_id: str,
    role_id: str,
    person_id: str,
    effective_start_date: str | None,
    effective_end_date: str | None = None,
    date_precision: str = "exact",
    occupancy_source: str,
    notes: str = "",
) -> dict[str, Any]:
    occupancy_id = _validate_required_text("occupancy_id", occupancy_id)
    role_id = _validate_required_text("role_id", role_id)
    person_id = _validate_required_text("person_id", person_id)
    effective_start_date = _validate_optional_iso_date(
        "effective_start_date", effective_start_date
    )
    effective_end_date = _validate_optional_iso_date("effective_end_date", effective_end_date)
    if (
        effective_start_date is not None
        and effective_end_date is not None
        and effective_end_date <= effective_start_date
    ):
        raise ValueError("effective_end_date must be after effective_start_date")
    date_precision = validate_role_occupancy_date_precision(date_precision)
    occupancy_source = _validate_required_text("occupancy_source", occupancy_source)
    notes = _validate_text("notes", notes)
    now = _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO ke_role_occupancies (
                occupancy_id, role_id, person_id, effective_start_date, effective_end_date,
                date_precision, occupancy_source, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                occupancy_id, role_id, person_id, effective_start_date, effective_end_date,
                date_precision, occupancy_source, notes, now, now,
            ),
        )

    row = connection.execute(
        "SELECT * FROM ke_role_occupancies WHERE occupancy_id = ?", (occupancy_id,)
    ).fetchone()
    if row is None:
        raise RuntimeError(f"Role occupancy was not persisted for occupancy_id: {occupancy_id}")
    return dict(row)


def list_role_occupancies(
    connection: sqlite3.Connection, *, role_id: str
) -> list[dict[str, Any]]:
    role_id = _validate_required_text("role_id", role_id)
    rows = connection.execute(
        """
        SELECT * FROM ke_role_occupancies
        WHERE role_id = ?
        ORDER BY (effective_start_date IS NULL) DESC, effective_start_date
        """,
        (role_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_role_occupant_as_of(
    connection: sqlite3.Connection, *, role_id: str, as_of_date: str
) -> dict[str, Any] | None:
    """Resolve who holds ``role_id`` on ``as_of_date`` (an ISO date).

    A row with ``effective_start_date IS NULL`` means "occupant since before this
    registry began tracking" and is treated as the earliest possible start for ordering
    purposes, so any later dated occupancy correctly supersedes it. Among the occupancy
    rows valid on ``as_of_date`` (started on or before it, and not yet ended), the one
    with the latest start wins.
    """
    role_id = _validate_required_text("role_id", role_id)
    as_of_date = _validate_optional_iso_date("as_of_date", as_of_date)
    if as_of_date is None:
        raise ValueError("as_of_date must not be empty")

    rows = connection.execute(
        """
        SELECT * FROM ke_role_occupancies
        WHERE role_id = ?
          AND (effective_start_date IS NULL OR effective_start_date <= ?)
          AND (effective_end_date IS NULL OR ? < effective_end_date)
        """,
        (role_id, as_of_date, as_of_date),
    ).fetchall()
    if not rows:
        return None

    def _sort_key(row: sqlite3.Row) -> str:
        return row["effective_start_date"] or ""

    best = max(rows, key=_sort_key)
    occupancy = dict(best)
    person = get_person(connection, occupancy["person_id"])
    occupancy["person"] = person
    return occupancy


# ------------------------------------------------------------------------ affiliations


def create_affiliation(
    connection: sqlite3.Connection,
    *,
    affiliation_id: str,
    person_id: str,
    organization: str,
    title: str | None = None,
    effective_start_date: str | None = None,
    effective_end_date: str | None = None,
) -> dict[str, Any]:
    affiliation_id = _validate_required_text("affiliation_id", affiliation_id)
    person_id = _validate_required_text("person_id", person_id)
    organization = _validate_required_text("organization", organization)
    title = _validate_optional_text("title", title)
    effective_start_date = _validate_optional_iso_date(
        "effective_start_date", effective_start_date
    )
    effective_end_date = _validate_optional_iso_date("effective_end_date", effective_end_date)
    if (
        effective_start_date is not None
        and effective_end_date is not None
        and effective_end_date <= effective_start_date
    ):
        raise ValueError("effective_end_date must be after effective_start_date")
    now = _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO ke_affiliations (
                affiliation_id, person_id, organization, title, effective_start_date,
                effective_end_date, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                affiliation_id, person_id, organization, title, effective_start_date,
                effective_end_date, now, now,
            ),
        )

    row = connection.execute(
        "SELECT * FROM ke_affiliations WHERE affiliation_id = ?", (affiliation_id,)
    ).fetchone()
    if row is None:
        raise RuntimeError(f"Affiliation was not persisted for affiliation_id: {affiliation_id}")
    return dict(row)


def list_affiliations(connection: sqlite3.Connection, *, person_id: str) -> list[dict[str, Any]]:
    person_id = _validate_required_text("person_id", person_id)
    rows = connection.execute(
        """
        SELECT * FROM ke_affiliations
        WHERE person_id = ?
        ORDER BY (effective_start_date IS NULL) DESC, effective_start_date
        """,
        (person_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_affiliation_as_of(
    connection: sqlite3.Connection, *, person_id: str, as_of_date: str
) -> dict[str, Any] | None:
    person_id = _validate_required_text("person_id", person_id)
    as_of_date = _validate_optional_iso_date("as_of_date", as_of_date)
    if as_of_date is None:
        raise ValueError("as_of_date must not be empty")

    rows = connection.execute(
        """
        SELECT * FROM ke_affiliations
        WHERE person_id = ?
          AND (effective_start_date IS NULL OR effective_start_date <= ?)
          AND (effective_end_date IS NULL OR ? < effective_end_date)
        """,
        (person_id, as_of_date, as_of_date),
    ).fetchall()
    if not rows:
        return None

    def _sort_key(row: sqlite3.Row) -> str:
        return row["effective_start_date"] or ""

    return dict(max(rows, key=_sort_key))


# ----------------------------------------------------------------------------- topics


def create_topic(
    connection: sqlite3.Connection,
    *,
    topic_id: str,
    name: str,
    category: str | None = None,
    notes: str = "",
) -> dict[str, Any]:
    topic_id = _validate_required_text("topic_id", topic_id)
    name = _validate_required_text("name", name)
    category = _validate_optional_text("category", category)
    notes = _validate_text("notes", notes)
    now = _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO ke_topics (topic_id, name, category, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (topic_id, name, category, notes, now, now),
        )

    row = connection.execute(
        "SELECT * FROM ke_topics WHERE topic_id = ?", (topic_id,)
    ).fetchone()
    if row is None:
        raise RuntimeError(f"Topic was not persisted for topic_id: {topic_id}")
    return dict(row)


def list_topics(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute("SELECT * FROM ke_topics ORDER BY name, topic_id").fetchall()
    return [dict(row) for row in rows]


# --------------------------------------------------------------------------- companies


def create_company(
    connection: sqlite3.Connection,
    *,
    company_id: str,
    legal_name: str,
    display_name: str,
    roster_group: str,
    roster_status: str,
    roster_group_rank: int | None = None,
    roster_group_rank_basis: str | None = None,
    market_cap_display: str | None = None,
    market_cap_as_of_date: str | None = None,
    market_cap_source: str | None = None,
    fund_weight_percent: float | None = None,
    priority_tier: str | None = None,
    domain_topic_tags: list[str] | None = None,
    ir_root_url: str | None = None,
    events_page_url: str | None = None,
    filings_page_url: str | None = None,
    fiscal_year_end: str | None = None,
    reporting_cadence: str | None = None,
    primary_reporting_timezone: str | None = None,
    status: str = "active",
    manual_pin: bool = False,
    linked_theses: list[str] | None = None,
    source_verification_date: str | None = None,
    added_effective_date: str | None = None,
    removed_effective_date: str | None = None,
    notes: str = "",
) -> dict[str, Any]:
    company_id = _validate_required_text("company_id", company_id)
    legal_name = _validate_required_text("legal_name", legal_name)
    display_name = _validate_required_text("display_name", display_name)
    roster_group = validate_company_roster_group(roster_group)
    roster_status = validate_company_roster_status(roster_status)
    if roster_group_rank is not None and roster_group_rank <= 0:
        raise ValueError("roster_group_rank must be positive")
    if roster_group_rank_basis is not None:
        roster_group_rank_basis = validate_company_roster_rank_basis(roster_group_rank_basis)
    if priority_tier is not None:
        priority_tier = validate_company_priority_tier(priority_tier)
    status = validate_company_status(status)
    manual_pin = _validate_bool("manual_pin", manual_pin)
    added_effective_date = _validate_optional_iso_date(
        "added_effective_date", added_effective_date
    )
    removed_effective_date = _validate_optional_iso_date(
        "removed_effective_date", removed_effective_date
    )
    if (
        added_effective_date is not None
        and removed_effective_date is not None
        and removed_effective_date <= added_effective_date
    ):
        raise ValueError("removed_effective_date must be after added_effective_date")
    notes = _validate_text("notes", notes)
    domain_topic_tags_json = _serialize_json(list(domain_topic_tags or []))
    linked_theses_json = _serialize_json(list(linked_theses or []))
    now = _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO ke_companies (
                company_id, legal_name, display_name, roster_group, roster_group_rank,
                roster_group_rank_basis, roster_status, market_cap_display,
                market_cap_as_of_date, market_cap_source, fund_weight_percent,
                priority_tier, domain_topic_tags_json, ir_root_url, events_page_url,
                filings_page_url, fiscal_year_end, reporting_cadence,
                primary_reporting_timezone, status, manual_pin, linked_theses_json,
                source_verification_date, added_effective_date, removed_effective_date,
                notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company_id, legal_name, display_name, roster_group, roster_group_rank,
                roster_group_rank_basis, roster_status, market_cap_display,
                market_cap_as_of_date, market_cap_source, fund_weight_percent,
                priority_tier, domain_topic_tags_json, ir_root_url, events_page_url,
                filings_page_url, fiscal_year_end, reporting_cadence,
                primary_reporting_timezone, status, int(manual_pin), linked_theses_json,
                source_verification_date, added_effective_date, removed_effective_date,
                notes, now, now,
            ),
        )

    company = get_company(connection, company_id)
    if company is None:
        raise RuntimeError(f"Company was not persisted for company_id: {company_id}")
    return company


def get_company(connection: sqlite3.Connection, company_id: str) -> dict[str, Any] | None:
    company_id = _validate_required_text("company_id", company_id)
    row = connection.execute(
        "SELECT * FROM ke_companies WHERE company_id = ?", (company_id,)
    ).fetchone()
    return _company_row_to_dict(row) if row is not None else None


def list_companies(
    connection: sqlite3.Connection,
    *,
    roster_group: str | None = None,
    roster_status: str | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if roster_group is not None:
        clauses.append("roster_group = ?")
        params.append(validate_company_roster_group(roster_group))
    if roster_status is not None:
        clauses.append("roster_status = ?")
        params.append(validate_company_roster_status(roster_status))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = connection.execute(
        f"""
        SELECT * FROM ke_companies
        {where}
        ORDER BY roster_group, roster_group_rank, company_id
        """,
        params,
    ).fetchall()
    return [_company_row_to_dict(row) for row in rows]


def count_companies(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "ke_companies")


def list_confirmed_companies(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    """Companies whose roster membership has been Conductor-confirmed -- excludes every
    row still sitting in a candidate pool (amendment §9.4: "no company is promoted... automatically")."""
    return list_companies(connection, roster_status="confirmed")


def _company_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["manual_pin"] = bool(item["manual_pin"])
    item["domain_topic_tags"] = _deserialize_json_array(item.pop("domain_topic_tags_json"))
    item["linked_theses"] = _deserialize_json_array(item.pop("linked_theses_json"))
    return item


def create_company_identifier(
    connection: sqlite3.Connection,
    *,
    identifier_id: str,
    company_id: str,
    identifier_type: str,
    identifier_value: str,
    exchange: str | None = None,
    verified_as_of_date: str | None = None,
    effective_end_date: str | None = None,
    provenance: str = "",
) -> dict[str, Any]:
    identifier_id = _validate_required_text("identifier_id", identifier_id)
    company_id = _validate_required_text("company_id", company_id)
    identifier_type = validate_company_identifier_type(identifier_type)
    identifier_value = _validate_required_text("identifier_value", identifier_value)
    exchange = _validate_optional_text("exchange", exchange)
    verified_as_of_date = _validate_optional_iso_date(
        "verified_as_of_date", verified_as_of_date
    )
    effective_end_date = _validate_optional_iso_date("effective_end_date", effective_end_date)
    provenance = _validate_text("provenance", provenance)
    now = _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO ke_company_identifiers (
                identifier_id, company_id, identifier_type, identifier_value, exchange,
                verified_as_of_date, effective_end_date, provenance, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                identifier_id, company_id, identifier_type, identifier_value, exchange,
                verified_as_of_date, effective_end_date, provenance, now, now,
            ),
        )

    row = connection.execute(
        "SELECT * FROM ke_company_identifiers WHERE identifier_id = ?", (identifier_id,)
    ).fetchone()
    if row is None:
        raise RuntimeError(
            f"Company identifier was not persisted for identifier_id: {identifier_id}"
        )
    return dict(row)


def list_company_identifiers(
    connection: sqlite3.Connection, *, company_id: str
) -> list[dict[str, Any]]:
    company_id = _validate_required_text("company_id", company_id)
    rows = connection.execute(
        "SELECT * FROM ke_company_identifiers WHERE company_id = ? ORDER BY identifier_id",
        (company_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_company_by_ticker(connection: sqlite3.Connection, ticker: str) -> dict[str, Any] | None:
    ticker = _validate_required_text("ticker", ticker)
    row = connection.execute(
        """
        SELECT c.* FROM ke_companies c
        JOIN ke_company_identifiers i ON i.company_id = c.company_id
        WHERE i.identifier_type = 'ticker' AND i.identifier_value = ?
        """,
        (ticker,),
    ).fetchone()
    return _company_row_to_dict(row) if row is not None else None
