"""OpenRouter smoke client for the Phase 14-C OpenClaw model lane."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any


OPENROUTER_CHAT_COMPLETIONS_ENDPOINT = (
    "https://openrouter.ai/api/v1/chat/completions"
)
OPENROUTER_PROVIDER_NAME = "openrouter"


class OpenRouterModelSmokeClient:
    """Minimal OpenRouter chat-completions client for one smoke probe."""

    def __init__(
        self,
        *,
        api_key: str,
        models_by_alias: Mapping[str, str],
        endpoint: str = OPENROUTER_CHAT_COMPLETIONS_ENDPOINT,
        timeout_seconds: float = 20.0,
        opener: Callable[..., Any] = urllib.request.urlopen,
    ) -> None:
        self._api_key = api_key
        self._models_by_alias = dict(models_by_alias)
        self._endpoint = endpoint
        self._timeout_seconds = timeout_seconds
        self._opener = opener

    def run_probe(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        started = time.monotonic()
        model_alias = str(request.get("model_alias", "")).strip()
        model_id = self._models_by_alias.get(model_alias, "").strip()
        if not model_id:
            return {
                "success": False,
                "provider_alias": OPENROUTER_PROVIDER_NAME,
                "failure_category": "missing_model_id",
                "latency_ms": 0,
            }

        payload = {
            "model": model_id,
            "messages": [
                {
                    "role": "user",
                    "content": str(request.get("prompt", "")),
                }
            ],
            "max_tokens": int(request.get("max_output_tokens", 256)),
            "temperature": 0,
        }
        http_request = urllib.request.Request(
            self._endpoint,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with self._opener(http_request, timeout=self._timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
            parsed = json.loads(response_body)
        except urllib.error.HTTPError as error:
            return _failure_result("http_error", started, http_status=error.code)
        except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError):
            return _failure_result("transport_or_parse_error", started)

        if not isinstance(parsed, Mapping):
            return _failure_result("malformed_response", started)
        response_text = _extract_response_text(parsed)
        if response_text is None:
            return _failure_result("malformed_response", started)

        usage = parsed.get("usage")
        usage_mapping = usage if isinstance(usage, Mapping) else {}
        return {
            "success": True,
            "provider_alias": OPENROUTER_PROVIDER_NAME,
            "response_text": response_text,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "input_tokens": _optional_int(usage_mapping.get("prompt_tokens")),
            "output_tokens": _optional_int(usage_mapping.get("completion_tokens")),
        }


def _extract_response_text(response: Mapping[str, Any]) -> str | None:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, Mapping):
        return None
    message = first.get("message")
    if not isinstance(message, Mapping):
        return None
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    return None


def _failure_result(
    failure_category: str,
    started: float,
    *,
    http_status: int | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "success": False,
        "provider_alias": OPENROUTER_PROVIDER_NAME,
        "failure_category": failure_category,
        "latency_ms": int((time.monotonic() - started) * 1000),
    }
    if http_status is not None:
        result["http_status"] = http_status
    return result


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None
