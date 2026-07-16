"""Knowledge Edge adapter contracts + fixture implementations (P-KE-1B).

``contracts.py`` defines the typed interfaces (the AD-1 seam between the engine/
orchestrator and future ``rails/knowledge_edge/**`` live adapters, Phase 2/3).
``fixtures.py`` is this packet's only implementation of those contracts: no
network-capable import exists anywhere in this package, and none may be added to
it -- live implementations belong in ``rails/knowledge_edge/**`` under their own
G5-gated packets.
"""

from __future__ import annotations
