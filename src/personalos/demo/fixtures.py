"""Deterministic fixture data for the Phase 13E-D no-send demo."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from personalos.config import DEFAULT_TIMEZONE

DEMO_NAME = "phase_13e_d_synthetic_no_send_e2e"
PHASE_NAME = "Phase 13E-D - synthetic end-to-end no-send demo"
COMMAND_CONTRACT = (
    "PYTHONPATH=src python3 -m personalos.cli demo no-send-e2e "
    "--output-dir <safe_output_dir> --json"
)
SOURCE_DATE = "2026-06-15"
FIXED_TIME = "2026-06-15T10:00:00+00:00"
FIXED_COMPLETED_TIME = "2026-06-15T10:00:01+00:00"
FIXED_SECOND_COMPLETED_TIME = "2026-06-15T10:00:02+00:00"


def build_synthetic_fixture_manifest() -> dict[str, Any]:
    manifest = {
        "demo_name": DEMO_NAME,
        "phase_name": PHASE_NAME,
        "schema_version": "phase_13e_d_fixture_manifest.v1",
        "source_date": SOURCE_DATE,
        "timezone": DEFAULT_TIMEZONE,
        "fixed_time": FIXED_TIME,
        "routines": _routines(),
        "priorities": _seed_priorities(),
        "projects": _seed_projects(),
        "followups": _seed_followups(),
        "synthesis_payload": build_synthesis_payload(),
        "synthesis_approval": build_synthesis_approval(
            preview_id="filled_after_preview",
        ),
        "side_effect_intents": build_side_effect_inputs(),
        "scheduler_profile": "safe_no_send",
        "coverage": {
            "routines": True,
            "priorities": True,
            "projects_focus_areas": True,
            "followups": True,
            "todoist_preview_only_candidates": True,
            "calendar_preview_only_candidates": True,
            "gmail_no_send_briefing_export_only": True,
            "markdown_note_review_only_candidates": True,
            "blocked_high_stakes_candidates": [
                "tax",
                "legal_estate",
                "portfolio_crypto_investments",
                "health_medical",
                "relationship_messages",
            ],
            "side_effect_idempotency_evidence": True,
            "scheduler_simulation_preview": True,
        },
    }
    manifest["fixture_manifest_hash"] = stable_fixture_hash(manifest)
    return manifest


def stable_fixture_hash(payload: dict[str, Any]) -> str:
    material = {
        key: value
        for key, value in payload.items()
        if key != "fixture_manifest_hash"
    }
    encoded = json.dumps(
        material,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_synthesis_payload() -> dict[str, Any]:
    return {
        "schema_version": "synthesis_import.v1",
        "source_type": "chatgpt_synthesis",
        "source_timestamp": FIXED_TIME,
        "source_reference": "phase-13e-d-synthetic-fixture",
        "summary": "Synthetic no-send demo payload for local preview and apply.",
        "candidates": _synthesis_candidates(),
        "warnings": [
            "Synthetic fixture only.",
            "External rails remain preview-only or blocked.",
        ],
    }

def build_synthesis_approval(*, preview_id: str) -> dict[str, Any]:
    return {
        "preview_id": preview_id,
        "approved_candidates": [
            {"candidate_type": "priority", "candidate_index": 0},
            {"candidate_type": "project", "candidate_index": 0},
            {"candidate_type": "followup", "candidate_index": 0},
        ],
        "rejected_candidates": [
            {
                "candidate_type": "todoist_task",
                "candidate_index": 0,
                "reason": "External Todoist rail stays preview-only in Phase 13E-D.",
            },
            {
                "candidate_type": "calendar_block",
                "candidate_index": 0,
                "reason": "External Calendar rail stays preview-only in Phase 13E-D.",
            },
            {
                "candidate_type": "clarity_note",
                "candidate_index": 0,
                "reason": "Markdown writes stay review-only in Phase 13E-D.",
            },
        ],
        "approval_note": "Approve only internal SQLite priority/project/followup candidates.",
    }


def build_side_effect_inputs() -> list[dict[str, Any]]:
    return [
        {
            "intent": {
                "source_type": "phase_13e_d_demo",
                "source_id": "todoist-preview-candidate",
                "target_system": "todoist",
                "operation_type": "create",
                "payload": {
                    "task_title": "Review no-send evidence bundle",
                    "preview_only": True,
                },
                "risk_level": "low",
                "approval_mode": "auto_allowed",
                "dedupe_key": "phase 13e d todoist preview candidate",
                "created_at": FIXED_TIME,
                "updated_at": FIXED_TIME,
            },
            "attempt": {
                "mode": "dry_run",
                "adapter_name": "phase_13e_d_inert_demo_adapter",
                "status": "succeeded",
                "response_summary": {
                    "preview_only": True,
                    "external_mutation": False,
                },
                "created_at": FIXED_TIME,
            },
        },
        {
            "intent": {
                "source_type": "phase_13e_d_demo",
                "source_id": "calendar-preview-candidate",
                "target_system": "calendar",
                "operation_type": "create",
                "payload": {
                    "title": "Review no-send briefing",
                    "preview_only": True,
                },
                "risk_level": "low",
                "approval_mode": "auto_allowed",
                "dedupe_key": "phase 13e d calendar preview candidate",
                "created_at": FIXED_TIME,
                "updated_at": FIXED_TIME,
            },
            "attempt": {
                "mode": "dry_run",
                "adapter_name": "phase_13e_d_inert_demo_adapter",
                "status": "succeeded",
                "response_summary": {
                    "preview_only": True,
                    "external_mutation": False,
                },
                "created_at": FIXED_TIME,
            },
        },
        {
            "intent": {
                "source_type": "phase_13e_d_demo",
                "source_id": "gmail-briefing-export",
                "target_system": "gmail",
                "operation_type": "export",
                "payload": {
                    "briefing_window": "morning",
                    "manual_export_only": True,
                },
                "risk_level": "low",
                "approval_mode": "auto_allowed",
                "dedupe_key": "phase 13e d gmail manual export",
                "created_at": FIXED_TIME,
                "updated_at": FIXED_TIME,
            },
            "attempt": {
                "mode": "dry_run",
                "adapter_name": "phase_13e_d_no_send_export_adapter",
                "status": "succeeded",
                "response_summary": {
                    "manual_export_only": True,
                    "external_mutation": False,
                },
                "created_at": FIXED_TIME,
            },
        },
        {
            "intent": {
                "source_type": "phase_13e_d_demo",
                "source_id": "markdown-review-candidate",
                "target_system": "personalos_markdown",
                "operation_type": "write_file",
                "payload": {
                    "title": "Synthetic clarity note",
                    "review_only": True,
                },
                "risk_level": "high",
                "approval_mode": "manual_only",
                "dedupe_key": "phase 13e d markdown review candidate",
                "created_at": FIXED_TIME,
                "updated_at": FIXED_TIME,
            },
            "attempt": {
                "mode": "live_blocked",
                "adapter_name": "phase_13e_d_markdown_block_adapter",
                "status": "blocked",
                "response_summary": {
                    "review_only": True,
                    "external_mutation": False,
                },
                "error_message": "PersonalOS Markdown writes are blocked in Phase 13E-D.",
                "created_at": FIXED_TIME,
            },
        },
    ]


def _routines() -> list[dict[str, Any]]:
    return [
        {
            "routine_id": "routine-phase-13e-d-morning-review",
            "name": "Morning Review",
            "status": "active",
            "enabled": True,
            "settings": {
                "cadence_rule": "weekdays",
                "preferred_window": "morning",
                "todoist_behavior": "preview_only",
                "calendar_behavior": "preview_only",
            },
            "notes": "Synthetic routine for no-send demo evidence.",
        },
        {
            "routine_id": "routine-phase-13e-d-reading",
            "name": "Reading",
            "status": "active",
            "enabled": True,
            "settings": {
                "cadence_rule": "x_times_per_week",
                "weekly_target": 4,
                "missed_behavior": "carry_forward_within_week",
            },
            "notes": "Synthetic reading routine.",
        },
        {
            "routine_id": "routine-phase-13e-d-shutdown",
            "name": "Shutdown Review",
            "status": "active",
            "enabled": True,
            "settings": {
                "cadence_rule": "daily",
                "preferred_window": "evening",
            },
            "notes": "Synthetic evening shutdown routine.",
        },
    ]


def _seed_priorities() -> list[dict[str, Any]]:
    return [
        {
            "priority_id": "priority-phase-13e-d-no-send-proof",
            "title": "Prove no-send workflow evidence",
            "status": "active",
            "metadata": {
                "focus_area": "Personal OS safety",
                "source": "phase_13e_d_fixture",
            },
            "notes": "Synthetic priority seeded before synthesis import.",
        }
    ]


def _seed_projects() -> list[dict[str, Any]]:
    return [
        {
            "project_id": "project-phase-13e-d-demo",
            "title": "Phase 13E-D evidence bundle",
            "status": "active",
            "metadata": {
                "focus_area": "no-send demo",
                "source": "phase_13e_d_fixture",
            },
            "notes": "Synthetic project/focus area seeded for dashboard evidence.",
        }
    ]


def _seed_followups() -> list[dict[str, Any]]:
    return [
        {
            "followup_id": "followup-phase-13e-d-review",
            "title": "Review synthetic evidence bundle",
            "status": "open",
            "source": "phase_13e_d_fixture",
            "metadata": {
                "review_window": "after PR validation",
                "source": "phase_13e_d_fixture",
            },
            "notes": "Synthetic follow-up for Chris review.",
        }
    ]


def _synthesis_candidates() -> dict[str, list[dict[str, Any]]]:
    return {
        "priorities": [
            {
                "title": "Keep no-send review loop deterministic",
                "summary": "Use fixed fixture inputs and explicit safe output paths.",
                "source_type": "chatgpt_synthesis",
                "source_id": "phase-13e-d",
                "risk_level": "low",
                "approval_mode": "auto_allowed",
                "status": "active",
                "review_note": "Internal SQLite priority candidate only.",
                "domain": "productivity",
            },
            {
                "title": "Review portfolio and crypto thesis manually",
                "summary": "Portfolio, crypto, and investment decisions stay review-only.",
                "source_type": "chatgpt_synthesis",
                "source_id": "phase-13e-d-high-stakes",
                "risk_level": "high",
                "approval_mode": "approval_required",
                "status": "paused",
                "review_note": "High-stakes review-only item.",
                "domain": "portfolio_crypto_investments",
            },
        ],
        "projects": [
            {
                "title": "No-send evidence review",
                "summary": "Bundle local workflow, readiness, ledger, and briefing evidence.",
                "source_type": "chatgpt_synthesis",
                "source_id": "phase-13e-d",
                "risk_level": "low",
                "approval_mode": "auto_allowed",
                "status": "active",
                "review_note": "Internal SQLite project candidate only.",
                "domain": "personal_os",
            }
        ],
        "followups": [
            {
                "title": "Confirm Phase 13E-D evidence with Chris",
                "summary": "Review the generated local evidence bundle before merge.",
                "source_type": "chatgpt_synthesis",
                "source_id": "phase-13e-d",
                "risk_level": "low",
                "approval_mode": "auto_allowed",
                "status": "open",
                "due_date_or_review_note": "Review after local validation.",
                "domain": "personal_os",
            },
            {
                "title": "Relationship message requires manual review",
                "summary": "Relationship message to another person stays review-only.",
                "source_type": "chatgpt_synthesis",
                "source_id": "phase-13e-d-relationship",
                "risk_level": "high",
                "approval_mode": "approval_required",
                "status": "open",
                "due_date_or_review_note": "Manual review only.",
                "domain": "relationship_messages",
                "recipient": "review-recipient",
                "message_to": "review-recipient",
            },
        ],
        "routine_changes": [
            {
                "routine_name": "Shutdown Review",
                "change_type": "review",
                "summary": "Consider checking no-send evidence during evening review.",
                "proposed_fields": {
                    "review_prompt": "Check no-send evidence before live rail discussion."
                },
                "risk_level": "low",
                "approval_mode": "auto_allowed",
                "status": "proposed",
                "domain": "routines",
            }
        ],
        "todoist_tasks": [
            {
                "task_title": "Review no-send evidence bundle",
                "description": "Preview-only Todoist candidate; no live task is created.",
                "source_type": "chatgpt_synthesis",
                "source_id": "phase-13e-d",
                "project": "Admin",
                "labels": ["phase-13e-d", "preview"],
                "due_date_or_due_string": "2026-06-16",
                "priority": 2,
                "risk_level": "low",
                "approval_mode": "auto_allowed",
                "dedupe_key": "phase 13e d todoist review evidence",
                "status": "proposed",
                "domain": "todoist_preview",
            },
            {
                "task_title": "File tax amendment automatically",
                "description": "Submit the tax directive without manual review.",
                "source_type": "chatgpt_synthesis",
                "source_id": "phase-13e-d-tax",
                "project": "Admin",
                "labels": ["tax", "blocked"],
                "due_date_or_due_string": "2026-06-16",
                "priority": 3,
                "risk_level": "low",
                "approval_mode": "auto_allowed",
                "dedupe_key": "phase 13e d blocked tax task",
                "status": "proposed",
                "domain": "tax",
            },
            {
                "task_title": "Buy crypto for portfolio rebalance",
                "description": "Execute crypto investment allocation change.",
                "source_type": "chatgpt_synthesis",
                "source_id": "phase-13e-d-portfolio",
                "project": "Admin",
                "labels": ["portfolio", "blocked"],
                "due_date_or_due_string": "2026-06-16",
                "priority": 4,
                "risk_level": "low",
                "approval_mode": "auto_allowed",
                "dedupe_key": "phase 13e d blocked crypto task",
                "status": "proposed",
                "domain": "portfolio_crypto_investments",
            },
            {
                "task_title": "Diagnose health issue and prescribe treatment",
                "description": "Medical directive must not be automated.",
                "source_type": "chatgpt_synthesis",
                "source_id": "phase-13e-d-health",
                "project": "Admin",
                "labels": ["health", "blocked"],
                "due_date_or_due_string": "2026-06-16",
                "priority": 3,
                "risk_level": "low",
                "approval_mode": "auto_allowed",
                "dedupe_key": "phase 13e d blocked health task",
                "status": "proposed",
                "domain": "health_medical",
            },
            {
                "task_title": "Draft relationship message for review",
                "description": "Relationship message stays approval-required.",
                "source_type": "chatgpt_synthesis",
                "source_id": "phase-13e-d-relationship-task",
                "project": "Admin",
                "labels": ["relationship", "review"],
                "due_date_or_due_string": "2026-06-16",
                "priority": 2,
                "risk_level": "high",
                "approval_mode": "approval_required",
                "dedupe_key": "phase 13e d relationship review task",
                "status": "needs_approval",
                "domain": "relationship_messages",
                "recipient": "review-recipient",
            },
        ],
        "calendar_blocks": [
            {
                "title": "Review no-send briefing",
                "description": "Self-only preview block; no live Calendar event is created.",
                "source_type": "chatgpt_synthesis",
                "source_id": "phase-13e-d",
                "start_time": "2026-06-16T10:00:00-05:00",
                "end_time": "2026-06-16T10:30:00-05:00",
                "duration_minutes": 30,
                "calendar_id": "primary",
                "timezone": DEFAULT_TIMEZONE,
                "approval_mode": "auto_allowed",
                "risk_level": "low",
                "dedupe_key": "phase 13e d calendar review block",
                "status": "proposed",
                "domain": "calendar_preview",
            },
            {
                "title": "Estate planning call with attorney",
                "description": "Legal and estate external meeting requires review.",
                "source_type": "chatgpt_synthesis",
                "source_id": "phase-13e-d-legal-estate",
                "start_time": "2026-06-16T13:00:00-05:00",
                "end_time": "2026-06-16T14:00:00-05:00",
                "duration_minutes": 60,
                "calendar_id": "primary",
                "timezone": DEFAULT_TIMEZONE,
                "approval_mode": "approval_required",
                "risk_level": "high",
                "dedupe_key": "phase 13e d legal estate review block",
                "status": "needs_approval",
                "domain": "legal_estate",
                "attendees": ["attorney@example.test"],
                "is_external_meeting": True,
            },
            {
                "title": "External tax meeting",
                "description": "Auto-scheduled tax meeting is blocked.",
                "source_type": "chatgpt_synthesis",
                "source_id": "phase-13e-d-tax-meeting",
                "start_time": "2026-06-16T15:00:00-05:00",
                "end_time": "2026-06-16T15:30:00-05:00",
                "duration_minutes": 30,
                "calendar_id": "primary",
                "timezone": DEFAULT_TIMEZONE,
                "approval_mode": "auto_allowed",
                "risk_level": "low",
                "dedupe_key": "phase 13e d blocked tax calendar block",
                "status": "proposed",
                "domain": "tax",
                "attendees": ["tax@example.test"],
                "is_external_meeting": True,
            },
        ],
        "clarity_notes": [
            {
                "title": "No-send demo remains local",
                "summary": "Synthetic Markdown note candidate remains review-only.",
                "category": "architecture",
                "source_reference": "phase-13e-d-synthetic-fixture",
                "durable_insight": "Markdown candidates need explicit approval later.",
                "risk_level": "low",
                "approval_mode": "auto_allowed",
                "status": "proposed",
                "domain": "markdown_review_only",
            },
            {
                "title": "Investment thesis note requires review",
                "summary": "Portfolio and investment note remains manual-only.",
                "category": "investment_review",
                "source_reference": "phase-13e-d-synthetic-fixture",
                "durable_insight": "Investment notes require manual review before durable write.",
                "risk_level": "high",
                "approval_mode": "manual_only",
                "status": "needs_approval",
                "domain": "portfolio_crypto_investments",
            },
        ],
        "review_questions": [
            {
                "question": "Did every external rail candidate remain preview-only, blocked, or review-only?",
                "reason": "Phase 13E-D is a no-send evidence phase.",
                "candidate_refs": [
                    "todoist_tasks[0]",
                    "todoist_tasks[1]",
                    "calendar_blocks[0]",
                    "clarity_notes[0]",
                ],
                "status": "open",
            }
        ],
    }
