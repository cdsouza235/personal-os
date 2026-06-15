import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.permissions import PermissionMode
from personalos.reports import (
    CHART_PACK_REVIEWS_READ_PERMISSION,
    CHART_PACK_REVIEWS_WRITE_PERMISSION,
    REPORT_JOBS_READ_PERMISSION,
    REPORT_JOBS_RUN_PERMISSION,
    REPORT_JOBS_WRITE_PERMISSION,
    FakeReportRunner,
    ReportModulePermissionDenied,
    ReportValidationError,
    build_report_run_output,
    create_chart_pack_review_record,
    create_report_job_record,
    create_report_run_record,
    preview_report_job_output,
    read_chart_pack_review_count,
    read_chart_pack_reviews,
    read_report_job_count,
    read_report_jobs,
    read_report_run_count,
    read_report_runs,
    run_fake_report_job,
    stable_report_id,
    update_chart_pack_review_record,
    update_report_job_record,
    update_report_run_record,
    validate_chart_pack_review,
    validate_report_job,
    validate_report_run,
)
from personalos.state import (
    count_chart_pack_reviews,
    count_report_jobs,
    count_report_runs,
    create_chart_pack_review,
    create_report_job,
    create_report_run,
    get_chart_pack_review,
    get_report_job,
    get_report_run,
    list_chart_pack_reviews,
    list_report_jobs,
    list_report_runs,
    upsert_permission_setting,
)


class ReportMigrationAndStateTest(unittest.TestCase):
    def test_migration_0006_is_applied(self) -> None:
        with _migrated_test_connection() as connection:
            rows = connection.execute(
                "SELECT version, name FROM schema_migrations ORDER BY version"
            ).fetchall()

        self.assertEqual(rows[-1]["version"], "0006")
        self.assertEqual(rows[-1]["name"], "report_jobs_chart_pack_tables")

    def test_state_helpers_create_read_list_and_count_records(self) -> None:
        job = _valid_job()
        output = build_report_run_output(
            job=job,
            input_json={"chart_pack_count": 1},
            run_type="dry_run",
            status="completed",
            generated_at="2026-06-15T14:00:00+00:00",
        )
        run = _valid_run(output_json=output)
        review = _valid_review()

        with _migrated_test_connection() as connection:
            created_job = create_report_job(
                connection,
                job_id=job["id"],
                job_type=job["job_type"],
                name=job["name"],
                description=job["description"],
                cadence=job["cadence"],
                config_json=job["config_json"],
                status=job["status"],
                next_due_at=job["next_due_at"],
                created_at=job["created_at"],
                updated_at=job["updated_at"],
            )
            created_run = create_report_run(
                connection,
                run_id=run["id"],
                job_id=run["job_id"],
                run_type=run["run_type"],
                dry_run=run["dry_run"],
                status=run["status"],
                input_json=run["input_json"],
                output_json=run["output_json"],
                created_at=run["created_at"],
                completed_at=run["completed_at"],
            )
            created_review = create_chart_pack_review(
                connection,
                review_id=review["id"],
                review_date=review["review_date"],
                week_start=review["week_start"],
                week_end=review["week_end"],
                source_type=review["source_type"],
                source_id=review["source_id"],
                title=review["title"],
                thesis_context=review["thesis_context"],
                chart_pack_json=review["chart_pack_json"],
                tradingview_alerts_json=review["tradingview_alerts_json"],
                synthesis_markdown=review["synthesis_markdown"],
                structured_summary_json=review["structured_summary_json"],
                status=review["status"],
                created_at=review["created_at"],
                updated_at=review["updated_at"],
            )

            self.assertEqual(get_report_job(connection, job["id"]), created_job)
            self.assertEqual(get_report_run(connection, run["id"]), created_run)
            self.assertEqual(get_chart_pack_review(connection, review["id"]), created_review)
            self.assertEqual([item["id"] for item in list_report_jobs(connection)], [job["id"]])
            self.assertEqual([item["id"] for item in list_report_runs(connection)], [run["id"]])
            self.assertEqual(
                [item["id"] for item in list_chart_pack_reviews(connection)],
                [review["id"]],
            )
            self.assertEqual(count_report_jobs(connection), 1)
            self.assertEqual(count_report_runs(connection), 1)
            self.assertEqual(count_chart_pack_reviews(connection), 1)


class ReportValidationTest(unittest.TestCase):
    def test_report_job_validation_accepts_valid_job(self) -> None:
        job = validate_report_job(_valid_job())

        self.assertEqual(job["schema_version"], "report_job.v1")
        self.assertEqual(job["job_type"], "weekly_chart_pack_index")
        self.assertEqual(job["config_json"]["manual_inputs_only"], True)

    def test_report_job_validation_rejects_missing_required_fields(self) -> None:
        job = _valid_job()
        del job["cadence"]

        with self.assertRaises(ReportValidationError):
            validate_report_job(job)

    def test_report_job_validation_rejects_invalid_job_type(self) -> None:
        job = _valid_job(job_type="live_tradingview_fetch")

        with self.assertRaises(ValueError):
            validate_report_job(job)

    def test_report_job_validation_rejects_invalid_cadence(self) -> None:
        job = _valid_job(cadence="hourly")

        with self.assertRaises(ValueError):
            validate_report_job(job)

    def test_report_run_validation_accepts_valid_dry_run(self) -> None:
        run = validate_report_run(_valid_run())

        self.assertEqual(run["schema_version"], "report_run.v1")
        self.assertTrue(run["dry_run"])
        self.assertTrue(run["output_json"]["no_external_writes"])

    def test_report_run_validation_rejects_invalid_run_type_or_status(self) -> None:
        with self.assertRaises(ValueError):
            validate_report_run(_valid_run(run_type="live"))
        with self.assertRaises(ValueError):
            validate_report_run(_valid_run(status="sent"))

    def test_report_run_validation_rejects_external_write_output(self) -> None:
        run = _valid_run(output_json={"no_external_writes": False})

        with self.assertRaises(ReportValidationError):
            validate_report_run(run)

    def test_chart_pack_review_validation_accepts_valid_structured_review(self) -> None:
        review = validate_chart_pack_review(_valid_review())

        self.assertEqual(review["schema_version"], "chart_pack_review.v1")
        self.assertEqual(review["source_type"], "chatgpt_synthesis")
        self.assertEqual(review["structured_summary_json"]["btc_context"], "Range-bound.")

    def test_chart_pack_review_validation_rejects_missing_summary_sections(self) -> None:
        review = _valid_review()
        del review["structured_summary_json"]["warnings"]

        with self.assertRaises(ReportValidationError):
            validate_chart_pack_review(review)

    def test_chart_pack_review_validation_rejects_empty_synthesis(self) -> None:
        review = _valid_review(synthesis_markdown=" ")

        with self.assertRaises(ReportValidationError):
            validate_chart_pack_review(review)

    def test_chart_pack_review_validation_rejects_autonomous_investment_action(self) -> None:
        review = _valid_review()
        review["structured_summary_json"]["followup_candidates"] = [
            {
                "title": "Buy BTC",
                "candidate_type": "review_candidate",
                "action_type": "buy",
                "risk_level": "low",
                "approval_mode": "auto_allowed",
                "approval_required": False,
            }
        ]

        with self.assertRaises(ReportValidationError):
            validate_chart_pack_review(review)


class FakeReportRunnerTest(unittest.TestCase):
    def test_preview_report_output_is_local_only(self) -> None:
        output = preview_report_job_output(
            job=_valid_job(),
            input_json={"alerts": 3},
            generated_at="2026-06-15T14:00:00+00:00",
        )

        self.assertEqual(output["job_id"], "report-job-1")
        self.assertEqual(output["run_type"], "preview")
        self.assertTrue(output["no_external_writes"])
        self.assertFalse(output["network_called"])

    def test_fake_report_runner_deterministic_success(self) -> None:
        runner = FakeReportRunner()
        job = _valid_job()

        first = runner.run(
            job=job,
            input_json={"alerts": ["a", "b"]},
            run_type="dry_run",
            generated_at="2026-06-15T14:00:00+00:00",
        )
        second = runner.run(
            job=job,
            input_json={"alerts": ["a", "b"]},
            run_type="dry_run",
            generated_at="2026-06-15T14:00:00+00:00",
        )

        self.assertEqual(first, second)
        self.assertEqual(
            runner.calls,
            [
                {
                    "job_id": "report-job-1",
                    "run_type": "dry_run",
                    "input_digest": runner.calls[0]["input_digest"],
                },
                {
                    "job_id": "report-job-1",
                    "run_type": "dry_run",
                    "input_digest": runner.calls[0]["input_digest"],
                },
            ],
        )

    def test_fake_report_runner_success_persists_report_run(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, REPORT_JOBS_WRITE_PERMISSION)
            _set_permission(connection, REPORT_JOBS_RUN_PERMISSION)
            _create_raw_job(connection, _valid_job())

            result = run_fake_report_job(
                connection,
                job=_valid_job(),
                input_json={"alerts": 2},
                run_at="2026-06-15T14:00:00+00:00",
            )
            report_runs = count_report_runs(connection)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["report_run"]["status"], "completed")
        self.assertEqual(report_runs, 1)
        self.assertTrue(result["output_json"]["no_external_writes"])

    def test_fake_report_runner_failure_mode_persists_failed_run(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, REPORT_JOBS_WRITE_PERMISSION)
            _set_permission(connection, REPORT_JOBS_RUN_PERMISSION)
            _create_raw_job(connection, _valid_job())

            result = run_fake_report_job(
                connection,
                job=_valid_job(),
                input_json={"alerts": 2},
                runner=FakeReportRunner(should_fail=True),
                run_at="2026-06-15T14:00:00+00:00",
            )
            report_runs = list_report_runs(connection)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(report_runs[0]["status"], "failed")
        self.assertIn("failure mode", report_runs[0]["error_message"])

    def test_fake_report_runner_output_includes_no_external_writes_true(self) -> None:
        output = build_report_run_output(
            job=_valid_job(),
            input_json={"alerts": 1},
            run_type="dry_run",
            status="completed",
            generated_at="2026-06-15T14:00:00+00:00",
        )

        self.assertIs(output["no_external_writes"], True)


class ReportPermissionTest(unittest.TestCase):
    def test_permission_defaults_fail_closed(self) -> None:
        with _migrated_test_connection() as connection:
            with self.assertRaises(ReportModulePermissionDenied):
                read_report_jobs(connection)
            with self.assertRaises(ReportModulePermissionDenied):
                read_chart_pack_reviews(connection)

            job_result = create_report_job_record(connection, job=_valid_job())
            review_result = create_chart_pack_review_record(connection, review=_valid_review())
            run_result = run_fake_report_job(
                connection,
                job=_valid_job(),
                input_json={"alerts": 1},
                run_at="2026-06-15T14:00:00+00:00",
            )

        self.assertEqual(job_result["status"], "blocked")
        self.assertEqual(review_result["status"], "blocked")
        self.assertEqual(run_result["status"], "blocked")

    def test_permission_gated_read_write_run_helpers(self) -> None:
        job = _valid_job()
        run = _valid_run()
        review = _valid_review()

        with _migrated_test_connection() as connection:
            _set_permission(connection, REPORT_JOBS_WRITE_PERMISSION)
            _set_permission(connection, REPORT_JOBS_READ_PERMISSION)
            _set_permission(connection, REPORT_JOBS_RUN_PERMISSION)
            _set_permission(connection, CHART_PACK_REVIEWS_WRITE_PERMISSION)
            _set_permission(connection, CHART_PACK_REVIEWS_READ_PERMISSION)

            created_job = create_report_job_record(connection, job=job)
            created_run = create_report_run_record(connection, run=run)
            created_review = create_chart_pack_review_record(connection, review=review)
            run_result = run_fake_report_job(
                connection,
                job=job,
                input_json={"alerts": 1},
                run_at="2026-06-15T15:00:00+00:00",
            )
            updated_job = update_report_job_record(
                connection,
                job_id=job["id"],
                status="paused",
                updated_at="2026-06-15T16:00:00+00:00",
            )
            updated_run = update_report_run_record(
                connection,
                run_id=run["id"],
                status="completed",
                completed_at="2026-06-15T16:00:00+00:00",
            )
            updated_review = update_chart_pack_review_record(
                connection,
                review_id=review["id"],
                status="stored",
                updated_at="2026-06-15T16:00:00+00:00",
            )

            job_count = read_report_job_count(connection)
            jobs = read_report_jobs(connection)
            run_count = read_report_run_count(connection)
            runs = read_report_runs(connection)
            review_count = read_chart_pack_review_count(connection)
            reviews = read_chart_pack_reviews(connection)

        self.assertEqual(created_job["status"], "created")
        self.assertEqual(created_run["status"], "created")
        self.assertEqual(created_review["status"], "created")
        self.assertEqual(run_result["status"], "completed")
        self.assertEqual(updated_job["job"]["status"], "paused")
        self.assertEqual(updated_run["report_run"]["status"], "completed")
        self.assertEqual(updated_review["review"]["status"], "stored")
        self.assertEqual(job_count, 1)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(run_count, 2)
        self.assertEqual(len(runs), 2)
        self.assertEqual(review_count, 1)
        self.assertEqual(len(reviews), 1)


class ReportDocumentationAndSafetyTest(unittest.TestCase):
    def test_docs_describe_phase_7_scope_and_non_goals(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        docs_text = "\n".join(
            [
                (repo_root / "README.md").read_text(encoding="utf-8"),
                (repo_root / "docs" / "ROADMAP.md").read_text(encoding="utf-8"),
                (repo_root / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8"),
                (repo_root / "docs" / "SAFETY_POLICY.md").read_text(encoding="utf-8"),
            ]
        ).lower()

        for expected in (
            "phase 7",
            "weekly chart pack",
            "report jobs are coded jobs",
            "chatgpt is the interpretation layer",
            "tradingview alerts are manually supplied",
            "no live market data fetching",
            "no tradingview api",
            "no investment recommendations",
            "no portfolio execution",
            "no scheduler",
            "no production sqlite",
            "no dashboard ui",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, docs_text)

    def test_repo_has_no_runtime_database_or_var_artifacts(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        sqlite_artifacts = [
            path
            for path in repo_root.rglob("*")
            if ".git" not in path.parts
            and path.is_file()
            and path.suffix in {".sqlite", ".sqlite3", ".db"}
        ]
        var_dirs = [
            path
            for path in repo_root.rglob("var")
            if ".git" not in path.parts and path.is_dir()
        ]

        self.assertEqual(sqlite_artifacts, [])
        self.assertEqual(var_dirs, [])


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


def _set_permission(
    connection: sqlite3.Connection,
    category: str,
    mode: PermissionMode = PermissionMode.AUTO_WRITE,
) -> None:
    upsert_permission_setting(
        connection,
        category=category,
        mode=mode.value,
        metadata={"phase": "7", "dev_test_only": True},
        updated_by="tests",
        updated_at_utc="2026-06-15T10:00:00+00:00",
    )


def _create_raw_job(connection: sqlite3.Connection, job: dict[str, object]) -> None:
    create_report_job(
        connection,
        job_id=str(job["id"]),
        job_type=str(job["job_type"]),
        name=str(job["name"]),
        description=str(job["description"]),
        cadence=str(job["cadence"]),
        config_json=job["config_json"],
        status=str(job["status"]),
        next_due_at=str(job["next_due_at"]),
        created_at=str(job["created_at"]),
        updated_at=str(job["updated_at"]),
    )


def _valid_job(**overrides: object) -> dict[str, object]:
    job: dict[str, object] = {
        "schema_version": "report_job.v1",
        "id": "report-job-1",
        "job_type": "weekly_chart_pack_index",
        "name": "Weekly Chart Pack Index",
        "description": "Indexes manually supplied chart packs and alerts.",
        "cadence": "weekly",
        "config_json": {
            "manual_inputs_only": True,
            "tradingview_fetch_enabled": False,
            "live_market_data_enabled": False,
        },
        "status": "active",
        "last_run_at": None,
        "next_due_at": "2026-06-22T10:00:00+00:00",
        "created_at": "2026-06-15T10:00:00+00:00",
        "updated_at": "2026-06-15T10:00:00+00:00",
    }
    job.update(overrides)
    return job


def _valid_run(**overrides: object) -> dict[str, object]:
    output = build_report_run_output(
        job=_valid_job(),
        input_json={"chart_pack_count": 1},
        run_type="dry_run",
        status="completed",
        generated_at="2026-06-15T14:00:00+00:00",
    )
    run: dict[str, object] = {
        "schema_version": "report_run.v1",
        "id": stable_report_id("report-run", "report-job-1|dry-run"),
        "job_id": "report-job-1",
        "run_type": "dry_run",
        "dry_run": True,
        "status": "completed",
        "input_json": {"chart_pack_count": 1},
        "output_json": output,
        "error_message": None,
        "created_at": "2026-06-15T14:00:00+00:00",
        "completed_at": "2026-06-15T14:00:00+00:00",
    }
    run.update(overrides)
    return run


def _valid_review(**overrides: object) -> dict[str, object]:
    review: dict[str, object] = {
        "schema_version": "chart_pack_review.v1",
        "id": "chart-pack-review-1",
        "review_date": "2026-06-15",
        "week_start": "2026-06-08",
        "week_end": "2026-06-14",
        "source_type": "chatgpt_synthesis",
        "source_id": "chatgpt-thread-fixture",
        "title": "Weekly Chart Pack Review",
        "thesis_context": "Manual thesis review only.",
        "chart_pack_json": {
            "charts": [
                {
                    "symbol": "BTC",
                    "timeframe": "weekly",
                    "notes": "Manual chart pack note.",
                }
            ]
        },
        "tradingview_alerts_json": {
            "alerts": [
                {
                    "symbol": "BTC",
                    "message": "Manual alert digest item.",
                    "triggered_at": "2026-06-14T20:00:00+00:00",
                }
            ],
            "manual_supply": True,
        },
        "synthesis_markdown": "ChatGPT synthesis provided by Chris. Review only.",
        "structured_summary_json": _valid_structured_summary(),
        "status": "validated",
        "created_at": "2026-06-15T10:00:00+00:00",
        "updated_at": "2026-06-15T10:00:00+00:00",
    }
    review.update(overrides)
    return review


def _valid_structured_summary() -> dict[str, object]:
    return {
        "market_context": "Risk appetite mixed.",
        "btc_context": "Range-bound.",
        "eth_context": "Relative strength under review.",
        "miner_hpc_context": "Watch AI/HPC revenue narrative.",
        "portfolio_watch_items": ["BTC weekly close", "ETH/BTC relative trend"],
        "week_over_week_changes": {
            "btc": "No autonomous interpretation; ChatGPT supplied synthesis only."
        },
        "followup_candidates": [
            {
                "title": "Review BTC weekly close",
                "candidate_type": "review_candidate",
                "risk_level": "medium",
                "approval_mode": "approval_required",
                "approval_required": True,
                "creates_external_action": False,
            }
        ],
        "warnings": ["Review/logging only; no recommendations or execution."],
    }
