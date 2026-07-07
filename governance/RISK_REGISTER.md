# RISK_REGISTER.md — Personal OS

Deterministic risk triggers. **Fail toward high-stakes: any path matching no rule, unknown
extension, or new top-level directory PROMOTES — never defaults routine.** The digest shows
coverage (`scanned_clean` vs `unmatched`), not just hits.

## Path triggers

| Pattern | Trigger | Effect |
|---|---|---|
| `migrations/**` | schema/data-model | high-stakes; destructive DDL → +G4 |
| `.env*`, anything credential-shaped | secrets | G3 |
| `src/personalos/rails/**` (future), the six network-capable modules named in GOVERNANCE_MANIFEST | live-rail code | G5 + high-stakes |
| `src/personalos/permissions.py`, `src/personalos/path_safety.py` | safety substrate | high-stakes |
| `src/personalos/side_effects.py`, `src/personalos/idempotency.py` | ledger semantics | high-stakes |
| `src/personalos/db/**` | connection/migration machinery | high-stakes |
| `governance/**` (excl. `living/`), `GOVERNANCE_MANIFEST.yaml`, `AGENTS.md`, `docs/PRD.md`, `docs/ARCHITECTURE.md`, `audits/*BRIEF*`, `audits/test-strategy.md` | rulebook | G-GOV |
| `pyproject.toml`, any lockfile | dependency | G7 + high-stakes |
| `scripts/**` | host-touching | high-stakes |
| deleted files / destructive commands | irreversibility | G4 |
| tests deleted/disabled, assertions removed, discovery pattern changed | test-weakening | high-stakes / G-GOV |
| `audits/signoffs/**` written by ANY agent | forged approval | blocker — stop, void the file, Conductor review |
| new top-level dir, unknown extension, unmatched path | unknown | high-stakes (fail-toward-safety) |
| write outside packet `allowed_paths` or into `forbidden_paths` | scope drift | high-stakes |

## Content triggers
- Secret-like content (key/token patterns, gitleaks ruleset + `TODOIST_`, `OPENROUTER_`,
  Gmail app-password shapes, `sk-or-`, SMTP credentials) in any diff or log → G3, digest
  blocked until sanitized.
- Any occurrence of a real personal path (`/Users/coldstake/PersonalOS`,
  `/Users/coldstake/.openclaw`) in new code outside SECURITY.md's deny-list definitions →
  high-stakes.
- Network primitives (`smtplib`, `urllib.request`, `http.client`, `socket`, `requests`)
  imported by any module NOT already on the manifest's network-capable list → G5 +
  high-stakes. This is the "new rail" tripwire.

## Standing risk notes (folded from SAFETY_POLICY v0.2)
1. **Live rails reach Chris's real accounts** (Gmail, Todoist, Google Calendar). Blast
   radius of a bad send/write is personal-reputational, not just technical. All four rails
   have run live exactly once (2026-06-30/07-01 bounded smokes); the wiring is proven
   live-capable. Treat "inert" as a current posture, not an assumption.
2. **High-stakes domains** (legal, tax, medical, investments, relationship/family messages,
   large financial commitments) are never auto-executed; composer/task output touching them
   is approval-required at the permission layer, independent of any gate here.
3. **Protected systems** (never in scope without an exact-scope Conductor approval):
   `/Users/coldstake/PersonalOS`, `/Users/coldstake/.openclaw`, credential stores, production
   SQLite paths, production ledgers, LaunchAgents, crontab, daemons.
4. **Scheduler/background activation** (launchd, crontab, daemons) is a G4+G5 event — it
   makes the system act while unattended, which multiplies every other risk.
5. **The permission model is only a boundary if there is one evaluator.** The 12-fold
   duplicated evaluator (Phase 0 finding) is a standing risk until P-DEBT-01 unifies it;
   until then, any packet touching permission logic in ANY module is high-stakes.
