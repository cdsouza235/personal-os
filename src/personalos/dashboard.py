"""Minimal read-only local dashboard shell for Personal OS Today View."""

from __future__ import annotations

import argparse
import json
import sqlite3
import tempfile
from collections.abc import Mapping, Sequence
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

from personalos.config import DEFAULT_TIMEZONE, REPO_ROOT
from personalos.today import create_today_view_summary

DEFAULT_DASHBOARD_HOST = "localhost"
DEFAULT_DASHBOARD_PORT = 8765
LOCALHOST_BIND_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

_DATABASE_SUFFIXES = {".sqlite", ".sqlite3", ".db"}
_PRODUCTION_MARKERS = {"prod", "production", "live"}
_SENSITIVE_PATH_MARKERS = (
    "credential",
    "credentials",
    "client" + "_" + "sec" + "ret",
    "token" + ".json",
    "api" + "_" + "key",
    "o" + "auth",
    "pass" + "word",
    "sec" + "ret",
)


def render_today_view_html_from_connection(
    connection: sqlite3.Connection,
    *,
    source_date: str | None = None,
    timezone: str = DEFAULT_TIMEZONE,
) -> str:
    summary = create_today_view_summary(
        connection,
        source_date=source_date,
        timezone=timezone,
    )
    return render_today_view_html(summary)


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


def render_today_view_html(summary: Mapping[str, Any]) -> str:
    no_external_writes = _format_bool(summary["no_external_writes"])
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
    </ul>
  </div>

  {_render_routine_summary(summary["routine_summary"])}
  {_render_priority_summary(summary["priority_summary"])}
  {_render_followup_summary(summary["followup_summary"])}
  {_render_todoist_candidate_summary(summary["todoist_candidate_summary"])}
  {_render_calendar_block_summary(summary["calendar_block_summary"])}
  {_render_briefing_window_summary(summary["briefing_window_summary"])}
  {_render_permission_summary(summary["permission_summary"])}
  {_render_system_status_summary(summary["system_status_summary"])}
  {_render_warnings(summary["warnings"])}
</main>
</body>
</html>
"""


def connect_dashboard_db_read_only(db_path: str | Path) -> sqlite3.Connection:
    validated_path = validate_dashboard_db_path(db_path)
    db_uri = f"file:{quote(str(validated_path), safe='/')}?mode=ro"
    connection = sqlite3.connect(db_uri, uri=True)
    connection.row_factory = sqlite3.Row
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
            self._send_response(
                HTTPStatus.NOT_FOUND,
                "text/plain; charset=utf-8",
                b"Not found",
            )

        def log_message(self, format: str, *args: object) -> None:
            return

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
    path = Path(db_path).expanduser()
    if not path.is_absolute():
        raise ValueError("dashboard db_path must be an explicit absolute path")
    resolved = path.resolve()
    _reject_protected_path(resolved)
    _reject_sensitive_path(resolved)
    _reject_production_path(resolved)
    if resolved.suffix not in _DATABASE_SUFFIXES:
        allowed = ", ".join(sorted(_DATABASE_SUFFIXES))
        raise ValueError(f"dashboard db_path suffix must be one of: {allowed}")
    if not (_is_under_repo(resolved) or _is_under_temp(resolved)):
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


def _e(value: object) -> str:
    return escape(str(value), quote=True)


def _reject_protected_path(path: Path) -> None:
    home = Path.home().resolve()
    protected_personalos = home / "PersonalOS"
    protected_openclaw = home / ".openclaw"
    try:
        path.relative_to(protected_personalos)
    except ValueError:
        pass
    else:
        raise ValueError("dashboard db_path points at a protected PersonalOS path")
    try:
        path.relative_to(protected_openclaw)
    except ValueError:
        pass
    else:
        raise ValueError("dashboard db_path points at a protected OpenClaw path")
    if ".openclaw" in path.parts:
        raise ValueError("dashboard db_path points at a protected OpenClaw path")
    if "LaunchAgents" in path.parts:
        raise ValueError("dashboard db_path points at a protected LaunchAgents path")


def _reject_sensitive_path(path: Path) -> None:
    lowered = str(path).lower()
    if any(marker in lowered for marker in _SENSITIVE_PATH_MARKERS):
        raise ValueError("dashboard db_path looks like a credential or authorization path")


def _reject_production_path(path: Path) -> None:
    parts = {part.lower() for part in path.parts}
    stem_markers = {part.lower() for part in path.stem.replace("-", "_").split("_")}
    if parts & _PRODUCTION_MARKERS or stem_markers & _PRODUCTION_MARKERS:
        raise ValueError("production-looking dashboard db_path is blocked in Phase 10A")


def _is_under_repo(path: Path) -> bool:
    try:
        path.relative_to(REPO_ROOT.resolve())
    except ValueError:
        return False
    return True


def _is_under_temp(path: Path) -> bool:
    temp_root = Path(tempfile.gettempdir()).resolve()
    try:
        path.relative_to(temp_root)
    except ValueError:
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
