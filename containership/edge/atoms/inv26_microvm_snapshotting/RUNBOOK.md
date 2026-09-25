# Runbook — day-0 / day-1 / day-2 (C040, C092, C096)

## Day 0 — bootstrap an empty node (deterministic, idempotent)
`tools/bootstrap.sh` (each step records a marker in `$INV26_STATE/bootstrap/`, safe to re-run):
1. **Preflight** `python -m inv26_microvm_snapshotting.tools.preflight --json` — Linux, Python ≥ 3.10,
   `cryptography` import + AES-GCM self-test, `/dev/kvm` present (warn-only for reference profile), work dir is
   tmpfs with mode 0700, metadata/blob dirs writable and not world-readable, clock sync (`timedatectl`),
   core dumps disabled. Exits non-zero on any production blocker.
2. **Install verified artifact**: `sha256sum -c SHA256SUMS` then
   `python -m inv26_microvm_snapshotting.tools.release verify --dist <dir>` (DSSE + digests), then
   `pip install --no-deps -r requirements.lock` (hash pinning pending, see requirements.lock) and the wheel. No curl|sh, no `latest`.
3. **Identity**: create system user `inv26` (no shell), groups `vmm-api`; directories 0700 owned by `inv26`;
   work dir `mount -t tmpfs -o mode=0700,uid=inv26,noexec,nosuid,nodev tmpfs /run/inv26/work`.
4. **Trust roots**: install caller + grant-issuer public keys (verified out of band) into the trust store;
   KMS key alias provisioned by the security owner.
5. **Configuration**: validate then activate `examples/config.production.json` overlay set with
   `expect_revision=0` and an approval reference.
6. **Start + verify**: construct the service, run `reconcile()`, check `health()["ready"]`, run the smoke
   capture/restore with a test tenant, `python -m inv26_microvm_snapshotting.audit verify`.
The clean-node CI job (`.github/workflows/ci.yml` → `bootstrap-smoke`) runs steps 1, 2, 5, 6 with the
reference profile; a production clean-node run needs KVM + a real VMM (BLOCKED_EXTERNAL).

## Day 1 — deployment
Staged per `ops/ROLLOUT_POLICY.json`: canary (1 node/site, 60 min bake) → 10 % → 50 % → 100 %, each gated on
no defect/integrity alerts, reseed failures = 0, and (once X014 exists) restore p99 within threshold.
Automatic rollback triggers are listed there. Config and software roll back together when a schema major
changed. Record the release in `ops/REVIEWS.json` and the evidence bundle (`evidence/EXIT_GATE.json`).

## Day 2 — operation
* **Dependency outage** (`INV26-DependencyOutage`): check `health()["dependencies"]`; KMS/storage/VMM outages
  fail closed by design — do not bypass; restore capacity comes back automatically when probes recover and the
  breaker half-opens.
* **Overload** (`INV26-OverloadRatio`): look at `inv26_admission_rejected_total{reason}`; tenant-rate → talk to
  the tenant; queue full → capacity (C069); raise limits only through a config activation.
* **Integrity alert**: follow INCIDENT_RESPONSE.md#integrity — quarantine is automatic via scrub; run
  `SnapshotService.scrub()` fleet-wide.
* **Emergency disable**: `handle("disable", <admin token>, {"reason": ...})`; readiness goes false;
  `handle("enable", …)` to resume. Both are audited fail-closed.
* **Key rotation**: `kms.rotate(alias)` → `service.rewrap_all()` → disable old version after grants re-issued.
* **Backups**: BACKUP_RESTORE.md. **Scrub**: daily `scrub()`. **Reviews**: `ops/REVIEWS.json` cadence.
* **Explain a failure**: `service.explain(<correlation_id>, text=True)`.
