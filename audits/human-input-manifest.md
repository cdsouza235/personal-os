# Human-Input Manifest — Personal OS re-baseline (SPEC §16.2 artifact 2)

Every point where only the Conductor can provide an input. Sensitive values are referenced
by NAME only and go into the environment/keychain, never through agent hands; each is
verified when provided (a wrong token fails worse than a missing one — verification =
name-present preflight + the activation packet's bounded live probe).

| ID | What | Consumed by | Delivery | Status |
|---|---|---|---|---|
| HI-01 | Approval of the governance pack (this packet, P-GOV-01) | Phase A | sign-off file in `audits/` | **requested** |
| HI-02 | Ratification of D-PO-004 (OpenClaw cut) — rides with HI-01 | ROADMAP | DECISIONS.md | **requested** |
| HI-03 | Per-module keep/delete calls on orphans (fitness, reports, runtime_bootstrap, completion) | P-DEBT-03 | gate decision | **provided** (D-PO-012, 2026-07-10: delete fitness/reports/completion; runtime_bootstrap excluded, actually in use) |
| HI-04 | Routine model sign-off: confirm PRD §3.1 cadence/missed-behavior semantics match how you actually live (esp. GTG rotation + weekly targets) | P-DESIGN-01 (G6) | gate decision | pending |
| HI-05 | Seed routine list confirmation (names, cadences, windows) | P-CORE-03 | state seed review | pending |
| HI-06 | `TODOIST_API_TOKEN` present in env (name-only) | P-RAIL-TD-02 | env/keychain | pending |
| HI-07 | Gmail app password + sender + controlled recipient (names only) | P-RAIL-GM-02 | env/keychain | pending |
| HI-08 | Briefing quality judgment on soak artifacts (Q-PO-003) | P-BRIEF-01→GM-02 | gate decision | pending |
| HI-09 | Production DB location + backup destination | P-SCHED-02 G0 | gate decision | **provided** (D-PO-011, 2026-07-10: `/Users/coldstake/PersonalOS/personal_os.db`, SQLite Online Backup API) |
| HI-10 | Mac Mini launchd authorization (unattended execution) | P-SCHED-02 | G4+G5 sign-off | pending |
| HI-11 | B-00 sequencing decision (Q-PO-004) | after Phase A | direction | pending |
| HI-12 | Google Calendar credential/connector choice | P-RAIL-CAL (post-MVP) | gate decision | **provided** (D-PO-013, 2026-07-13: OAuth identity = sandboxed `cdsouza.bot@gmail.com`; target calendar = Chris's personal calendar via sharing; four `PERSONALOS_RAIL_CALENDAR_*` env vars confirmed set on the Mac Mini) |

No packet may consume an input whose status is not **provided/verified**. Requesting an
input early is fine; building against an unprovided input is not.
