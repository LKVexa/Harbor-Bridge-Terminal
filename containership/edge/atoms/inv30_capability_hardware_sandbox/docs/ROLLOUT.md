# Canary, staged rollout, rollback, emergency disable (INV30-GAP-062 · INV-30-C092)

Tooling: `python -m pk_components.inv30_capability_hardware_sandbox.ops {status|promote|rollback|disable|enable}`.

| Stage | % | Minimum soak | Promote gate (all required) |
|---|---|---|---|
| canary | 1 | 1 h | error_rate_ok, latency_ok, invariant_violations_zero |
| canary | 5 | 4 h | same |
| staged | 25 | 24 h | same + no SEV2 open |
| staged | 50 | 24 h | same |
| full | 100 | — | — |

* `promote` refuses on any red gate and records the refusal in the rollout audit ledger.
* **Rollback:** `ops rollback` → previous stage; config rollback via ConfigStore; artifact rollback = redeploy
  previous signed release (evidence dir kept).
* **Emergency disable:** `ops disable --reason …` → rollout 0 %, service `disabled` state revokes all capabilities;
  re-enable only after incident review (`ops enable`).
* Exercised by `tests/test_ops.py`; must also be exercised against each release candidate (exit gate item).
