# Constraint precedence (INV-38-C019)

Strict lattice SECURITY > ISOLATION > RESIDENCY > CORRECTNESS > AVAILABILITY >
PERFORMANCE > COST. Source: `precedence.py`; policy: `policy/constraint-precedence.yaml`.
Security/DMA isolation override latency/throughput unless an approved exception
exists; kernel fallback may not cross a residency boundary merely for
availability; SLO conflicts never silently relax a safety limit. Emergency
overrides are time-bounded, authorized and audited. Decision-table tests
(`tests/test_precedence.py`) prove deterministic ordering. **Status:** `DONE`.
