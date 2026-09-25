# Telemetry, explainability, dashboards and alerts (work item 23 — C052, C071–C080)

## Health (`CatalogueStore.health()`)
`live` (process up) is distinct from `ready` (dependencies probed OK **and** audit sink OK). Also:
version, environment, active digest, active/disabled devices, dependency map, audit head, schema
versions, pending candidates. Stall detection: `ready=false` for > 60 s, or
`last_activation_seconds` > 0.05 s p99 budget, pages SEV3.

## Metrics (`signals()`)
Gauges `catalogue_size`, `surface_registers`, `unreviewed_entries` (must be 0); counters
`surface_growth`, `registration_accepted/rejected`, `replacement_accepted/rejected`, `authn_denied`,
`authz_denied`, `artifact_verification_failed`, `activations`, `activation_failures`, `rollbacks`,
`emergency_disables`; `errors_by_code{code}`; `last_activation_seconds`. The host exporter maps these
to Prometheus/OpenTelemetry names `inv25_<name>` with labels `environment`, `code` only (low cardinality).

## Logs / audit
Every audit event carries stable `environment`, `device`, `actor`, `correlation_id`, `event_type`,
`result`, `error_code`. Tenant/workload identifiers are not logged by INV-25 (estate-level component).

## Tracing
`correlation_id` is accepted on every store call and propagated into audit events, activation records
and the runtime handoff. The host service maps W3C `traceparent` → `correlation_id` and opens spans:
`inv25.validate`, `inv25.authorize`, `inv25.verify_artifact`, `inv25.activate`, `inv25.rollback`.

## Explainability
Every activation/rollback records who proposed, who approved, capability + reason + policy revision,
previous/new digest and surface diff; `explain(activation_id)` returns the operator view with links
to raw audit event IDs.

## Retention / sampling / privacy / export (PROPOSED)
| Stream | Retention | Sampling | Export |
|---|---|---|---|
| Audit events | 7 years, WORM | none | SIEM; failure ⇒ mutations halt |
| Activation history | life of component | none | release evidence |
| Metrics | 13 months | none | TSDB; failure ⇒ local buffer, no halt |
| Logs | 90 days | none for errors, 10% debug | log pipeline |
| Traces | 14 days | 10% head, 100% on error | tracing backend |
Access: audit read requires `catalogue.audit`; residency follows the hosting site.

## Dashboards
1. Load (activations, reads, rate-limit hits). 2. Rejections by `errors_by_code`. 3. Security
(surface_growth, forbidden_class attempts, authn/authz denials, artifact failures). 4. Dependency health
(`ready`, dependency map). 5. Release/config (active digest, version, last activation).

## Alerts
| Alert | Condition | Classification | Sev |
|---|---|---|---|
| Unexpected surface widening | `surface.widened` without linked activation | probable attack | SEV2 |
| Forbidden-class attempts | > 0 in 10 min | policy rejection / probable attack | SEV3 |
| Auth failure burst | authn_denied > 20 / 5 min | probable attack | SEV2 |
| Evidence/audit chain break | verify_chain fails | integrity | SEV1 |
| Incompatible peer | COMPATIBILITY_MISMATCH > 0 | dependency | SEV3 |
| Activation/rollback failure | activation_failures increase | software defect / dependency | SEV2 |
| Saturation | RATE_LIMITED sustained 15 min or pending ≥ 28 | capacity | SEV3 |
| unreviewed_entries > 0 | any | software defect | SEV1 |

Deploying these to the owner's monitoring stack is BLOCKED (no stack access; C080).
