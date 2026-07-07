# QUALITY_GATES.md — Personal OS

The commands the evidence runner executes (orchestrator once B-00 lands; until then the
Conductor's pinned manual procedure). **Agent-run results are development aids only; the
evidence of record is runner-executed** (command + exit code + output + tested SHA,
`verified_by: orchestrator`).

## Commands (run from repo root, in order; all must exit 0)

```bash
# 1. worktree hygiene
git status --short
git diff --check

# 2. full test suite (canonical)
PYTHONPATH=src python3 -m unittest discover -s tests -p "test_*.py"

# 3. ResourceWarning-sensitive pass
PYTHONTRACEMALLOC=10 PYTHONPATH=src python3 -W always::ResourceWarning -m unittest discover -s tests -p "test_*.py" -q

# 4. artifact hygiene (both must print nothing)
find . -maxdepth 2 -name var -print
find . -path ./.git -prune -o \( -name "*.sqlite" -o -name "*.sqlite3" -o -name "*.db" \) -print

# 5. secret scan (pinned gitleaks 8.30.1 + .gitleaks.toml; must exit 0)
gitleaks detect --no-git --source . --config .gitleaks.toml --exit-code 9

# 6. env hygiene (local env files must be ignored and never tracked)
git check-ignore -q .env.local
test -z "$(git ls-files '.env*' | grep -v '^.env.example$')"
```

Baseline at governance adoption: **809 tests, ~14s** (P-GOV-01 working tree; was 887 on
main @ 58fc27e — the −78 delta is the sanctioned P-GOV-01 retirement of the doc-phrase
test class: 10 `test_*_docs.py` files + 19 embedded doc-phrase methods (17 test_docs_* + 2 README-link), enumerated in
the P-GOV-01 audit trail). A packet that reduces the passing count without a
ROADMAP-sanctioned, audit-verified delta is a test-weakening event (RISK_REGISTER).

## Test-integrity rules
- Never delete or disable a test (`skip`, `expectedFailure`, commenting out, assertion
  removal, narrowed discovery pattern) to make a packet pass → high-stakes / G-GOV trigger.
- Exception: **P-CLEAN-02 deletes the phase-14C process modules and their remaining tests
  together** — sanctioned in the ROADMAP with an explicit expected test-count delta; the
  audit verifies deletions match the sanctioned module list exactly and product-module
  tests are untouched.
- New code paths require tests in the same packet (Definition of Done, AGENTS.md).
- The doc-phrase test class was retired by **P-GOV-01** (the 887 → 809 delta above);
  no new tests may assert prose phrasing of documentation.

## Network rule
The suite must run with the network unreachable. Any test that opens a socket to a real
service is a defect. (Live-rail adapters are tested against fakes; live verification happens
only inside G5-gated activation packets, never in the suite.)
