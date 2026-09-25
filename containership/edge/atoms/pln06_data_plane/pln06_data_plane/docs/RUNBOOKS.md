# PLN-06 runbooks — day-0 / day-1 / day-2 and incident response (WP #50, #1, C096/C097)

Every procedure names the operator capability it needs. All operator actions are audited automatically.

## Day 0 — bootstrap from an empty node (C040)

1. `python -m pip install .` (or copy the release artifact and verify `SHA256SUMS.txt`: `sha256sum -c SHA256SUMS.txt`).
2. Create mutable state dirs (never inside the artifact): `/var/lib/pln06/{journal,audit,config-history}` owned by the service user, mode 0700.
3. Provision keys: bind `KeyProvider` to KMS/HSM (W-012) or, in non-production, `KeyRing.add("k-<date>")`.
4. Write config: `config/base.json` + one overlay from `config/overlays/`; validate with `python -m pln06_data_plane.tools.release_gate --config config/base.json --overlay config/overlays/prod.json --config-only`.
5. Start the service; verify `health()["ready"] is True` and every entry in `dependencies` is `ok`.
6. Run the smoke suite: `python -m unittest discover -s tests -p "test_service*"`.

## Day 1 — deploy / upgrade (canary → staged → full)

1. Confirm the release gate passed for the exact artifact SHA-256 (`evidence/dossier.json`).
2. `ConfigController.propose(cfg, revision=..., author=..., approver=<different person>, canary=<apply to canary>, probe=<health probe>)`. Canary failure auto-rolls back and records `canary_failed`.
3. Stage: 1 node → 10 % → 50 % → 100 %, waiting ≥ 15 min at each stage with alerts `PLN06*` silent.
4. Upgrade order in mixed fleets: receivers (NetworkRpcServer) first, then senders.

## Day 2 — operations

| Situation | Action | Capability |
|---|---|---|
| Planned maintenance | `svc.freeze(cred, reason)` → `svc.drain(cred, timeout)` → work → `svc.unfreeze(cred)` | `control.freeze` |
| Suspect destination site | `svc.quarantine(cred, destination=..., reason=...)`; failover selects only residency-legal, equal-or-stronger isolation sites | `control.freeze` |
| Faulty adapter (e.g. shm leak) | `svc.quarantine(cred, transport="shared-memory", reason=...)` — selector records explicit fallback | `control.freeze` |
| Bad config rollout | `ConfigController.rollback(author=...)` (or `to_revision=`) | `policy.rollback` |
| Security incident / data exposure | `svc.emergency_disable(cred, reason=<incident id>)` — admission refused non-retryably | `control.freeze` |
| Policy change | via GAP-13 then `svc.sync_policy()`; manual override `svc.update_policy(cred, ..., revision=...)` refuses if it would invalidate live transfers | `policy.update` |
| Key rotation | `keys.rotate("k-new")`; wait max credential/label TTL; `keys.retire("k-old")`. Compromise: `keys.revoke("k-old")` immediately | key custodian |
| Stalled transfers | `svc.reap_stalled()` (also on a timer) | service |
| Audit integrity check | `audit.verify()` (daily cron; alert on failure) | `audit.read` |

## Dependency outages (see `lifecycle.DEGRADED_MODES`)

* **GAP-13 down:** service keeps the last verified policy up to `max_policy_age_s` for the context; then admission is refused (`PK_POLICY_UNAVAILABLE`, retryable). Do **not** raise the max age during an incident without security approval.
* **Key service down:** admission refused (`PK_KEY_UNAVAILABLE`). Restore KMS; no bypass exists by design.
* **Bulk transport down:** inline continues; bulk returns retryable transport errors; if a failover candidate list is configured, residency-safe failover is attempted.
* **Journal disk full/unwritable:** health not ready; free space; restart reconciles open transfers to `expired`.

## Backup / restore / reconstruction (#49, C095)

State that must persist: transfer journal, audit ledger, config history, fencing lease. Payloads are never persisted.

* Backup: `journal.backup(dest)` returns `{sha256, records, epoch}`; copy `audit.jsonl` and `config-history.jsonl` together; store the metadata in the backup catalogue.
* Restore: `TransferJournal.restore(backup, target, expected_sha256=...)`; then `AuditLedger(keyring, path)` verifies the chain on load; start the service — open transfers are reconciled to `expired` and a `restore` audit event is written.
* Reconstruction without backup: start with an empty journal; senders retry expired/unknown transfers (at-least-once; receivers dedupe by `transfer_id` + manifest root).

## Incident response (C097)

| Sev | Definition | Page | Response | Update cadence |
|---|---|---|---|---|
| SEV1 | Residency/integrity/security breach, or admission unavailable fleet-wide | SRE on-call immediately + security + service owner | 15 min ack; emergency-disable if data exposure suspected | 30 min |
| SEV2 | Admission error rate > 5 % or p99 SLO breached for 15 min in one site | SRE on-call | 30 min ack | 1 h |
| SEV3 | Single adapter degraded with working fallback; audit verify warning | Ticket, business hours | 1 business day | daily |
| SEV4 | Cosmetic / documentation | Ticket | backlog | — |

Escalation chain and contacts: `OWNERSHIP.json` (**currently vacant — W-001; release blocked**). Containment options in order: quarantine destination → quarantine transport → freeze → emergency-disable. Recovery: unquarantine/unfreeze after the root cause is fixed and `audit.verify()` passes; post-incident review within 5 business days, tracked in `reviews/`.
