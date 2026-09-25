# ADR-005: KMS-shaped key interface with a software backend only
Status: Proposed · Date: 2026-09-22

**Decision.** Every signing path goes through `KeyStore.sign(key_id, msg, principal=…)` with a per-key ACL and versioned key ids; retired versions cannot sign. The only backend is in-process Ed25519 (`SoftwareKeyStore`). HSM/cloud KMS backends are **blocked** (no device/service).
**Consequences.** Non-exportability, audit logging of key use by the KMS itself, and hardware zeroization are not achieved.
**Links.** R2, R5 · `mc/keys.py`.
