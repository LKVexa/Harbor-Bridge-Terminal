# Release process (M29)

1. `ci/scripts/ci.sh` — compile, unit/contract/security/fault/integration tests (normal and `-O`), schema lock, RTM check, fuzz smoke, benchmarks gate.
2. `python -m inv65_capability_providers.tools.release_gate` — runs everything, writes `evidence/pk_evidence.jsonl` (hash chain), `evidence/*-results.json`, `sbom/`, `provenance/`, `release/manifest.json` and `conformance/PK_GATE_RESULTS.json`.
3. Signing of manifest/SBOM/provenance with the owner's release key (not performed by tooling here — the key is owner-held).
4. Deprecation: a v1 contract field is removed only after one minor release served both v1 and v2.
