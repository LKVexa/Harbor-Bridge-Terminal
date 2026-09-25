# Threat model (INV55-TM-001, DRAFT — STRIDE over boundaries B1–B4)

Assets: secret values; lease handles; audit chain; scope policy; provider credentials; configuration.

| ID | Threat (STRIDE) | Boundary | Control | Test |
|---|---|---|---|---|
| T-01 | Information disclosure: existence oracle via error differences | B1 | identical DENIED for missing/unauthorized | `test_T01_no_existence_oracle` |
| T-02 | Elevation: cross-tenant access | B1 | tenant namespace in authz; scope cannot name another tenant | `test_T02_cross_tenant` |
| T-03 | Spoofing: lease replay by another workload | B1 | lease bound to subject | `test_T03_lease_replay_by_other_workload` |
| T-04 | Use of stale grant after expiry/revoke/retire/scope removal | B1 | checks at use time | `test_T04_*`, `test_T04b_*` |
| T-05 | Spoofing: forged/expired/wrong-audience token | B1 | HMAC verify, iss/aud/nbf/exp/lifetime | `test_T05_*`, `Identity.test_negative_matrix` |
| T-06 | Tampering: schema smuggling, oversize, version games | B1 | strict schemas, size cap, negotiation | `test_T06_*` |
| T-07 | Repudiation/tampering: log injection | B1/B3 | identifier patterns; structured JSON | `test_T07_*` |
| T-08 | Elevation: consumer rotates or rescopes | B1 | role→verb catalogue | `test_T08_*` |
| T-09 | Incident containment unavailable | B4 | freeze scopes | `test_T09_*` |
| T-10 | Clock rollback extends leases / mints quota | B1 | monotonic check before any time control | `test_T10_clock_rollback` |
| T-11 | Disclosure via logs/metrics/traces/errors/snapshots | all | `_SecretValue`, scrubber, audit field allow-list | `test_T11_*`, fuzz |
| T-12 | DoS: one workload starves others | B1 | per-workload quota, bulkhead, bounded tables | `test_T12_quota_and_overload` |
| T-13 | Tampering with audit history | B3 | hash chain + HMAC seal + external head | `Audit.test_chain_file_roundtrip_and_tamper_detection` |
| T-14 | MITM on provider link | B2 | TLS ≥ 1.2, CA pin, hostname check, mTLS | `test_tls_hostname_verified`, `test_mtls_client_certificate_required` |
| T-15 | Split-brain rotation on replica | B2 | writes never fail over | `test_failover_reads_only` |
| T-16 | Credential committed to repo/config | supply chain | `tools/secret_scan.py`, config credential scan | `test_scanner_detects_and_never_prints` |
| T-17 | Memory scraping of plaintext in process | host | **residual risk**: CPython cannot zeroize `str`; mitigate by process isolation (W-005) | none — accepted risk pending approval |
| T-18 | Compromised IdP signing key | B1 | key ids + rotation; external IdP binding **blocked** (W-003) | partial |

Residual risks require security-owner acceptance (UNASSIGNED). Re-review triggers: new provider, new auth method, new wire version, any incident with severity ≥ SEV2.
