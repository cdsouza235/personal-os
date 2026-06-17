"""Deterministic idempotency keys and payload fingerprints.

The current truncated SHA-256 keys are for local dev/test ledgers. Before any
external-write rail is enabled, the live-rail plan must decide the collision
posture for production idempotency records.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


def payload_fingerprint(payload: Mapping[str, Any]) -> str:
    """Return a stable fingerprint for equivalent JSON-safe payload objects."""
    payload_json = stable_json_dumps(payload)
    return "sha256:" + hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def generate_idempotency_key(
    *,
    target_system: str,
    operation_type: str,
    source_type: str,
    source_id: str,
    dedupe_key: str,
    payload: Mapping[str, Any],
) -> str:
    """Build a deterministic key from stable intent fields and payload content."""
    target = normalize_idempotency_component("target_system", target_system)
    operation = normalize_idempotency_component("operation_type", operation_type)
    material = {
        "target_system": target,
        "operation_type": operation,
        "source_type": normalize_idempotency_component("source_type", source_type),
        "source_id": normalize_idempotency_component("source_id", source_id),
        "dedupe_key": normalize_idempotency_component("dedupe_key", dedupe_key),
        "payload_fingerprint": payload_fingerprint(payload),
    }
    digest = hashlib.sha256(stable_json_dumps(material).encode("utf-8")).hexdigest()
    return f"idem:{target}:{operation}:{digest[:32]}"


def stable_side_effect_id(prefix: str, key_material: str) -> str:
    prefix = normalize_idempotency_component("prefix", prefix).replace(" ", "-")
    key_material = normalize_idempotency_component("key_material", key_material)
    digest = hashlib.sha256(key_material.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}-{digest}"


def stable_json_dumps(value: Any) -> str:
    normalized = _normalize_json_value(value)
    return json.dumps(
        normalized,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def normalize_idempotency_component(field_name: str, value: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    normalized = " ".join(value.strip().lower().split())
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _normalize_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _normalize_json_value(nested)
            for key, nested in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, str) or value is None or isinstance(value, bool):
        return value
    if type(value) in (int, float):
        return value
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return [_normalize_json_value(item) for item in value]
    raise TypeError(f"Value is not JSON-safe for idempotency: {type(value).__name__}")
