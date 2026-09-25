# Runbook — install (day 0)
1. Verify the release: `python -m inv67_kubernetes_integration_mechanism.governance.release verify --manifest RELEASE_MANIFEST.json` → must print `OK`.
2. `kubectl apply -k deploy/overlays/<env>` (namespace, CRD, RBAC, Deployment, NetworkPolicy, PDB).
3. Create `inv67-config` ConfigMap (`config.json`, validated by `schemas/INV67_CONFIG_v1.schema.json`) and `inv67-secrets` Secret (mode 0400). Bind namespaces to tenants in config.
4. `kubectl -n inv67-system rollout status deploy/inv67-controller`; `/readyz` must be 200 on the leader.
5. Smoke: apply `examples/wasmworkload.yaml`; expect `Accepted=True` and phase `Pending→Running`.
**Rollback:** `kubectl delete -k deploy/overlays/<env>` only after all WasmWorkloads are deleted (finalizers need the controller).
