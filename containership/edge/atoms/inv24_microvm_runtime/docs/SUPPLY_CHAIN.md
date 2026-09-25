# Supply chain, packaging, provenance (MC-017, MC-018, MC-019)

- Package: `pyproject.toml` (stdlib only — no runtime dependencies to lock). `requirements.lock` states this explicitly.
- Bootstrap: `tools/bootstrap.sh` creates a venv, installs the package offline from the source tree and runs the standalone suite.
- Approved artifacts: `artifacts/firecracker/manifest.json` — **UNPINNED** today; launch fails closed.
- SBOM: `tools/run_evidence.py` emits `evidence/sbom.json` (every shipped file + SHA-256) and `evidence/artifact-digests.json`.
- Provenance: evidence records name the git commit, archive SHA-256 and tool versions. Signing (Sigstore/in-toto) is **BLOCKED** on an org signing identity.
- Licence: **no licence has been chosen by the owner**; see `NOTICE`. Distribution is BLOCKED until one is recorded (MC-019).
