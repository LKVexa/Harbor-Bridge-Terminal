# Canary, staged rollout, rollback and emergency disable (C092)

1. **Pre-flight:** exit gate bundle for the exact source digest; config digest recorded; backup of every store.
2. **Canary (1 site, 1 % tenants, 24 h):** watch refusals by code, p99, DLQ growth, audit verify. Abort on any
   `E_CORRUPT`, `E_STORAGE` or `E_SECURITY_DEPENDENCY`.
3. **Staged:** 10 % → 50 % → 100 % of sites, each stage ≥ 24 h with the same abort criteria.
4. **Rollback:** stop the new version (`drain` then `shutdown`), start the previous one on the same stores.
   Store format `inv53.store/1` is unchanged in 5.1.x, so rollback within 5.1.x is data-compatible. A release
   that changes the store schema must ship a tested down-migration or be declared roll-forward-only here.
   Config rollback: `ConfigStore.rollback()`.
5. **Emergency disable:** `broker.emergency_disable(reason=…, actor=…)` refuses every data-plane op with
   `E_FROZEN` while keeping state intact; audited. Re-enable with `emergency_enable`. Per-tenant or per-queue:
   `freeze` / `unfreeze`.

Drill status: the disable/freeze/drain/shutdown/restart sequence is executed by
`test_service.py::BrokerTest::test_freeze_emergency_disable_and_drain` and
`test_graceful_shutdown_then_restart_preserves_state`; a production drill with named operators has not been run.
