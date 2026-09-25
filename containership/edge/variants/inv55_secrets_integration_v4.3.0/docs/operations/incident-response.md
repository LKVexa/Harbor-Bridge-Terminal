# Incident response

| ID | INV55-OPS-IR | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: operations-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

Escalation: `<UNASSIGNED: on-call-rotation>` → `<UNASSIGNED: service-owner>` → `<UNASSIGNED: security-owner>`. Severity timers in OWNERSHIP.md.

## 1. Secret leak (value exposed)
1. Rotate immediately: `rotate` with new value and `expected_version`.
2. `retire(version=<leaked>, destroy=true)` on every instance (retirements persist per instance via `state_path` but are not replicated; destroy makes it global in Vault KV v2).
3. `revoke` known leases (a `secret-admin` may revoke any subject's lease in the tenant; audited `revoked_by_admin`); or `set_scope` to narrow, which revokes removed subjects' leases.
4. Plaintext already delivered cannot be recalled; revoke the credential at its issuing system.
5. Use `DecisionLedger.explain(request_id)` and audit file to identify `use` calls for the version.

## 2. Provider outage
1. Confirm via `health()["dependencies"]["provider"]` and `circuit`.
2. Offline-deny is the default. Do NOT raise `stale_grace_s` without owner waiver.
3. Existing leases keep working until expiry; new resolves fail PROVIDER_UNAVAILABLE.
4. Escalate to Vault owners `<UNASSIGNED: vault-platform-team>`.

## 3. Audit chain break
1. `verify_chain` returns `chain break`/`hash mismatch` at seq N.
2. At boot this is automatic: `bootstrap.build_service` quarantines on `resume_from_file` failure (`state_reason: audit_chain_divergence`). At runtime, call `quarantine("audit_chain_break")` manually (revokes all leases; requests return FROZEN); runtime detection is NOT IMPLEMENTED.
3. Preserve the file (copy, hash). Since chains now resume across restarts, any break is suspicious and MUST be treated as possible tampering.
4. Start a new audit file; to resume service: `freeze` then `unfreeze` with a `platform`-tenant operator credential (attempts are audited; review them for unexpected actors).

## 4. Key compromise
- **Workload signing key**: any principal can be forged. Freeze all instances, replace `HmacJwtAuthenticator.key` (restart), reissue tokens. Multi-key overlap NOT IMPLEMENTED — expect downtime.
- **Audit HMAC key**: chain forgeable; rotate key, start new file, record old head.
- **Vault AppRole secret_id / token**: revoke in Vault, issue new secret_id, restart.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-23 | Platform operator; admin revoke |
| 4.3.0 | 2026-09-22 | Boot-time audit quarantine |
