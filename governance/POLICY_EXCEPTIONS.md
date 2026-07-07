# POLICY_EXCEPTIONS.md — Personal OS

Exceptions to any rule in the governance kit live HERE, never in chat. An exception not
recorded in this file does not exist. Chat-borne approvals are void.

Format per entry:

```
## E-NNN <title>
- scope: <exact files/actions covered>
- reason: <why the rule is suspended>
- approved_by: Chris
- approved_on: <date>
- expires: <date or condition — mandatory; no open-ended exceptions>
- compensating_controls: <what holds the line meanwhile>
```

## Active exceptions

### E-001 Manual loop until B-00
- scope: packets are driven by the manual loop (Conductor performs git ops, evidence
  capture per QUALITY_GATES, approval sign-off files in `audits/`) instead of the MIS
  orchestrator.
- reason: the harness's production CLI / project onboarding (B-00) is not yet built; the
  audit + governance discipline applies now, the mechanical enforcement arrives with B-00.
- approved_by: Chris (kickoff, 2026-07-07)
- expires: when B-00 merges and the orchestrator drives its first personal-os packet.
- compensating_controls: pinned manual procedure — governance-diff check against
  GOVERNANCE_MANIFEST on every packet; Conductor-run quality gates committed to `audits/`;
  Codex machine-invoked per-packet audit; sign-off files at
  `audits/signoffs/<packet>-<gate>-signoff.md` authored+committed by the Conductor ONLY
  (manifest-protected path; agent write there = blocker; non-Conductor git author = void);
  single-writer file ownership (AGENTS.md).

### E-002 SPEC §7 kit artifacts deliberately not instantiated in this repo
- scope: `LOOP_DOCTRINE.md`, `HARNESS_CONFIG.yaml`, `living/orchestrator-only/**`
  (BUDGET_LEDGER, LOOP_STATE, METRICS), planning-record template.
- reason: these are harness-side artifacts, not project-overlay artifacts (D-PO-007
  in-repo split): the doctrine lives in the harness repo (`SPEC-v0.4.md` §16 +
  `LOOP_DOCTRINE.md`); machine config + orchestrator-only state are created by **B-00**
  when the orchestrator first drives this repo (it, not an agent, owns them). The
  planning record for this project is the committed P-GOV-01 pack itself
  (`governance/ROADMAP.md` + `audits/test-strategy.md` + `audits/human-input-manifest.md`
  + the Codex plan-audit trail).
- approved_by: Chris — **pending, rides with the P-GOV-01 sign-off (HI-01)**
- expires: B-00 merge (config + orchestrator-only state) — at which point this exception
  is replaced by the real artifacts and the manifest is amended (G-GOV).
- compensating_controls: E-001's manual procedure; the RISK_REGISTER path/content
  triggers are the interim machine-readable scan config.

(no other active exceptions)
