# Disconnected / intermittent control plane (item 07)

| Situation | Behavior | Test |
|---|---|---|
| API server unreachable | No reconciles complete; nothing is torn down; runtime keeps running already-placed workloads; watch pump logs and retries. | `test_disconnected_control_plane_reconnect_converges`, `test_api_outage_then_recovery` |
| Reconnect | Full `resync()`; level-triggered reconcile converges status from the runtime; no relaunch because attempt ids are unchanged. | same |
| Watch history expired (410) | Relist. | `test_watch_history_expired_relists` |
| Downstream unreachable | Breaker opens; new placements → `Degraded`; running ones project `Unknown` after `staleObservationSec`. | `test_downstream_outage_…`, `test_stale_observation_goes_unknown` |
| Lease store unreachable | Leader keeps acting only within 80 % of its lease; then stands down. | `test_lease_store_partition_…` |
| Delete while downstream down | Finalizer held until cancel succeeds. | `test_delete_during_downstream_outage_…` |

**Safety precedence during disconnection:** never launch without a fresh leader lease; never cancel on the basis of a missing observation; prefer `Unknown` over a guess. **Conflict resolution on reconnect:** user spec (generation) wins over anything cached; runtime state wins over cached status.
