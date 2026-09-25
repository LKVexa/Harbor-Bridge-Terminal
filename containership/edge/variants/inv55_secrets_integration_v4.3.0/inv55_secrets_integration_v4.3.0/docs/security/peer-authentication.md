# Peer and provider authentication

| ID | INV55-SEC-PEERAUTH | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: security-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

| Peer | Mechanism | Code | Status |
|---|---|---|---|
| Workload → INV-55 | HS256 JWT (iss/aud/nbf/exp/tenant) | `HmacJwtAuthenticator` | Implemented |
| INV-55 → Vault: server identity | TLS >= 1.2, CA bundle, hostname check | `build_tls_context(ca_file)` | Implemented |
| INV-55 → Vault: client identity | Vault token via `TokenAuth` (dev only; refused in prod by `bootstrap.py`), `AppRoleAuth`, `KubernetesAuth` | `vault.py` | Implemented; AppRole tested `test_approle_login_and_namespace_header` |
| INV-55 → Vault: mTLS | client cert/key loaded into SSL context | `build_tls_context(client_cert, client_key)` | Implemented (Vault TLS-cert auth method login NOT IMPLEMENTED) |
| Token freshness | re-login at 0.67×TTL; 401/403 clears token | `_ensure_token`, `_request` | Implemented; `renew_self` tested (`tests/test_vault_adapter.py::VaultHttp.test_lease_revoke_renew_and_token_renew`) but not scheduled by the service |
| Peer SPIFFE / SVID | — | — | NOT IMPLEMENTED (plug in via `Authenticator` protocol) |
| OIDC / JWKS asymmetric tokens | — | — | NOT IMPLEMENTED |
| Workload key rotation (multi-key) | — | — | NOT IMPLEMENTED (single `key`) |

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-22 | Test evidence |
