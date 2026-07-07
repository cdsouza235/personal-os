# Personal OS

Chris's private, local-first routine / priority / briefing OS with gated live rails into
his real Todoist, Google Calendar, and Gmail. SQLite state, stdlib-only Python, built in
audited packets under the MIS harness doctrine.

## Start here

| What | Where |
|---|---|
| Current state (the resume point) | [governance/living/agent-writable/STATUS.md](governance/living/agent-writable/STATUS.md) |
| Agent rules | [AGENTS.md](AGENTS.md) |
| Product spec | [docs/PRD.md](docs/PRD.md) · [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| The plan (packets) | [governance/ROADMAP.md](governance/ROADMAP.md) |
| Gates, risks, security, runbook | [governance/](governance/) — governed by [GOVERNANCE_MANIFEST.yaml](GOVERNANCE_MANIFEST.yaml) |
| Decisions / open questions | [governance/living/agent-writable/](governance/living/agent-writable/) |
| Audit trail | [audits/](audits/) (briefs, prompts/reports, sign-offs, Phase 0 findings) |

## Rollback quick-ref
Packets merge `--no-ff`; undo = `git revert -m 1 <merge-commit>` through a normal audited
packet. Live-rail kill procedures: [governance/RUNBOOK.md](governance/RUNBOOK.md).

## Validation
The canonical commands (tests, hygiene, secret scan) are pinned in
[governance/QUALITY_GATES.md](governance/QUALITY_GATES.md).

Historical docs (pre re-baseline, 2026-07): [docs/archive/](docs/archive/) and
[archive/](archive/). They are records, not rules.
