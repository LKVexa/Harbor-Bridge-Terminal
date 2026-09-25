# Quota and fairness model

| ID | INV55-ARCH-QUOTA | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: service-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

Implemented by `resilience.py::AdmissionController` and `service.py::ServiceLimits` in two stages:

1. `AdmissionController.admit()` — global in-flight cap, in `SecretsService._run` **before** authentication (load shedding).
2. `AdmissionController.charge(tenant, workload)` — per-tenant/per-workload token buckets, in `SecretsService._guard` **after** authentication, keyed on the authenticated `Principal.tenant` and `Principal.subject`.

| Control | Default | Scope | Error |
|---|---|---|---|
| `max_in_flight` | 256 | process | OVERLOADED (429, 250 ms) |
| `tenant_rate` / `tenant_burst` | 200/s / 400 | per tenant token bucket | QUOTA_EXCEEDED (429, 1000 ms) |
| `workload_rate` / `workload_burst` | 50/s / 100 | per tenant/workload | QUOTA_EXCEEDED |
| `max_tracked_keys` | 10 000 buckets | process | OVERLOADED |
| `max_active_leases` | 100 000 | process | OVERLOADED (after purging expired/revoked) |
| `max_leases_per_subject` | 1 000 | tenant+subject | QUOTA_EXCEEDED |

Rules:

- Workload bucket is taken before tenant bucket; one workload cannot exceed 50/s even if the tenant has headroom, so no single workload can consume more than 25% of its tenant's sustained rate.
- Buckets are never evicted; once `max_tracked_keys` is reached, new tenant/workload keys are rejected OVERLOADED.
- Buckets are charged only to authenticated principals, so request fields cannot spend another tenant's quota (WVR-009 CLOSED; evidence `tests/test_security_adversarial.py::Elevation.test_quota_charged_to_authenticated_tenant`, `tests/test_resilience.py::AdmissionTests.test_fairness_isolated_per_tenant`).
- Unauthenticated requests consume only a global in-flight slot, not a bucket; they are not rate-limited per source (NOT IMPLEMENTED).
- Quotas are per process; there is no cluster-wide or provider-side quota allocation. NOT IMPLEMENTED.
- Per-tenant tuning (`contract.py` optional) requires constructing `AdmissionController` with different parameters; per-tenant overrides are NOT IMPLEMENTED.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-22 | Admission split into admit()/charge(); quotas bound to authenticated principal |
