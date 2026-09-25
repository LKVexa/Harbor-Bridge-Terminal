# GAP-04 Operational Runbook

**Applies to:** GAP-04 v4.3.0 · **Controls:** GAP04-C25, C29, C41, C42, C51 · **Status:** draft — requires operations-owner approval (see `GOVERNANCE.md`).

Every alert in `ops/alerts.rules.yml` links to one section below. Severity definitions are in `INCIDENT_SEVERITY.md`. All commands that change state are authenticated at a named boundary (`runtime/authz.py`) and are journaled; nothing here requires editing files on disk.

Diagnostic entry points for every section: `GET /healthz` (full `PK_GAP04_HEALTH/1` document), `GET /readyz` (503 with `not_ready_reasons` when not ready), `GET /metrics`, and the structured log stream (`PK_GAP04_LOG/1`, filter by `event`).

<a id="rb-01-partition"></a>
## RB-01 Ordinary partition (SEV4)
Symptom: `reachability_state{state="down"}`, tier `full`. This is designed behaviour: the site is operating on its lease.
1. Confirm `health.lease.remaining_s` exceeds expected outage length; confirm `policy.stale=false`.
2. Check GAP-12 for the WAN cause. Do **not** extend the lease locally — it is not possible by design.
3. On recovery, confirm `reconcile.complete` log event and `reconciliation.last.conflicts`.

<a id="rb-02-prolonged"></a>
## RB-02 Prolonged degradation (SEV3)
Tier `sustain`/`freeze` for >30 min. New admissions are being refused per schedule.
1. Estimate outage vs `lease.remaining_s`. If the outage will outlast the lease, prepare RB-03.
2. If business-critical admissions are blocked, the only lever is restoring connectivity; tier overrides can only **narrow** authority.

<a id="rb-03-lease"></a>
## RB-03 Lease expiring / expired (SEV2)
Tier `expired` = no local authority; running workloads continue, no new local decisions.
1. Restore control-plane reachability (heartbeats must verify, `up_after` consecutive).
2. Reconnect reconciles first; the control plane then issues a new signed lease (`install_lease`).
3. If the lease was revoked (`lease_dropped=true` after `apply_revocations`), a lease at the new authority epoch is required.

<a id="rb-04-policy"></a>
## RB-04 Stale policy (SEV3)
`policy_staleness_seconds` near `max_policy_staleness_s`. At the bound every decision is refused with `GAP04-E0102`.
1. Policy can only be refreshed while reachable and after any open partition is reconciled.
2. A policy with the same version but different digest is refused (`GAP04-E0221`) — the issuer must bump `policy_version`.

<a id="rb-05-storage"></a>
## RB-05 Journal pressure / storage freeze (SEV2 / SEV1)
At 80% utilization an alarm fires; when the non-reserved budget is exhausted the node enters **emergency freeze** (`storage_frozen`), refuses decisions with `GAP04-E0400`, and uses reserved capacity for control/audit frames only.
1. Check disk: `journal.disk_free`, `journal.bytes`.
2. Restore connectivity and reconcile — acknowledged frames are compacted and archived under `<state>/archive/`.
3. Archived segments may be moved off-box **after** the reconciliation record has been accepted upstream.
4. `storage_frozen` clears only on a fresh node open after space is recovered and state verified (restart the service).

<a id="rb-06-reconcile"></a>
## RB-06 Reconciliation conflicts / partial failure (SEV3)
Outcomes: `accepted`, `compensated` (authoritative state won; local effect reversed), `quarantined` (compensation not confirmed — operator must resolve the subject).
1. Pull the reconciliation record (`txn_id`) from the replication service; list `quarantined` subjects.
2. A failed reconnect persists progress; re-running `reconnect()` resumes with the **same** `txn_id` (idempotent at GAP-05).
3. `GAP04-E0701` = circuit open to GAP-05; wait for cool-down, do not hammer.

<a id="rb-07-security"></a>
## RB-07 Verification failures / clock rollback — possible attack (SEV1)
Repeated `GAP04-E020x`, `E0210`, `E0220` or `E0300`.
1. Treat as a security incident (`INCIDENT_SEVERITY.md` §containment). Page security on-call.
2. Quarantine the node (RB-08) if forged leases, replayed leases, or clock rollback are confirmed.
3. Preserve evidence: take a backup (`runtime/backup.py backup`) **before** any repair.
4. Rotate issuer keys through a new trust bundle (bundle_version must increase); revoke the compromised key.

<a id="rb-08-quarantine"></a>
## RB-08 Quarantine and emergency disable (SEV2)
Engage: `node.quarantine(reason, principal)` (authorized local operator) or a signed `PK_QUARANTINE_COMMAND/1` from the control plane. Effect is immediate and survives restart.
Release requires **both**: a control-plane signed `PK_QUARANTINE_RELEASE/1` bound to the quarantine nonce, and an authorized local approver who is not the principal that engaged it. Release requires verified reachability.
Operator overrides: `request_override(kind in freeze|tier_cap|disable)` + approval by a second principal (two-person control in prod); time-bounded (`overrides.max_ttl_s`), reason required, journaled.

<a id="rb-09-integrity"></a>
## RB-09 Journal/state integrity failure (SEV1)
`GAP04-E0401` (corruption), `E0402` (audit chain), `E0403` (decrypt/key), `E0404` (schema). The node refuses to start — fail closed.
1. Do not delete the journal. Take a raw copy of the state directory.
2. `E0402` mid-file = tampering or media fault: engage security (RB-07).
3. Restore from the most recent verified backup (`backup.py restore` into an **empty** directory; the restored node's generation is bumped so any surviving original is fenced).
4. Decisions after the backup point must be recovered from the upstream reconciliation records.

<a id="rb-10-overload"></a>
## RB-10 Load shedding (SEV3)
`GAP04-E0700` rejections: bounded admission (`admission.max_concurrency`/`max_queue`) is protecting the node. Identify the caller from logs; do not raise limits without the capacity model (`CAPACITY_MODEL.md`).

<a id="rb-11-latency"></a>
## RB-11 decide() latency SLO breach (SEV3)
p99 above 50 ms. Usual cause is fsync latency on the journal volume. Check storage health; the WAL fsync is not optional. See `SLO.md` for error-budget policy.

<a id="rb-12-telemetry"></a>
## RB-12 Telemetry missing (SEV3)
Metrics absent for 10 min. Telemetry never blocks decisions (rendering is in-process and non-blocking), so autonomy is unaffected; operators are blind. Check the scrape target, mTLS client certificate, and `GET /livez` locally.

## Storage-freeze exit (C20)
After space is recovered and the partition reconciled, an authorized approver calls `clear_storage_freeze()`. It re-verifies the audit chain, requires utilization below 70% and no pending decisions, then journals the exit.

## Backup and restore procedure (C41)
`GAP04_BACKUP_PASSPHRASE=… python -m gap04_disconnected_operation_controller.runtime.backup backup <state_dir> <file>` — stop the node first or accept a crash-consistent snapshot. Restore only into an empty directory; verify output shows `restored_seq` and `head`. Exercise quarterly (`REVIEW_PROCESS.md`).
