# Threat Model (MC-032) — STRIDE over the INV-06 data flow

Status: **Draft; needs independent security review.** Assets: authoritative state, plans, approvals, audit trail, provider credentials, configuration.

| # | Threat | Surface | Mitigation in package | Residual / owner action |
|---|---|---|---|---|
| T1 | Spoofed caller | API entry | `TokenAuthenticator` (sig, aud, exp, kind) | Replace with OIDC/mTLS/SPIFFE (MC-033 estate) |
| T2 | Privilege escalation | actions | default-deny `Authorizer`, unknown action refused, SoD | Role assignment governance |
| T3 | Cross-tenant access | state paths | `TenantRegistry` name regex + path containment, tenant-scoped authz | Network isolation (estate) |
| T4 | Plan tampering | plan in transit | SHA-256 digest + HMAC approval signature | Asymmetric signing via KMS (MC-038) |
| T5 | Replay of an applied plan | apply | serial binding → `StalePlan`; idempotency keys | — |
| T6 | Stale writer / split brain | backend | CAS on serial + fencing tokens | Cross-site lease service |
| T7 | State corruption / rollback attack | disk | revision digests + parent chain; rollback creates new serial | WORM backups |
| T8 | Malicious config | parser | minimal subset, size limit, fuzzed | — |
| T9 | Supply chain: engine/provider | execution | digest-pinned binary, provider allowlist, no runtime download, `CHECKPOINT_DISABLE` | Signature/SBOM attestation verification |
| T10 | Credential leakage | logs/audit/metrics/explain | `redact`, label allowlist, secret-like label refusal | DLP on sinks |
| T11 | Ambient authority abuse | subprocess | scrubbed env, rlimits, setsid, refuse ambient cloud creds | Container/VM sandbox, egress policy |
| T12 | Resource exhaustion | all inputs | admission shedding, size/node/queue/series limits | Gateway rate limits |
| T13 | Audit repudiation | audit | hash-chained HMAC-signed fsync'd JSONL | External WORM + trusted timestamps (MC-040 estate) |
| T14 | Security-service outage abused to bypass | identity/policy/keys | `outage_decision` fail-closed | — |
| T15 | Policy bypass | apply path | decision bound to plan digest + policy version | Wire PolicyGate as mandatory in the service wrapper |
| T16 | Control-plane escape via provider response | provider | provider data treated as untrusted; normalised JSON only | Provider adapter review |

Adversarial tests: `tests/test_production.py::SecurityTest`, `AdversarialPropertyTest`.
