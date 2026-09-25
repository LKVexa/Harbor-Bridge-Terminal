# Release, evidence and supply chain (C090, C100, REPO-006, REPO-010)

`python verify.py` is the single release gate. It:

1. compiles all sources; 2. regenerates schemas in check mode (drift ⇒ FAIL);
3. runs every suite (unit, contracts, fixtures, fuzz, concurrency, security,
faults, integration, performance) — **any skip of a mandatory suite ⇒ not PASS**;
4. rebuilds the RTM and checks it covers all 100 checklist rows;
5. builds `release/manifest/MANIFEST.json` (SHA-256 per file + tree digest),
`release/sbom/sbom.cdx.json` (CycloneDX 1.5), `release/provenance/provenance.intoto.json`
(in-toto/SLSA v1 statement), `release/NEXUS_SPEC_MANIFEST.json`;
6. evaluates governance (owners, license, approvals, waivers, reviews, dependency pins);
7. writes `conformance/PK_GATE_RESULTS.json` (`INV35_GATE_RESULTS/1`) and
`evidence/gate-<version>.json`, sealed with HMAC-SHA-256 when `INV35_EVIDENCE_KEY` is set.

Verdicts: `FAIL` (exit 1) — a technical check failed; `PARTIAL` (exit 2) — all
technical checks pass but production blockers remain (pk_core, governance,
unsealed evidence); `PASS` (exit 0) — nothing outstanding. A human-readable
summary is regenerated from the JSON (`tools/exit_summary.py`), never hand-edited.

Planned hardening (TD-002): replace HMAC seal with Sigstore keyless signing bound
to the CI OIDC identity; attach SLSA provenance from the CI builder.
