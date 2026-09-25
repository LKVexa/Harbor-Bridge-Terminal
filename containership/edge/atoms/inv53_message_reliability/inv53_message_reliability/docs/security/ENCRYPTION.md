# Encryption and key rotation (C047) — specification, partially implemented

| Layer | Status | Detail |
|---|---|---|
| Request authenticity | Implemented | HMAC-SHA256, 256-bit keys, key ids, rotation (`Keyring.rotate`), verify-only overlap, retirement |
| Journal integrity | Implemented | SHA-256 hash chain per record; snapshot digest; backup manifest |
| Transport confidentiality | Not in scope | TLS 1.3 at the transport that embeds the broker |
| Payload confidentiality at rest | **BLOCKED** | The standard library has no authenticated cipher. Required design: AES-256-GCM (or ChaCha20-Poly1305) envelope encryption, per-tenant data keys wrapped by a KMS key, key id stored per journal record, AAD = tenant/queue/seq. Needs an owner decision on a crypto dependency and a bound KMS (`UnboundKmsProvider` fails closed today). |

Rotation procedure (authentication keys): add new key → `rotate` (new active, old verify-only) → wait one
skew window + longest client cache → `retire` old key. Emergency revocation: `retire` immediately; clients
signing with it get `E_UNAUTHENTICATED`.
