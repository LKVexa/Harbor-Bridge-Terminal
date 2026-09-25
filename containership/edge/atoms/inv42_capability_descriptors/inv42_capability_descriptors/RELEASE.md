# Release and supply-chain procedure (MC-014)

1. Tag from a clean tree. `provenance.intoto.json` records the `dirty` flag.
2. CI job `gate` builds with `tools/release.py build`. The build produces:
   - a deterministic tarball (fixed epoch, uid, gid and mode, sorted entries);
   - a CycloneDX 1.5 SBOM;
   - SLSA v1 provenance;
   - a per-file SHA-256 manifest;
   - an Ed25519 signature over the canonical manifest.
3. Signing uses a KMS/HSM-backed key through the signing service (KEY_MANAGEMENT.md). CI never holds a raw long-lived key. A build signed with an ephemeral key is marked `channel: dev-only`, and the exit gate refuses it.
4. Consumers verify before install:

   ```
   python tools/release.py verify --dist <dir> --pubkey release-pub.pem
   ```

   This checks the signature, key identity, artifact hashes, SBOM↔archive and provenance↔archive binding, and byte-reproducibility of the archive.
5. Only artifacts with `production_eligible: true` and a `PRODUCTION_APPROVED` exit verdict are published to the production channel.
6. Provenance and evidence are retained for the support lifetime plus 3 years.
7. Dependencies: the runtime has no third-party dependencies. Release tooling installs from `requirements-release.txt` with `--require-hashes`, and CI actions are pinned by commit SHA.
