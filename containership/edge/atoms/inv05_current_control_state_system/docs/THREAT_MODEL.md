# INV-05 Threat Model (STRIDE)

Traceability: C041, C043, C048, C050, C087; MC-*-16/17/18/19. Review cadence: every minor release and quarterly (GOVERNANCE.md).

**Assets:** control state (all tenants), revision history, lease ownership, WAL/snapshots/backups, data/audit/backup keys, audit log, policy, configuration.
**Actors:** authenticated tenant workloads (untrusted beyond their namespace), operators, security admins, replication peers, compromised workload, network attacker, malicious insider with disk access, supply-chain attacker.
**Entry points / trust boundaries:** HTTP listener (TLS), hello handshake, replication feed, config overlays, secret files, data directory, backup directory, CI pipeline.

| # | Threat (STRIDE) | Abuse case | Mitigation (code) | Test |
|---|---|---|---|---|
| T1 | Spoofing | forged client identity / token | mTLS chain + SPIFFE SAN + trust-domain + validity + revocation + purpose (`MTLSAuthenticator`); HMAC tokens with kid/aud/exp | `test_security.MTLSTest`, `TokenTest`, `test_http.test_foreign_trust_domain_rejected_and_audited` |
| T2 | Tampering | edit WAL/snapshot/backup on disk | CRC + AES-GCM tag + SHA-256 + HMAC manifest; fail closed | `test_durability.*corrupt*`, `test_tampered_ciphertext_detected`, backup tamper tests |
| T3 | Tampering | rewrite audit history | HMAC hash chain + external anchor | `test_service.AuditTest` |
| T4 | Repudiation | admin denies break-glass | audited admin/policy/compaction/authn/authz events with request ids | `test_break_glass_is_audited...` |
| T5 | Information disclosure | cross-tenant read via crafted keys/watches/errors/metrics | server-side namespace mapping, prefix stripping, no tenant metric labels, allow-listed error details | `IsolationTest.*`, fuzz authz |
| T6 | Information disclosure | secrets in logs/traces | `redact()`, span attribute allow-list, secret refs only | `test_redaction`, observability tests |
| T7 | DoS | request floods, huge payloads, watch floods, slowloris | token buckets, in-flight gate, size limits, watch quotas, socket timeouts, handshake off accept thread | limits/quota/HTTP tests, resource fuzz |
| T8 | DoS | unbounded history growth | history ceiling + compaction controller | `test_limits`, controller tests |
| T9 | Elevation | writer performs admin/compaction | deny-by-default policy, cluster-scoped admin actions | `AuthzTest.*`, authz fuzz |
| T10 | Elevation | stale lease holder writes after expiry | fencing tokens + FENCE compares, lease ownership check | `LeaseTest.test_fencing_blocks_stale_owner` |
| T11 | Replay | replay old txn to re-apply | idempotency keys scoped per subject; CAS compares; token expiry | `test_idempotent_request_id`, `DeadlineTest` |
| T12 | Split-brain | old primary keeps writing after failover | site epochs, `CSTATE_FENCED`, replica read-only role | `test_backup_repl.ReplicationTest` |
| T13 | Supply chain | tampered dependency/artifact | lock with hashes, SBOM, signed evidence manifest, pinned backend digest | `tools/ci_gate.py`, `tools/sbom.py` |
| T14 | Injection | JSON duplicate keys / type confusion | strict parser, strict op/compare objects | `test_protocol.NegotiationTest.test_strict_parsing`, fuzz |

**Safe behaviour when dependencies are unavailable (C048):** identity/PKI unavailable ⇒ no new connections authenticate (fail closed); KMS unavailable at start ⇒ refuse start, after start ⇒ keep serving with in-memory data key; policy unavailable ⇒ last active version stays (atomic swap); time service unavailable ⇒ no effect on correctness (monotonic lease clock; certificate validity uses wall clock — skew beyond tolerance rejects certs = fail closed).

**Ambient authority (C043):** the process needs only its data dir (0700), its audit file, its secret files (0600, read-only) and its listen socket; the systemd unit and k8s manifest drop all capabilities, use read-only root FS, no new privileges, and a non-root UID.

**Open risks** are tracked in `docs/EXCEPTIONS.json` with owners and expiry dates.
