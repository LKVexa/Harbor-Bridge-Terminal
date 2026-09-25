# Dependency-outage matrix

| ID | INV55-SEC-DEPOUTAGE | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: security-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

| Dependency | Outage behaviour | Code | Fail-closed? |
|---|---|---|---|
| Vault (read) | PROVIDER_UNAVAILABLE after retries/breaker; stale cache only if `stale_grace_s>0` | `_provider_call`, `resolve`; `tests/test_resilience.py::FaultInjection` | Yes (default) |
| Vault (write/destroy/revoke) | PROVIDER_UNAVAILABLE | `rotate`, `retire`, `revoke` | Yes |
| Vault auth (AppRole/K8s login) | login error → ProviderError → PROVIDER_UNAVAILABLE / DENIED | `_ensure_token` | Yes |
| Identity issuer | tokens already issued still verify (local HMAC); no online check | `HmacJwtAuthenticator` | N/A (revocation of tokens NOT IMPLEMENTED) |
| Authorization (INV-59) | Local `PolicyEngine`; no remote PDP | `PolicyEngine` | N/A |
| Audit sink | AUDIT_UNAVAILABLE for every op | `_audit` | Yes |
| Clock | CLOCK_ROLLBACK | `_now` | Yes |
| DNS | transport error → ProviderUnavailable | `urllib_transport` | Yes |
| Config | start → QUARANTINED if none active | `start` | Yes |
| Audit file diverged at boot | QUARANTINED | `bootstrap.build_service` | Yes |
| State file unreadable/bad format | `SecretsService.__init__` raises; service not constructed | `_load_state` | Yes |
| Metrics/log/trace sinks | in-process; logger stream failure propagates as exception | `JsonLogger.log` | Not isolated (gap) |
| KMS/HSM | via Vault seal → Vault sealed → unreachable | `VaultProvider.health` | Yes |

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-22 | Audit/state file rows; tests |
