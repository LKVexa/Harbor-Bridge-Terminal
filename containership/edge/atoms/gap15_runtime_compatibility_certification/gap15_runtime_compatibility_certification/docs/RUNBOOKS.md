# GAP-15 Operational Runbooks

Runbook version tracks the package (`4.3.0`). Commands assume the folder that
contains `gap15_runtime_compatibility_certification/` is the working directory.
`$DB` is the store path (default `data/gap15.db`). Every destructive step is
preceded by an evidence-preservation step. Escalation contacts come from
`docs/OWNERS.json` — **currently unassigned** (blocker MC-43-01); until it is
filled, escalate to the person who deployed the service.

> These runbooks have not yet been exercised in a game day (MC-48-09 blocker).

## Day 0 — install and bootstrap <a id="rb-day0"></a>

1. Preflight: `python -c "from gap15_runtime_compatibility_certification.production import release, config; print(config.validate_config(__import__('json').load(open('deploy/config.example.json'))))"` — expect `[]` after replacing every `*_ref`.
2. Create the data dir with mode `0700`; never place it on a synced/network drive (SQLite + OneDrive = I/O errors).
3. Start once to migrate: `python -m gap15_runtime_compatibility_certification.production.cli migrate --db $DB` → `{"ok": true, "schema_version": 3}`.
4. Verify: `... cli verify --db $DB` → `"ok": true`, `events: 0`.
5. Load the trust bundle (producer, builder, attestation, IdP, service keys) and the signed authz/precedence policies.
6. `GET /readyz` must be `200 {"ready": true}` before routing traffic.
7. Take and restore-verify the initial backup (see rb-backup).

## Day 1 — routine operations <a id="rb-day1"></a>

- **Add a runtime/profile:** add its registry values (capability model), add fixture rows to `deploy/supported-versions.json`, enqueue `coverage-gap` recert jobs. New rows show as coverage gaps until tested.
- **Signer rotation:** add the new key with `not_before` overlapping the old key's `not_after`; never reuse a key id; producers switch; the old key simply expires.
- **Lifecycle update:** `lifecycle(state=deprecated|blocked-for-new|end-of-life, effective_at, replacement)`; publish the advance warning from `upcoming_lifecycle()`.
- **Policy deployment:** `policy.simulate(old, new, recent_contexts)`; review every changed verdict; activate; keep the previous revision for rollback.
- **Coverage review:** `update_gauges(requested_keys)`; coverage < 0.8 pages the service owner.

## Day 2 — maintenance <a id="rb-day2"></a>

- **Upgrade:** backup → `cli migrate --dry-run` → deploy → `cli verify`. Older binaries refuse newer schemas (`E_SCHEMA_TOO_NEW`); rollback = restore the pre-upgrade backup.
- **Restore drill (monthly):** rb-backup step 3.
- **Retention/compaction:** ledger and audit are never pruned; the hot `matrix` table holds one row per key by design.
- **Decommission:** export ledger + audit (`cli export`), sign a final checkpoint, archive with the trust bundle.

## Failure trees

### Elevated errors / SLO burn <a id="rb-elevated-errors"></a>
1. `GET /readyz` — which check failed? (`chains`, `time`, `key_provider`, `accepting`)
2. Error categories in `gap15_requests_total{outcome="error"}` and `gap15_evidence_rejections_total{category}`.
3. `validation` spike → a producer shipped a bad envelope: contact the producer, do not relax schemas.
4. `dependency` → go to rb-dependency-outage. `conflict` → rb-conflicts.
5. Rollback the last deploy if the spike began with it (rb-rollback).

### Expiry storm / recert backlog <a id="rb-expiry-storm"></a>
1. **Never extend the TTL to make the alert go away.** Expired means not deployable.
2. Raise lab quotas in the scheduler; prioritise by `scheduler.priority()`.
3. Inspect `dead` jobs: runtime unavailable vs harness defect.

### EOL runtime still admitted / in service <a id="rb-eol-exposure"></a>
1. `emergency_disable(scope="runtime:<name@ver>", incident=…, until≤24h)`.
2. Confirm `prestart_recheck` refuses new launches.
3. Migrate workloads to the `replacement` runtime from the lifecycle record.

### Coverage low <a id="rb-coverage"></a>
Enqueue `coverage-gap` jobs for the missing keys; never infer from a similar profile.

### Signature failures <a id="rb-signature-failures"></a>
1. Group rejections by `code` (`E_SIG_UNKNOWN_KEY`, `E_SIG_KEY_EXPIRED`, `E_SIG_INVALID`, `E_SIG_SIGNER_UNAUTHORIZED`).
2. Expired → producer missed a rotation. Invalid/unknown from one producer → suspected compromise: `revoke(subject_type="signer", …)`; review `affected_evidence`.

### Attestation failures <a id="rb-attestation-failures"></a>
`E_ATT_MEASUREMENT` after a firmware rollout → baseline update needed (two-person change). `E_ATT_FIRMWARE_DOWNGRADE` / `E_ATT_NONCE` spikes → possible replay: quarantine the node.

### Provenance failures <a id="rb-provenance-failures"></a>
`E_PROV_DIGEST_MISMATCH` / `E_PROV_SBOM_SUBJECT` → build pipeline publishing mismatched subjects; `E_PROV_BUILDER_REVOKED` → expected after a builder compromise.

### Audit / ledger chain broken <a id="rb-audit-chain"></a>
1. **Preserve evidence first:** copy `$DB`, `$DB-wal`, `$DB-shm` read-only to the forensics store; record hashes.
2. `emergency_disable(scope="admissions")` and `scope="ingestion"`.
3. `cli verify --db <copy>` gives the first broken seq; compare with the last off-box checkpoint.
4. Restore from the last backup whose head matches an exported checkpoint (rb-backup), then re-ingest producer evidence after that point.

### Replay / credential abuse <a id="rb-replay"></a>
Revoke the affected token ids / subjects (`update_revocations`), rotate the IdP key if tokens were forged, review audit for `E_AUTH_REPLAY`.

### Revocation propagation lag <a id="rb-revocation-lag"></a>
Stop admissions at lagging sites (`emergency_disable`), push a new offline bundle with a fresh revocation checkpoint, confirm `status()` counter advanced.

### Evidence conflicts <a id="rb-conflicts"></a>
Assign an owner; gather both producers' harness digests; resolve with two people via `resolve_conflict(decision=…)`. The scope stays quarantined until then.

### Untrusted time <a id="rb-time"></a>
Check NTS/PTP sources; decisions fail closed while confidence is below policy. Do **not** switch the policy to `low`.

### Storage saturation <a id="rb-storage"></a>
Expand the volume. Never delete ledger/audit rows (the triggers refuse anyway).

### Backup / restore <a id="rb-backup"></a>
1. Backup: `Store.backup(dest, sign=…)` writes `dest` + `dest.manifest.json`.
2. Verify: `restore_to_staging(dest, staging, verify_sig=…, expected_partitions=…)` — never restores over a live store.
3. Drill: time step 2, record RTO; compare manifest revision with live revision for RPO.
4. Encryption at rest of backups requires a KMS (blocker MC-01-08 / MC-47-03).

### Observability / alert pipeline <a id="rb-observability"></a>
`GAP15Watchdog` must always be firing; if `GAP15AlertPipelineDead` pages, the notification path is broken — treat all silence as unknown.

### Dependency outage <a id="rb-dependency-outage"></a>
Follow the fail-open/closed matrix in ADR-008. Time/store/chain outages stop decisions by design.

### Rollback <a id="rb-rollback"></a>
Application rollback is safe while the schema version is unchanged; after a migration, rollback = restore the pre-upgrade backup. A rolled-back binary replays the same ledger, so revocations are never resurrected.

## Incident containment <a id="rb-incident"></a>

| Incident | Contain | Recover |
|---|---|---|
| Compromised signer/producer | `revoke(signer)`, list `affected_evidence` | re-test affected keys under a new key |
| Compromised node | `revoke(node / profile)` | re-attest after reimage |
| Incorrect certification allow | `emergency_disable(runtime/artifact)` | find the decision via `explain`, fix root cause, conflict case |
| Data corruption | rb-audit-chain | restore + re-ingest |
| Site partition | edge stays on offline bundle until `not_after` | `reconcile()` on reconnect; review offline allows |

## Disconnected site <a id="rb-disconnected"></a>
Admissions continue only from a valid offline bundle; when the bundle expires or its revocation checkpoint is older than `max_revocation_age_s`, **admissions stop**. On reconnect run `OfflineCache.reconcile()` and open conflict cases for any offline allow the online service would have denied.

## Component → runbook map

| Components | Runbook sections |
|---|---|
| 01 store, 11 concurrency, 15 recovery, 47 backup/restore | rb-backup, rb-storage, rb-audit-chain, rb-day2 |
| 02 ledger, 12 audit | rb-audit-chain, rb-backup |
| 03 signing, 45 supply chain | rb-signature-failures, rb-day1 |
| 04 provenance | rb-provenance-failures |
| 05 attestation | rb-attestation-failures |
| 06 time | rb-time |
| 07 authn, 08 authz | rb-replay, rb-day1 |
| 09 schemas, 10 ingestion, 35 fuzz | rb-elevated-errors |
| 13 revocation | rb-revocation-lag, rb-incident |
| 14 service host, 32 capacity | rb-elevated-errors, rb-dependency-outage |
| 16-19 negotiation/capability/versions/features | rb-day1, rb-coverage |
| 20 lifecycle, 21 negative ageing, 22 scheduler | rb-eol-exposure, rb-expiry-storm |
| 23 policy, 49 waivers | rb-day1 |
| 24 offline cache, 25 partitions | rb-disconnected |
| 26 metrics, 27 logs/traces, 28 explain, 29 alerts | rb-observability |
| 30 admission, 46 rollout/emergency | rb-eol-exposure, rb-rollback |
| 31 conflicts | rb-conflicts |
| 33-41, 50 verification/release/gate | rb-day2 |
| 42 ADR, 43 owners, 44 bootstrap, 48 runbooks | rb-day0 |
| 47 migration rollback | rb-rollback, rb-backup |
| 51 MASTER.md source integrity | rb-day2 (release source check) |
