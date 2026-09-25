# Telemetry policy (C073, C075, C079, C080)

* Tenants appear only as `t:<sha256[:12]>`; scratch contents never leave the instance.
* Retention/sampling/export — **PROPOSED**: logs 14 days, metrics 90 days, audit chain
  per parent-platform retention; no sampling of audit or error records.
* Alerts distinguishing conditions (C080), by signal:
  - ordinary load: `saturation.utilisation` rising, errors flat
  - degradation: `degraded` non-empty
  - policy rejection: `errors.INV31-E-AUTHZ` / `-QUOTA`
  - dependency failure: `errors.INV31-E-DEPENDENCY-UNAVAILABLE`
  - attack: `errors.INV31-E-AUTHN` / `-REPLAY` bursts (audited)
  - internal bug: any `errors.INV31-E-INTERNAL`
  Dashboards themselves live in GAP-09 and were not built (no sink supplied).
