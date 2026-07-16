"""Knowledge Edge deterministic engine (P-KE-1B).

Every submodule here is a pure-function module: no I/O, no database connection, no
network import, no wall-clock read (mirrors ``docs/ARCHITECTURE.md`` invariant #2,
applied to Knowledge Edge by
``docs/knowledge_edge/PHASE0_ARCHITECTURE_DECISIONS.md`` AD-1). Anything that reads
a clock, opens a connection, or touches the filesystem belongs in
``scan_orchestrator.py`` or the ``adapters/`` package, not here.

- ``canonicalize`` -- amendment §11.2 URL/identifier/alias/timestamp normalization.
- ``directness`` -- amendment §11.3 directness classification + the §8.3 P0/§8.2 P2
  substantive-appearance gate.
- ``matching`` -- the deterministic thesis/topic matching grammar
  (``PHASE0_THESIS_MATCHING.md`` Part 2).
- ``dedup`` -- amendment §11.4 deduplication / canonical-group evidence rules.
- ``ranking`` -- amendment §11.5 deterministic ranking + queue-section/cap
  assignment (the scan-time portion of it; see that module's docstring for the
  1B/1C scope split).
"""

from __future__ import annotations
