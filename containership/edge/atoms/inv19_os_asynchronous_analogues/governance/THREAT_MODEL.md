# INV-19 threat model (C041, C087)

| Threat (STRIDE) | Vector | Control | Test |
|---|---|---|---|
| Spoofing: forged tenant identity | caller-built Capability | HMAC-SHA256 over identity/actions/scope/expiry/serial; mint validates identifiers | `CapabilityTest.test_forged_expired_revoked_scope`, `test_identity_spoof_rejected_at_mint` |
| Tampering: audit edit/delete/reorder | file edit | hash chain + signed checkpoints + head check | `AuditTest.*` |
| Repudiation | denied actions unrecorded | every denial emits an audit event | `CrossTenantDriverTest.test_denial_before_allocation_and_audited` |
| Information disclosure: secrets/fds in logs/metrics | diagnostics | central `redact`, label allow-lists, pseudonymised tenants | `RedactionTest.*`, `ObservabilityTest.test_label_safety` |
| Information disclosure: kernel inference by guest | timing | backend never exposed in guest-visible tags; residual timing channel ACCEPTED (documented, not mitigated) | `SecurityAbuse.test_timing_review_backend_not_exposed_to_guest` |
| DoS: descriptor/op exhaustion | flood | admission + per-scope quotas + credit pool | `SecurityAbuse.test_resource_exhaustion_attack_is_contained` |
| DoS: retry storm | retryable errors | bounded attempts + budget + jitter | `PolicyTest.test_retry_*`, soak burst |
| Elevation: cross-tenant cancel/reap | op id guessing | owner check before action; generation-tagged op ids | `SecurityAbuse.test_spoofed_and_replayed_op_ids` |
| Replay of old completion ids | stale CQE / packet | generation check, stale counter | `test_operation_table_invariants_and_id_reuse`, `test_stale_cqe_never_delivered` |
| Supply chain | tampered artifact | signed manifest, digest verify, SBOM | `run_gate --self-test` negative checks |
| Log injection | control chars in fields | escaping in `redact` | `RedactionTest.test_log_injection_and_bounds` |
