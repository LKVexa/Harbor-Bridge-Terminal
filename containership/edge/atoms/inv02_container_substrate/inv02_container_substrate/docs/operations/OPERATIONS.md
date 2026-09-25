# INV-02 operations guide (MC50–MC53, MC55, MC56)

Escalation contacts come from `OWNERS.yaml`. Every procedure below writes to the audit
ledger; verify it afterwards with `audit.verify_ledger(path, key, expected_head=...)`.

## 1. Health, metrics, dashboards (MC48, MC45, MC50)

`observability.serve_http(health, metrics)` serves `/healthz` (liveness), `/readyz`
(readiness: store writable, fsck clean, policy bundle loaded) and `/metrics` on
loopback (`config.metrics_listen`). Recommended metric names:

| Metric | Type | Labels |
|---|---|---|
| `inv02_pulls_total` | counter | `result` (ok, auth, integrity, notfound, offline_miss) |
| `inv02_pull_seconds` | histogram | — |
| `inv02_admission_decisions_total` | counter | `allow`, `rule` |
| `inv02_store_bytes` / `inv02_store_blobs` | gauge | — |
| `inv02_store_corrupt_blobs` | gauge | — |
| `inv02_quarantined_digests` | gauge | — |
| `inv02_admission_shed_total` | counter | — |
| `inv02_circuit_open` | gauge | `endpoint` (bounded by mirror config) |
| `inv02_signing_key_expiry_seconds` | gauge | `key_id` |

Dashboard panels: pull rate/error ratio, p50/p99 pull latency, store bytes vs capacity,
corrupt/quarantined counts, admission denies by rule, shed rate, open circuits, key expiry.
Alert rules: `alerts.yaml` (Prometheus format).

## 2. Capacity and saturation model (MC51)

Local measurements (`evidence/bench.json`, x86_64, Python 3.11): CAS put ≈166 MiB/s
(1 MiB blobs, fsync), verified get ≈1,075 MiB/s, manifest parse ≈38k/s,
unpack ≈42 layers/s at 200×2 KiB files, Ed25519 verify ≈250/s, policy evaluation ≈120k/s.

Sizing rules:

* **Disk:** `max_store_bytes ≥ 1.5 × (Σ unique layer bytes of the working set)`; GC
  reclaims only after `gc_grace_s`, so keep 20 % headroom above the peak ingest per grace window.
* **Signature verification** is the CPU bottleneck: ≈4 ms per signature per core.
  Cache verified (digest, key id) results; budget `pulls/s × signatures × 4 ms` of CPU.
* **Concurrency:** `max_inflight_pulls` ≈ 2 × cores for network-bound pulls;
  `max_queued_pulls` bounds memory; beyond it requests are shed (`Overloaded`).
* **Saturation signals:** shed rate > 0 for 5 min, p99 pull latency > 3× baseline,
  store > 85 % of `max_store_bytes`, lock wait (`LockTimeout`) errors.

## 3. Backup, restore, reconstruction (MC52)

```python
digest = store.backup("/backups/inv02-2026-09-22.tar")       # consistent (taken under lock)
ContentStore.restore("/backups/inv02-….tar", "/var/lib/inv02-new", expected_digest=digest)
```

Record the backup digest in the audit ledger. Restore refuses a non-empty target, an
archive whose digest differs, unexpected archive members, and a store that fails fsck.
**Reconstruction without backup:** tags are lost but content is not — re-pull by digest
from the registry (`DistributionClient.resolve(name@digest)`), then re-apply tags from
the audit ledger's `tag.set` events. RPO = backup interval; RTO ≈ archive size / disk throughput.

## 4. Rolling upgrade and rollback (MC53)

1. Read `CHANGELOG.md` for schema changes. Store schema 2 reads schema 1 (auto-migrates on open).
2. Take a backup (§3). Upgrade one node; check `/readyz` and `store.fsck()`.
3. Roll forward node by node. Mixed versions are safe only while no node has written a
   newer schema; a newer schema makes older binaries refuse to start (`SchemaTooNew`)
   instead of corrupting data.
4. **Rollback:** after a schema bump, roll back by restoring the pre-upgrade backup;
   without a schema bump, reinstall the previous package.

## 5. Credential and key rotation (MC55)

* **Signing keys (verification side):** `keyring.rotate(old_id, new_key, overlap_s, now)`.
  Publish the new public key, sign new releases with both keys during the overlap,
  then only with the new one. `keyring.expiring(now, 30*86400)` feeds the expiry alert.
* **Compromise:** `keyring.revoke(key_id, reason)` — a revoked id can never be re-added.
  Then quarantine every digest signed only by that key and re-sign or rebuild.
* **Registry credentials:** rotate at the secret store backing the `CredentialProvider`;
  tokens are per (host, repository) and in memory only, so restart or wait for 401 to re-auth.
* **Audit ledger key:** start a new ledger file with the new key; anchor the old ledger's
  final head hash in release evidence before switching.

## 6. Incident runbooks (MC56)

| Incident | Detect | Immediate action | Follow-up |
|---|---|---|---|
| **Corrupt content** | `inv02_store_corrupt_blobs > 0`, `IntegrityError` on get | `store.repair(fetch=verified_refetch)`; corrupt files kept in `corrupt/` | disk health; check audit ledger for tampering |
| **Registry compromise suspected** | signature/attestation failures spike, unexpected tag moves in audit | set `offline: true` (serve verified local content only); quarantine affected digests | rotate registry creds; re-verify all tags vs signatures |
| **Signing key compromise** | security report | `keyring.revoke`; quarantine digests signed only by that key | rotate (§5); advisory per SECURITY.md SLA |
| **Metadata corruption** | store refuses to open (`IntegrityError`) | stop writers; restore latest backup (§3) | reconstruct tags from the audit ledger |
| **Runtime isolation escape suspected** | host alerts, unexpected host mounts or processes | stop affected containers (`OCIRuntime.kill/delete`); preserve host state | move the workload class to a sandboxed runtime class (gvisor/kata); security owner leads |
| **Policy engine errors** | all admissions denied, `rule error` in decision explain | fail-closed is the designed behaviour; roll back the policy bundle version | add a regression test for the bundle |
| **Overload** | shed rate, p99 latency | raise `max_inflight_pulls` only if CPU/disk allow; add mirrors | capacity review (§2) |

Every runbook ends with: verify the audit ledger, record a timeline, and file a closure issue.
