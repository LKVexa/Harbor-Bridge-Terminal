# Canary / staged rollout plan  (component 92)
1. **Gate:** `tools/gen_evidence.py` exit-gate must not be NO_GO for the target profile; benchmark gate green.
2. **Stage 0 – shadow:** new version reads, does not serve; compare `health()` and metrics.
3. **Stage 1 – canary 5 %** of tenants (by tenant id hash) for ≥ 1 h. Abort if: error rate of terminal codes +0.5 pp, p99 append > threshold, any `INV54-E0501/E0503/E1001`, any stall.
4. **Stage 2 – 25 %**, **Stage 3 – 100 %**, each ≥ 1 h with the same abort criteria.
5. **Rollback:** drain canary nodes (`BrokerService.drain`), revert package, `ConfigStore.rollback()` if config changed; storage format is unchanged in 4.3.x so rollback is data-compatible.
Executable automation of these stages against a real fleet: **UNVERIFIED** (no deployment target).
