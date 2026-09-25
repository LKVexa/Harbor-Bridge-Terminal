# Runbook: Incident Response

| Field | Value |
|---|---|
| Document ID | INV63-RB-INCIDENT |
| INV-63 C-IDs covered | C097, C059, C009 (escalation path) |
| Status | DRAFT — pending approval |
| Owner | Service owner (role) — UNASSIGNED |
| Reviewers | SRE lead (role), Security contact (role) — UNASSIGNED |
| Revision | 4.3.0 |
| Approval date | pending |
| Supersedes | none |
| Change-review triggers | Revisit when interfaces, state ownership, topology or dependencies change, or when on-call roles change. |

## Severity

| SEV | Definition (INV-63) | Examples | Page? | Response target (proposed) |
|---|---|---|---|---|
| SEV1 | Cross-tenant breach, untrusted artifact running, mass unavailability caused by INV-63, journal corruption on the leader | `INV63-E-STATE-CORRUPT` on start; rollout took all replicas down | yes, immediately | ack 15 min |
| SEV2 | Control plane down, stalled workloads, security-event burst, split-brain suspicion | alerts `INV63ControlPlaneDown`, `INV63Stalled`, `INV63SecurityEvents`; `INV63-E-STALE-EPOCH` | yes | ack 30 min |
| SEV3 | Degradation without customer impact | `INV63Degraded` (shedding), `PARTIAL` outcomes | no (business hours) | 1 business day |
| SEV4 | Policy rejections, cosmetic | `INV63PolicyRejections` | ticket | best effort |

## Paging and escalation (all roles UNASSIGNED — must be filled by the owner in `OWNERS.yaml`, C009; gate criterion G-05)
1. Primary on-call (SRE) — UNASSIGNED
2. Secondary on-call (SRE) — UNASSIGNED
3. Service owner — UNASSIGNED
4. Security contact (any SEV1/security event) — UNASSIGNED
5. Incident commander / engineering manager — UNASSIGNED
6. Upstream/downstream owners: INV-64, INV-60, INV-66, Wadm platform — UNASSIGNED
No paging integration is bundled; `alerts.json` `page: true` rules must be wired in the deployment.

## Triage
1. `svc.status()` → `ready`, `leader`, `epoch`, `degraded`, `dependencies`, `controls`, `stalled`, `preflight`.
2. Logs `request_failed` grouped by `code`; `trace_id` from the caller's response.
3. `explain` `{tenant, component}` for recent decisions.
4. Journal: `Journal(state_dir).verify()`-style reopen in a copy to check chain integrity.

## Containment (smallest blast radius first)
| Scope | Action | Effect |
|---|---|---|
| One workload | request op `freeze` `{tenant, component, reason}` (role `sre-operator`) | lifecycle `FROZEN`; `set_desired`/`reconcile`/`rollout` → `INV63-E-FROZEN`; `tick` skips |
| One workload, unsafe | `quarantine` `{tenant, component, reason}` | lifecycle `QUARANTINED`; `INV63-E-QUARANTINED` |
| Whole tenant | `freeze`/`quarantine` `{tenant}` (component defaults to `*`) | all `tenant/*` blocked |
| One lattice host | `svc.quarantine_host(host, True, principal)` (tenant `*`, `control:quarantine`) | host excluded from placement; next `tick` moves instances off |
| Everything | `svc.emergency_disable(True, principal)` (tenant `*`, `control:freeze`) | all automated actions stop; `ready=false` |
| Compromised token key | `TokenAuthority.rotate` new kid, `retire` compromised kid, restart | old tokens rejected |
| Compromised signing key | remove `key_id` from verifier `trusted_keys`, add digests to `revoked_digests`, freeze affected workloads | new deploys of those artifacts rejected; **running instances are not stopped automatically** |

All controls are journaled (`control`, `host_quarantine`, `emergency_disable`) and survive restart. `reconcile_ns` and `op_rollback` honour them.

## Recovery
1. Fix cause (lattice, config, capacity, keys).
2. Release controls: `unfreeze` / `release_quarantine` (lifecycle → `VALIDATED`), `quarantine_host(host, False, principal)`, `emergency_disable(False, principal)`. A `FAILED` workload (rollback incomplete): fix the lattice, then `set_desired` (→ `VALIDATED`) and `reconcile`.
3. `svc.tick()` (resyncs pending offline intents first); confirm convergence (second reconcile no-op).
4. Journal corruption: `BACKUP_RESTORE.md`.
5. Split brain: stop all but one instance; the survivor calls `journal.acquire()` (restart does this only if its handle epoch is 0).

## Postmortem
Within 5 business days (proposed) for SEV1/SEV2: timeline (journal `ts`, decision `trace_id`s), root cause, detection gap, action items with role owners, update to `FAILURE_MATRIX.md`/`THREAT_MODEL.md`. Blameless.

Last exercised: NEVER — game day required
