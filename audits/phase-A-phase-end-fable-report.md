# Phase-A Phase-End Report — Fable

Packet scope: Phase A (P-GOV-01 `229f974` · P-CLEAN-01 `1772f40` · P-CLEAN-02 `d5bc829`)
Date: 2026-07-07 · Reviewed at: `main` @ `8cdf6d0` · Auditor: Fable (phase-end seat, fresh
session — this session did not build Phase A)

## VERDICT: sign_off

The clean state is real. Deletions match the sanction lists exactly, the product runs
end-to-end post-surgery on a scratch DB, the rail-state surface held against every tamper
probe I derived, no readiness/process import survives outside `archive/`, the governance
kit is the only rulebook, and the whole-phase attestation is clean. One judgment item is
surfaced for Conductor ratification (§4, R1 — sign-off provenance), and four located
recommendations are handed to Phase B. None of them falsify the phase guarantee, which is
why this is a sign_off with named follow-ups rather than a hold.

All evidence below is auditor-run (development aid, not evidence of record) — reproduced
in-session per the standing brief; nothing was taken from Builder claims.

---

## 1. Drive the real thing (charge 1) — PASS

Scratch DB built via `personalos.db.apply_migrations` (14 migrations) under `/private/tmp`
(path_safety-sanctioned), seeded through `state.py` core APIs only (2 routines, 1 priority,
1 project, 1 follow-up — synthetic data).

- `workflows` — catalog shows ONLY product commands; help text matches the retired-layer
  claim. Top-level CLI: `workflows demo status today briefing synthesis side-effects
  dashboard scheduler`. No phase14/readiness subcommand anywhere.
- `status --db` — renders counts (matched the seed exactly), permission settings, rail
  states (all inert / scheduler off), `access=read_only_status`. Read-only is mechanical:
  `_connect_read_only` opens `file:...?mode=ro` (cli.py:1064).
- `today --db --date 2026-07-07` — renders, rail states present.
- `dashboard render` — HTML written; contains `Personal OS rails: all inert` headline;
  the render path RAISES on missing/malformed `rail_state_summary` (dashboard.py:95–100),
  as the Codex F1 fix promised.
- `briefing preview` — **fails closed correctly** without permissions: blocked on
  `briefing_loop_dev_test_write`, then `briefing_loop_dev_test_run`, each with a ledgered
  refusal shape and `no_send_mode: true`. After granting via
  `state.upsert_permission_setting` + seeding a `briefing_windows` row: `status: generated`,
  briefing_output_id produced, exit 0.
- `demo no-send-e2e` — exit 0; all 18 artifacts under `--output-dir`;
  `safety_assertions.json` all-pass (no rail touched, no daemon, no crontab, no
  launch-agent, no protected path).

Quality gates re-run in-session at `8cdf6d0`: suite 421 OK (12.3s), ResourceWarning pass
421 OK, artifact hygiene clean, gitleaks clean (8.57 MB), env hygiene clean, worktree
clean before and after this review (my probes wrote nothing into the repo).

## 2. Rail-state surface attack (charge 2) — HOLDS; boundary stated precisely

Probes run in-session against `src/personalos/status.py`, each with a positive control
(P7: the untampered source loads and reports inert in the same harness):

| Probe | Result |
|---|---|
| P1 item assignment on public `RAIL_STATES` | TypeError (immutability real) |
| P2 rebind `status.RAIL_STATES` to all-live | report unaffected — reads privates |
| P3 private-dict tamper to a LEGAL value (`todoist: live`) | report says live, `any_rail_live: true` |
| P4 private-dict tamper to an ILLEGAL value | `RailStateError`, no report |
| P5 private scheduler tamper legal/illegal | legal reported / illegal refused |
| P6 import-time gate (tampered source exec'd in fresh namespace) | `RailStateError` at load — every consumer refuses to start |
| P7 positive control | clean source loads, reports inert |

`RailStateError` subclasses `ValueError` and the CLI dispatcher catches `ValueError`
(cli.py:427) — but converts it to `error: ...` + exit 1, i.e. it fails closed, never
renders a report. Consumer sweep: every producer of a `rail_states`/`rail_state_summary`
value in `src/**` calls `create_rail_state_report()` (cli.py:444,480,1016; today.py:105;
status.py:138; demo/no_send_e2e.py:288); no consumer path constructs posture by hand.

**The precise boundary (P3/P5):** the guard is a *vocabulary* check, not an
*authorization* check. It stops illegal labels; it cannot stop an in-process transition to
a legal value. The module docstring declares exactly this residual (host-level tampering),
so it is documented, not hidden — but Phase D reviewers must remember that nothing in
`status.py` authorizes transitions; only the G5 packet discipline does. There is currently
zero code that could consume a spoofed `live` (no `rails/**`, zero network-capable imports
in `src/**` — verified by grep), so the residual has no blast radius in Phase A.

**What both prior seats missed (found, latent, not exploitable today):**
`_with_workflow_context` merges workflow results with
`enriched.setdefault("rail_states", create_rail_state_report())` (cli.py:1016) — a
pre-existing `rail_states` key in any workflow result dict takes precedence over the
authoritative source, and the human formatter `_append_rail_state_lines` (cli.py:1479)
renders whatever strings it is handed, degrading silently to `Scheduler: unavailable`.
Codex's r2 residual covered only *direct* calls to the private formatter; the setdefault
precedence means an ordinary first-party handler that spreads a stored/parsed dict into its
result would spoof posture with no forged call. I verified no current workflow result
carries data-derived top-level keys (all `**result` spreads at cli.py:634–969 have
code-defined keys), so today this is unreachable — see R2.

## 3. Survivors and casualties (charge 3) — CLEAN

- **Casualty fidelity:** `git diff --name-status 58fc27e..main` shows exactly 32 deleted
  `src/personalos/` modules — all `phase14c_*` (21), `phase14_*` (2), plus
  `mvp_readiness`, `nonhuman_closure`, `weekend_test_readiness`, `dry_run_evidence`,
  `final_nonhuman_handoff`, `openclaw_model_strategy`, `openrouter_model_smoke_client`,
  `pre_live_readiness`, `operator_status`. 37 deleted test files = 10 doc-phrase
  (P-GOV-01) + 27 process-module (P-CLEAN-02). Counts match both declared deltas
  (887→809→421).
- **No enforcement died:** at baseline `58fc27e`, kept modules imported ONLY the two
  report creators (`create_default_pre_live_readiness_report`,
  `create_operator_status_report`) from the deleted set; `phase14c_safety_utils` had zero
  kept-module importers. Only asserting/reporting code died, as claimed.
- **Correct survivors:** all remaining OpenClaw/OpenRouter references are *protective*
  (path_safety deny-lists, runtime_bootstrap refusals, tests asserting protection).
  `execution_rails.py` (shared validation/approval vocabulary used by 7 kept modules) is
  product substrate, correctly kept — see R3. `serve_today_dashboard` survived as a
  wired-nowhere localhost server (no CLI or test caller; bind host validated against
  `{localhost, 127.0.0.1, ::1}`) — see R4.
- **No remnants:** grep for process vocabulary across `src tests docs scripts` root files
  (excluding archives) is empty; `scripts/` contains no tracked files; migrations untouched
  across the whole phase (empty diff — P-CLEAN forbidden path held).
- Cosmetic residue only: demo artifact/variable still named `status_readiness_report`,
  demo help still says "Phase 13E-D", and the demo's human completion banner renders
  "unknown / unavailable" (the JSON artifacts are complete and correct) — see R2/R5.

## 4. Audit trail (charge 4) — VERIFIED, one provenance item surfaced

- `audits/AUDIT-LOG.md`: 8 rows — P-GOV-01 rework → adopt_with_fixes → conditions_closed;
  P-CLEAN-01 accept; P-CLEAN-02 reject ×3 → accept. Matches the checkpoint prompt's
  description. (The r3 reject row was appended retroactively by Codex in r4, self-described
  in its report — acceptable, count-based.)
- Merge commits reference the right gates (`HI-01`, `G4/G1`, `G4/G-GOV/G1`), all `--no-ff`.
- Three sign-off records exist at `audits/signoffs/`, contents match packets and gates.

**R1 — sign-off provenance is currently unverifiable in principle (the §9 find of this
review).** HUMAN_GATES voids any approval "whose git author is not the Conductor," but
every one of the last 17 commits — Builder packet commits and Conductor sign-off commits
alike — carries the identical identity `Chris D'Souza <you@example.com>` (a placeholder
email). The authorship test has zero distinguishing power. Concretely: the P-GOV-01
sign-off record entered the tree **inside the packet build commit itself** (`02951b5`),
the same class Codex's B1 caught and remediated for P-CLEAN-01 — but this earlier instance
was never remediated (bootstrap context: the sign-off store was *defined by* that same
packet, so some circularity was unavoidable). This is doctrine-as-implementation: the
unforgeable-store rule exists as prose; the mechanism (git authorship) cannot enforce it.
Asked of the Conductor: (a) one-line ratification that `02951b5`'s embedded sign-off is
his, recorded in DECISIONS.md; (b) before Phase B gates rely on the store, either commit
sign-offs under a distinct git identity or land B-00's OS-permissioned store.

## 5. Attestation (charge 5) — CLEAN

Over `git diff 58fc27e..main` (193 files, +6,490/−37,232): every manifest-listed file that
changed was created by P-GOV-01 under its sanctioned allowed_paths; the ONLY
manifest-listed file changed after `02951b5` is `GOVERNANCE_MANIFEST.yaml`, and its diff is
exactly the sanctioned P-CLEAN-02 shrink (six dead smoke modules out, `status.py` in).
Manifest closure: every listed file exists. Per-packet forbidden paths held: P-GOV-01
touched no `src/**`/`migrations/**`; P-CLEAN-02 commits touched no `migrations/**` or
`governance/**` (excl. living). One STATUS, root STATUS.md archived; `archive/pr-audits`
holds 33 files (32 PR audits + kickoff prompt); `docs/archive` holds 30; zero runtime
dependencies in pyproject. Minor note: the P-CLEAN-01 packet commit `61a3703` also wrote
STATUS.md and the audit prompt — outside its literal `allowed_paths` but these are the
Builder's designated single-writer living files (AGENTS.md D-014); no rule text reconciles
this tension — worth one clarifying line in a future G-GOV edit.

## Recommendations handed to Phase B (located, non-blocking)

- **R1** (above) — Conductor ratification + distinguishable sign-off identity. The one
  item that should land before Phase B gates rely on the store.
- **R2** — `cli.py:1016`: change `enriched.setdefault("rail_states", ...)` to an
  unconditional set (the authoritative report should never lose to a passed-in key), and
  make `_append_rail_state_lines` (cli.py:1479) validate shape instead of degrading to
  `unavailable` — the same silent-degradation class Codex made the dashboard raise on.
- **R3** — RISK_REGISTER's network-primitive tripwire enumerates `smtplib, urllib.request,
  http.client, socket, requests` but omits `http.server`/`socketserver` (and `asyncio`
  streams, `ftplib`, `xmlrpc`). `dashboard.py` already imports `ThreadingHTTPServer`
  (localhost-validated, wired to nothing). P-CORE-03 works in exactly this file — widen the
  tripwire wording, and consider whether `execution_rails.py` (ApprovalMode/dedupe
  semantics consumed by 7 modules) belongs in the deterministic path-trigger table rather
  than only under standing note 5.
- **R4** — decide `serve_today_dashboard`'s fate in P-CORE-03: wire it or delete it; a
  wired-nowhere server with a synthesis-import POST handler is exactly the "wired-nowhere
  safety helper" class this seat exists to flag, even localhost-bound.
- **R5** — housekeeping riding the next sanctioned G-GOV edit: QUALITY_GATES baseline line
  still reads 809 (actual 421 — declared carry in STATUS); rename the demo's
  `status_readiness_report` artifact/vocabulary; fix the demo human banner.

## WAYS_THIS_REVIEW_COULD_BE_WRONG

- **Same-family caveat (mandatory):** the Builder and I are both Anthropic — and in this
  project the governance kit itself was authored by a Fable seat, so I am reviewing
  same-family prose with same-family priors. The blind-spot classes I hunted (setdefault
  precedence, tripwire wording, provenance circularity) are the ones an Anthropic reasoner
  *can* see; the one we share by construction is the one this report misses.
- My tamper probes ran in-process in one Python; cross-process, harness-level, or
  filesystem-race tampering of `status.py` consumers was not exercised (documented as the
  host-level residual, but "documented" is not "tested").
- Sanction-list fidelity was checked against the ROADMAP text read the same way the
  Builder read it. `pre_live_readiness`/`operator_status` deletion is sanctioned only
  implicitly (the "replaces … consumption" clause); if that reading is wrong, Codex and I
  are wrong together.
- The CLI drive used synthetic seed data and granted permissions through the same core
  APIs the product trusts; a real-shaped DB (or a corrupted one) could exercise different
  paths. Briefing preview was proven for one window/date only.
- Provenance conclusions (R1) rest on git metadata that any same-machine actor could have
  rewritten; I treated commit graph shape as honest.
- All evidence here is auditor-run; the evidence of record is runner-executed
  (QUALITY_GATES doctrine). If the runner disagrees with my in-session results, the runner
  wins.

## Attestations

- No GOVERNANCE_MANIFEST-listed file changed beyond each packet's sanction across
  `58fc27e..main` (verified by set intersection, §5).
- I wrote ONLY this file (`audits/phase-A-phase-end-fable-report.md`). I did not touch
  STATUS/DECISIONS/ROADMAP, Codex's files, or `audits/signoffs/**`; I ran no git write
  command; the worktree was clean before and after this review except this report.
- No credential value was read; no external service contacted; no live-capable path
  executed; scratch artifacts confined to the session scratchpad outside the repo.
