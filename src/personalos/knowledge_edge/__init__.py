"""Knowledge Edge Daily Intelligence Queue — Personal OS sibling package.

Sibling to ``personalos.state`` per
``docs/knowledge_edge/PHASE0_ARCHITECTURE_DECISIONS.md`` AD-1: Knowledge Edge's
scan orchestrator, engine, and rails must know about each other, which the
network-blind ``state`` package's layering rule ("state.py knows nothing of
rails or briefings") does not allow. This package therefore holds its own
three-layer shape (state -> engine -> orchestrator/rails) instead of nesting
under ``personalos.state``.

Packet 1A (P-KE-1A) implemented the ``state/`` subpackage: persistence and
validation for the Knowledge Edge data model, zero network-capable imports.
Packet 1B (P-KE-1B) adds ``engine/`` (pure deterministic classification/ranking),
``adapters/`` (typed fixture-mode adapter contracts, still zero network-capable
imports), and ``scan_orchestrator.py`` (fixture-mode end-to-end scan wiring).
``dashboard.py``/``cli`` surfacing is Packet 1C; live (network-capable)
``personalos.rails.knowledge_edge.*`` adapters are later, G5-gated packets.
"""

from __future__ import annotations
