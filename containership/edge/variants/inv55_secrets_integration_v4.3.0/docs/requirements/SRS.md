# Software Requirements Specification — INV-55 Secrets integration

| Field | Value |
|---|---|
| ID | INV55-SRS |
| Version | 4.3.0 |
| Status | Draft (`status: PENDING-OWNER-APPROVAL`) |
| Owner | `<UNASSIGNED: service-owner>` |

Keywords MUST/SHALL, SHOULD, MAY per RFC 2119/8174. "Impl" cites the implementing symbol; "Status" says whether code implements it. Tests: `tests/test_service_contract.py`, `tests/test_security_adversarial.py` (see threat-model.md), `tests/test_resilience.py`, `tests/test_config_audit_telemetry.py`; traceability in `evidence/traceability.json`.

## Scope

INV-55 resolves named secrets to leased, versioned values for authenticated workloads, via `PK_SECRET_RESOLVE/1`, `PK_SECRET_ROTATE/1`, `PK_SECRET_SCOPE/1` (`service.py::SecretsService`). It does not store secrets, hold root keys, or issue identities (`contract.py::build`).

## Requirements

### General pipeline
| ID | Requirement | Impl | Status |
|---|---|---|---|
| INV55-SRS-001 | Every operation SHALL shed globally, authenticate, charge the authenticated tenant's quota, authorize, durably audit, then act. | `_run` (`admit`), `_guard` (`charge`), `_audit` | Implemented |
| INV55-SRS-002 | Every request SHALL carry a supported `protocol` of the operation's family; otherwise UNSUPPORTED_VERSION. | `negotiate(protocol, expected)` | Implemented |
| INV55-SRS-003 | Identifiers SHALL match `_ID` and SHALL NOT contain empty, `.` or `..` segments; otherwise INVALID_REFERENCE. | `_ident`, `valid_path_segments` | Implemented |
| INV55-SRS-004 | Every response SHALL include `request_id`; errors SHALL use `PK_SECRET_ERROR/1`. | `_run`, `Inv55Error.to_wire` | Implemented |
| INV55-SRS-006 | Non-dict requests SHALL return INVALID_REFERENCE; any unexpected exception SHALL return INTERNAL without exception text. | `_run` | Implemented |
| INV55-SRS-005 | Requests in states other than ready/degraded SHALL fail FROZEN. | `_guard` | Implemented |

### Resolve / use / revoke
| ID | Requirement | Impl | Status |
|---|---|---|---|
| INV55-SRS-010 | `resolve` SHALL require action `resolve` and subject membership in the scope for (tenant, name); otherwise DENIED. | `resolve` | Implemented |
| INV55-SRS-011 | Missing and unauthorized secrets SHALL be externally indistinguishable (both DENIED). | `_provider_call` maps NotFound/Denied → DENIED | Implemented |
| INV55-SRS-012 | `resolve` SHALL NOT return plaintext; it SHALL return `lease_id`, `version`, `expires_in_s`. | `resolve` | Implemented |
| INV55-SRS-013 | Lease TTL SHALL be finite, > 0 and capped at `max_lease_ttl_s`. | `resolve` | Implemented |
| INV55-SRS-014 | `use` SHALL be the only path returning plaintext and SHALL verify tenant, subject, name, revocation, retirement, expiry. | `use` | Implemented |
| INV55-SRS-015 | `revoke` SHALL require action `revoke` and matching tenant+name; SHALL call provider revoke when a provider lease id exists. | `revoke` | Implemented (`VaultProvider.read` carries `lease_id`) |
| INV55-SRS-016 | Retired versions SHALL NOT be resolved or used. | `resolve`, `use` | Implemented (per process) |

### Rotate / retire / scope
| ID | Requirement | Impl | Status |
|---|---|---|---|
| INV55-SRS-020 | Rotation SHALL add a version, never overwrite. | `provider.write` | Implemented (KV v2); KV v1 overwrites |
| INV55-SRS-021 | `rotate` SHALL require an `idempotency_key`; the first request per tenant/name/key SHALL perform the write, duplicates SHALL replay it, and a different value under the same key SHALL return CONFLICT (single process only). | `rotate` `_idem` | Implemented |
| INV55-SRS-022 | `rotate` SHALL honour `expected_version` as CAS and SHALL return CONFLICT on mismatch. | `VaultProvider.write`, `rotate` | Implemented (KV v2) |
| INV55-SRS-023 | Secret values SHALL be <= `max_secret_bytes`. | `rotate` | Implemented |
| INV55-SRS-024 | `retire` SHALL mark a version retired and, when `destroy=true`, destroy it at the provider. | `retire` | Implemented |
| INV55-SRS-025 | Narrowing a scope SHALL revoke leases of removed subjects. | `set_scope` | Implemented |
| INV55-SRS-026 | Scopes and retirements SHALL persist across restarts when `state_path` is configured, written ahead of the in-memory change (atomic write, mode 0600); on write failure nothing SHALL be applied. | `_save_state`, `_load_state` | Implemented (per instance; not replicated) |
| INV55-SRS-027 | The service SHOULD renew provider leases and its Vault token before expiry. | `renew`, `renew_self` exist | NOT IMPLEMENTED in service |

### Authentication / authorization
| ID | Requirement | Impl | Status |
|---|---|---|---|
| INV55-SRS-030 | Workload tokens SHALL be HS256-verified with constant-time compare; `alg` other than HS256 SHALL be rejected. | `HmacJwtAuthenticator.authenticate` | Implemented |
| INV55-SRS-031 | `iss`, `aud`, `nbf`, `exp` (±30 s leeway), `sub`/`tenant` formats and `roles` (≤ 16 strings) SHALL be validated; failures SHALL be audited. | same | Implemented |
| INV55-SRS-032 | Authorization SHALL be deny-by-default and require both a role granting the action and a matching tenant rule. | `PolicyEngine.decide`, `ROLE_ACTIONS` | Implemented |
| INV55-SRS-035 | Policy changes SHALL be applied only via `PolicyEngine.replace`, which SHALL recompute the cached digest and per-tenant rule index; changes SHALL take effect on the next decision. | `PolicyEngine.replace` | Implemented |
| INV55-SRS-033 | freeze/unfreeze SHALL require role `operator` in tenant `platform`, and every attempt SHALL be audited. | `_operator` | Implemented |
| INV55-SRS-034 | Asymmetric / SPIFFE / OIDC authentication. | — | NOT IMPLEMENTED (pluggable `Authenticator`) |

### Audit
| ID | Requirement | Impl | Status |
|---|---|---|---|
| INV55-SRS-040 | Allowed and denied decisions SHALL be appended to a hash-chained audit record before acting. | `AuditChain.record` | Implemented |
| INV55-SRS-041 | If the audit append fails the operation SHALL fail AUDIT_UNAVAILABLE. | `_audit` | Implemented |
| INV55-SRS-042 | Audit records SHALL NOT contain secret values. | `_audit` fields | Implemented |
| INV55-SRS-045 | Scope and retire SHALL audit `requested` before and `applied`/`retired` only after the state write succeeds. | `set_scope`, `retire` | Implemented |
| INV55-SRS-046 | Denied revokes (context mismatch) SHALL be audited; admin revokes of other subjects SHALL be audited `revoked_by_admin`. | `revoke` | Implemented |
| INV55-SRS-044 | At boot the audit chain SHALL be verified and continued; divergence SHALL quarantine the service. | `audit.resume_from_file`, `bootstrap.build_service` | Implemented |
| INV55-SRS-043 | `FileAuditSink` SHALL fsync before acknowledging and create files 0600. | `FileAuditSink.append` | Implemented |

### Redaction
| ID | Requirement | Impl | Status |
|---|---|---|---|
| INV55-SRS-050 | `SecretValue` SHALL redact repr/str/format and refuse pickle/copy. | `secretvalue.py::SecretValue` | Implemented |
| INV55-SRS-051 | Log fields, span attributes and error details SHALL pass through `redact_text`. | `JsonLogger.log`, `Tracer` | Implemented |
| INV55-SRS-052 | Error `message` SHALL be fixed text. | `to_wire` | Implemented |
| INV55-SRS-053 | Configuration SHALL reject plaintext credential keys. | `config.py::_CREDENTIAL_KEYS` | Implemented |

### Limits
| ID | Requirement | Impl | Status |
|---|---|---|---|
| INV55-SRS-060 | All limits in interface-limits.md SHALL be enforced with the listed error. | `ServiceLimits`, `AdmissionController` | Implemented |

### Clock
| ID | Requirement | Impl | Status |
|---|---|---|---|
| INV55-SRS-070 | Time decisions SHALL use a monotonic clock and fail CLOCK_ROLLBACK on regression or non-finite value. | `_now` | Implemented |
| INV55-SRS-071 | Audit `at` SHOULD be wall-clock for correlation. | — | NOT IMPLEMENTED (monotonic value recorded) |

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-23 | Security-review fixes |
| 4.3.0 | 2026-09-23 | Write-ahead state; policy replace |
| 4.3.0 | 2026-09-22 | Admission split, CONFLICT, INTERNAL, state persistence, audit resume |
