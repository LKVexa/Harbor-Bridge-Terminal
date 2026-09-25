# PLN-07 — Security plane

**Version:** 4.3.0  
**Group:** 02_Synthesis_Planes  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`

> **Audit note:** the prior README claimed that `MASTER.md` was bundled. It is not present in the supplied archive and has not been fabricated in this revision. The missing source artifact is tracked in `MISSING_COMPONENTS.md`.

## Responsibility

The security plane replaces ambient trust with explicit, attenuable capabilities. It owns grant representation, attenuation invariants, verification, trust-class definitions, and revocation semantics. It does **not** provision identities, author policy, store secret material, or enforce grants inside other planes.

## What changed in 4.2.0

The security-critical grant model is now isolated in `grants.py`, which has no `pk_core` dependency. This closes the previous test blind spot where every conformance test could skip when `pk_core` was unavailable. The hardening pass adds strict input validation, constructor-time parent/tenant/scope/expiry/depth invariants, no-op attenuation rejection, cycle protection, structured verification results and error codes, canonical signature payloads, optional fail-closed signature verification, and a full SHA-256 audit fingerprint while preserving the existing 4.x 16-hex grant ID format for revocation compatibility.

Three versioned JSON schemas are included under `schemas/`:

- `PK_GRANT-1.schema.json`
- `PK_GRANT_VERIFICATION-1.schema.json`
- `PK_REVOCATION-1.schema.json`

The package still depends on external architectural components for production-complete identity/attestation, policy authorization, signing/trust roots, disconnected-site coordination, and enforcement. Those and all other unresolved production gaps are enumerated in `MISSING_COMPONENTS.md` and traced requirement-by-requirement in `POST_AUDIT.md`.

## Public grant primitives

- `Grant` — immutable tenant-bound capability grant with scope, expiry, parent chain, issuer metadata, stable 4.x ID, and full SHA-256 fingerprint.
- `Grant.attenuate(...)` — derives a same-or-narrower child; widening, cross-tenant children, invalid depth, and no-op attenuation are refused.
- `Verifier.verify(...)` — validates the complete chain, revocations, expiry/skew, tenant boundary, delegation depth, capability membership, and optional signatures.
- `Verifier.verify_detailed(...)` — emits a machine-readable `PK_GRANT_VERIFICATION/1` decision.

## External dependencies named by the contract

- `GAP-06 Device identity and attestation` — holder identity
- `GAP-13 Policy engine` — issuance authorization
- `GAP-07 Artifact provenance/signing` — cryptographic signing/trust verification
- `GAP-04 Disconnected-operation controller` — disconnected-site revocation horizon coordination
- `PLN-04 Execution plane`, `PLN-03 Distributed runtime plane`, and `PLN-01 Intent plane` — enforcement/admission integrations

The uploaded archive does not include these dependencies, so their integration cannot be certified by this package alone.

## Verification

From the folder containing `pln07_security_plane`:

```text
python pln07_security_plane/tests/test_grants.py
python -O pln07_security_plane/tests/test_grants.py
python pln07_security_plane/tests/test_component.py   # requires pk_core; set PK_CORE_PATH when external
python -m compileall -q pln07_security_plane
```

The first two commands exercise the security primitives without the orchestration framework. The `test_component.py` suite is an integration/conformance suite and skips when `pk_core` is not available; a skip is **not** production acceptance evidence.

## Operational outline

- **Day 0:** install the component with its pinned `pk_core` and required sibling planes, run the framework gate, and archive machine-readable evidence.
- **Day 1:** deploy only after identity, policy, signing, time, revocation, and enforcement integrations are present and the production exit gate passes.
- **Day 2:** rerun conformance and security checks on every contract or implementation change and preserve the evidence chain.

Rollback is the previous sealed release/evidence head. Emergency disable must remove or deny the component through the controlling registry/orchestrator rather than silently bypassing verification.

## Audit artifacts

- `SECURITY.md` — threat model and secure-use constraints for this revision.
- `POST_AUDIT.md` — second-pass audit, validation results, and 100-requirement traceability matrix.
- `POST_AUDIT.json` — machine-readable form of the post-audit (explicitly not a production gate result).
- `MISSING_COMPONENTS.md` — consolidated inventory of unresolved components required for production completeness.


## 4.3.0 quick start

```bash
python -m unittest pln07_security_plane.tests.test_v43 pln07_security_plane.tests.test_grants
python -m pln07_security_plane.ci.gate          # writes evidence/EVIDENCE.json, prints verdict
python -m pln07_security_plane.bench.bench --quick
PLN07_AUTH_SECRET=... python -m pln07_security_plane.deploy.host
```

Modules: `grants` (model), `clock`, `signing`, `identity`, `policy`, `revocation`, `config`, `resilience`, `observability`, `service`. Status of every remediation item is in `MISSING_COMPONENTS.md`.
