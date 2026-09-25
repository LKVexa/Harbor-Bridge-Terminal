# Operator runbooks (MC-060, MC-059)

## Day 0 — bootstrap
Prereqs: KVM host passing `docs/KVM_PREREQUISITES.md`; approved manifest pins; keys provisioned in KMS.
1. `tools/bootstrap.sh` → expect "standalone suite OK".
2. `python -c "from inv24_microvm_runtime.virtualization import preflight; print(preflight().to_dict())"` → `usable: true`. Failure branch: follow the error code table; do not continue.
3. Verify artifacts: `ArtifactManifest.load(...).verify(name, path)` for firecracker, jailer, kernel, rootfs.
4. Activate config revision 1 (`ConfigStore.activate`). 5. `python tools/run_evidence.py && python tools/production_gate.py`. Archive both outputs.
Rollback: remove node from PLN-04 pool. Escalate: owner.

## Day 1 — deploy / change
Follow `ROLLOUT.md`. Verification after each stage: readiness true, 0 stalled, audit `verify()` ok.

## Day 2 — operate
- **Stalled guest** (`HealthReport.stalled`): check VMM alive → if dead, `destroy` (cleans resources) and let PLN-04 re-admit; if alive, capture serial log, then destroy.
- **Breaker open**: identify dependency (`microvm_dependency_up == 0`), fix, breaker half-opens automatically after `reset_s`.
- **Audit verify failure**: SEV1; freeze admission; preserve file; engage security.
- **Key rotation**: `Keyring.rotate(new_id)`; old key verifies for the grace window only.
- **Orphan sockets after crash**: `reap_orphan_sockets(run_dir, live)`.

## Backup / restore / reconstruction (MC-059)
Back up hourly: config dir, `ops.jsonl`, `leases.json`, audit log (append-only copy), snapshot store metadata.
Restore: stop runtime → restore files → `AuditLog(path).verify()` → `ConfigStore(dir).active` → `AdmissionController.reconcile(live)` → resume.
RPO 1 h, RTO 30 min (targets; not yet exercised — BLOCKED).
