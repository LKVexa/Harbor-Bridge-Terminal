# 06 — Ledger entry (paste once the yard office is installed)

```bash
ledger log-job --job "gap07_artifact_provenance_signing overhaul" \
  --parts "build-new: all 48 GAP-07 completion components; dependency cryptography (Apache-2.0 OR BSD-3-Clause)" \
  --outcome "GAP-07 v6.0.0: asymmetric PK_SIGNATURE/3, KMS adapters, cert trust, DSSE/SLSA, tlog, persistence/distribution, policy, admission; 143 tests; production_ready=false pending estate integrations + independent review" \
  --notes "work-order-gap07_artifact_provenance_signing-20260922; build-new: sigstore/in-toto/rekor/tuf-class parts (searched by name: sigstore cosign in-toto rekor tuf slsa dsse notary sbom cyclonedx spdx trillian merkle; listing capped at 2000)"
```
