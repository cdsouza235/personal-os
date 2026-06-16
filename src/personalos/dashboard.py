"""Minimal read-only local dashboard shell for Personal OS Today View."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections.abc import Mapping, Sequence
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlparse

from personalos.config import DEFAULT_TIMEZONE
from personalos.path_safety import (
    DATABASE_SUFFIXES,
    is_under_repo,
    is_under_temp,
    reject_production_path,
    reject_protected_path,
    reject_sensitive_path,
    resolve_explicit_path,
)
from personalos.synthesis_import import (
    ALLOWED_SOURCE_TYPES,
    REPORT_SAFETY_FLAGS,
    SynthesisImportValidationError,
    create_synthesis_import_preview_record,
)
from personalos.today import create_today_view_summary

DEFAULT_DASHBOARD_HOST = "localhost"
DEFAULT_DASHBOARD_PORT = 8765
LOCALHOST_BIND_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
DASHBOARD_SYNTHESIS_IMPORT_FORM_MAX_BYTES = 128 * 1024
DASHBOARD_SYNTHESIS_IMPORT_INPUT_MAX_CHARS = 128 * 1024


def render_today_view_html_from_connection(
    connection: sqlite3.Connection,
    *,
    source_date: str | None = None,
    timezone: str = DEFAULT_TIMEZONE,
    include_synthesis_import_form: bool = True,
) -> str:
    summary = create_today_view_summary(
        connection,
        source_date=source_date,
        timezone=timezone,
    )
    return render_today_view_html(
        summary,
        include_synthesis_import_form=include_synthesis_import_form,
    )


def render_today_view_html_from_db_path(
    db_path: str | Path,
    *,
    source_date: str | None = None,
    timezone: str = DEFAULT_TIMEZONE,
) -> str:
    with connect_dashboard_db_read_only(db_path) as connection:
        return render_today_view_html_from_connection(
            connection,
            source_date=source_date,
            timezone=timezone,
        )


def render_today_view_json_from_db_path(
    db_path: str | Path,
    *,
    source_date: str | None = None,
    timezone: str = DEFAULT_TIMEZONE,
) -> str:
    with connect_dashboard_db_read_only(db_path) as connection:
        summary = create_today_view_summary(
            connection,
            source_date=source_date,
            timezone=timezone,
        )
    return json.dumps(summary, allow_nan=False, ensure_ascii=True, indent=2, sort_keys=True)


def render_today_view_html(
    summary: Mapping[str, Any],
    *,
    include_synthesis_import_form: bool = True,
) -> str:
    no_external_writes = _format_bool(summary["no_external_writes"])
    synthesis_form_html = (
        render_synthesis_import_preview_form_html()
        if include_synthesis_import_form
        else ""
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Personal OS Today View</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }}
    body {{
      margin: 0;
      background: #f7f7f4;
      color: #202124;
    }}
    main {{
      max-width: 960px;
      margin: 0 auto;
      padding: 24px 16px 48px;
    }}
    section {{
      border-top: 1px solid #d9d9d2;
      padding: 18px 0;
    }}
    h1 {{
      font-size: 2rem;
      margin: 0 0 8px;
    }}
    h2 {{
      font-size: 1.1rem;
      margin: 0 0 12px;
    }}
    .banner {{
      background: #fff8d6;
      border: 1px solid #e1cc67;
      border-radius: 6px;
      padding: 12px;
      margin: 18px 0;
    }}
    dl {{
      display: grid;
      grid-template-columns: minmax(150px, 220px) 1fr;
      gap: 8px 12px;
      margin: 0;
    }}
    dt {{
      font-weight: 700;
    }}
    dd {{
      margin: 0;
    }}
    ul {{
      margin: 0;
      padding-left: 22px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.95rem;
    }}
    th, td {{
      border-bottom: 1px solid #e5e5df;
      padding: 8px 4px;
      text-align: left;
      vertical-align: top;
    }}
    pre {{
      background: #f0f0ea;
      border: 1px solid #d9d9d2;
      border-radius: 6px;
      overflow-x: auto;
      padding: 12px;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    label {{
      display: block;
      font-weight: 700;
      margin: 12px 0 4px;
    }}
    textarea, input, select {{
      box-sizing: border-box;
      width: 100%;
      border: 1px solid #bdbdb5;
      border-radius: 6px;
      font: inherit;
      padding: 8px;
    }}
    textarea {{
      min-height: 260px;
      resize: vertical;
    }}
    button {{
      border: 1px solid #202124;
      border-radius: 6px;
      background: #202124;
      color: #ffffff;
      cursor: pointer;
      font: inherit;
      margin-top: 14px;
      padding: 8px 12px;
    }}
    .warning {{
      color: #7a2417;
      font-weight: 700;
    }}
    @media (max-width: 640px) {{
      main {{
        padding: 18px 12px 36px;
      }}
      dl {{
        grid-template-columns: 1fr;
      }}
      dt {{
        margin-top: 8px;
      }}
    }}
  </style>
</head>
<body>
<main>
  <h1>Personal OS Today View</h1>
  <p>{_e(summary["source_date"])} - {_e(summary["timezone"])}</p>

  <div class="banner" id="safety-banner">
    <strong>Read-only preview</strong>
    <ul>
      <li>no_external_writes={no_external_writes}</li>
      <li>no live Todoist/Calendar/Gmail/model calls</li>
      <li>localhost-only by default</li>
      <li>no task, calendar, routine, priority, or briefing mutation routes</li>
      <li><a href="/today.json">today.json</a></li>
    </ul>
  </div>

  {_render_synthesis_import_preview_summary(summary["synthesis_import_preview_summary"])}
  {synthesis_form_html}
  {_render_routine_summary(summary["routine_summary"])}
  {_render_priority_summary(summary["priority_summary"])}
  {_render_followup_summary(summary["followup_summary"])}
  {_render_todoist_candidate_summary(summary["todoist_candidate_summary"])}
  {_render_calendar_block_summary(summary["calendar_block_summary"])}
  {_render_briefing_window_summary(summary["briefing_window_summary"])}
  {_render_briefing_loop_summary(summary["briefing_loop_summary"])}
  {_render_briefing_output_summary(summary["briefing_output_summary"])}
  {_render_permission_summary(summary["permission_summary"])}
  {_render_system_status_summary(summary["system_status_summary"])}
  {_render_warnings(summary["warnings"])}
</main>
</body>
</html>
"""


def render_synthesis_import_page_html_from_db_path(
    db_path: str | Path,
    *,
    source_date: str | None = None,
    timezone: str = DEFAULT_TIMEZONE,
) -> str:
    with connect_dashboard_db_read_only(db_path) as connection:
        summary = create_today_view_summary(
            connection,
            source_date=source_date,
            timezone=timezone,
        )
    return render_synthesis_import_page_html(summary["synthesis_import_preview_summary"])


def render_synthesis_import_page_html(
    synthesis_import_summary: Mapping[str, Any],
    *,
    result_html: str = "",
) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ChatGPT Synthesis Import Preview</title>
</head>
<body>
<main>
  {render_synthesis_import_preview_form_html()}
  {_render_synthesis_import_preview_summary(synthesis_import_summary)}
  {result_html}
</main>
</body>
</html>
"""


def render_synthesis_import_preview_form_html() -> str:
    source_options = "".join(
        f'<option value="{_e(source_type)}">{_e(source_type)}</option>'
        for source_type in ("chatgpt_synthesis", "manual_structured_import")
    )
    return _section(
        "synthesis-import-preview",
        "ChatGPT Synthesis Import Preview",
        """
<div class="banner" id="synthesis-import-safety-banner">
  <strong>Preview-only</strong>
  <ul>
    <li>No core state mutation</li>
    <li>No PersonalOS Markdown writes</li>
    <li>No Todoist/Calendar/Gmail writes</li>
    <li>No live model/API calls</li>
  </ul>
</div>
<form method="post" action="/synthesis-import/preview">
  <label for="structured_synthesis">Structured synthesis input</label>
  <textarea id="structured_synthesis" name="structured_synthesis" required></textarea>

  <label for="source_type">Source type</label>
  <select id="source_type" name="source_type">
    """
        + source_options
        + """
  </select>

  <label for="source_reference">Source reference</label>
  <input id="source_reference" name="source_reference" type="text">

  <label for="source_timestamp">Source timestamp</label>
  <input id="source_timestamp" name="source_timestamp" type="text">

  <button type="submit">Preview import</button>
</form>
""",
    )


def create_dashboard_synthesis_import_preview(
    connection: sqlite3.Connection,
    form_fields: Mapping[str, object],
) -> dict[str, Any]:
    try:
        raw_input = _field_text(form_fields, "structured_synthesis")
        if len(raw_input) > DASHBOARD_SYNTHESIS_IMPORT_INPUT_MAX_CHARS:
            raise SynthesisImportValidationError("synthesis import input is too large.")
        source_type = _validate_dashboard_source_type(
            _field_text(form_fields, "source_type", default="chatgpt_synthesis")
        )
        source_reference = _field_text(form_fields, "source_reference", default="")
        source_timestamp = _field_text(form_fields, "source_timestamp", default="")
        prepared_input = _merge_json_form_metadata(
            raw_input,
            source_type=source_type,
            source_reference=source_reference,
            source_timestamp=source_timestamp,
        )
        return create_synthesis_import_preview_record(connection, prepared_input)
    except SynthesisImportValidationError as error:
        return _synthesis_import_error_result(
            status="rejected",
            reason=str(error),
            source_type=_field_text(
                form_fields,
                "source_type",
                default="chatgpt_synthesis",
                strict=False,
            ),
        )


def create_dashboard_synthesis_import_preview_from_db_path(
    db_path: str | Path,
    form_fields: Mapping[str, object],
) -> dict[str, Any]:
    with connect_dashboard_db_read_write(db_path) as connection:
        return create_dashboard_synthesis_import_preview(connection, form_fields)


def render_synthesis_import_preview_result_html(result: Mapping[str, Any]) -> str:
    report = result.get("preview_report")
    report = report if isinstance(report, Mapping) else {}
    record = result.get("record")
    record = record if isinstance(record, Mapping) else None
    preview_id = report.get("preview_id") or (record or {}).get("id") or "none"
    source_type = report.get("source_type") or (record or {}).get("source_type") or "none"
    input_format = report.get("input_format") or (record or {}).get("input_format") or "none"
    raw_excerpt = (record or {}).get("raw_excerpt", "")

    body = (
        _definition_list(
            (
                ("Status", result.get("status", "unknown")),
                ("Reason", result.get("reason", "")),
                ("preview_id", preview_id),
                ("source_type", source_type),
                ("input_format", input_format),
                ("database_write", _format_bool(result.get("database_write"))),
                ("external_mutation", _format_bool(result.get("external_mutation"))),
                ("candidate_counts", _format_json(report.get("candidate_counts", {}))),
            )
        )
        + "<h3>accepted candidates</h3>"
        + _render_json_block(report.get("accepted_candidates", []))
        + "<h3>rejected candidates</h3>"
        + _render_json_block(report.get("rejected_candidates", []))
        + "<h3>blocked candidates</h3>"
        + _render_json_block(report.get("blocked_candidates", []))
        + "<h3>review-required candidates</h3>"
        + _render_json_block(report.get("review_required_candidates", []))
        + "<h3>manual-only candidates</h3>"
        + _render_json_block(report.get("manual_only_candidates", []))
        + "<h3>warnings</h3>"
        + _render_json_block(report.get("warnings", []))
        + "<h3>questions_for_review</h3>"
        + _render_json_block(report.get("questions_for_review", []))
        + "<h3>safety flags</h3>"
        + _definition_list(
            tuple(
                (flag, _format_bool(result.get(flag, report.get(flag))))
                for flag in sorted(REPORT_SAFETY_FLAGS)
            )
        )
    )
    if raw_excerpt:
        body += "<h3>raw_excerpt</h3>" + f"<pre>{_e(raw_excerpt)}</pre>"
    return _section("synthesis-import-preview-result", "Preview Result", body)


def render_synthesis_import_preview_result_page_html(
    result: Mapping[str, Any],
) -> str:
    return render_synthesis_import_page_html(
        _empty_synthesis_import_summary(),
        result_html=render_synthesis_import_preview_result_html(result),
    )


def connect_dashboard_db_read_only(db_path: str | Path) -> sqlite3.Connection:
    validated_path = validate_dashboard_db_path(db_path)
    db_uri = f"file:{quote(str(validated_path), safe='/')}?mode=ro"
    connection = sqlite3.connect(db_uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def connect_dashboard_db_read_write(db_path: str | Path) -> sqlite3.Connection:
    validated_path = validate_dashboard_db_path(db_path)
    connection = sqlite3.connect(validated_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def make_dashboard_request_handler(
    db_path: str | Path,
    *,
    source_date: str | None = None,
    timezone: str = DEFAULT_TIMEZONE,
) -> type[BaseHTTPRequestHandler]:
    validated_path = validate_dashboard_db_path(db_path)

    class TodayViewRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path in {"/", "/today"}:
                body = render_today_view_html_from_db_path(
                    validated_path,
                    source_date=source_date,
                    timezone=timezone,
                ).encode("utf-8")
                self._send_response(HTTPStatus.OK, "text/html; charset=utf-8", body)
                return
            if parsed.path == "/today.json":
                body = render_today_view_json_from_db_path(
                    validated_path,
                    source_date=source_date,
                    timezone=timezone,
                ).encode("utf-8")
                self._send_response(HTTPStatus.OK, "application/json; charset=utf-8", body)
                return
            if parsed.path == "/synthesis-import":
                body = render_synthesis_import_page_html_from_db_path(
                    validated_path,
                    source_date=source_date,
                    timezone=timezone,
                ).encode("utf-8")
                self._send_response(HTTPStatus.OK, "text/html; charset=utf-8", body)
                return
            self._send_response(
                HTTPStatus.NOT_FOUND,
                "text/plain; charset=utf-8",
                b"Not found",
            )

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path != "/synthesis-import/preview":
                self._send_response(
                    HTTPStatus.NOT_FOUND,
                    "text/plain; charset=utf-8",
                    b"Not found",
                )
                return
            result = self._handle_synthesis_import_preview_post()
            body = render_synthesis_import_preview_result_page_html(result).encode("utf-8")
            self._send_response(
                _synthesis_import_http_status(result),
                "text/html; charset=utf-8",
                body,
            )

        def log_message(self, format: str, *args: object) -> None:
            return

        def _handle_synthesis_import_preview_post(self) -> dict[str, Any]:
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip()
            if content_type != "application/x-www-form-urlencoded":
                return _synthesis_import_error_result(
                    status="rejected",
                    reason="Synthesis import preview accepts form-encoded input only.",
                )
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return _synthesis_import_error_result(
                    status="rejected",
                    reason="Invalid Content-Length for synthesis import preview.",
                )
            if content_length > DASHBOARD_SYNTHESIS_IMPORT_FORM_MAX_BYTES:
                return _synthesis_import_error_result(
                    status="rejected",
                    reason="Synthesis import form body is too large.",
                )
            try:
                body = self.rfile.read(content_length).decode("utf-8")
            except UnicodeDecodeError:
                return _synthesis_import_error_result(
                    status="rejected",
                    reason="Synthesis import form body must be UTF-8.",
                )
            fields = parse_qs(body, keep_blank_values=True)
            return create_dashboard_synthesis_import_preview_from_db_path(
                validated_path,
                fields,
            )

        def _send_response(
            self,
            status: HTTPStatus,
            content_type: str,
            body: bytes,
        ) -> None:
            self.send_response(status.value)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    return TodayViewRequestHandler


def serve_today_dashboard(
    db_path: str | Path,
    *,
    host: str = DEFAULT_DASHBOARD_HOST,
    port: int = DEFAULT_DASHBOARD_PORT,
    source_date: str | None = None,
    timezone: str = DEFAULT_TIMEZONE,
) -> None:
    validated_host = validate_dashboard_bind_host(host)
    validated_port = validate_dashboard_port(port)
    handler = make_dashboard_request_handler(
        db_path,
        source_date=source_date,
        timezone=timezone,
    )
    server = ThreadingHTTPServer((validated_host, validated_port), handler)
    server.serve_forever()


def validate_dashboard_bind_host(host: str) -> str:
    if not isinstance(host, str) or not host.strip():
        raise ValueError("dashboard host must be a non-empty string")
    normalized = host.strip()
    if normalized not in LOCALHOST_BIND_HOSTS:
        raise ValueError("Phase 10A dashboard only supports localhost bind hosts")
    return normalized


def validate_dashboard_port(port: int) -> int:
    if not isinstance(port, int):
        raise ValueError("dashboard port must be an integer")
    if port < 1 or port > 65535:
        raise ValueError("dashboard port must be between 1 and 65535")
    return port


def validate_dashboard_db_path(db_path: str | Path, *, must_exist: bool = True) -> Path:
    resolved = resolve_explicit_path(db_path, path_label="dashboard db_path")
    reject_protected_path(resolved, path_label="dashboard db_path")
    reject_sensitive_path(resolved, path_label="dashboard db_path")
    reject_production_path(resolved, path_label="dashboard db_path")
    if resolved.suffix not in DATABASE_SUFFIXES:
        allowed = ", ".join(sorted(DATABASE_SUFFIXES))
        raise ValueError(f"dashboard db_path suffix must be one of: {allowed}")
    if not (is_under_repo(resolved) or is_under_temp(resolved)):
        raise ValueError("dashboard db_path must stay in explicit temp or repo-local dev paths")
    if must_exist and not resolved.is_file():
        raise ValueError("dashboard db_path must point to an existing SQLite file")
    return resolved


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the local read-only Today View dashboard.")
    parser.add_argument("db_path", help="Absolute temp/dev SQLite database path.")
    parser.add_argument("--host", default=DEFAULT_DASHBOARD_HOST)
    parser.add_argument("--port", default=DEFAULT_DASHBOARD_PORT, type=int)
    parser.add_argument("--source-date", default=None)
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    args = parser.parse_args(argv)
    serve_today_dashboard(
        args.db_path,
        host=args.host,
        port=args.port,
        source_date=args.source_date,
        timezone=args.timezone,
    )
    return 0


def _render_routine_summary(summary: Mapping[str, Any]) -> str:
    return _section(
        "routine-summary",
        "Routines",
        _definition_list(
            (
                ("Total", summary["total_count"]),
                ("Enabled", summary["enabled_count"]),
                ("Disabled", summary["disabled_count"]),
                ("Completed today", summary["completed_for_source_date_count"]),
                ("Status counts", _format_counts(summary["counts_by_status"])),
            )
        ),
    )


def _render_priority_summary(summary: Mapping[str, Any]) -> str:
    active_titles = [
        priority["title"]
        for priority in summary.get("active_priorities", [])
    ]
    active_html = _render_list(active_titles) if active_titles else "<p>No active priorities.</p>"
    return _section(
        "priority-summary",
        "Priorities",
        _definition_list(
            (
                ("Total", summary["total_count"]),
                ("Active", summary["active_count"]),
                ("Status counts", _format_counts(summary["counts_by_status"])),
            )
        )
        + active_html,
    )


def _render_followup_summary(summary: Mapping[str, Any]) -> str:
    followup_titles = [
        f"{followup['title']} ({followup['status']})"
        for followup in summary.get("followups", [])
    ]
    followups_html = _render_list(followup_titles) if followup_titles else "<p>No follow-ups.</p>"
    return _section(
        "followup-summary",
        "Follow-ups",
        _definition_list(
            (
                ("Total", summary["total_count"]),
                ("Open", summary["open_count"]),
                ("Status counts", _format_counts(summary["counts_by_status"])),
            )
        )
        + followups_html,
    )


def _render_todoist_candidate_summary(summary: Mapping[str, Any]) -> str:
    return _section(
        "todoist-candidate-summary",
        "Todoist Candidates",
        _definition_list(
            (
                ("Total", summary["total_count"]),
                ("Status counts", _format_counts(summary["counts_by_status"])),
                ("Risk counts", _format_counts(summary["counts_by_risk_level"])),
                ("Approval counts", _format_counts(summary["counts_by_approval_mode"])),
            )
        ),
    )


def _render_calendar_block_summary(summary: Mapping[str, Any]) -> str:
    return _section(
        "calendar-block-summary",
        "Calendar Blocks",
        _definition_list(
            (
                ("Total", summary["total_count"]),
                ("For source date", summary["source_date_count"]),
                ("Status counts", _format_counts(summary["counts_by_status"])),
                ("Risk counts", _format_counts(summary["counts_by_risk_level"])),
                ("Approval counts", _format_counts(summary["counts_by_approval_mode"])),
            )
        ),
    )


def _render_briefing_window_summary(summary: Mapping[str, Any]) -> str:
    windows = summary.get("windows", [])
    rows = [
        (
            window["name"],
            window["scheduled_time"],
            window["timezone"],
            window["delivery_mode"],
            window["status"],
        )
        for window in windows
    ]
    return _section(
        "briefing-window-summary",
        "Briefing Windows",
        _definition_list(
            (
                ("Total", summary["total_count"]),
                ("Status counts", _format_counts(summary["counts_by_status"])),
                ("Delivery modes", _format_counts(summary["counts_by_delivery_mode"])),
            )
        )
        + _table(("Name", "Time", "Timezone", "Delivery", "Status"), rows),
    )


def _render_briefing_loop_summary(summary: Mapping[str, Any]) -> str:
    return _section(
        "briefing-loop-summary",
        "Briefing Loop",
        _definition_list(
            (
                ("Latest outputs", summary["latest_briefing_output_count"]),
                ("Outputs for source date", summary["source_date_briefing_output_count"]),
                ("Window statuses", _format_counts(summary["briefing_windows_status"])),
                ("No-send mode", _format_bool(summary["no_send_mode"])),
            )
        ),
    )


def _render_briefing_output_summary(summary: Mapping[str, Any]) -> str:
    latest_outputs = summary.get("latest_briefing_outputs", [])
    latest_output = latest_outputs[0] if latest_outputs else None
    latest_status = "none" if latest_output is None else latest_output["status"]
    latest_window = "none" if latest_output is None else latest_output["briefing_window_name"]
    latest_created = "none" if latest_output is None else latest_output["created_at"]
    latest_delivery = "none" if latest_output is None else latest_output["delivery_mode"]
    manual_preview = summary.get("latest_manual_export_preview") or "No manual export preview."
    failed_warning = ""
    if summary["failed_briefing_count"] > 0:
        failed_warning = (
            '<p class="warning">Failed briefing output warning: '
            f'{_e(summary["failed_briefing_count"])} failed briefing output(s).</p>'
        )
    warning_html = (
        _render_list(summary.get("warnings", []))
        if summary.get("warnings")
        else "<p>No briefing output warnings.</p>"
    )

    rows = [
        (
            output["briefing_window_name"],
            output["status"],
            output["delivery_mode"],
            output["created_at"],
        )
        for output in latest_outputs
    ]
    body = (
        _definition_list(
            (
                ("Total outputs", summary["total_briefing_output_count"]),
                ("Outputs for source date", summary["source_date_briefing_output_count"]),
                ("Daily plans for source date", summary["source_date_daily_plan_count"]),
                ("Latest window", latest_window),
                ("Latest status", latest_status),
                ("Latest delivery", latest_delivery),
                ("Latest created", latest_created),
                ("Failed briefings", summary["failed_briefing_count"]),
                ("Warnings", summary["warning_count"]),
                ("Status counts", _format_counts(summary["counts_by_status"])),
                ("Delivery modes", _format_counts(summary["counts_by_delivery_mode"])),
                ("Completion safety flags", _format_safety_flags(summary["safety_flags"])),
            )
        )
        + failed_warning
        + "<h3>Latest Outputs</h3>"
        + _table(("Window", "Status", "Delivery", "Created"), rows)
        + "<h3>Latest Manual Export Preview</h3>"
        + f"<pre>{_e(manual_preview)}</pre>"
        + "<h3>Completion Report Safety Flags</h3>"
        + _definition_list(
            tuple(
                (key, _format_bool(value))
                for key, value in sorted(summary["safety_flags"].items())
            )
        )
        + "<h3>Briefing Output Warnings</h3>"
        + warning_html
    )
    return _section("briefing-output-summary", "Briefing Outputs", body)


def _render_synthesis_import_preview_summary(summary: Mapping[str, Any]) -> str:
    if not summary.get("available", False):
        return _section(
            "synthesis-import-preview-summary",
            "Synthesis Import Previews",
            _definition_list(
                (
                    ("Available", "false"),
                    ("Permission required", summary.get("permission_required", "")),
                    ("Reason", summary.get("reason", "")),
                    ("no_external_writes", _format_bool(summary.get("no_external_writes"))),
                )
            ),
        )
    return _section(
        "synthesis-import-preview-summary",
        "Synthesis Import Previews",
        _definition_list(
            (
                ("synthesis_import_preview_count", summary["synthesis_import_preview_count"]),
                ("Latest preview timestamp", summary["latest_preview_timestamp"] or "none"),
                ("Latest preview status", summary["latest_preview_status"] or "none"),
                ("Latest source type", summary["latest_source_type"] or "none"),
                ("Latest blocked count", summary["latest_blocked_count"]),
                ("Latest rejected count", summary["latest_rejected_count"]),
                ("Latest warnings count", summary["latest_warnings_count"]),
                ("no_external_writes", _format_bool(summary["no_external_writes"])),
            )
        ),
    )


def _render_permission_summary(summary: Mapping[str, Any]) -> str:
    return _section(
        "permission-summary",
        "Permissions",
        _definition_list(
            (
                ("Total", summary["total_count"]),
                ("Mode counts", _format_counts(summary["counts_by_mode"])),
                ("Live-like keys", summary["live_like_permission_count"]),
                (
                    "No live external permission keys",
                    _format_bool(summary["no_live_external_permission_keys"]),
                ),
            )
        ),
    )


def _render_system_status_summary(summary: Mapping[str, Any]) -> str:
    counts = summary["counts"]
    return _section(
        "system-status-summary",
        "System Status",
        _definition_list(
            (
                ("Generated at UTC", summary["generated_at_utc"]),
                ("Routines", counts["routines"]),
                ("Priorities", counts["priorities"]),
                ("Follow-ups", counts["followups"]),
                ("Permission settings", summary["permission_settings_count"]),
                ("Runtime bootstrap runs", summary["runtime_bootstrap_run_count"]),
                ("no_external_writes", _format_bool(summary["no_external_writes"])),
            )
        ),
    )


def _render_warnings(warnings: Sequence[str]) -> str:
    return _section("warnings", "Warnings", _render_list(warnings))


def _section(section_id: str, title: str, body: str) -> str:
    return f'<section id="{_e(section_id)}"><h2>{_e(title)}</h2>{body}</section>'


def _definition_list(items: Sequence[tuple[str, object]]) -> str:
    parts = ["<dl>"]
    for key, value in items:
        parts.append(f"<dt>{_e(key)}</dt><dd>{_e(value)}</dd>")
    parts.append("</dl>")
    return "".join(parts)


def _render_list(items: Sequence[object]) -> str:
    if not items:
        return "<ul></ul>"
    return "<ul>" + "".join(f"<li>{_e(item)}</li>" for item in items) + "</ul>"


def _table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    if not rows:
        return "<p>No rows.</p>"
    header_html = "".join(f"<th>{_e(header)}</th>" for header in headers)
    row_html = "".join(
        "<tr>" + "".join(f"<td>{_e(cell)}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{header_html}</tr></thead><tbody>{row_html}</tbody></table>"


def _format_counts(counts: Mapping[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{key}: {value}" for key, value in sorted(counts.items()))


def _format_bool(value: object) -> str:
    return "true" if value is True else "false"


def _format_safety_flags(flags: Mapping[str, object]) -> str:
    return ", ".join(
        f"{key}={_format_bool(value)}"
        for key, value in sorted(flags.items())
    )


def _format_json(value: object) -> str:
    return json.dumps(value, allow_nan=False, ensure_ascii=True, sort_keys=True)


def _render_json_block(value: object) -> str:
    rendered = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        indent=2,
        sort_keys=True,
    )
    return f"<pre>{_e(rendered)}</pre>"


def _field_text(
    form_fields: Mapping[str, object],
    field_name: str,
    *,
    default: str = "",
    strict: bool = True,
) -> str:
    value = form_fields.get(field_name, default)
    if isinstance(value, str):
        return value
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        if not value:
            return default
        first = value[0]
        if isinstance(first, str):
            return first
    if strict:
        raise SynthesisImportValidationError(f"{field_name} must be a form text field.")
    return default


def _validate_dashboard_source_type(source_type: str) -> str:
    if source_type not in ALLOWED_SOURCE_TYPES:
        allowed = ", ".join(ALLOWED_SOURCE_TYPES)
        raise SynthesisImportValidationError(f"source_type must be one of: {allowed}")
    return source_type


def _merge_json_form_metadata(
    raw_input: str,
    *,
    source_type: str,
    source_reference: str,
    source_timestamp: str,
) -> str:
    text = raw_input.strip()
    if not text.startswith("{"):
        return raw_input
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return raw_input
    if not isinstance(parsed, dict):
        return raw_input
    if not parsed.get("source_type"):
        parsed["source_type"] = source_type
    if source_reference.strip():
        parsed["source_reference"] = source_reference.strip()
    if source_timestamp.strip():
        parsed["source_timestamp"] = source_timestamp.strip()
    try:
        return json.dumps(parsed, allow_nan=False, ensure_ascii=True, sort_keys=True)
    except ValueError as error:
        raise SynthesisImportValidationError(
            "Synthesis import JSON contains non-finite values."
        ) from error


def _synthesis_import_error_result(
    *,
    status: str,
    reason: str,
    source_type: str = "chatgpt_synthesis",
) -> dict[str, Any]:
    return {
        "status": status,
        "reason": reason,
        "dry_run": False,
        "database_write": False,
        "external_mutation": False,
        "permission": None,
        "preview_report": {
            "preview_id": None,
            "source_type": source_type,
            "input_format": None,
            "candidate_counts": {},
            "accepted_candidates": [],
            "rejected_candidates": [],
            "blocked_candidates": [],
            "review_required_candidates": [],
            "manual_only_candidates": [],
            "warnings": [reason],
            "questions_for_review": [],
            **REPORT_SAFETY_FLAGS,
        },
        "record": None,
        "would_write": None,
        **REPORT_SAFETY_FLAGS,
    }


def _synthesis_import_http_status(result: Mapping[str, Any]) -> HTTPStatus:
    status = result.get("status")
    if status == "created":
        return HTTPStatus.OK
    if status == "blocked":
        return HTTPStatus.FORBIDDEN
    if status == "rejected":
        return HTTPStatus.BAD_REQUEST
    return HTTPStatus.OK


def _empty_synthesis_import_summary() -> dict[str, Any]:
    return {
        "available": True,
        "synthesis_import_preview_count": 0,
        "latest_preview_timestamp": None,
        "latest_preview_status": None,
        "latest_source_type": None,
        "latest_blocked_count": 0,
        "latest_rejected_count": 0,
        "latest_warnings_count": 0,
        "no_external_writes": True,
    }


def _e(value: object) -> str:
    return escape(str(value), quote=True)


if __name__ == "__main__":
    raise SystemExit(main())
