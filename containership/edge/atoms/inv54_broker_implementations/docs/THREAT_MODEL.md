# INV-54 threat model  (C041 · component 36; drives components 44 and 87)

Method: STRIDE per trust boundary. Assets: message payloads, offsets, audit chain, secrets, configuration, provider credentials.
Trust boundaries: TB1 caller→BrokerService; TB2 tenant↔tenant inside one process; TB3 service→provider/storage; TB4 operator/config plane; TB5 supply chain (package, dependencies).

| ID | Boundary | Threat (STRIDE) | Mitigation (code) | Test |
|---|---|---|---|---|
| T01 | TB1 | Spoofed identity (S) | HMAC tokens, constant-time compare | `test_c19_authentication_required_and_tamper_rejected` |
| T02 | TB1 | Token replay (S/R) | nonce cache bounded by TTL | `test_c19_expired_and_replayed_tokens_rejected` |
| T03 | TB1 | Forged admin token (E) | signature under server key only | `test_c44_*` (forged) |
| T04 | TB1 | Privilege escalation via unguarded action (E) | deny-by-default grants | `test_c20_*` |
| T05 | TB2 | Malicious tenant reads/moves another tenant's data/offsets (I/T) | per-tenant broker instances + tenant check | `test_c39_*` |
| T06 | TB1 | Hostile payload / injection in names (T) | `fullmatch` name grammar, JSON-only payloads, size cap | `test_c44_*` (found and fixed the trailing-newline bypass) |
| T07 | TB1 | Resource exhaustion (D) | quotas, admission, backlog/record/subscriber ceilings | `test_c08_*`, `test_c68_*`, `test_c54_*` |
| T08 | TB3 | Storage tampering / record swap (T) | CRC + AES-GCM with (partition,offset) AAD | `test_c41_*`, `test_c57_*` |
| T09 | TB3 | Stale leader writes after failover (T) | epoch fencing + leases | `test_c50_*` |
| T10 | TB4 | Malicious/erroneous config (T/E) | fail-closed validator, staged commit, provenance, rollback | `test_c27_*`, `test_c29_c30_*`, `test_c31_*` |
| T11 | TB4 | Secret leakage in logs/errors/evidence (I) | `Secret` type, redaction in errors/logs/config | `test_c22_*`, `test_c74_*`, `test_c32_*` |
| T12 | TB4 | Audit repudiation / log tampering (R) | HMAC hash chain + external head | `test_c43_*` |
| T13 | TB3 | Security-service outage used to bypass checks (E) | fail closed `INV54-E0105` | `test_c42_*` |
| T14 | TB5 | Tampered artifact/dependency (T) | digest allow-list, zero runtime deps, checksums | `test_c38_*`, `evidence/checksums.sha256` |
| T15 | TB1 | Side channels (timing on MAC) (I) | `hmac.compare_digest` | code review only — **no timing test** |
| T16 | TB3 | Compromised provider credentials (S) | secret refs + rotation grace; provider-side IAM | rotation tested; IAM **UNVERIFIED** |
| T17 | TB1 | Sandbox/process escape by payload | payloads never executed/deserialised beyond JSON | by construction; **no fuzz corpus beyond unit** |

Residual risks: T15, T16 (provider IAM), network TLS (no live TLS test), supply-chain signing (no signing key). Review: on any new interface, provider, or trust boundary.
