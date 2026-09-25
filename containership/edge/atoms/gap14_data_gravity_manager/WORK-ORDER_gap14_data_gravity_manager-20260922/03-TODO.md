# 03 — Ordered to-do (dependencies first)

1. Reason-code registry (`errors.py`) — everything else raises through it.
2. Trust primitives: canonical JSON, key ring, strict validators, freshness, replay guard (`trust.py`).
3. Resilience primitives (`resilience.py`).
4. Identity and tenant model (`identity.py`).
5. Estate adapters + PLN-06 handoff (`adapters.py`).
6. Audit sink and verifier (`audit.py`).
7. Signed config manager and knob table (`config.py`).
8. pk_core handshake and gate evaluator (`compat.py`).
9. Observability (`observability.py`).
10. Planner and DAG optimiser (`planner.py`), drift/canary (`modeling.py`).
11. Decision service composing 1–10 (`service.py`), contract update.
12. Wire schemas + validator (`tools/gen_schemas.py`, `schema_check.py`).
13. Signed estate fixtures (`tests/fixtures/estate.py`).
14. Tests: security/adapters, evidence/config/gate, operability, property/fuzz, fault matrix, P2, packaging.
15. Bench, CLI, pyproject, release evidence, SBOM, manifest.
16. Docs: design, operations, runbooks, compatibility, supply chain, owners; README/CHANGELOG/audit report/residual register.
17. Certification manifest (all 1,831 items) + independent sampling review; fix findings.
