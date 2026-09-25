# Canary, staged rollout, rollback and emergency disable — INV-42 (MC-036)

## Stages

| Stage | Share of fleet | Minimum soak |
|---|---|---|
| 0: canary | 1% (one host) | 30 min |
| 1 | 10% | 2 h |
| 2 | 50% | 6 h |
| 3 | 100% | — |

Promotion is decided by `tools/rollout.py evaluate --baseline base.prom --canary canary.prom`, which compares Prometheus exports from `telemetry.Metrics.prometheus()`. It exits with:

- `0` to **promote**;
- `7` to **roll back**;
- `8` to **hold** (not enough traffic).

A rollback is triggered by any of the following:

- a security-class error rate more than 2× the baseline (and above 10 events);
- terminal-class errors from `internal_error`;
- a resolve p99 above threshold;
- the emergency-disable gauge set on the canary.

## Rollback

Redeploy the previous signed artifact after verifying it with `tools/release.py verify`. Descriptors don't survive a restart, so rollback has no data-migration step. Clients re-acquire descriptors. `PK_DESCRIPTOR/2` is unchanged between 4.2.0 and 4.3.0, so mixed fleets interoperate.

## Emergency disable

You can disable the component in three ways:

- **In process:** `descriptors.emergency_disable()`.
- **Per host:** set `INV42_EMERGENCY_DISABLE=1` and restart. Alternatively, have the service's admin endpoint call `emergency_disable()`.
- **Revoke everything now:** call `DescriptorTable.destroy()` on every table.

While disabled, `health()` reports `not_ready` and `inv42_emergency_disabled` is 1. `status()` and `destroy()` keep working.

Rehearse emergency disable each quarter, and record the drill in `REVIEWS.json` (`kind: drill`).
