# Changelog

## 4.3.0 — 2026-09-23 — missing-components remediation

Driven by `PLN07_v4.2.0_MISSING_COMPONENTS_COMPREHENSIVE_CHECKLIST.md` (72 items). Status: `MISSING_COMPONENTS.md`.

### Added
- `clock.py` trusted time: quorum, disagreement bound, rollback detection, fail-closed (MC-12).
- `signing.py` KeyStore: Ed25519/HMAC, key ids, rotation, key revocation, algorithm policy, `PK_SIG/1` (MC-05).
- `identity.py` boundary authentication and attestation policy (MC-03, MC-64).
- `policy.py` issuance authorizer, per-tenant/capability/environment depth limits, quota, precedence (MC-04, MC-15, MC-62, MC-63).
- `revocation.py` durable hash-chained registry: fingerprint keys, epoch fencing, acks, horizon, tombstones, crash recovery (MC-06, MC-10, MC-14, MC-29, MC-30).
- `config.py` declarative config: schema, secure defaults, overlays, provenance, atomic activation, rollback, redaction (MC-17..MC-20).
- `resilience.py` health/watchdog, retry, idempotency, admission, circuit breaker, quarantine (MC-25..MC-28, MC-31).
- `observability.py` metrics, structured logs, W3C tracing, hash-chained audit, redaction, cardinality guard (MC-40..MC-47).
- `service.py` versioned issue/attenuate/verify/revoke/health/explain boundary + wire codec (MC-09, MC-10, MC-16, MC-39, MC-45).
- `deploy/` stdlib HTTP host, systemd unit, Kubernetes stable+canary, alerts, dashboard (MC-22, MC-48).
- `bench/` benchmark suite with budgets and reference results (MC-33..MC-38, MC-55).
- `ci/gate.py` gate + evidence bundle + CycloneDX SBOM + manifest reseal (MC-23, MC-56, MC-57, MC-72).
- `tests/test_v43.py`: 49 tests — contract, HTTP transport, threat, concurrency, fuzz (with corpus), durability, performance smoke.
- New schemas: `PK_GRANT/2`, `PK_REVOCATION/2`, `PK_SIG/1`, `PK_AUDIT/1`.
- `pyproject.toml`, `lock/requirements.lock`, `NOTICE`, `docs/` (ADR, semantics, boundary auth, performance, observability, compatibility, support/vuln, ownership, profiles, review program, waivers, exit gate, runbooks, incident response).

### Changed
- `Grant` gains optional `environment/site/workload/audience/issued_at/not_before/nonce`; v1 bodies and legacy ids are byte-identical to 4.2.0.
- `Verifier` accepts full fingerprints in `revoked`, plus `revocation_source`, `depth_policy`, `require_v2` and boundary context; `verify_detailed` maps malformed input to `grant.malformed`.
- `component.py` uses in-package signing/revocation when GAP-07/GAP-04 are absent (findings stay `partial`).

### Not done (external)
MASTER.md recovery, pk_core pin, sibling integrations, LICENSE choice, far-edge power/thermal, human approvals. See `evidence/EXTERNAL_BLOCKERS.json`.

## 4.2.0 — 2026-09-22

Second audit, correctness hardening, and evidence-quality pass.

### Security-core hardening

- Added `grants.py` as a framework-independent security core so grant invariants can be tested even when `pk_core` is absent.
- Added strict validation for subjects, tenants, capability atoms, expiry/depth/skew integers, scope cardinality, parent type, and revocation identifiers.
- Enforced parent constraints at object construction, closing the direct-constructor bypass for scope widening, expiry extension, tenant crossing, and forged depth.
- Reject no-op attenuation and cap delegation depth on both derivation and verification paths.
- Added cycle detection for malformed/tampered grant chains.
- Added canonical JSON payloads for signature binding and optional fail-closed signature verification across every link in the chain.
- Added machine-readable verification decisions and stable error codes.
- Added a full SHA-256 audit fingerprint while deliberately preserving the previous 4.x 16-hex `Grant.id` algorithm for revocation compatibility.

### Verification and schemas

- Added framework-independent unit tests covering widening, expiry, tenant isolation, capability checks, revocation inheritance, depth, no-op attenuation, input validation, structured decisions, signatures, and identifier compatibility.
- Verified the standalone suite under normal Python and `python -O`.
- Added versioned schemas for `PK_GRANT/1`, `PK_GRANT_VERIFICATION/1`, and `PK_REVOCATION/1`.
- Added `SECURITY.md`, `POST_AUDIT.md`/`.json`, and `MISSING_COMPONENTS.md`.

### Documentation corrections

- Removed the false statement that `MASTER.md` is bundled. The source file was absent from the supplied archive and is now explicitly tracked as missing rather than reconstructed and misrepresented as verbatim source material.
- Corrected the prior blanket “all 100 requirements satisfied” framing. Checklist answers and framework-derived findings are not the same as production implementation evidence; the post-audit matrix records the distinction.

## 4.1.0 — 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- `component.py`: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O`.
- `component.py`: expected-refusal findings gained explicit failure branches.
- `tests/test_component.py`: stdlib conformance test for finding count, optimization-mode parity, and version pin.
- Added `VERSION` and package `__version__`.

### Defects fixed

- `Grant.id`: parent identity included in the seed.
- `Verifier.verify`: child expiry and delegation depth are checked per link.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
