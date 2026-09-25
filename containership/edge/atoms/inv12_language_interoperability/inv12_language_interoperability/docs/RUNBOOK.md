# INV-12 Runbook — rollback and emergency disable (MC-057)

## Signals to watch

* `inv12_mapping_refusals_total`, `inv12_range_violations_total`, `inv12_encoding_refusals_total`,
  `inv12_canonicalization_refusals_total` by `code` — sudden rises indicate a schema/profile mismatch or a
  hostile peer.
* `inv12_boundary_latency_us_bucket` — p99 regression against `ci/bench_thresholds.json`.
* `Health.status()` — `BLOCKED` stops readiness; `DEGRADED` keeps serving.
* Audit events `trust_check_failed`, `provenance_rejected`, `config_rolled_back`.

## A. Roll back a configuration or mapping-profile change

1. Confirm the active revision: `ConfigManager.current.revision` / `.digest`; list history with `provenance()`.
2. `ConfigManager.rollback(actor="<you>")` — atomically restores the previous immutable snapshot; in-flight
   calls finish on the snapshot they started with (no mixed-version call can occur, REQ-G/MC-044).
3. Verify: `Health.status()["state"] != "BLOCKED"`; refusal counters return to baseline; `AuditLog.verify()` is true
   and the last event is `config_rolled_back`.
4. Re-applying the rolled-back document requires a **new, higher revision** with fresh approvals (replay is refused).

## B. Roll back an engine/runtime release

1. Pick the previous release bundle (`evidence/RELEASE_EVIDENCE.json` of that version); verify its
   `source_tree_sha256` against `MANIFEST.sha256` before deploying.
2. Drain: stop admitting new calls (`CapacityController` with zero shares, or remove from the registry).
3. Deploy the previous version on **all** instances of a composition before re-admitting traffic — canonical
   layout and mapping profile must be identical on both sides of every boundary (mixed versions are refused by
   negotiation, MC-015).
4. Re-run `python tools/ci.py --quick` against the deployed artifacts; archive the new `evidence/ci_run.json`
   next to the previous head to keep evidence continuity.

## C. Emergency disable

* Per language: activate a config revision removing the language from `languages` (calls fail closed with
  `PK_INTEROP_UNREPRESENTABLE`).
* Whole component: set health condition `emergency_disabled` (readiness false) and remove INV-12 from the
  registry package; `pk_core gate` reports a reduced element count rather than a silent pass.
* Record `AuditLog.emit("emergency_disable", actor, reason=...)`.

## Known failure signatures

| Signature | Meaning | Action |
|---|---|---|
| `PK_INTEROP_VERSION` spikes after deploy | peers on different profile/ABI | finish rollout or roll back (B) |
| `PK_INTEROP_REALLOC` | guest allocator returned invalid region | quarantine guest artifact; check provenance |
| `PK_INTEROP_BORROW` | callee kept a borrow | guest bug; file against guest owner |
| `PK_INTEROP_TRUST_UNAVAILABLE` | trust service or trusted time down | see playbook P6 |
| `PK_INTEROP_LIMIT` (retryable) | quota/backpressure | scale or tighten tenant shares |

Escalation: on-call INV-12 maintainer → platform security (for T1/T10/T12/T13 classes) → incident commander.
