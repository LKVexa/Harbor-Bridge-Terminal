# INV-09 operations: M33–M44

## M33 Health / readiness
`Gate.health()` → `PK_HEALTH/1`. `ready` requires a loaded bundle and a passing self-test (valid empty
module accepted, bad version refused). Expose it as the readiness probe; route no traffic while `degraded`.

## M34 Metrics (Prometheus text via `Gate.metrics.exposition()`)
* `inv09_validations_total{outcome,profile,cache,code}` — label values are closed sets; unknown values
  collapse to `other` (bounded cardinality).
* `inv09_validation_latency_ms_bucket{profile,le}`.
* Cache: `hits`, `misses`, `evictions`, `integrity_failures` attributes on `ValidationCache`.

## M35/M36 Logs and traces
JSON logs (`telemetry.JsonFormatter`), every field sanitised; module identity is always the digest.
W3C `traceparent` is accepted on `validate(..., traceparent=)`; malformed headers mint a fresh trace.
`trace_id`/`span_id` are returned in every verdict and written into audit events.

## M27 Audit
`AuditStream` is append-only and hash-chained; `telemetry.verify_chain` detects deletion, reordering and
edits. Events: `config.activated|rejected`, `validation.accept|reject|refuse|error`,
`admission.granted|refused`, `execution.started|refused`.

## M37 Explain view
`telemetry.explain(verdict)` renders reason, byte offset, section, remedy and feature evidence.

## M38 Dashboards and alerts
`ops/alerts.yml` (Prometheus rules) and `ops/dashboard.json` (panel list). Each alert links a runbook.

## M39 Rollout
`prod/canary.py`: shadow → 1% → 10% → 50% → 100%. Promotion is blocked by any widening (candidate
accepts what incumbent refused), any candidate `error`, or unacknowledged narrowing.

## M40 Runbooks
| ID | Trigger | Steps |
|---|---|---|
| RB-01 | Unexplained refusal reported by tenant | 1. `explain(verdict)`. 2. Re-run `validate_module` locally on the bytes (digest must match). 3. If code is `UNSUPPORTED_PROPOSAL`, point tenant to profile docs. 4. If a genuine false reject, file defect + add module to `tests/oracle_corpus.py`. |
| RB-02 | `INTERNAL_ERROR` > 0 | Page owner. Module was refused (safe). Capture digest + trace id; reproduce; add regression; hotfix via canary. |
| RB-03 | `DEADLINE_EXCEEDED` rate > 1% | Check CPU saturation; check module sizes; do **not** raise limits without an ADR; scale out. |
| RB-04 | Suspected signing-key compromise | `Verifier.revoke(key_id)` on all admitters; rotate key; bump bundle epoch (invalidates caches and tickets); re-validate. |
| RB-05 | Bad bundle activated | Activate previous signed bundle with a **higher** epoch (rollback-by-roll-forward); `ConfigStore.reconstruct` for history. |
| RB-06 | Differential false-accept found | Sev-1. Revoke affected profiles (bundle with feature removed), re-validate cache, patch, add to corpus. |
| RB-07 | Cache integrity failures > 0 | Treat as memory-corruption/tamper indicator: drain node, collect core, restart. |

## M41 Vulnerability response and EOL
Security reports → owner within 1 business day; Sev-1 (false accept, attestation bypass) fix or
feature-revocation within 72 h. A validator version is EOL 180 days after its successor ships; EOL
versions are removed from the admitters' accepted `validator` set by bundle update.

## M42–M44 Configuration
`ConfigStore` records every activated signed bundle (hash-chained, fsync'd). Activation order is
signature → schema → epoch → atomic swap; any failure leaves the old configuration live.
**Backup:** copy the store file (it is self-verifying). **Restore test:** `ConfigStore.reconstruct(epoch)`
(exercised in `ConfigTest`).
