# INV-55 Secrets Integration — Normative Requirements

| Field | Value |
|---|---|
| Document ID | INV55-REQ-001 |
| Version | 1.0.0-draft (runtime 4.3.0) |
| Status | **DRAFT — not approved** (approver UNASSIGNED, see `docs/governance/OWNERSHIP.md`) |
| Change history | 1.0.0-draft 2026-09-22 — created by the 4.3.0 chop-shop pass |

The key words MUST, MUST NOT, SHOULD and MAY are to be interpreted as described in RFC 2119 / RFC 8174 when, and only when, they appear in all capitals. Rationale is separated from requirements and is non-normative.

## Scope and actors

* **Workload** — an application instance identified by `spiffe://<domain>/tenant/<tenant>/workload/<app>`.
* **Rotator**, **Scope admin**, **Operator**, **Auditor** — human or automation principals holding the roles in `runtime/identity.py::ROLES`.
* **Provider** — the system of record for secret versions (HashiCorp Vault KV v2 in production; in-memory in tests).
* Trust boundaries: (B1) workload ↔ INV-55 wire boundary; (B2) INV-55 ↔ provider (network, TLS); (B3) INV-55 ↔ audit sink; (B4) operator ↔ controls.
* Non-goals: storing secrets, holding root keys, issuing identities, hard in-process confidentiality in Python.
* Unsupported configurations: plain HTTP to a provider outside `environment=test` on loopback; memory provider in production; stale serving in production without an approved waiver.

## Requirements

| ID | Requirement | Verified by |
|---|---|---|
| R-REF-01 | Applications MUST reference secrets by name `<tenant>/<path>`; request messages MUST NOT carry secret values. | `test_T06_schema_smuggling_and_oversize`, fixture `resolve_invalid_extra_field` |
| R-REF-02 | The wire response to RESOLVE MUST carry a lease handle and MUST NOT carry plaintext. | `test_resolve_then_use`, fixture `resolve_response_invalid_value_leak` |
| R-AUTHN-01 | Every wire request MUST be authenticated before any scope, quota or provider interaction. | `test_T05_forged_and_expired_tokens`, `Identity.test_negative_matrix` |
| R-AUTHZ-01 | Authorization MUST be deny-by-default and require role, tenant and scope membership. | `Authz.test_deny_by_default_and_reasons`, `test_property_scope_decision_matches_model` |
| R-AUTHZ-02 | Missing and unauthorized secrets MUST be externally indistinguishable. | `test_T01_no_existence_oracle` |
| R-AUTHZ-03 | Scope MUST be re-evaluated at use time. | `test_T04b_scope_removed_after_resolve_denies_use` |
| R-TEN-01 | A principal MUST NOT resolve, rotate or scope a secret outside its tenant namespace. | `test_T02_cross_tenant`, `test_T08_consumer_cannot_rotate_or_rescope` |
| R-LEASE-01 | A lease MUST be bound to the resolving subject; use by any other subject MUST fail. | `test_T03_lease_replay_by_other_workload` |
| R-LEASE-02 | Use after expiry, revocation or version retirement MUST fail. | `test_T04_expiry_revocation_retirement_scope_removal` |
| R-LEASE-03 | Leases MUST NOT survive a process restart (fail closed). | `test_restart_invalidates_leases_keeps_scopes_and_retirements` |
| R-ROT-01 | Rotation MUST add a version; existing leases MUST stay bound to their version. | `test_rotation_keeps_old_lease_on_old_version` |
| R-ROT-02 | Rotation MUST be idempotent per (subject, idempotency_key); key reuse with a different request MUST fail with CONFLICT. | `test_rotate_idempotency` |
| R-RED-01 | No secret value MAY appear in audit, logs, metrics, traces, errors or snapshots. | `test_T11_no_plaintext_in_any_channel_after_mixed_traffic`, `test_random_requests_never_crash_or_leak` |
| R-AUD-01 | Every security decision MUST produce a hash-chained audit record with reason, policy digest and config digest. | `Audit.test_chain_file_roundtrip_and_tamper_detection`, `test_explain_view` |
| R-TIME-01 | Time decisions MUST use a monotonic clock and fail closed on rollback, including quota accounting. | `test_T10_clock_rollback` |
| R-RES-01 | Only RETRYABLE outcomes MAY be retried, bounded by attempts and deadline. | `Resilience.test_retry_only_retryable_and_bounded`, `test_retry_respects_deadline` |
| R-RES-02 | Provider outage MUST deny (offline-deny) unless stale serving is configured, in which case responses MUST be marked DEGRADED and audited. | `test_outage_offline_deny_then_recovery`, `test_degraded_stale_serving_when_configured` |
| R-RES-03 | Writes MUST NOT fail over to a replica. | `test_failover_reads_only` |
| R-OPS-01 | Operators MUST be able to freeze by global/tenant/secret/op scope; frozen operations MUST be DENIED. | `test_T09_freeze_blocks_resolve_and_use` |
| R-CFG-01 | Configuration MUST validate before activation, reject credential material, and keep a rollback target. | `Config.test_transactional_activation_and_rollback`, `Config.test_negative_cases` |
| R-TLS-01 | Provider transport MUST be TLS ≥ 1.2 with hostname verification outside the loopback test lane. | `test_transport_policy_fail_closed`, `test_tls_hostname_verified` |
| R-LIM-01 | Request size, in-flight concurrency, per-workload rate, lease table, cache and metric series MUST be bounded. | `test_T12_quota_and_overload`, `Resilience.test_bulkhead_refuses_when_full`, `Telemetry.test_prometheus_export_and_cardinality_cap` |

## Constraint precedence (checklist #11)

When requirements conflict the order is: **(1) confidentiality / R-RED, R-AUTHZ** → **(2) integrity / R-AUD, R-TIME** → **(3) data residency** → **(4) availability / SLO** → **(5) latency** → **(6) cost** → **(7) operator convenience**. An operator override MAY lower (4)–(7) only; it MUST NOT lower (1)–(3) and every override is an audited freeze/config change. Example: during a provider outage availability yields to confidentiality — offline-deny is the default.

## Acceptance

Each row is machine-checked: `tests/test_tools.py::Traceability::test_requirement_tests_exist` fails if a named test does not exist.
