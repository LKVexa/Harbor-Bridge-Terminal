# Runbook — degraded modes
| Symptom | Meaning | Action |
|---|---|---|
| `Degraded=True, reason=DownstreamUnavailable` | SCH-01 unreachable, breaker open | check SCH-01 health; nothing to do in INV-67; converges automatically |
| `Ready=Unknown, reason=StaleObservation` | no runtime observation for > staleObservationSec | same as above; do NOT delete workloads to "fix" it |
| `inv67_leader` 0 everywhere | Lease API unavailable or RBAC broken | check `leases` RBAC in inv67-system |
| `inv67_watch_relists_total` rising | watch history expiring | API server load; expected occasionally |
| queue depth growing | saturation | see CAPACITY.md; raise quotas or add capacity |
