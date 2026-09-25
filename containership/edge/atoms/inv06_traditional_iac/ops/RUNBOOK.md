# INV-06 Operations and Incident Runbook (MC-066, CHK-030/047)

Status: **Draft — severity/paging destinations depend on `governance/OWNERS.yaml`.**

## Install / configure
`pip install .` from the package directory (no runtime deps). Choose a state root on a local POSIX filesystem (not a sync folder). Configure `StaticKeyProvider` only for tests; bind `KeyProvider` to KMS in production.

## Normal operation
plan → policy → approve (different principal) → acquire lease → execute → apply → commit → audit/provenance/lineage. Check `health_status()["ready"]`.

## Faults
| Symptom (code) | Meaning | Action |
|---|---|---|
| `PK_IAC_STALE_PLAN` | state moved | re-plan; never force |
| `PK_IAC_STATE_CONFLICT` | another writer committed | reload HEAD, re-plan |
| `PK_IAC_STATE_CORRUPT` | revision digest/chain failure | freeze scope; `restore()` from latest verified backup into empty dir; compare; switch root |
| `PK_IAC_LEASE_LOST` / `FENCING_VIOLATION` | writer paused past lease | discard in-flight result; drift scan; re-plan |
| `PK_IAC_POLICY_UNAVAILABLE` | GAP-13 down | mutations blocked by design; restore policy service |
| `PK_IAC_SECURITY_DEPENDENCY_UNAVAILABLE` | identity/keys/audit down | per OUTAGE_POLICY; only freeze allowed |
| `PK_IAC_OVERLOADED` / `CIRCUIT_OPEN` | saturation / provider failing | back off; check provider status |
| partial `execute_plan` | provider failed mid-run | do not commit; `drift(provider.list())`; re-plan from reality |
| watchdog `stalled` | op without progress | cancel token; inspect provider; freeze if unsafe |

## Recovery verification
`FileStateBackend.verify_chain()`, `SignedAuditLog.verify()`, `ProvenanceLedger.verify()`, drift scan returns `{}`.

## Rollback / upgrade
State: `rollback_to(serial, expected_serial=HEAD, actor, reason)`. Package: `CanaryRollout` with previous version; state schema majors need `migrate_snapshot`.

## Incident response
Severity: Sev1 = unsafe mutation or state loss; Sev2 = mutations blocked; Sev3 = degraded telemetry. Contain: `FreezeController.freeze("*")`. Preserve: `SignedAuditLog.export()`, backup archive, provenance ledger. Recover per table above. Communicate via owner channel. Post-incident review within 5 business days recorded in `governance/WAIVERS.json` review_log.
