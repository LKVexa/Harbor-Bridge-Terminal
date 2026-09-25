# Threat model (STRIDE)

| ID | INV55-SEC-THREAT | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: security-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

## Assets
Secret values; workload signing key (`HmacJwtAuthenticator.key`); Vault token / AppRole secret_id; audit log and HMAC key; policy rules, scopes, state file.

## Trust boundaries
- **TB1** Caller → `SecretsService` (untrusted input, workload token).
- **TB2** `SecretsService` → Vault (network, TLS).
- **TB3** `SecretsService` → audit sink / state file / logs / metrics / traces.
- **TB4** Operator → service (freeze/unfreeze, config, bootstrap).

Threat IDs S-*, E-*, I-*, T-2, T-3, R-1, D-3 match the docstrings in `tests/test_security_adversarial.py`. Other IDs are defined here. `tests/` paths below are relative to repo root; `SA` = `tests/test_security_adversarial.py`.

| ID | TB | STRIDE | Threat | Control (code) | Test |
|---|---|---|---|---|---|
| S-1 | TB1 | S | Forged token `alg=none` | HS256 only (`HmacJwtAuthenticator.authenticate`) | `SA::Spoofing.test_alg_none_rejected` |
| S-2 | TB1 | S | Tenant switch by editing claims | HMAC over header.body, `compare_digest` | `SA::Spoofing.test_tampered_claims_rejected`; `tests/test_property_fuzz.py::Fuzz.test_jwt_bitflip_never_authenticates` |
| S-3 | TB1 | S | Expired credential replay | `exp`/`nbf` ± leeway | `SA::Spoofing.test_expired_token_rejected` |
| S-4 | TB1 | S | Parser abuse (oversize/garbage token) | `max_token_bytes`, structure checks | `SA::Spoofing.test_oversized_and_garbage_credentials` |
| S-6 | TB2 | S | MITM / fake Vault | TLS >= 1.2, `CERT_REQUIRED`, hostname | `tests/test_vault_adapter.py::VaultTls.test_verified_tls`, `test_untrusted_ca_refused`, `test_min_tls_version` |
| S-5 | TB1 | S | Malformed signed claims (non-object header/claims, bad sub/tenant/roles) | claim validation → UNAUTHENTICATED, audited | `tests/test_security_adversarial.py::Spoofing.test_malformed_signed_claims_are_unauthenticated_and_audited` |
| T-1 | TB2 | T | Downgrade to HTTP | non-loopback http refused | `tests/test_vault_adapter.py::VaultHttp.test_plain_http_refused_for_non_loopback` |
| T-2 | TB1 | T | Control chars into audit via identifiers | `_ID` regex | `SA::Disclosure.test_log_injection_blocked` |
| T-3 | TB1 | T | Clock rollback extends lease | `_now` | `SA::FailClosed.test_clock_rollback_denies` |
| T-4 | TB3 | T | Audit tampering / deletion / reorder | hash/HMAC chain, `verify_chain`, `resume_from_file` → boot quarantine | `tests/test_config_audit_telemetry.py::AuditTests.test_chain_verifies_and_detects_tamper_delete_reorder`, `test_file_sink_resume` |
| T-5 | TB4 | T | Credential in config | `_CREDENTIAL_KEYS` | `tests/test_config_audit_telemetry.py::ConfigTests.test_rejects_plaintext_credentials_and_unknown_keys` |
| T-6 | TB4 | T | Unsigned release artifact | NONE — signing NOT IMPLEMENTED | — (WVR-003) |
| R-1 | TB3 | R | Access without audit | fail-closed `_audit` | `SA::FailClosed.test_audit_sink_failure_denies`; `tests/test_config_audit_telemetry.py::AuditTests.test_service_audit_is_complete_and_secret_free` |
| I-1 | TB1/3 | I | Value in audit/metrics/traces/ledger/health/errors | `SecretValue`, fixed messages, bounded labels | `SA::Disclosure.test_secret_never_in_any_diagnostic` |
| I-2 | TB1 | I | Errors echo caller input | fixed `message` in `to_wire`; INTERNAL hides exception text | `SA::Disclosure.test_error_payload_is_fixed_text`; `tests/test_resilience.py::FaultInjection.test_unexpected_exception_fails_closed` |
| I-3 | TB1 | I | Plaintext via str ops / pickle / copy | `SecretValue` | `SA::Disclosure.test_secret_value_not_str_and_not_serialisable` |
| I-4 | TB1 | I | Residual plaintext in memory | `SecretValue.wipe` (best effort) | `SA::Disclosure.test_wipe_zeroises_buffer` |
| I-5 | TB3 | I | Credentials in logs | `redact_text` in `JsonLogger` | `SA::Disclosure.test_logger_redacts_credential_shapes` |
| I-6 | TB1 | I | Existence oracle | NotFound/Denied → DENIED | `tests/test_service_contract.py::ResolveUseContract.test_unauthorized_and_missing_are_indistinguishable` |
| I-7 | TB2 | I | Vault token leak | token only in header | `tests/test_vault_adapter.py::VaultHttp.test_token_never_in_url_or_body` |
| I-8 | TB3 | I | Secret names in exported telemetry | names not in metrics; `pseudonymise` available, not wired to an exporter | `tests/test_config_audit_telemetry.py::AuditTests.test_pseudonymise_is_keyed_and_stable` (function only) |
| D-1 | TB1 | D | Request flood | `admit()` global cap | `tests/test_resilience.py::AdmissionTests.test_global_shed` |
| D-2 | TB2 | D | Vault outage / oversize response | retry, breaker, offline-deny, `MAX_RESPONSE_BYTES` | `tests/test_resilience.py::FaultInjection.test_circuit_opens_and_sheds_provider_load`, `test_offline_default_is_deny` |
| D-3 | TB1 | D | Spoofed request fields exhaust another tenant's quota | `charge()` on authenticated principal | `SA::Elevation.test_quota_charged_to_authenticated_tenant` |
| D-4 | TB1 | D | Malformed input crashes service | non-dict → INVALID_REFERENCE; catch-all INTERNAL; tolerant traceparent | `tests/test_property_fuzz.py::Fuzz.test_public_api_never_raises_and_never_leaks` |
| E-1 | TB1 | E | Cross-tenant read | tenant-prefixed path, rule tenant match | `SA::Elevation.test_cross_tenant_read_denied` |
| E-2 | TB1 | E | Lease replay by other workload | `use` context checks | `SA::Elevation.test_lease_replay_by_other_app` |
| E-3 | TB1 | E | Lease replay cross-tenant | same | `SA::Elevation.test_lease_replay_cross_tenant` |
| E-4 | TB1 | E | Consumer rotates/scopes | `ROLE_ACTIONS` + rules | `SA::Elevation.test_consumer_cannot_rotate_or_scope` |
| E-5 | TB1 | E | Glob injection in names | `_ID` excludes `*?[]` | `SA::Elevation.test_glob_injection_in_name` |
| E-7 | TB1 | E | Path traversal via `.`/`..`/empty segments in names | `valid_path_segments` | `tests/test_security_adversarial.py::Elevation.test_path_traversal_in_names_rejected` |
| E-8 | TB1 | E | Tenant claim containing `/` addresses another subtree | tenant regex | `tests/test_security_adversarial.py::Elevation.test_tenant_claim_cannot_contain_path_separator` |
| E-6 | TB4 | E | Stale policy decision | no decision cache | `SA::FailClosed.test_policy_change_takes_effect_immediately` |
| E-9 | TB4 | E | Non-operator or non-platform-tenant freeze | `_operator`: role `operator` AND tenant `platform`; every attempt audited | `tests/test_service_contract.py::LifecycleContract.test_non_operator_cannot_freeze` |

## Residual risks
Expired/dropped leases do not wipe their value (WVR-037). Symmetric single workload key (WVR-008); per-instance scopes/retirements not replicated (WVR-012); no artifact signing (WVR-003); plaintext delivered to callers cannot be recalled (`contract.py` assumptions); runtime audit divergence not auto-detected.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-23 | Added S-5, E-7, E-8 per security review; renumbered MITM to S-6, freeze to E-9 |
| 4.3.0 | 2026-09-22 | IDs aligned to adversarial suite; planned markers replaced with real tests |
