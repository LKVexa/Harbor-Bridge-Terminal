# Rollout / rollback / drain / emergency disable (M33)

1. `RolloutController.start(change_id)`; stages 1→5→25→50→100 % by stable link hash bucket; ≥100 requests and bake time per stage.
2. Error ratio > 1 % at any stage ⇒ automatic rollback (config: `ConfigHistory.rollback`, new revision equal to last good).
3. Drain: `service.drain()` — no new calls, in-flight finish, then stop.
4. Emergency disable: two distinct authenticated operators → `service.disable([...], reason)`; audited as `provider.emergency_disable`. Re-enable = lifecycle `disabled → ready` after incident review.
Exercised only against local durable state in `tests/integration/test_rollout.py`; **not yet against production-like state**.
