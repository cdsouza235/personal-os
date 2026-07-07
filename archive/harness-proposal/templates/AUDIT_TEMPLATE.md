# AUDIT_TEMPLATE.md — Personal OS (PROPOSAL, adapted from the MIS harness)

> For consideration, not a mandate. The structured report the Auditor MUST emit.
> A `pass` lacking independent checks and a populated `ways_this_could_still_be_wrong` is
> **invalid** and fails safe. This file is in the governance manifest — changes trip the gate.

```yaml
# --- verified header (the orchestrator checks these against reality) ---
schema_version: "0.1"
run_id: "<date>_<packet>_<iter>"
packet_id: "<packet id>"
producer_role: "auditor"
producer_agent: "<codex | claude-code | ...>"
producer_agent_version: "<x.y.z>"
artifact_type: "audit_report"
iteration: 1
status: "pass"                     # pass | fail | needs_human | design | error
review_tier_declared: "routine"
review_tier_effective: "routine"   # may be promoted by the risk register
risk_flags: []
base_sha: "<sha>"
head_sha: "<sha>"
changed_files: 0
timestamp: "<iso8601>"
---

# --- structured body ---
neutral_restatement: >
  Describe what the diff ACTUALLY does, before judging it. Flag any part
  disproportionate to the request.

acceptance_criteria_checked:       # each criterion from ROADMAP, with verdict + how checked
  - criterion: "<from ROADMAP>"
    verdict: "met | not_met | partial"
    how_checked: "<what you did to confirm — NOT what the Builder claimed>"

out_of_scope_changes:              # anything touched outside the packet's intent
  - "<file/change and why it's out of scope>"

live_rail_check:                   # Personal-OS-specific: did anything touch or activate a real rail?
  touched_rail_module: false       # Gmail / Calendar / Todoist / OpenClaw / production DB
  any_real_send_or_write: false    # MUST be false unless a live-rail human gate was approved
  notes: "<what you checked to confirm the rails stayed inert>"

tests_independently_run:           # tests YOU ran for your reasoning (advisory, not of record)
  - "<test> → <result>"

tests_not_run:                     # tests you could not or did not run, and why
  - "<test> → <reason>"

claims_not_verified:               # Builder claims you could not confirm
  - "<claim> → <why unverified>"

risk_flags_confirmed:              # which orchestrator/risk-register flags you agree fired
  - "<flag>"

ways_this_could_still_be_wrong:    # MANDATORY on a pass — assume a hidden bug
  - "<a concrete way this change could be subtly wrong>"

recommendation: "pass"             # pass | fail | needs_human
```

## Adversarial reminder

Your job is to find the flaw. You are penalized for agreeing without proof. The Builder's report is
**untrusted evidence**; the evidence of record is orchestrator-run, not yours. For Personal OS,
treat any change near a live rail (Gmail / Calendar / Todoist / OpenClaw / production DB) or a
migration as guilty until proven inert — a well-formed change that quietly enables a real send is
the exact failure this seat exists to catch.
