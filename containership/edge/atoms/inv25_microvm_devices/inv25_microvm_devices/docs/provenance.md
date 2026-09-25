# Artifact trust policy (work item 18 — C045; supports C090/C100)

| Artifact | Integrity | Signature required |
|---|---|---|
| catalogue / policy documents | SHA-256 | yes |
| package / archive | SHA-256 | yes (release) |
| pk_core distribution | SHA-256 + index hash pin | yes |
| schemas, fixtures, SBOM | SHA-256 | optional |
| gate result | SHA-256 | yes |

Attestation format `INV25_ARTIFACT_ATTESTATION/1` binds `artifact_type`, `name`, `version`, `digest`,
`signer`, `source_revision`, `builder`. Verification order: format → digest (before any parse) →
binding → approved-version manifest → signer trust/revocation → signature. Any failure raises
`INV25_ARTIFACT_VERIFICATION_FAILED`; the store emits `artifact.verification_failed`.

Signer roots, rotation (≤ 12 months) and revocation lists are owned by `@inv25-release`. The shipped
reference scheme is HMAC; organisational asymmetric signing (Sigstore / X.509) is PENDING (W-0005) and
plugs into `TrustPolicy`. Unknown schemes fail closed.
