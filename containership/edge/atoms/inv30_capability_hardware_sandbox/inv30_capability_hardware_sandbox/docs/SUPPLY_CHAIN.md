# Supply chain and integrity (INV30-GAP-024 · INV-30-C045, C090, C094)

* `integrity.manifest()` → `evidence/MANIFEST.sha256.json` (per-file SHA-256 + tree digest).
* `integrity.sbom()` → `evidence/SBOM.cdx.json` (CycloneDX 1.5) naming this package and the resolved `pk_core`
  with a digest over its sources.
* `integrity.sign_manifest/verify_manifest` — HMAC-SHA256 detached signature (estate-internal key).
* **Production path (not bundled, required before a public release):** Sigstore/cosign keyless signing of the
  wheel + SLSA provenance generated in CI (`.github/workflows/ci.yml` job `provenance`, gated on repo secrets).
* Dependency policy: stdlib only; any new dependency needs owner + security review and a lock entry.
* Consumers verify with `python -m …release --verify --out evidence/` (offline).
