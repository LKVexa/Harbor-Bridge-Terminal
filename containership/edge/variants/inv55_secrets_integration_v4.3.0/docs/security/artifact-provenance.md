# Artifact provenance

| ID | INV55-SEC-PROVENANCE | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: security-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

- Release evidence SHOULD record SHA-256 digests of each source file, schema and config layer. Config digests are implemented (`config.py::canonical_digest`, `ConfigController.provenance`) and exposed in `health()["config"]`; policy digest in `health()["policy_digest"]`.
- Source/package digests: `tools/release_evidence.py` writes `evidence/release_evidence.json` with sha256 of every file, Python/platform versions and test results, plus a CycloneDX SBOM `evidence/sbom.cdx.json` (release-policy.md).
- Credential exclusion: `tools/secret_scan.py` (CI job `secret-scan`).
- **Signing and signature verification: NOT IMPLEMENTED — requires a key custody decision (dependency GAP-07 Artifact provenance/signing, `contract.py::build`).** No SLSA/in-toto attestation, SBOM signature or verify-on-load exists.
- Tracked as WVR-003.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-22 | Release evidence and secret-scan tools |
