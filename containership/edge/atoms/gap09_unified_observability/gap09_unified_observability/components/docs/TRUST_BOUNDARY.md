# GAP-09 v5.1.0 — trust boundary (normative)

Applies to components 01–15, 19 and 40. Every arrow that crosses a dashed box is
an untrusted input until the named check has passed. Every decision fails closed.

```mermaid
flowchart LR
  subgraph U[Untrusted]
    R[Reporter / site agent]
    Q[Query client]
  end
  subgraph E[GAP-09 edge  - server.py]
    T[mTLS  - auth.server_tls_context]
    B[Body limit 1 MiB, CSP/1 depth 16]
  end
  subgraph V[Verified ingest  - ingest.VerifiedIngest]
    TA[TimeAuthority skew and confidence]
    QU[Quarantine]
    AD[Admission buckets, retry_after]
    SIG[Ed25519 over GAP09-CSP/1  - keys.Ed25519Verifier]
    KR[(KeyRegistry: rotate, revoke, expiry)]
    AT[AttestationVerifier GAP09-ATT/1]
    SC[Scope + per-tenant quota]
    RP[(DurableReplayGuard)]
    ST[(SignalStore atomic commit)]
  end
  subgraph P[Query path]
    QA[QueryAuthenticator GAP09-QTOKEN/1]
    PB[(PolicyBundle, signed, expiring)]
  end
  AUD[(AuditLedger hash chain + external head)]
  R --> T --> B --> TA --> QU --> AD --> SIG --> AT --> SC --> RP --> ST
  KR -.-> SIG
  Q --> T --> QA --> PB --> ST
  SIG -. decisions .-> AUD
  QA -. decisions .-> AUD
```

| Trust root | Held by | Rotation | Status in this archive |
|---|---|---|---|
| Reporter signing keys (Ed25519) | `KeyRegistry` | `rotate()` with overlap window | real mechanism; keys in tests are fixtures |
| Attestation endorsement roots | `AttestationVerifier.roots` | replace root set | **fixture only** — real GAP-06 roots BLOCKED |
| Policy-service signing key | `PolicyBundle` | new key → new bundle | **fixture only** — real policy service BLOCKED |
| Query-gateway token keys | `QueryAuthenticator.issuer_keys` | kid set | **fixture only** — real gateway BLOCKED |
| mTLS CA | `server_tls_context(client_ca=…)` | CA bundle swap | test CA generated per run |

Fail-open decisions: **none**. `allow_legacy_trust=True` is refused by the
production config validator (`config.DANGEROUS`).
