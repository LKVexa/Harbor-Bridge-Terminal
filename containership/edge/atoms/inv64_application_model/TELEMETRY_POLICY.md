# Telemetry governance (MC-26; C079-C080)

**Owner:** `inv64-sre-oncall` (unassigned). **Privacy reviewer:** `inv64-security-contact` (unassigned). Contract: `PK_APP_TELEMETRY/1` (`telemetry.py`).

## Data classes

| Class | Examples | Allowed in metrics | Allowed in logs/traces | Export |
|---|---|---|---|---|
| public | component version, contract versions | yes | yes | any approved backend |
| internal | operation, outcome, error code, digests, revision IDs, correlation/trace IDs | low-cardinality only | yes | approved backends in the same residency region |
| sensitive | tenant, workload, actor, app name, provider names, topology | **never** as labels | yes, tenant-scoped views | same region only; tenant-scoped access |
| secret-prohibited | credentials, tokens, keys, secret values, manifest payloads | never | never (redacted at emit) | never |

Enforcement: metric labels are fixed per metric in `telemetry.METRICS` (a new label is a reviewed contract change); ≤ 200 series per metric with an overflow series; logs pass `redaction.redact`; decision records carry digests, never payloads.

## Retention and deletion

| Stream | Retention | Notes |
|---|---|---|
| metrics | 400 days (downsampled after 30 days) | no personal data by construction |
| structured logs | 30 days hot, 90 days cold | tenant-scoped deletion on tenant offboarding |
| traces | 7 days (errors/security events 30 days) | |
| decision records | 180 days | needed for incident reconstruction |
| audit ledger | ≥ 3 years, immutable (WORM) | security evidence; not telemetry; never sampled |
| release evidence | lifetime of the release line + 3 years | |

## Sampling

Head sampling 10% for successful requests; **100%** for errors, rejections with security codes (`auth.*`, `authz.*`, `tenant.*`, `secret.*`, `artifact.*`, `crypto.*`), `internal`, activation/rollback, and anything with a correlation ID under active incident. Sampling never applies to the audit ledger.

## Export and residency

Exporters run in the host process region; cross-region export of *sensitive* class data requires a documented legal basis and the security contact's approval (ops/REVIEWS.json policy review). External SaaS telemetry providers need a privacy review before use (not yet performed — MC-26 blocker).

## Dashboards and alerts

`dashboards/inv64-overview.json` and `ops/alerts.json` are versioned as code; `tools/governance_check.py` fails when an alert/dashboard references a metric outside the catalog, lacks an owner/route/runbook, or points at a missing runbook anchor. Alert classes distinguish: SLO burn (multi-window), overload, dependency outage, policy-rejection spike, attack pattern (auth failures/replay), software defect (`internal`), audit integrity, change safety (auto-rollback), telemetry self-health (drops, sink errors, absent series), crypto failures.

Suppression: needs reason, owner and an expiry ≤ 7 days; recorded in `ops/alerts.json` `suppression.active`; expired suppressions are ignored.

Not yet done (MC-26 blockers): end-to-end alert routing test to a real pager, exporter outage drill in production, privacy review.
