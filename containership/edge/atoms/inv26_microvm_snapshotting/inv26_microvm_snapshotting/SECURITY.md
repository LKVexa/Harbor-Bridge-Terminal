# Security design (C023, C024, C039, C042-C045, C047, C048)

## Authentication (C023, C044)
EdDSA (Ed25519) compact tokens, verified against a `TrustStore` of keys with **role** (`caller` or
`grant-issuer`), **trust domain** (`<environment>/<site>`) and state (active / verify_only / revoked).
Checks: algorithm allowlist (HS256 only in the `reference` profile; `none` and everything else refused), kid
known and not revoked, role matches use, trust domain equals this node's, signature, `aud` = this service
instance, `env`/`site` match, `nbf`/`exp` with ±30 s skew, lifetime ≤ 1 h (break-glass ≤ 15 min). Revocation
is immediate; a revoked kid cannot be re-added. **Not provided here:** mTLS/SPIFFE transport identity,
automated trust-root distribution/rotation, hardware attestation (C044 PARTIAL).

## Authorization (C024)
Deny-by-default capabilities `snapshot.{capture,restore,delete,inspect,quarantine,admin}` scoped to
tenant/workload/environment; wildcards only honoured on `snapshot.admin`. Authorization is evaluated against
the **request** scope before any storage access, key unwrap, hypervisor mutation or entropy injection, and
restore additionally requires a one-shot grant bound to node, target VM, snapshot manifest digest and
generation. Break-glass: `bg: true` + reason ≥ 10 chars + ≤ 15 min lifetime; every use is audited fail-closed.

## Secrets (C039)
No secret may appear in configuration (`find_secrets` → `SNAP_CONFIG_INVALID`; only `secretref://` references),
logs, audit details, metrics labels (all pass through `redaction.redact`), responses (public envelopes only),
or decision records. The entropy seed is never returned (only `sha256(seed)`), never logged, and its only
reference is dropped after injection; DEK buffers are zeroized where Python allows (bytearray), acknowledging
that immutable `bytes` copies cannot be wiped (DATA_LIFECYCLE.md). `tools/secret_scan.py` scans the tree and
the evidence directory.

## Least privilege and ambient authority (C042, C043)
Specification: `ops/least_privilege.json`. The runtime reads no environment variables, opens no network
sockets itself, holds no `/dev/kvm` (the VMM does), writes only to the configured metadata/blob/work
directories with 0600/0700 modes, and talks to the VMM only through the brokered `HypervisorPort`.
**Enforcement (seccomp, capabilities drop, namespaces, IAM scoping) is the deployer's and cannot be verified
from this repository** — C042/C043 stay PARTIAL.

## Artifact verification (C045)
Releases carry SHA256SUMS, a CycloneDX SBOM and an in-toto/SLSA-shaped DSSE provenance statement
(`provenance.py`, `tools/release.py`); `tools/release.py verify` refuses tampered or unsigned artifacts.
The signing key is **ephemeral** (generated per build) until a managed signer exists — so provenance proves
integrity, not publisher identity (C045 PARTIAL, X005 BLOCKED_EXTERNAL).

## Encryption (C047)
See `crypto.py`: AES-256-GCM chunked envelope, per-snapshot DEK, KMS-wrapped with context-bound AAD, key
versions with rotation/rewrap (`SnapshotService.rewrap_all`), disable, destroy (crypto-erase). In-transit
encryption for remote KMS/storage/control-plane links is the transport adapter's (not included).

## Dependency outages (C048)
`policy.OUTAGE`: identity, KMS, storage, hypervisor, entropy, time → fail closed; audit → bounded buffer for
capture/restore, fail closed for privileged ops; telemetry → degrade; control plane → issued grants honoured
until expiry. Readiness reports `dependency_down:<name>`. Proven by `tools/faults.py` dependency matrix.
