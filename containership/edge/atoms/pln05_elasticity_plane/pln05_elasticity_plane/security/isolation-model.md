# PLN-05 isolation model

| Domain | Mechanism in this package | Enforced by deployment (SHALL) |
|---|---|---|
| tenant | every scope key is `tenant/site/workload` derived from the authenticated message *after* `authorize()` checks the credential's tenant; explain/status filter by the caller's tenant | separate state_dir per trust zone if tenants must not share a host volume |
| workload | one `ElasticityController` per scope; never shared | — |
| site | credential `sites` scope checked; site ceilings via GAP-10 | per-site plane instances for edge |
| process | no sockets, no subprocesses, no env reads; files only under `state_dir`, `config_dir`, `audit_path` | non-root UID, read-only rootfs, drop all Linux capabilities, seccomp default, no devices, no host network |
| state store | HMAC envelope per scope file; file name = sha256(scope) so tenant identifiers cannot select paths | volume encryption (see crypto policy), 0700 directory |
| metrics | no tenant/workload label values (allowlist), series cap | per-tenant telemetry separation in the backend |
| audit | append-only chain, HMAC-anchored head | write-once storage for the durable sink |

**Multi-tenant instance model:** one plane instance MAY serve many tenants; separation is logical (scope keys, per-scope controller objects, per-scope files). Where tenants require physical separation, deploy one instance per tenant — the configuration is identical.

Tests: `tests/security/test_adversarial.py::test_T06_cross_tenant_and_site`, `test_T08_injection_surfaces`, `test_T16_leakage`; `tests/test_units.py::StateTest.test_round_trip_and_scope_isolation`.
