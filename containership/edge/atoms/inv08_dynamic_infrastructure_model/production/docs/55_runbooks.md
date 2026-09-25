# 55 - Alert runbooks (INV-08)

Paging routes: UNASSIGNED (no on-call rotation exists). Owner: UNASSIGNED.
Definitions: `production/fixtures/dashboards/alerts.json`.

## PoolTickFailing
Severity page. `inv08_tick_errors_total` increasing: Pool.tick rejects inputs or
state (`ValueError`, `PoolInvariantError`, `OverflowError`). Check the decision
journal (`explain.DecisionJournal.query(kind="error")`) for the failing input;
restored state violating invariants means a snapshot is corrupt - restore last
good snapshot, do not hand-edit `nodes`.

## AttestationQuarantine
Severity page. A node produced a replayed nonce, bad quote or PCR mismatch. Keep it
quarantined, preserve evidence, compare event log with golden PCRs; never re-admit
without fresh attestation.

## ArtifactVerificationRejected
Severity page. The artifact gate refused a release or policy bundle. Read the audit
entry (`action=verify`, `outcome=DENY`) for the reason; do not bypass - re-fetch or re-sign.

## ReconcileDrift
Severity ticket. Size differs from target by more than 2 nodes; usually busy nodes
blocking scale-down or provider quota. Check `inv08_pool_leases_renewed_total` and quotas.

## ProviderErrorsElevated
Severity ticket. Provider errors above threshold; check retryable label split and provider status.

## DecisionLatencyHigh
Severity ticket. Mean decision latency above 2 ms (PROPOSED budget). Run `production/bench.py` against baseline.

## MetricsCardinalityCap
Severity info. A metric hit its series cap and series were dropped; find the label with
`telemetry_gov.detect_high_cardinality` and bucket or drop it.

## ExporterScrapeErrors
Severity info. Rendering failed; the exporter served self-health only. Inspect controller logs.

## ExporterAbsent
Severity page. No scrape recorded - the exporter is down or unreachable; the fleet is unobserved.
