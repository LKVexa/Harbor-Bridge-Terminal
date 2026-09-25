# Key management (M19)

- **At rest:** AES-256-GCM (`cryptography` extra `[crypto]`), AAD = record key, key id in every blob. `KeyRing` = one active + retired decrypt-only keys. Rotation: add new active key → `LinkStateStore.rekey()` → retire old key. Missing library or key ⇒ PK_PROVIDER_KEY_UNAVAILABLE; no plaintext fallback.
- **In transit:** TLS 1.3 only, client certificates required (mTLS). Plaintext only for loopback tests with an explicit flag.
- Key material is read from files named in host config; never inlined. KMS/HSM integration is an external adapter (not in archive).
