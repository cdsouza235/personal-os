# OpenClaw Model Strategy

This document defines the deterministic model strategy for Phase 14-C
OpenClaw smoke and planning work. It is a configuration and policy surface; it
does not call any provider, load credentials, invoke OpenClaw runtime, or
activate live model/API behavior.

This strategy supports the bounded smoke envelope in
[PHASE_14C_SUPERVISED_SMOKE_TEST.md](PHASE_14C_SUPERVISED_SMOKE_TEST.md).

Source contract:

- `src/personalos/openclaw_model_strategy.py`
- `build_openclaw_model_strategy_config`
- `build_openclaw_model_call_plan`
- `build_openclaw_model_provider_readiness_report`
- `run_openclaw_model_smoke_probe`
- `sanitize_openclaw_model_run_metadata`

CLI discovery:

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c openclaw-model-readiness --json
```

That command checks model-provider config entry names only. It does not read
credential values, load credentials, initialize a model client, call a model
provider, execute tools, invoke OpenClaw, open a database, or write files.

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
  available, and sanitized error code/category.

## Provider Readiness

Model-provider readiness reports required config names only by count and
missing names:

- `PERSONALOS_OPENCLAW_MODEL_PROVIDER`
- `PERSONALOS_OPENCLAW_MODEL_API_KEY`
- `PERSONALOS_OPENCLAW_NEMOTRON_SUPER_MODEL`
- `PERSONALOS_OPENCLAW_GLM_5_2_MODEL`

Reports must not print present config names, credential values, OAuth material,
raw provider responses, full prompts, or environment dumps.

If config names are missing, the smoke probe reports
`openclaw_model_smoke_not_run_missing_provider_config`.

If config names are present but no injected model client exists, the smoke
probe reports `openclaw_model_smoke_not_run_missing_client`.

If a future supervised operator path injects a configured model client, the
smoke probe may make at most one Nemotron Super primary call and one GLM 5.2
fallback call only after primary validation failure. The prompt is a short
constant smoke probe and is not included in the report.

## Non-Goals

This strategy does not:

- add a complex autonomous router;
- construct a provider SDK client;
- call Nemotron Super, GLM 5.2, OpenRouter, or any live provider without a
  separately injected model smoke client;
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
