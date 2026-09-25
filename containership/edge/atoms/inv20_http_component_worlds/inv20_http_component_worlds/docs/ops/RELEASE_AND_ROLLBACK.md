# Release, rollout, rollback and emergency controls (component 21)

Artifact: wheel + sdist from `tools/release.py`, SHA-256, CycloneDX SBOM, provenance statement
(**unsigned** until signing infrastructure exists), evidence bundle from `evidence_gate collect`.

Rollout rings: canary 1 % (1 site, 1 h) → 10 % (4 h) → 50 % (12 h) → 100 %. Stage advance requires
gate verdict GO for the exact artifact digest plus: error rate Δ < 0.5 pp, dispatch p99 < 1 ms,
zero policy-bypass alerts, no crash loops. Scoping by tenant/site/environment via config overlays.

Automatic rollback triggers: readiness false > 2 min, error-rate/tail-latency thresholds, any
security-policy bypass alert, crash loop, resource regression > 20 %; 15-min hysteresis before re-advance.

Operator controls (all audited):
- `ConfigStore.rollback(operator)` — previous known-good configuration;
- artifact rollback — redeploy previous digest (previous evidence bundle stays addressable);
- `CapabilityStore.revoke_all()` — emergency disable of all outgoing HTTP;
- `CapabilityStore.quarantine(tenant[, workload])` — isolate a tenant/workload;
- `HealthMonitor.quarantine(reason)` — take an instance out of traffic.

Drills (canary, failed-canary auto-rollback, manual rollback, downgrade, emergency disable, partial
fleet reconciliation): **not executed** — require a deployment fleet.
