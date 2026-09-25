# Threat model (item 23) — STRIDE over the ADR-001 data flow

**Status:** authored; independent security review pending (EXC-002).

Assets: tenant workloads, runtime capacity, controller credentials, audit trail, placement protocol integrity.
Trust boundaries: user↔API server, API server↔controller, controller↔SCH-01, controller↔secret volume, controller↔telemetry.

| # | Threat | STRIDE | Mitigation (code) | Test |
|---|---|---|---|---|
| T1 | Privileged/hostPath/hostNetwork workload silently weakened or run | E | strict translator refuses by path | adversarial suite |
| T2 | Unknown Pod field silently dropped | T | subset allow-list; CRD preserves unknown fields so they reach the refusal | fuzz P2, CRD test |
| T3 | Cross-tenant launch via unbound namespace | E/I | explicit ns→tenant binding, watch scope | adversarial |
| T4 | Malicious/unpinned image | T | registry allow-list, digest pin, attestation verifier, fail closed | artifact tests |
| T5 | Stolen/expired credential replay | S | token expiry+HMAC, mTLS trust domain, TokenReview in-cluster | authz tests |
| T6 | Controller over-privilege | E | RBAC without delete/create/secrets/pods/wildcards | RBAC test |
| T7 | Split-brain double launch/cancel | T | lease + fencing token enforced downstream | failover test |
| T8 | Replay/duplicate events cause duplicate launch | T | idempotency key = attempt id; journal replay | crash/idempotency tests |
| T9 | Secret leakage via logs/status/audit/metrics | I | secretRef only, `Secret` repr redaction, log/audit redaction, no object names in metric labels | adversarial secret test |
| T10 | Audit tampering | R | SHA-256 chain + optional HMAC + exported head | audit tests |
| T11 | Resource exhaustion (huge quantities, fan-out, floods) | D | bounded quantity length/value, maxItems 32, admission, rate limits, metrics cardinality cap | fuzz, resilience |
| T12 | Hot-loop DoS on API server | D | bounded jittered backoff, dedup queue preserving delay, per-pass cap | queue test |
| T13 | Config tampering / unsafe config | T | schema validation, https-only endpoint, no inline creds, audited activation | config tests |
| T14 | Downstream spoofing | S | https + mTLS required by config/ADR; **mTLS client not implemented in archive (EXC-008)** | — |

Residual risks are recorded in `docs/governance/exceptions.json`.
