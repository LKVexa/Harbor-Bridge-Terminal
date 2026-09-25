# GAP-05 v4.3.0 Runbooks

Status: **draft, unreviewed, never exercised in a game day.**  Every procedure below uses
the supported API or the read-only `gap05-admin` CLI; none edits files under a data
directory by hand.  Required authorization is named per step (permissions from
`production/authz.py`).  Owners are UNASSIGNED.

## Severity map (automated by `lifecycle.triage`)

| Signal / reason code | Severity | Runbook |
|---|---|---|
| `health.live == false` (`CORR_FAIL_STOP`), `CORR_WAL_CORRUPT` | SEV1 | RB-02 |
| `CORR_AUDIT_TAMPER`, `CORR_AUDIT_TRUNCATED` | SEV1 | RB-05 |
| `SEC_COUNTER_EQUIVOCATION`, `SEC_VECTOR_EQUIVOCATION` | SEV1 | RB-06 |
| `SEC_FENCED_RETIRED`, `SEC_BAD_SIGNATURE` | SEV2 | RB-04 / RB-06 |
| `CAP_AUDIT_FULL`, audit_pressure >= 0.9 | SEV2 | RB-05 |
| quarantine_pressure >= 0.5, `CAP_FRONTIER_FULL`, `CAP_HOT_KEY` | SEV3 | RB-03 |
| `DEP_POLICY_UNAVAILABLE` | SEV3 | RB-03 |
| recovery mode / `CORR_RECOVERY_MODE` | SEV3 | RB-01 |

First response for every SEV1/SEV2: **contain, preserve evidence, then diagnose**.
Containment = `lifecycle.contain(node, tenant, env, keys, principal, reason)` (needs
`quarantine_admin`), which freezes keys (reversible, audited).  Evidence = copy the data
directory read-only and export the signed audit head (`node.audit.signed_head()`).

## Decision tree: repair vs restore vs reseed vs rollback

1. Node live and ready, replicas diverged -> **repair** (RB-01 anti-entropy).
2. Node not live; WAL tail torn only -> restart (recovery truncates the tail automatically).
3. Node not live; mid-log corruption or snapshot chain invalid -> **restore** (RB-02).
4. Disk lost, or restore older than the replica's retirement -> **reseed** (RB-04, new incarnation).
5. Bad membership change -> **rollback** (RB-04, forward rollback; never un-retires).

## RB-01 Replication lag / divergence / restored node in recovery mode
- Check: `node.health()` -> `reasons`; compare `anti_entropy.digest_tree` roots.
- Act: `anti_entropy.reconcile(a, b, tenant, env, principal_a, principal_b)` (peer identities need `replicate`).
- Verify: roots equal; `health.ready` true; restored node left recovery mode (audit `recovery_complete`).

## RB-02 WAL / checkpoint corruption
- Symptom: `CORR_WAL_CORRUPT`, `CORR_SNAPSHOT_*`, readiness reason "recovery rejected N durable records".
- Contain: remove node from traffic (not ready already); do **not** delete WAL.
- Diagnose: `gap05-admin verify-wal DATA_DIR`; `gap05-admin inspect DATA_DIR`.
- Recover: restore the latest verified backup into an empty directory (`lifecycle.restore`, needs `recover`), start node, then RB-01.
- Verify: `verify_backup` passed; audit chain verifies; reconcile converged.

## RB-03 Quarantine surge / conflict flood / policy outage
- Diagnose: `node.quarantine_list(tenant, env, principal)`; `node.analytics.report()` for hot keys / site pairs.
- Contain: freeze hot keys (`contain`); admission already throttles `CAP_HOT_KEY`.
- Drain: request decisions via `ResolutionAdapter.request(conflict_set, ctx)`, apply with `node.resolve(..., decision=...)` (needs `resolve`). A stale decision is refused (`CORR_STALE_DECISION`) - re-request.
- Policy outage: conflicts stay open by design; do not hand-pick winners without an authorised manual decision recorded in audit.

## RB-04 Membership change, fencing and reseed
- Remove: drain the replica, collect its final own counters (`high_water`), `store.remove_replica(name, high_water=..., expected_epoch=E)` on every node's store (needs `reconfigure`).
- Reseed: `store.reseed_replica(...)` -> new incarnation `name~N`, provision a new credential, start empty, RB-01.
- Rollback: `store.rollback_to(epoch, expected_epoch=E)` - retired replicas stay retired.
- Verify: `SEC_FENCED_RETIRED` rejections for the old incarnation; health `membership_epoch` equal on all nodes.

## RB-05 Audit pressure / tamper alarm
- Pressure: configure/restore the archive directory; sealed segments move after verified copy.
- Tamper: `gap05-admin verify-audit ARCHIVE_DIR AUDIT_DIR --pub HEX --head HEAD.json` against an externally retained signed head; the first break is reported; escalate to security; restore from backup.

## RB-06 Identity, key or equivocation failure
- Revoke the credential (`IdentityVerifier.revoke(serial)`), rotate trust bundle (add new CA, re-issue, remove old - never the last anchor).
- Equivocation evidence: `node.guard.evidence` + audit; treat the author replica as compromised: RB-04 remove, reseed.
- Encryption keys: `Keyring.rotate`, `rewrap` historical envelopes, then `retire` (refused while referenced).

## RB-07 Authorization denial spike
- Check audit `authz` events (policy_version, principal, tenant). Fix grants in the policy provider; there is no cache to flush.

## RB-08 Upgrade / migration
- `gap05-admin migrate SNAP_DIR --tenant T --environment E` (dry-run) then `--apply`; backups `*.pre-migration-vN` are kept. Downgrade is refused by design.
