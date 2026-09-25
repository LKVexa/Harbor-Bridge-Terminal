# PLN-04 threat model (4.3.0) — PLN-04-C041, PLN-04-C050, PLN-04-C087

| # | Threat | Surface | Control | Test |
|---|---|---|---|---|
| T1 | Tenant claims a weaker trust class to get a weaker tier | admission request | signed classification bound to workload+tenant (MR-010) | `test_classification_binding` |
| T2 | Forged or replayed actor token | transport / facade | HMAC envelope, purpose binding, aud/iat/exp, optional one-shot jti | `test_authn_authz_failures`, fuzz envelope |
| T3 | Cross-tenant takeover or teardown | admission / teardown | ownership check, AUTHZ-002, tenant-bound actors | `test_cross_tenant_and_teardown_ownership` |
| T4 | Unapproved or tampered artifact | provider start | digest allowlist, signed provenance, revocation, per-tier approval, content-digest check | `test_artifact_policy` |
| T5 | Stale or replayed attestation; tier admitted without hardware | catalogue | nonce binding, single use, freshness, reference measurements, capability gating, expiry → quarantine | `test_attestation_replay_and_nonce_binding`, `test_discovery_and_tier_gating` |
| T6 | Stale controller double-starts a workload | provider | global epochs, lease CAS, provider fence floor | `test_lease_partition_pause_and_resume`, `test_stale_epoch_is_rejected_by_provider` |
| T7 | Residue leaks to the next tenant | provider teardown | zeroization receipt required; unverified → withheld | `test_unverified_zeroization_withholds_resources` |
| T8 | Side channel via co-residency | placement | tenant-exclusive / dedicated policy | `test_coresidency` |
| T9 | Hostile JSON (depth, size, duplicate keys, NaN) | parser | pre-scan bounds, strict parse, schema | `test_bounds_and_hostile_documents`, fuzz parse |
| T10 | Audit tampering or truncation | audit log | hash chain + external anchors | `test_audit_tamper_and_truncation_detected` |
| T11 | State corruption or torn write | state store | per-record checksums; torn-tail vs corrupt distinction | `test_cas_persistence_torn_tail_and_corruption`, fuzz WAL |
| T12 | Secret leakage in logs, errors or audit | telemetry | redaction by key and value; allow-listed error details | `test_metrics_logs_traces_slo_and_privacy`, `test_audit_sink_resume_anchor_and_redaction` |
| T13 | Admission flood / noisy tenant | queue / capacity | bounded queue, per-tenant fairness, fair share + headroom | `test_admission_gate_backpressure_fairness_and_deadline`, perf burst |
| T14 | Process-tier escape via syscalls/network | process provider | **not mitigated in-tree** (rlimits only) → `process` accepts only `trusted` | residual, ADR-0001 |
| T15 | Compromised signing key | all envelopes | kid rotation / retirement in HmacKeyring; asymmetric roots recommended | residual (W-003) |
