
<!-- WATCH_TOWER_BUILDER_PROTOCOL v1 -->

## Watch Tower Builder Protocol

This repository participates in the Watch Tower puck-tracking workflow.

At the end of any bounded builder work packet, leave the project in a legible state.

Required final artifacts:

1. Update or create `.agent/status.yaml`.
2. Create a final report under `.agent/runs/`.
3. Produce a `WATCH_TOWER_HANDOFF.md` in the final response, or write it to `.agent/outbox/WATCH_TOWER_HANDOFF.md`.

The handoff must start with this front matter:

---
event_type: handoff
project_id: short_snake_case_id
project_name: Human Readable Project Name
source_agent: codex_or_claude_code
puck_with: one_allowed_value
next_action: "One concrete next action."
human_attention: none
---

Allowed `puck_with` values:

- me
- chatgpt
- claude
- codex
- claude_code
- openclaw
- none

Allowed `human_attention` values:

- none
- dispatch_only
- decision_required
- approval_required
- unblock_required
- review_required

Rules:

- Set `puck_with` to the actual next owner of the project action.
- Use `puck_with: me` only when the user must make a real decision, approve something, unblock something, or personally do the next action.
- If the user only needs to carry a packet to another tool, set `puck_with` to that destination tool and use `human_attention: dispatch_only`.
- Use `puck_with: none` only when the project has no next action or is complete.
- Do not directly ingest into Watch Tower unless explicitly authorized.
- Do not inspect unrelated folders.
- Do not access credentials, secrets, OAuth tokens, API keys, or protected paths.
- Do not activate live external writes.
- Do not touch production databases.
- Do not activate schedulers, daemons, LaunchAgents, crontabs, background loops, or automations.

Final report must include:

- scope completed
- files changed
- validation results
- safety assertions
- deviations
- open questions
- next recommended owner
- next recommended action

<!-- /WATCH_TOWER_BUILDER_PROTOCOL v1 -->
