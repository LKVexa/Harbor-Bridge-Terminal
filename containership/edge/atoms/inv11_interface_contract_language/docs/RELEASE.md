# Release, signing and reproducibility

```sh
# full local qualification (tests normal + -O, differential, lint, types,
# benchmarks, soak, reproducible archive, SBOM, provenance, evidence bundle)
INV11_WASM_TOOLS=/path/to/wasm-tools-1.219.1 python -B tools/evidence.py --out evidence

# verify a bundle
python -B tools/verify_evidence.py evidence/EVIDENCE_BUNDLE.json
```

* Archive: `release.build_archive` — sorted entries, fixed 1980-01-01 dates (or
  `SOURCE_DATE_EPOCH`), mode 0644, deflate 9, caches excluded. Two builds are
  compared byte-for-byte (`verify_reproducible`); any difference blocks release.
* SBOM: CycloneDX 1.5 JSON with per-file SHA-256; runtime dependencies: none.
* Provenance: in-toto v1 statement with SLSA provenance predicate whose subject
  is the archive digest.
* Signature: Ed25519 over the archive bytes via OpenSSL. **The key used by the
  builder's run is ephemeral and proves the mechanism only**; a production
  signature requires the owner's release key and trust root (BLOCKED).
* Verification: `openssl pkeyutl -verify -pubin -inkey release.pub -rawin -in <zip> -sigfile <zip>.sig`
  and `sha256sum -c` against `MANIFEST.sha256`.
