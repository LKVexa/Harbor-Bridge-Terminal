# Security model — INV-37 v4.3.0

Threats, controls and residual risk per boundary are in `THREAT_MODEL.md`. This file summarises controls and what is still external.

## Implemented in 4.3.0

- **Authentication (C023, C044)** — `security.py`: HMAC-SHA256 capability tokens (`v1.<kid>.<claims>.<mac>`) carrying principal, tenant, node, actions, scope, iat/exp, nonce, single-use flag. Clock-skew window, expiry, not-before, revoked key ids and subjects, node binding, replay cache for single-use tokens. Failures return a generic `authentication failed`; the precise reason goes only to the audit log.
- **Authorization (C024, C042)** — deny by default, checked on **every** call against action, tenant and scope. Actions: `create-transfer, attach-buffer, write-chunk, read-progress, resume, finalize, cancel` (data) and `quarantine, release, inspect, administer, freeze` (admin); the two sets cannot be minted together. Admin tokens with tenant `*` can act across tenants for admin actions only.
- **Key lifecycle** — key ring file (mode 0600 enforced), active key + verification-only older keys, `rotate()`, `revoke()` (active key cannot be revoked before rotation). Minimum key length 32 bytes.
- **Tenant isolation (C046)** — per-transfer shared-memory regions with HMAC-bound descriptors and revocation; per-tenant quotas keyed by authenticated identity; checkpoint directories per transfer; tenant ids pseudonymised in logs/diagnostics.
- **Tamper-evident audit (C049)** — hash-chained, MAC-protected JSONL (`AuditLog`, `verify_audit`); events: create, verified, cancel, quarantine, tenant quarantine, freeze, authn denied/replay, authz denied, admin grants. A broken chain refuses start.
- **Provenance / artifact integrity (C045)** — zero runtime dependencies (`tools/check_pins.py`), exact build pin, SBOM with per-file SHA-256 (`artifacts/certification/sbom.cdx.json`), source digest in health, gate evidence and decision records.
- **Security-service outage (C048)** — time source failure → `security_service_unavailable` (fail closed); key ring is local so identity does not depend on a network service; policy is a local versioned file; encryption requirement without provider → refuse.
- **Residency and precedence (C019)** — `policy/precedence.json`, `precedence.resolve()`; security/residency/integrity can never be overridden.
- **Integrity** — unchanged from 4.2.0 (strict manifest validation, per-chunk and object verification, constant-time comparisons), plus in-place re-verification on the shm path and seal + re-hash on checkpoint load.

## Not implemented (tracked, production-gate BLOCKED)

| Control | Why not in-repo | Gate criterion |
|---|---|---|
| mTLS / SPIFFE / workload identity, node attestation | needs PKI/attestation service integration | `mtls_or_workload_identity` |
| Encryption in transit / at rest with managed rotation (C047) | stdlib has no AEAD; no crypto dependency approved or pinned. Provider hook `register_encryption_provider()` exists; configs requiring encryption fail closed. | `encryption_provider_pinned` |
| HSM/KMS key custody | external service | `mtls_or_workload_identity` |
| Signed release artifacts / attestations | release-infrastructure keys | `sbom_signed_artifact` |
| Independent penetration test, side-channel review | requires external assessor | `independent_penetration_test` |

## Reporting

Report suspected vulnerabilities to the `security_owner` role (governance/OWNERS.json). Response targets are in OPERATIONS.md §Vulnerability response.
