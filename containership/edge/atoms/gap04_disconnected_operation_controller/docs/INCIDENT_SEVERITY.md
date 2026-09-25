# Incident Severity, Paging and Containment (C51)

| Sev | GAP-04 examples | Page | Response | Commander | Security |
|---|---|---|---|---|---|
| SEV1 | audit-chain failure (E0402), clock rollback (E0300 bursts), forged/replayed lease bursts, split-brain / fencing violation (E0500 at supervisor), storage freeze | immediately, 24×7 | 15 min | on-call IC | mandatory |
| SEV2 | lease expiring/expired while partitioned, quarantine engaged, journal > 80% | immediately | 30 min | on-call | if cause unknown |
| SEV3 | prolonged degradation, reconcile conflicts, stale policy approach, load shedding, latency SLO | business hours | 4 h | owner | no |
| SEV4 | ordinary partition | none (dashboard) | next day | — | no |

## First response (all severities)
`GET /healthz` → record `code_version`, `config_digest`, `generation`, `lease.lease_id`, `authority_watermark`, `partition_epoch`, `journal`, `dependencies`, `clock`. Check recent config/policy/lease installs in logs (`event` in `policy.installed`, `lease.installed`, `override_*`).

## Safe containment actions
Freeze (override `freeze`), quarantine (`quarantine()` or signed remote command), revoke lease (control plane raises authority epoch), halt rollout (`Rollout` → ROLLBACK), isolate site at GAP-12, rotate issuer keys (new trust bundle).

## NEVER do
* delete or edit `journal.wal`, `keys.json`, or `generation.json`;
* reset epochs/generations or restore a backup over a live node's directory;
* roll the system clock back to "fix" expiry;
* disable fencing or run two controllers against one state directory.

## Evidence collection
Before remediation: `backup.py backup` of the state dir, `/healthz` snapshot, logs for the window, reconciliation records by `txn_id`, and `verify_export` output of the journal.

## Decision tree — reconciliation / integrity uncertainty
1. `reconnect()` fails with E0600 → progress persisted; retry after breaker cool-down (RB-06).
2. Node refuses to start with E0401/E0402/E0403 → do not repair in place; RB-09 restore.
3. Outcomes include `quarantined` → resolve subjects with GAP-05 owner before unfreezing.

## Recovery validation before unfreezing
Journal verifies; `ready=true`; no `reconciliation.in_progress`; new lease at current epoch; overrides cleared or expired.

## Post-incident
Timeline + RCA mandatory for SEV1/SEV2 within 5 business days; review runbooks and waivers (`REVIEW_PROCESS.md`). Keep an offline copy of this document and `RUNBOOK.md` at each site (C51-018). Game days: **not yet exercised** (C51-017, W-001).
