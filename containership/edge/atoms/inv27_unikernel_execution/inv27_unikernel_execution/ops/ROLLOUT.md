# Canary / staged rollout / emergency disable (MC-035; C092)

1. **Gate:** `tools/release_gate.py` must return GO for the exact SHA256SUMS digest.
2. **Canary:** 1 site at `environment=staging`, then 1 production site, with 24 h soak per stage.
   Watch `uk_seal_failures_total` by reason. A new reason code, or a rise over 2× baseline, halts
   the rollout.
3. **Staged:** 10% of sites, then 50%, then 100%, each after a green soak.
4. **Rollback:** redeploy the previous release, whose SHA256SUMS is in its RELEASE_MANIFEST.json.
   Config rolls back with `ConfigStore.rollback`.
5. **Emergency disable:** `disable()` on the affected controllers. Running instances continue and
   can be quarantined.

The staged rollout has not been exercised in a fleet (W-DRILLS).
