# Runbook — upgrade and rollback (day 2)
* Pre-check: release manifest verify; compatibility matrix for the target cluster; `inv67_leader == 1` on exactly one pod.
* Upgrade: CRD first (additive only within v1alpha1), then controller image (rolling, maxUnavailable 0). Config last — the new controller must understand any new config keys (unknown keys are refused).
* Watch: `inv67_refused_total` by reason, `inv67_requeues_total`, `/readyz`.
* Rollback: `kubectl rollout undo deploy/inv67-controller`; config rollback = previous ConfigMap (activation history on `/configz`). Status is re-derived from the runtime, so no data migration is needed within v1alpha1.
