# ADR-0004 — Channel encryption and key lifecycle

* **Status:** Proposed (W-001) · **Date:** 2026-09-22

* Channel: TLS 1.3 only (`minimum_version = TLSv1_3`), mutual auth, CA-pinned trust store, hostname verification on clients. Cipher suites: the TLS 1.3 defaults of the linked OpenSSL (AES-GCM / ChaCha20-Poly1305).
* Envelope: HMAC-SHA256, ≥ 256-bit keys, domain-separated (`INV61-REQ\0`, `INV61-HELLO\0`).
* Rotation: `KeyRing.rotate` with overlap ≥ max deadline + replay window; certificates rotated ≥ 7 days before expiry.
* Outage semantics: if the key ring or certificates cannot be loaded, the node is not ready and refuses traffic (fail closed). No cached-key grace period.
* At rest: INV-61 persists no payloads. `state.json` holds idempotency results (callee outputs) — these MUST reside on an encrypted volume (host responsibility; W-004). Audit key and TLS key are file/env references only.
