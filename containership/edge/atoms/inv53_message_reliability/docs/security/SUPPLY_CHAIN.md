# Supply-chain verification and SBOM policy (C045)

- Runtime dependency set: the CPython standard library only (`requirements/runtime.txt`).
- Test-time dependency `pk_core` is pinned by content digest in `requirements/pk_core.lock.json`; the CI
  `pk_core` lane refuses a copy whose digest differs.
- `tools/build_release.py` produces a byte-reproducible tarball and a CycloneDX SBOM; the CI `reproducible`
  lane builds twice and compares hashes.
- Not yet provided (owner action): signing of the release artifact and SBOM with an organisational key,
  provenance attestation (SLSA), and a vulnerability-feed scan — no feed is reachable from the build here.
