# Security model — INV-52 v4.3.0

See `THREAT_MODEL.md` for threats → controls → tests.

## Trust boundary

`PubSub` accepts an already-established application identity as `app`; it does **not** authenticate. `TenantBus` is the authenticated, tenant-isolated entry point: signed tokens (HMAC-SHA256, TTL ≤ 1 h, single-use nonce, key from a provider callback), explicit `publish:`/`subscribe:` capabilities per (tenant, app), tenant-namespaced topics, and a tamper-evident audit chain of grants, accepts and denials. Production SHOULD bind `TokenAuthority` to the platform IdP rather than shared keys.

## Local controls

Fail-closed publishing; `source` must equal the authenticated app; envelope and trace-context validation; size/depth/fan-out/topic bounds; isolated subscriber copies and read-only predicate views; predicate/sink exceptions contained (exception text never copied); deny when key/clock/identity is unavailable; secrets rejected from config and redacted from logs/audit; artifact admission by digest + provenance (`verify_artifact`); no filesystem/network/subprocess access in the core (only `adapters.py` performs HTTP, to a configured sidecar URL).

## External responsibilities (with evidence still required)

Transport encryption (Dapr Sentry mTLS, broker TLS), at-rest encryption and key rotation for persisted messages (broker/INV-53, KMS), workload/node attestation, artifact signing (Sigstore/cosign) — `verify_artifact` checks digests and provenance presence only, not signatures.

## Secret handling

No secret material belongs in message-routing configuration or diagnostics. Adapter credentials are fetched per call from the platform secret mechanism and never written into envelopes, exception details, metric labels or dead-letter reasons.
