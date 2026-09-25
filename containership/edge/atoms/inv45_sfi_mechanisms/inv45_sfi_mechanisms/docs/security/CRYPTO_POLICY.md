# Data classification, cryptography and key handling (C039, C044, C045, C047, C048)

## Data classification

| Data | Class | At rest | In transit | Retention |
|---|---|---|---|---|
| Artifact bytes (submitted / rewritten) | tenant-confidential | held by the caller; the service stores none | in-process / engine stdin pipe | not retained |
| Proofs, descriptors | internal integrity-critical | not stored by the service | in-process | caller-held until expiry |
| Sealing key, IdP key | secret | external secret store (env/file ref) | never leaves the process | rotation per below |
| Trust roots (public keys) | public, integrity-critical | config/control plane | — | until revoked |
| Tenant / workload ids | internal | audit, logs, metrics labels (bounded) | local | TELEMETRY_POLICY.md |
| Audit events | security record | local JSONL + exported checkpoints | local file | ≥ 400 days recommended |
| Diagnostics / crash data | internal | none persisted; errors carry allowlisted details only | — | — |

**Encryption.** The component stores no tenant-confidential data at rest and opens no network connections, so
it performs no bulk encryption itself. Encryption at rest of the audit/state directories and of any transport
that moves artifacts to the service is a **deployment requirement** (EXTERNAL; owner UNASSIGNED). C047 is
therefore recorded as *partial / external*, not implemented.

## Algorithms (pinned)

| Use | Algorithm | Keys |
|---|---|---|
| Artifact identity | SHA-256 over exact bytes | — |
| Canonical JSON digests | SHA-256 over `canonical_json` | — |
| Artifact provenance statement | Ed25519 (`cryptography`) | CI signer keys; public roots pinned by `key_id` |
| Sealed descriptor | HMAC-SHA256 | sealing keys ≥ 32 bytes by reference |
| Identity tokens | HMAC-SHA256 | IdP key ≥ 32 bytes by reference (a production IdP with asymmetric tokens is an open item) |

Rejected: SHA-1, MD5, CBC-mode anything, unauthenticated encryption, JSON signing over non-canonical text.

## Key lifecycle

* **Rotation:** add new key → activate (new descriptors use it) → keep old key for verification until all
  descriptors it sealed have expired (≤ `descriptor_ttl_seconds`, max 1 h) → revoke. Tested:
  `T03.test_key_rotation_old_descriptors_still_verify_until_revoked`.
* **Revocation / compromise:** revoke immediately (`KeyRing.revoke`, `ArtifactTrustStore.revoke`); every
  descriptor/statement under the key fails `SFI_SIGNATURE_INVALID`; resubmit under the new key; run the
  incident procedure in RUNBOOKS.md §Incident.
* **Trust-root update:** delivered with the config generation from the control plane; requires
  `sfi.keys.admin`, two humans (procedure), audit event.

## Behaviour when trust services are unavailable (C048)

| Service | Behaviour | Code |
|---|---|---|
| Secret store unreachable | no signing, no verification of descriptors → no new trust | `SFI_DEPENDENCY_UNAVAILABLE` (retryable) |
| Key/revocation data older than `trust_max_age_seconds` | no new submit/load; health `dependency_stale` | `SFI_TRUST_STALE` |
| IdP key unreachable | every call unauthenticated | `SFI_DEPENDENCY_UNAVAILABLE` |
| Time service skew | descriptors/tokens may expire early or late within skew; bound A-19 (±60 s) | — |
| Attestation service | not used in this release (no attestation claims are trusted) | — |
| Ed25519 provider missing | signature verification fails closed | `SFI_DEPENDENCY_UNAVAILABLE` |

Loss of any trust service can never produce a trust grant (tests `T11`, `FM04`, `FM06`).
