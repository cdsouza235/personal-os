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
- `sanitize_openclaw_model_run_metadata`

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

## Non-Goals

This strategy does not:

- add a complex autonomous router;
- call Nemotron Super, GLM 5.2, OpenRouter, or any live provider;
- inspect, print, copy, or store credentials;
- broaden OpenClaw runtime handoff;
- activate scheduler/background behavior;
- activate production DB;
- access protected paths.

## Validation Coverage

`tests/test_openclaw_model_strategy.py` verifies the alias map, smoke and
reasoning lane primary/fallback choices, configurable provider hints, routing
constraints, max call counts, output-token caps, and safe metadata
sanitization.
