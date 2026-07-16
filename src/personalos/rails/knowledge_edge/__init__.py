"""Knowledge Edge live rail adapters (P-KE-2A+, G5).

Sits inside `src/personalos/rails/**` (PHASE0_ARCHITECTURE_DECISIONS AD-2) so it
reuses the manifest's existing network-capable exemption for that glob -- no
GOVERNANCE_MANIFEST.yaml edit is needed to grant these modules network capability.
Every adapter here implements a Protocol from
`personalos.knowledge_edge.adapters.contracts` (the same seam the fixture adapters in
`personalos.knowledge_edge.adapters.fixtures` implement), so
`personalos.knowledge_edge.scan_orchestrator` never has to change when a fixture is
swapped for a live adapter.
"""

from __future__ import annotations
