# PLN-06 threat model — v4.3.0 (WP #18, C041/C050/C087)

**Review status:** drafted by the 4.3.0 implementation pass; **independent security review not yet recorded** (W-002). Review cadence: every release and at least quarterly (`docs/REVIEWS.md`).

## Assets

Payload bytes in motion; residency/classification policy; signing keys; audit ledger; transfer journal; tenant capacity; control transport.

## Trust boundaries

```
 workload (untrusted) ──cred+label──▶ GovernedDataPlane ──adapter SPI──▶ transports ──wire──▶ peer node (authenticated)
        ▲                                   │   │    │                                          │
 operator (authN, control.* caps)           │   │    └─ journal/audit (local disk, fsync)       └─ receiver verifies manifest
 GAP-13 policy (signed) ────────────────────┘   └─ KeyRing / KeyProvider (KMS/HSM, W-012)
 GAP-14 gravity hints (signed, advisory) ───────┘
```

Attacker-controlled inputs: every `submit` argument, credentials, labels, gravity hints, policy documents, completion records, network frames, shared-memory contents, journal/audit files at rest, configuration overlays.

## Threat matrix

| ID | STRIDE | Threat | Mitigation | Test |
|---|---|---|---|---|
| T-SPOOF-1 | S | Forged workload credential / capability escalation | HMAC-bound credential over canonical body; unknown caps rejected | `test_security::test_spoofed_tampered_expired_future_audience_replay` |
| T-SPOOF-2 | S | Rogue peer node / server impersonation | Mutual HMAC challenge + server id; optional mTLS | `test_transports::test_bad_peer_secret_*`, `test_server_impersonation_detected`, `test_mutual_tls` |
| T-REPLAY-1 | S/R | Credential replay | single-use `jti` with bounded replay cache (fails closed when full) | `test_replay_cache_is_bounded_and_fails_closed` |
| T-REPLAY-2 | S | Cross-service replay | audience binding | same |
| T-REPLAY-3 | T | Label replay by another tenant / other payload | label bound to tenant + digest + expiry | `LabelTest`, `test_authn_authz_label_residency_refusals_are_audited` |
| T-DOWNGRADE-1 | T | Policy rollback to older permissive revision | monotonic serial check | `test_gap13_policy_sync_degraded_and_fail_closed` |
| T-DOWNGRADE-2 | T | Protocol version downgrade | explicit version negotiation; unknown refused | `test_version_negotiation_refuses_unknown` |
| T-TAMPER-1 | T | In-flight payload modification | per-chunk + root manifest verification, quarantine | `test_in_flight_tamper_is_quarantined`, `test_inv37_*` |
| T-TAMPER-2 | T | Forged completion releasing another tenant's capacity | completion bound to admitted record | `test_runtime`, fuzz `test_completion_record_fuzz` |
| T-AUDIT-1..4 | R/T | Audit deletion, insertion, reorder, edit | hash chain + MAC per record; verify on load | `AuditLedgerTest` |
| T-XTENANT-1 | I/E | Tenant A acts on tenant B's transfers | tenant-scoped principals; `transfer.complete.any` required | `AuthorizationTest`, `service.cancel` |
| T-XTENANT-2 | I | Shared-memory name collision/guessing across tenants | SHA-256 namespaced + random suffix; always unlinked | `test_tenant_namespaces_are_disjoint`, `test_shared_memory_moves_bytes_and_always_unlinks` |
| T-ESCAPE-1 | E | Adapter uses ungranted network/fs/device/secret | `AuthorityGuard` per adapter `Grant` (OS layer: W-011) | `SandboxAndIsolationTest` |
| T-CTRL-1 | E/D | Bulk bytes abusing the control path (INV-36) | vsock adapter refuses non-inline/non-verb; no non-inline preference maps to vsock | `VsockControlTest` |
| T-DOS-1 | D | Oversized frames / hostile garbage | frame caps; server never crashes on hostile input | `test_hostile_garbage_does_not_crash_server`, frame fuzz |
| T-DOS-2 | D | Capacity exhaustion by one tenant | global + per-tenant limits; DRR fairness | `ConcurrencySoakTest`, `FairnessTest` |
| T-DOS-3 | D | Unbounded state growth | all caches/rings bounded | soak test bounded-state assertions |
| T-KEY-1..4 | S/T | Use of rotated, revoked, expired key; KMS outage | key states + expiry; outage fails closed | `KeyLifecycleTest`, `test_key_outage_fails_closed` |
| T-INFO-1 | I | Secrets/payload/tenant IDs leaking into logs/explain | redaction; hashed tenant labels; payload never logged | `test_structured_log_schema_redaction_and_sink_failure`, `test_explain_is_redacted_and_authorized` |
| T-SUPPLY-1 | T | Dependency substitution | zero runtime deps; SBOM; SHA256SUMS; evidence dossier (Sigstore: W-017) | `tools/release_gate.py` |
| T-SIDE-1 | I | Timing side channel on MAC compare | `hmac.compare_digest` everywhere | code review |
| T-CTRLPLANE-1 | E | Unauthorised policy/config change | `policy.update` cap; independent approver for config; audited | `test_policy_update_requires_capability_*`, `ConfigTest` |
| T-SPLIT-1 | T | Stale controller writes after partition | fencing epoch checked on every journal write | `test_fencing_blocks_stale_controller_split_brain` |

## Residual risks (tracked)

OS-level sandbox and hostile-tenant process isolation (W-011); KMS/HSM custody and at-rest volume encryption (W-012); wRPC wire interop (W-003); fleet-wide lease (TD-003); signed provenance (W-017).
