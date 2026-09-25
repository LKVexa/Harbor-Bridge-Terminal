# PLN-03 threat model (MC-027, MC-033)

- **Method:** STRIDE per trust boundary. **Review owner:** `security_contact` (OWNERS.yaml). **Next review:** with ownership recertification.

## Assets
Tenant state; messages in flight and buffered; secret values; capability-token keys; audit chain; configuration; adapter credentials (held by INV-49, never by PLN-03).

## Trust boundaries
| # | Boundary | Crosses |
|---|---|---|
| B1 | Workload → PLN-03 API (`wire.handle` / `GovernedRuntime`) | untrusted requests, tokens |
| B2 | PLN-03 → adapter (INV-49) | payloads, keys |
| B3 | PLN-07 → PLN-03 | token keys, revocation, time |
| B4 | Operator → PLN-03 | config, lifecycle, quarantine |
| B5 | Peer runtime ↔ PLN-03 | hello/negotiation, invoke |
| B6 | Build → deploy | artifacts, provenance |

## Threats, mitigations, residual risk
| ID | STRIDE | Threat | Mitigation (code) | Test | Residual |
|---|---|---|---|---|---|
| T1 | E | Workload reaches an unbound capability | binding check + token capability claim (`plane._call`) | test_mc013_* | Low |
| T2 | I | Namespace escape to another tenant | tenant validation, length-delimited channels, token tenant claim | test_mc031, fuzz | Low |
| T3 | I | Hostile adapter exfiltrates payloads | adapter quarantine; isolation delegated to PLN-04 | test_mc042 | **High until PLN-04 isolation is integrated (MC-028)** |
| T4 | T/R | Replay of a message | idempotency keys persisted in journal | test_mc035_replay, test_mc041 | Low |
| T5 | I | Secrets in logs/traces/metrics | config refusal, `redact`, audit meta excludes payloads | test_mc025_* | Low |
| T6 | S | Forged/expired token | HMAC-SHA256, kid ring, skew-bounded expiry, revocation hook | test_mc013_*, test_mc032 | Medium: symmetric keys shared with PLN-07; asymmetric tokens preferred (open) |
| T7 | T | Audit log tampering / truncation | hash chain + seq + optional HMAC seal, fsync | test_mc034_* | Medium: tail truncation detectable only against an external checkpoint (ship chain head to PLN-07) |
| T8 | D | Resource exhaustion | admission, quotas, bounded buffers/series, wire size pre-check, recursion guard | test_mc008_mc038, fuzz | Low |
| T9 | T | Split-brain dual writers | leases + fencing epochs | test_mc041_fencing | Low (single-journal scope) |
| T10 | S | Malicious artifact deployed | digest allowlist + provenance + seal (`artifacts.py`) | test_mc030 | Medium: public-key signature (Sigstore) not integrated |
| T11 | T | Malicious config (disable tokens, residency bypass) | validation + precedence; provenance ledger | test_mc021, test_mc010 | Low |
| T12 | I | Side channels between tenants on shared host | out of scope for this plane | — | **Accepted-pending: PLN-04** |
| T13 | S | Unauthenticated peer / control plane | negotiation schema only | test_mc016 | **High until mTLS/SPIFFE identity via PLN-07 (MC-029, MC-032 transport)** |

## Security-dependency outage matrix (MC-033)
| Dependency | Unavailable ⇒ | Code | Class |
|---|---|---|---|
| Trusted time | refuse all token evaluation | PK_SECURITY_DEPENDENCY_UNAVAILABLE | fail closed, retryable |
| Revocation source | refuse | PK_SECURITY_DEPENDENCY_UNAVAILABLE | fail closed, retryable |
| Signing keys (ring empty / kid retired) | refuse | PK_TOKEN_INVALID | fail closed, terminal |
| Policy / attestation (PLN-07) | refuse via `revoked` hook raising | PK_SECURITY_DEPENDENCY_UNAVAILABLE | fail closed |
| Audit sink write failure | call raises (fsync error propagates) | PK_RUNTIME_ERROR | fail closed |
