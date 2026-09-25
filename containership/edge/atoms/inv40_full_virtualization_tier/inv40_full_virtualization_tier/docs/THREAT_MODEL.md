# Threat model (INV-40-C041, C042..C050)

Assets: host kernel, other tenants' guests, device instances, capability keys, audit trail, config.
Trust boundaries: caller↔tier API; tier↔QEMU process; QEMU↔guest; tier↔disk state; controller↔tier.

| ID | Threat (STRIDE) | Actor | Control | Test |
|---|---|---|---|---|
| T1 | Hostile guest attacks VMM (E) | malicious tenant | KVM hardware boundary; QEMU `-sandbox` seccomp denying spawn/elevate; `-nodefaults`; no guest introspection | argv test; hardware escape testing BLOCKED (HW-KVM) |
| T2 | Emulation offered when hardware absent (T) | misconfig / attacker | const-false `allow_software_emulation`; probe-gated launch; argv refuses `tcg` | `test_no_software_fallback`, `test_security_critical_fail_closed` |
| T3 | Device instance shared across guests (I) | concurrent callers | lease registry; one boot in flight per guest (D-01) | lease race tests |
| T4 | Spoofed caller (S) | network attacker | HMAC capability tokens, audience, expiry, nonce | identity tests |
| T5 | Replay of captured token (S) | network attacker | nonce cache | `test_replay_refused`, `test_replayed_token_refused` |
| T6 | Cross-tenant action (E) | compromised tenant | exact op+tenant scopes; `*` only for controllers | `test_cross_tenant_denied_and_audited` |
| T7 | Injection via request fields (T) | caller | strict schema, ID pattern, size/depth bounds; argv built as list (no shell) | schema negative tests, fuzz |
| T8 | Resource exhaustion (D) | tenant | quotas, bounded queue, footprint ceiling, metric cardinality cap | admission/quota tests, bench burst |
| T9 | Supply-chain: tampered image/policy (T) | registry attacker | digest + allow-list + signature | integrity tests; asymmetric signing BLOCKED (SEC-SIGN) |
| T10 | Stale controller after partition (T) | split brain | fencing epochs | `test_split_brain_prevented` |
| T11 | Audit tampering / repudiation (R) | insider | hash chain + exported head | `test_chain_and_tamper` |
| T12 | Secret leakage via config/logs (I) | operator error | secret scan, log/audit redaction, tenant id hashing | config/telemetry tests |
| T13 | Trust services down → open admission (E) | outage | fail closed | `test_trust_services_unavailable_fail_closed` |
| T14 | Side channels (I) | co-tenant | NOT mitigated in repo (SMT/L1TF host policy); listed as open | — |

Least privilege (C042): tokens carry only named ops+tenants; tier-wide quarantine requires a human admin token; QEMU runs with seccomp deny-lists. Running QEMU under a dedicated unprivileged uid / cgroup / namespace is a host-deployment requirement not implementable here (PARTIAL).
Ambient authority (C043): QEMU `-nodefaults -no-user-config`, restricted user net, read-only disks, private QMP socket dir; no ambient filesystem paths accepted from callers.
Encryption (C047): at-rest encryption of state and in-transit TLS are **not implemented** (require KMS + transport; BLOCKED SEC-KMS / PROD-ENV).
