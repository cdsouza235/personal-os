"""Network-capable rail adapters (GOVERNANCE_MANIFEST.yaml protected path, G5).

Every module in this package may import network primitives (urllib, etc). Nothing
in this package's public API performs a real external write on its own: each
adapter's orchestrating function enforces permission -> ledger/dedupe -> rail-state
-> credentials (docs/ARCHITECTURE.md invariant #3) before ever constructing a live
client, and every rail currently sits at RAIL_STATES[...] == "inert"
(src/personalos/status.py), so the rail-state gate fails closed by default.
"""

from __future__ import annotations
