# RB-BACKUP — Backup, restore, reconstruction (MC-063)

Durable datasets: see `docs/TOPOLOGY.md` §Persisted datasets. Everything except the journal
(segments, summaries, anchors, holds) is derived and is rebuilt by replay.

| Item | PROPOSED value |
|---|---|
| Frequency | hourly `cli backup`, plus a continuous copy of anchors to SIEM |
| Retention | 35 daily + 12 monthly |
| Encryption | backup target encrypted by the storage KMS; bodies optionally sealed (AES-256-GCM) already |
| Immutability | object-lock/WORM target |
| Location | second region, same jurisdiction as `site` |
| RPO / RTO | RPO ≤ 1 h from backups (0 with synchronous volume replication); RTO ≤ 15 min |

## Backup
`python -m inv66_enterprise_wasm_control_plane.production.cli backup ROOT DEST`
→ `{"backup": DEST, "head_seq": N}`. `DEST/BACKUP.json` records the head seq and hash, and the copy is verified before the command returns.

## Verify (weekly, clean room)
1. `cli restore DEST /tmp/clean-root` (the target must be empty; restoring over live data is refused).
2. Expected: `"result":"INTACT"` and `head_seq` equal to the manifest. A mismatch → `ECP_STORE_CORRUPT`, and the backup is rejected.
3. Start a service on `/tmp/clean-root` and compare `config_generation` and the inventory count with production.
4. Record the achieved RTO and operator sign-off in `release/reviews.jsonl`.

## Restore (disaster)
1. Freeze admissions if any replica is still up.
2. Restore the keys first: anchor public keys, then data keys for sealed bodies.
3. `cli restore BACKUP ROOT`, then start the leader. Replay rebuilds all projections, including pending deliveries.
4. `redeliver_pending()`. INV-63 deduplicates on decision id.
5. `cli verify-journal ROOT --trusted-keys keys.json`, then release the freeze (2 votes).

## Reconstruction when projections are lost
Projections live only in memory and are rebuilt on every start, so restarting the service is the reconstruction.

## Schema migration
Journal records are `PK_ECP_AUDIT/2` and immutable. A future `/3` would be written alongside and read by a reader that accepts both. There are no in-place migrations.

Evidence: `tests/disaster/test_disaster.py` (backup → restore → identical state, tampered backup rejected).
