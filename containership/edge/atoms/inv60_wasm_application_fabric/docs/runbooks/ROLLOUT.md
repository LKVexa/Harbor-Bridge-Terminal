# Canary / staged rollout, rollback, emergency disable (M31/M78)

| Stage | Scope | Hold | Abort if |
|---|---|---|---|
| 0 canary | 1 host, internal tenant | 30 min | any `DIGEST_MISMATCH`/`SIGNATURE_INVALID`/`INTERNAL`; p99 call > 3 ms; failover > 10 s |
| 1 | 10 % hosts | 2 h | error ratio > 0.1 %; any SEV1/SEV2 alert |
| 2 | 50 % hosts | 12 h | same |
| 3 | 100 % | — | — |

**Config rollback:** `ConfigController.rollback(actor)` re-activates the previous revision as a new generation (monotonic; idempotent). Failed commit or unhealthy targets roll back automatically (compensation to the prior generation).
**Deployment rollback:** re-start the previous artifact ref — it goes through the same signature/provenance admission as a forward deploy.
**Emergency disable:** `set_mode(frozen)` (no mutations; calls continue), `quarantine(target)` (component or host isolated, links suspended). Both are ledgered and require an operator.
**Manual recovery when automation is unsafe:** freeze, snapshot state (`BACKUP_RESTORE.md`), restore last-known-good config revision explicitly, release freeze.
**Status:** written, never rehearsed (W-DRILLS).
