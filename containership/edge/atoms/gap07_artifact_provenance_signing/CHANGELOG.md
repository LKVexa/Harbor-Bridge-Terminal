# Changelog - GAP-07

## 6.0.0 - 2026-09-22

Production completion pass driven by `GAP07_MISSING_COMPONENTS_PROFESSIONAL_CHECKLIST_v5.0.0.md` (48 components, 1,005 items).

### Added
- `PK_SIGNATURE/3` asymmetric envelope (Ed25519, ECDSA P-256/P-384, RSA-PSS ≥ 3072) with domain-separated, length-delimited signed bytes, namespace-qualified key ids, explicit algorithm pinning and downgrade refusal (`signing.py`, `algorithms.py`, `canonical.py`).
- KMS/HSM custody contract with AWS KMS, Azure Key Vault/MHSM, GCP KMS, Vault Transit and PKCS#11 adapters. The resilience layer adds timeouts, transient-only retry, a circuit breaker, key-policy enforcement and post-sign pin verification (`keys.py`).
- Certificate trust model: anchors, name-constrained intermediates, `PK_CERT/1` leaves, revocation, path-length and usage constraints, deterministic path choice, and X.509 code-signing validation (`trust.py`).
- DSSE / in-toto Statement v1 / SLSA Provenance v1 verification with per-predicate signer authorisation, thresholds and conflict detection (`dsse.py`). CycloneDX/SPDX SBOM policy binding (`sbom.py`).
- RFC 6962/9162 transparency proofs, signed checkpoints, monotonic offline cache and split-view detection (`tlog.py`).
- Durable trust persistence: config-authority signatures, stage/commit, monotonic floor, crash-safe writes, backup/restore/DR (`store.py`). Signed snapshot/delta distribution, a site agent and a revocation propagation SLO tracker (`distribution.py`).
- Trusted time from signed attestations, with a persisted floor and rollback/jump detection (`timesrc.py`).
- GAP-13 policy adapter with deterministic evaluation, signed scoped waivers and thresholds (`policy.py`).
- OCI manifest/index/referrers, Wasm header checks, streaming verification and a TOCTOU-safe content store (`registry.py`).
- A single fail-closed `AdmissionController`: allow/deny/defer/error, quarantine, replay-safe break-glass, rate limiting, expiry-bounded decision cache, handoff re-verification (`admission.py`, `controls.py`). HTTP service (`service.py`).
- Audit export with append-only sink, spool, anchoring and an independent verifier (`audit_export.py`). Key-compromise workflow (`compromise.py`). Metrics, logs, traces and health (`telemetry.py`).
- Assurance: 143 tests including interop vectors pinned to RFC 8032/RFC 6962, property, fuzz, concurrency and fault-injection suites. Benchmark and soak tools.
- Ops and governance: threat model, security-review packet, runbooks, 7 ADRs, owners file, dependency policy, alert rules, dashboard, SLO budgets, CI workflow, Kubernetes manifests, compatibility matrix, traceability matrix, release evidence and signing tooling.

### Security review (in-pass adversarial review, all fixed with regression tests)
- A forged leaf that reused a pooled certificate serial was accepted by `validate_leaf`. The leaf's own signature is now always verified.
- Break-glass did not bind kind or site, bypassed quarantine, and its nonces were not durable.
- A checkpoint of equal or smaller size from a forked log was accepted (split view).
- SBOM deny lists could be bypassed through nested components or purl qualifiers.
- A cached allow outlived signature, cert, waiver and checkpoint expiry.
- Name constraints matched by raw string prefix, and dot segments were allowed.
- DSSE subject type confusion raised an unstructured error.
- Custody `sign()` skipped the key-policy check, and unexpected adapter errors escaped the breaker.
- Audit truncation was undetectable without a reference.
- JCS key ordering differed from RFC 8785.
- Handoff of missing content raised an unstructured error.
- The first attestation after a restart was not jump-checked.
- A trust generation issued in the future never went stale.

### Compatibility
v5 APIs (`TrustStore`, `PK_SIGNATURE/2`, `PK_PROVENANCE/2`) are unchanged and remain reference-only. Production verification refuses `PK_SIGNATURE/1` and `/2`.

## 5.0.0 - 2026-09-22

Major security and correctness hardening pass.

### Critical fixes

- Replaced `PK_SIGNATURE/1` digest-only MACs with `PK_SIGNATURE/2`, binding environment, artifact kind, signer, key ID, digest, issuance time, schema, and algorithm. This closes same-role cross-kind replay (for example `code` -> `bundle`) and cross-environment replay.
- Replaced the v4 provenance head (which was only the last artifact digest) with `PK_PROVENANCE/2`, where every link hash commits to index, step metadata, artifact digest, and previous link hash. Step editing/reordering is now detectable.
- Moved key material out of `TrustStore`. The store now retains only signer role/key metadata and resolves key material through an external `KeyProvider` boundary.
- Added explicit signer-key rotation and old-key retirement semantics; silent signer replacement is rejected.
- Added strict signature envelope parsing/shape validation and stable machine-readable verification error codes.
- Added optional signature maximum-age enforcement when callers supply trusted time.
- Added streaming SHA-256 (`digest_chunks`) for large artifact pipelines.

### Audit and assurance

- Added local hash-chained `AuditLedger` events for trust mutations and sign/verify decisions/refusals.
- Added dependency-free security regression tests that run without `pk_core`.
- Added replay, malformed-envelope, revocation, key-rotation/retirement, freshness, provenance-tamper, and audit-chain-tamper tests.
- Added formal JSON Schemas for signature, verification, provenance, trust-store snapshot, and audit-event envelopes.
- Corrected README content that referenced an unbundled `MASTER.md`.

### Compatibility

This is a major version because `TrustStore.add()` now accepts a `key_id` instead of secret bytes, and `TrustStore.sign()` requires an explicit artifact kind. Legacy `PK_SIGNATURE/1` envelopes are intentionally not accepted by the hardened verifier.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

- Replaced behavioral bare assertions with optimizer-safe checks in component assessment logic.
- Added refusal `else` checks so expected-failure evidence cannot silently pass.
- Added stdlib conformance checks, version pinning, fail-closed unknown-kind handling, trust-store input validation, non-empty provenance enforcement, and resilient exception handling.

## 4.0.0

Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
