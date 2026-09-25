# 06 — Ledger entry to record when the yard is connected

```bash
ledger log-job --job "gap14_data_gravity_manager overhaul" \
  --parts "none (build-new, stdlib only)" \
  --outcome "v4.3.0: estate-integrated decision service over signed GAP-13/GAP-03/GAP-05/SCH-01 inputs, PLN-06 idempotent handoff, identity, provenance, hash-chained audit, signed config, resilience, observability, P2 planner; 170 tests; 1,831-item certification manifest (NO-GO pending live estate, pk_core, signing, owners)" \
  --notes "work order WORK-ORDER_gap14_data_gravity_manager-20260922 (degraded: yard unreachable, no ledger/map/RCG); build-new: signed-artifact trust ring, hash-chained audit, circuit breaker + admission, stdlib json-schema subset validator, Page-Hinkley drift (searched: none — yard not searchable this session)"
```
