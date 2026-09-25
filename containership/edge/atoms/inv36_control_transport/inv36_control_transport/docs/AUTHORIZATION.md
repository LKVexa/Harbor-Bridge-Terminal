# Authorization and tenant policy (MC-07)

Implementation: `policy.py`; enforced in `endpoint.ControlEndpoint._dispatch` after authentication/decoding and before admission and handlers.

## Model

- **Principals** come only from the handshake credential: `subject`, `role` (`host_agent`, `guest_agent`, `node`, `service`, `operator`, `relay`), `tenant`. Caller-supplied tenant IDs inside messages are *targets*, never identity.
- **Operations -> capabilities** (`policy.OPERATIONS`): PLACEMENT `ctrl.placement.write`, LEASE_GRANT `ctrl.lease.grant`, LEASE_RENEW `ctrl.lease.renew`, LEASE_REVOKE `ctrl.lease.revoke`, HEARTBEAT `ctrl.heartbeat`, DRAIN `ctrl.drain`, STATUS_QUERY `ctrl.status.read`, ERROR_REPORT `ctrl.error.report`; plus `ctrl.break_glass`. An import-time guard fails if a registered message type lacks a mapping.
- **Rules**: effect (allow/deny), roles, capabilities, tenants (`$self` = principal's tenant; explicit tenant IDs; `*`), optional subjects, `approved_by`.
- **Precedence**: any matching deny wins; otherwise any matching allow; otherwise `cross_tenant_default_deny` or `default_deny`. Active quarantine overrides allow (checked first). Relays can never be authorized.
- **Wildcards and break-glass** allow-rules are rejected at load unless `approved_by` names the security owner's approval.
- **Versioning**: policy documents carry `version`, `issued_at`, `expires_at`. Loading an older or equal version is refused (`AUTHZ_POLICY_ROLLBACK`) unless a recovery authorization is supplied. Expired or absent policy => every decision is `policy_unavailable` (fail closed).
- **Decisions** are typed (`Decision(allow, reason, policy_version, capability, operation)`), audited (`authz.decision`) and rate-limited on repeated denials per subject (`AUTHZ_RATE_LIMITED`) without hiding the denial.

## Baseline policy (`default_policy`)

| Role | Allowed in own tenant | Explicitly denied |
|---|---|---|
| host_agent, node | PLACEMENT, LEASE_*, DRAIN, STATUS_QUERY, HEARTBEAT | - |
| guest_agent | LEASE_RENEW, HEARTBEAT, STATUS_QUERY, ERROR_REPORT | DRAIN, PLACEMENT, LEASE_GRANT |
| service | STATUS_QUERY, HEARTBEAT | - |
| operator, relay | nothing by default | - |

## TOCTOU

Authorization and the handler run in the same call with the immutable decoded message; handlers that mutate shared resources must re-check resource ownership under their own lock using the `Principal` passed to them.

Tests: `tests/test_control_planes.py::AuthorizationTest`, `tests/test_endpoint_integration.py::FullStackTest`.
