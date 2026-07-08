# DECISIONS.md — Personal OS (durable decisions; Builder-owned; reversals per SPEC §16.9)

## Locked
- **D-PO-001 Re-baseline in place.** Keep the code (291 commits); replace the governance
  shape (doc-sprawl narrative process → harness-standard machine-checked gates); findings
  audit seeds the ROADMAP. Neither blind-continue nor restart. — Chris, 2026-07-07
- **D-PO-002 MVP = the live morning loop.** Cadence engine computes today; routine tasks
  → Todoist; 8am briefing → Gmail; unattended after P-SCHED-02. Calendar + midday/evening
  windows post-MVP. Flexibility-as-routines-change is a first-class design requirement;
  zero bias toward incumbent design. — Chris, 2026-07-07
- **D-PO-003 Docs retire freely.** No legacy doc is personally load-bearing; all ~25
  phase/readiness docs + old STATUS archive out in P-GOV-01. SAFETY_POLICY content folded
  into RISK_REGISTER/SECURITY (its posture-flag vocabulary is retired with the readiness
  machinery). — Chris, 2026-07-07
- **D-PO-004 OpenClaw is cut.** Its operator role is filled by the harness + P-SCHED
  scheduler; model calls (if ever) go through a rails adapter. The fitness CSV workflow it
  served stays untouched and out of product scope. Re-entry requires a new G6. — proposed
  by Phase 0 findings §7; Conductor "best proposal wins" (2026-07-07); **ratified by
  approving P-GOV-01**.
- **D-PO-005 Governance authorship seam.** The rulebook is authored by the Fable
  (architect/phase-end) seat + Conductor, audited cross-family by Codex; the production
  Builder (Opus) never authors governance (D-004 circularity principle). Same-family
  caveat (Fable/Opus both Anthropic) is carried openly; the Codex audit + live-loop
  adversarial audits are the designed backstop. — 2026-07-07
- **D-PO-006 `not_ready` is retired as a concept.** Replaced by the per-rail activation
  ladder (`inert | soaking | live`, HUMAN_GATES) with Conductor-gated transitions. The
  three by-construction not-ready mechanisms (Phase 0 §5, §8.5) are deleted with
  P-CLEAN-02 rather than satisfied. — 2026-07-07

- **D-PO-007 Governance lives in-repo (Model B) + templates adopted.** The rulebook is a
  self-contained overlay in this repo (`governance/**` + manifest) because the agent
  build-sandbox receives a git-free export of THIS repo — in-repo law is visible to the
  governed agent with no extra B-00 mounting; the portable doctrine (SPEC/LOOP_DOCTRINE)
  stays harness-side, so there is no rulebook duplication (SPEC §7 overlay split). The
  Conductor's `_harness_proposal/` bundle (archived at `archive/harness-proposal/`)
  recommended harness-side (Model A) as its lean; its two templates were adopted into
  `governance/templates/` and its principles were already convergent with the pack.
  Revisit at B-00 (recorded there as an explicit onboarding question); reversal would be
  a G-GOV migration packet. Also fixes Codex plan-audit F7/F9: approvals =
  `audits/signoffs/**`, Conductor-only, manifest-protected. — 2026-07-07

- **D-PO-008 R1(a) ratification.** The Conductor ratifies the P-GOV-01 sign-off embedded
  in packet commit `02951b5` as his own authorship ("I ratify the P-GOV-01 sign-off
  embedded in 02951b5 as mine" — Chris, 2026-07-07, transcribed by Builder per D-014).
  Context: the Fable phase-A checkpoint (R1) found the sign-off entered the tree inside
  the packet build commit — unavoidable bootstrap circularity, as the sign-off store was
  created by that same packet. With this ratification the Phase A approval trail is
  complete. — 2026-07-07
- **D-PO-009 HI-11/Q-PO-004: B-00 first (Option B).** Phase B is preceded by **B-00**
  (harness repo: production CLI + project onboarding, hand-built + Codex/Fable audited,
  NOT dogfooded per SPEC §11). Rationale: the manual loop spent three audit rounds on
  approval-provenance issues that B-00's OS-permissioned approval store prevents by
  construction (closes checkpoint carry R1(b)); the upcoming product stretch
  (P-DESIGN-01 → P-CORE, migrations + engine) is exactly what the orchestrator should
  mechanically enforce. P-DESIGN-01 starts after B-00 drives its first personal-os
  packet. — Chris, 2026-07-07

## Reversals
(none)
