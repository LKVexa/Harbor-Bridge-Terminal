# INV-53 runbooks — day 0 / day 1 / day 2 (C096) and alert responses

All commands: `python -m inv53_message_reliability …` from the folder that contains the package.
Offline store commands take the store lock and **refuse** while a live broker owns the store.

## Day 0 — install and bootstrap (deterministic)
1. Python ≥ 3.10; no third-party runtime packages (`requirements/runtime.txt`).
2. Verify the release: `sha256sum` against the release record; `python tools/build_release.py /tmp/x` reproduces it.
3. Write config layers (`base.json`, `env-<ctx>.json`, `site-<id>.json`) and resolve:
   `python -m inv53_message_reliability config base=base.json env:prod=env-prod.json site:edge-7=site.json`
   → record the printed `digest` and `provenance` in the change ticket.
4. Provision keys (≥ 32 bytes) into the key provider; bind principals → kid; write grants (one tenant each).
5. Create the audit log location on durable storage; anchor its head daily (`audit FILE`).
6. Start the embedding service; check `health()` → `mode: NORMAL`, `ready: true`.

## Day 1 — verify
- `python inv53_message_reliability/tools/ci.py --pk-core <path>` on the target platform; attach
  `evidence/CI_EVIDENCE.json` to the release record.
- Smoke: put → receive → ack on a canary tenant; `explain` the id afterwards (`unknown_or_settled`).

## Day 2 — operate
| Task | Procedure |
|---|---|
| Config change | `ConfigStore.update(changes, expected_version=v)`; on regression `rollback()`; both are atomic file replaces. Record new digest. |
| Key rotation | See `docs/security/ENCRYPTION.md`. |
| Capacity | Watch depth gauges vs `max_*`; raise limits by config change, or add queues. |
| Compaction | Automatic every `compact_every` records; manual via backup (which compacts). |
| Backup/restore | `docs/ops/BACKUP_RESTORE.md`. |

## Alert responses
<a id="dlq-growth"></a>**DLQ growth** — `store explain DIR ID` for recent dead letters; fix the consumer; then
`store redrive DIR ID` (operations_owner) or purge (service_owner only).
<a id="stall"></a>**Stall** — consumers alive? leases expiring (redeliveries rising)? If consumers are gone,
nothing is lost: messages wait. Scale consumers.
<a id="storage"></a>**Storage errors / E_CORRUPT** — check disk space/IO errors. `E_STORAGE`: the breaker probes
automatically after `breaker_reset_seconds`. `E_CORRUPT`: the queue is frozen; stop the broker, `store inspect`,
restore the last good backup, then replay producers' idempotent retries.
<a id="security-dependency"></a>**Security dependency** — key provider or audit sink unreachable; the broker is
failing closed by design. Restore the dependency; do not disable authentication.
<a id="auth-spike"></a>**Auth failure spike** — check for a rotated/retired key still used by a client, or an attack;
audit log `authn_denied` / `authz_denied` records carry tenant/queue/op.
<a id="shedding"></a>**Shedding** — consumers are behind; scale consumers or raise `max_ready` deliberately.
<a id="latency"></a>**Latency** — compare with the bench baseline for this build; check fsync latency of the disk.
<a id="cardinality"></a>**Metrics dropped** — too many tenant/queue series; raise `max_series` or drop the tenant label.
