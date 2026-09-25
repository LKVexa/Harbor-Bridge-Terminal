# INV-12 Operational Incident Playbook (MC-058)

Each play: **detect → contain → diagnose → recover → evidence**. Never paste payload values into tickets; use
error envelopes (already redacted) and trace ids.

## P1 Mapping refusals surge
* Detect: `inv12_mapping_refusals_total` by `code` / `language`.
* Contain: none needed (fail-closed); if customer impact, roll back the triggering deploy (Runbook B).
* Diagnose: compare `PROFILE_DIGEST` on both sides; `negotiate()` transcripts; `compare(old, new)` for schema drift.
* Recover: align profiles/schemas; bump versions per `check_version_bump`.

## P2 ABI mismatch / negotiation failures
* Detect: `PK_INTEROP_VERSION` / `PK_INTEROP_INCOMPATIBLE`.
* Contain: freeze rollouts. Diagnose offers and policy floors. Recover: deploy adapter or complete major upgrade.

## P3 Corrupted resources (handle errors, borrow leaks, destructor anomalies)
* Detect: `PK_INTEROP_HANDLE`, `PK_INTEROP_BORROW`, table `live()` growth, `dtor_calls` vs creations.
* Contain: emergency-disable the offending guest (config `languages` or registry removal).
* Diagnose: audit `ownership_violation` events; reproduce with `ConcurrencyLeakTest` patterns.
* Recover: redeploy fixed guest; verify tables drain to zero.

## P4 Performance regression
* Detect: p99 over `ci/bench_thresholds.json × tolerance`; `DEGRADED` health.
* Contain: capacity shares down; roll back (Runbook B). Diagnose with `tools/bench.py` on the same host class.

## P5 Isolation-breach indicators
* Indicators: `PK_INTEROP_MEMORY_BOUNDS/OVERFLOW/ALIGNMENT`, `PK_INTEROP_REALLOC` from a guest that previously
  behaved; provenance rejections.
* Contain immediately: emergency disable the guest; preserve memory snapshot + audit log (hash chain).
* Escalate to platform security; treat as T1/T10/T13 per `THREAT_MODEL.md`.
* Recover only after artifact provenance is re-verified against `evidence/artifact_policy.json`.

## P6 Trust-service or trusted-time outage
* Expected behaviour: privileged actions fail closed; previously verified tokens continue for `grace_s`
  (`DEGRADED`); loss of trusted time fails everything closed (`BLOCKED`).
* Do **not** widen `grace_s` during an incident without a quorum-approved config revision.

## Evidence after every incident
Archive: error envelopes, `Metrics.exposition()`, `Tracer.export()`, `AuditLog.records` + `verify()` result,
config `provenance()`, and a fresh `tools/ci.py --quick` run.
