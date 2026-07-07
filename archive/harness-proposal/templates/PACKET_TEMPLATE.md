# PACKET_TEMPLATE.md — Personal OS (PROPOSAL, adapted from the MIS harness)

> For consideration, not a mandate. The contract for one unit of work.
> `allowed_paths` / `forbidden_paths` wire the mechanical scope-drift trigger (see RISK_REGISTER).
> This file is in the governance manifest — changes trip the governance gate.

```yaml
packet_id: "<short-stable-id>"          # e.g. PO-01-briefing-composer
title: "<one line>"
tier: "routine"                          # routine | high_stakes (a FLOOR; the risk register may promote)

acceptance_criteria:                     # what the Auditor verifies against (from ROADMAP)
  - "<criterion 1>"
  - "<criterion 2>"

non_goals:                               # explicitly out of scope
  - "<non-goal 1>"

allowed_paths:                           # writes permitted ONLY here
  - "src/personalos/**"
  - "tests/**"

forbidden_paths:                         # writes here → high-stakes scope-drift flag
  - "governance/**"
  - "docs/PRD.md"
  - "docs/ARCHITECTURE.md"
  - "migrations/**"                      # (a migration packet declares this in allowed_paths instead)
  - "src/personalos/gmail*/**"           # <VERIFY> live-rail modules — high blast radius
  - "src/personalos/calendar*/**"        # <VERIFY>
  - "src/personalos/todoist*/**"         # <VERIFY>
  - ".env*"

expected_tests:                          # tests that must exist/pass for this packet
  - "<test path or description>"

rollback_expectation: "<how to undo this packet if merged and wrong>"

definition_of_done: >
  Acceptance criteria met; tests exist for new paths and pass under
  orchestrator-run evidence; STATUS.md and DECISIONS.md updated; change fits
  allowed_paths; no governance file or live-rail module touched; no live rail
  activated (rails stay inert unless a HUMAN_GATES live-rail gate is explicitly
  approved for this packet).
```

## Notes for the author

- **Substance floor.** A packet is a complete, testable feature/module unit — not a file or a
  fragment. Default to the maximum coherent work that fits the scope, not the smallest safe step.
- **`allowed_paths` are proposed in the plan, checked by the Auditor, and frozen at Conductor
  approval.** Any mid-build widening is a **re-plan event, not an edit** — a Builder that moves its
  own fence mid-build has no fence. Keep them as narrow as the work truly needs; a wide
  `allowed_paths` weakens the scope-drift trigger.
- **Touching a `forbidden_path` is usually a signal to split the packet.** Exceptions are declared,
  not sneaked:
  - A **migration packet** legitimately authors migrations — it declares `migrations/**` in
    `allowed_paths`, which auto-sets `tier: high_stakes` and routes the destructive-migration gate.
  - A **live-rail packet** that must modify a Gmail/Calendar/Todoist module declares that module in
    `allowed_paths`, auto-sets `tier: high_stakes`, and requires the live-rail human gate. It still
    must not *activate* the rail unless the activation gate is separately approved.
- **Rails inert by default.** No routine packet may send a real email, write a real calendar event,
  or mutate a real Todoist/production-DB record. That capability is reachable only through an
  explicit, logged human gate.
