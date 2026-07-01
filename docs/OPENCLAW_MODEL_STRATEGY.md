# OpenClaw Model Strategy

This document defines the deterministic model strategy for Phase 14-C
OpenClaw smoke and planning work. The strategy and readiness surfaces are
configuration and policy surfaces; they do not call any provider, load
credentials, invoke OpenClaw runtime, or activate live model/API behavior.

This strategy supports the bounded smoke envelope in
[PHASE_14C_SUPERVISED_SMOKE_TEST.md](PHASE_14C_SUPERVISED_SMOKE_TEST.md).

Source contract:

- `src/personalos/openclaw_model_strategy.py`
- `build_openclaw_model_strategy_config`
- `build_openclaw_model_call_plan`
- `build_openclaw_model_provider_readiness_report`
- `run_openclaw_model_smoke_probe`
- `sanitize_openclaw_model_run_metadata`
- `src/personalos/openrouter_model_smoke_client.py`

CLI discovery:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c openclaw-model-readiness --json
```

That command checks model-provider config entry names only. It does not read
credential values, load credentials, initialize a model client, call a model
provider, execute tools, invoke OpenClaw, open a database, or write files.

Gated OpenRouter smoke command:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c openrouter-model-smoke --json
```

The default command is report-only and reads environment key names only. It
does not read credential values, initialize a model client, call OpenRouter,
execute tools, invoke OpenClaw, open a database, write files, or activate a
scheduler. A future supervised smoke run must add
`--execute-live --approval-reference <ref>` after config is present and
separate explicit approval has been recorded.

## Model Aliases

Provider-specific IDs may vary by platform, so code should route by aliases
and keep provider hints configurable.

```yaml
openclaw_models:
  smoke_primary:
    alias: nemotron_super
    provider_model_hint: nvidia/nemotron-3-super-120b-a12b
  smoke_fallback:
    alias: glm_5_2
    provider_model_hint: z-ai/glm-5.2
  reasoning_primary:
    alias: glm_5_2
    provider_model_hint: z-ai/glm-5.2
  reasoning_fallback:
    alias: nemotron_super
    provider_model_hint: nvidia/nemotron-3-super-120b-a12b
```

## Lanes

Smoke / low-cost lane:

- Primary: `nemotron_super`
- Fallback: `glm_5_2`
- Uses: OpenClaw no-op smoke probe, cheap sanity checks, basic tool-call
  format checks, and low-cost local/test/sandbox operator checks.
- Smoke probes cap output tokens.

Reasoning / high-complexity lane:

- Primary: `glm_5_2`
- Fallback: `nemotron_super`
- Uses: harder planning, ambiguous multi-step operator reasoning, and future
  higher-complexity OpenClaw planning tasks.

## Routing Constraints

- Routing is explicit by lane and task type.
- No self-modifying routing logic.
- No hidden model choice.
- No provider auto-escalation beyond the declared fallback.
- Max one primary call and one fallback call per smoke probe.
- Fallback is allowed only on provider/client failure, timeout, malformed
  response, or explicit validation failure.
- Full prompts must not be logged when they might contain secrets.
- Credential values must not be logged.
- Safe metadata is limited to provider alias, model alias, lane,
  success/failure, latency if safely available, token counts if safely
  available, HTTP status if available, and sanitized error category/class.

## Provider Readiness

Model-provider readiness reports required config names only by count and
missing names:

- `PERSONALOS_OPENCLAW_MODEL_PROVIDER`
- `PERSONALOS_OPENCLAW_MODEL_API_KEY`
- `PERSONALOS_OPENCLAW_NEMOTRON_SUPER_MODEL`
- `PERSONALOS_OPENCLAW_GLM_5_2_MODEL`

For OpenRouter setup, the current configured defaults are:

- `PERSONALOS_OPENCLAW_MODEL_PROVIDER=openrouter`
- `PERSONALOS_OPENCLAW_NEMOTRON_SUPER_MODEL=nvidia/nemotron-3-super-120b-a12b`
- `PERSONALOS_OPENCLAW_GLM_5_2_MODEL=z-ai/glm-5.2`

Reports must not print present config names, credential values, OAuth material,
raw provider responses, full prompts, or environment dumps.

If config names are missing, the smoke probe reports
`openclaw_model_smoke_not_run_missing_provider_config`.

If config names are present but no injected model client exists, the smoke
probe reports `openclaw_model_smoke_not_run_missing_client`.

If a future supervised operator path injects a configured model client, or the
gated `openrouter-model-smoke --execute-live` command is separately approved,
the smoke probe may make at most one Nemotron Super primary call and one GLM
5.2 fallback call only after primary validation failure. The prompt is a short
constant smoke probe and is not included in the report.

2026-06-30 bounded live OpenRouter results:

- First approval reference:
  `phase14c-2026-06-30-connectivity-live-smoke`.
- First status: `openclaw_model_smoke_validation_failed`.
- First primary call: `nemotron_super`, one call, sanitized
  `transport_or_parse_error`.
- First fallback call: `glm_5_2`, one call after primary validation failed,
  sanitized `transport_or_parse_error`.
- The approved primary/fallback call budget for the first evidence packet was
  exhausted.
- Diagnostic retry showed the local Python runtime needed a CA bundle:
  `SSL_CERT_FILE=/opt/homebrew/etc/ca-certificates/cert.pem`.
- CA-bundle retry approval reference:
  `phase14c-2026-06-30-connectivity-ca-retry`.
- CA-bundle retry status: `openclaw_model_smoke_passed`.
- CA-bundle retry primary call: `nemotron_super`, one call, validation passed.
- CA-bundle retry fallback calls: `fallback_calls=0`; GLM 5.2 was not called.
- Do not rerun without a new explicit approval.
- No credential values, full prompt, raw provider response, tool execution,
  OpenClaw runtime call, protected-path access, scheduler activation,
  production DB activation, or external mutation occurred.

Follow-up diagnostics:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c live-smoke-diagnostics --json
```

That command is repo-local/report-only. It does not read environment variables,
load credentials, initialize live clients, call OpenRouter, write Todoist,
send Gmail, write Calendar, invoke OpenClaw, open a database, or write files.
It records that the next separately approved OpenRouter smoke can include the
safe diagnostic fields `error_kind` and `http_status` while still dropping raw
provider responses, full prompts, configured model IDs, and credential values.

Connected rehearsal planning:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c connected-rehearsal-plan --json
```

That command is repo-local/report-only. It keeps the connected rehearsal model
step deterministic: Nemotron Super primary, GLM 5.2 fallback only if primary
validation fails, no full prompt logging, no raw provider response logging, no
configured model ID logging, no credential values, and no protected OpenClaw
runtime invocation.

Connected rehearsal executable gate:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c connected-rehearsal --json
```

The default gate makes no provider call. Its live mode keeps the same model
routing with one Nemotron Super primary call and one GLM 5.2 fallback call only
if primary validation fails. It sanitizes model metadata to the safe field
allowlist, does not log the full prompt, model-generated brief text, raw
provider response, configured model IDs, or credential values, and stops before
Todoist/Gmail if model validation fails.

## Non-Goals

This strategy does not:

- add a complex autonomous router;
- construct a provider SDK client;
- call Nemotron Super, GLM 5.2, OpenRouter, or any live provider without a
  separately injected model smoke client or the explicitly approved
  `openrouter-model-smoke --execute-live` gate;
- inspect, print, copy, or store credentials;
- print present config names;
- log full prompts or raw provider responses;
- broaden OpenClaw runtime handoff;
- activate scheduler/background behavior;
- activate production DB;
- access protected paths.

## Validation Coverage

`tests/test_openclaw_model_strategy.py` verifies the alias map, smoke and
reasoning lane primary/fallback choices, configurable provider hints, routing
constraints, provider-readiness missing-name reports, max call counts,
output-token caps, primary/fallback smoke-probe behavior, and safe metadata
sanitization.
