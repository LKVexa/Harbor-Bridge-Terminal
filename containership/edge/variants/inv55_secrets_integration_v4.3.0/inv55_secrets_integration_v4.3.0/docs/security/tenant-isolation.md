# Tenant isolation

| ID | INV55-SEC-TENANT | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: security-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

- Tenant comes only from the authenticated token claim (`Principal.tenant`).
- Provider path is `f"{tenant}/{name}"` (`resolve`, `rotate`, `retire`); the tenant prefix is always prepended. Names and app ids with empty, `.` or `..` segments are rejected INVALID_REFERENCE (`service.py::valid_path_segments` in `_ident`) — threat E-7, `tests/test_security_adversarial.py::Elevation.test_path_traversal_in_names_rejected`.
- The tenant claim itself must match `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$` (no `/`), so a token cannot name a nested tenant (`HmacJwtAuthenticator.authenticate`) — threat E-8, `tests/test_security_adversarial.py::Elevation.test_tenant_claim_cannot_contain_path_separator`.
- Policy rules match `r.tenant == p.tenant` (`PolicyEngine.decide`).
- Scopes (`_scopes`), cache (`_cache`), retirements (`_retired`), idempotency (`_idem`, keyed `tenant/name/key`) and per-subject lease counts are keyed by tenant.
- Leases are bound to tenant; `use`/`revoke` reject other tenants (CONTEXT_MISMATCH).
- Quota buckets are charged to the authenticated tenant/subject (`AdmissionController.charge` in `_guard`); evidence `tests/test_security_adversarial.py::Elevation.test_quota_charged_to_authenticated_tenant`, `test_cross_tenant_read_denied`.
- Not isolated: process memory, CPU, the single Vault identity (all tenants share INV-55's Vault token; Vault policy should limit it to tenant prefixes), audit file (shared, contains tenant field).

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-23 | Path-segment validation; tenant claim format |
| 4.3.0 | 2026-09-22 | Quota bound to authenticated tenant |
