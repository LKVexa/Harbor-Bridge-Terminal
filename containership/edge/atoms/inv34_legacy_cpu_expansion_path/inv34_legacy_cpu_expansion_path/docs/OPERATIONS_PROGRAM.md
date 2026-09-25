# INV-34 operations programme — DRAFT, no owner (MC-002, MC-062, MC-067, MC-068)

Every role below is UNASSIGNED (`governance/OWNERS.json`). This file is a template for the rights holder to adopt, not an operating commitment.

## Support and error budget (MC-062)
* SLOs (PROPOSED): 99% of accepted expansions converge (guest-observed) within 60 s p95; duplicate hot-add = 0 (safety invariant, any breach is Sev1).
* Error-budget policy: >50% burn in 7 d freezes feature rollout; >100% freezes all non-fix changes.
* Support hours / paging destination: UNASSIGNED.

## Incident procedure (MC-067)
| Sev | Examples | Containment |
|---|---|---|
| 1 | duplicate or regressive CPU action, cross-tenant expansion, audit chain break | freeze expansion; preserve store + audit; verify chain head |
| 2 | stalled convergence fleet-wide, adapter UNKNOWN surge, degraded mode > 30 min | freeze new expansion at affected site |
| 3 | capacity/quota rejections above forecast | capacity review |
Recovery: reconcile against live hypervisor + guest state (`tools/runbook.py day2`), never restore state blindly.

## Recurring reviews (MC-068)
Quarterly: access grants (`CapabilityPolicy`), config provenance, dependency lock/SBOM diff, compatibility matrix, waivers nearing expiry, threat model. Evidence: one JSON record per review under `governance/reviews/` (none exist yet).
