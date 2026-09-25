# Release evidence and production exit gate (INV30-GAP-060, GAP-069, GAP-047 · INV-30-C090, C100)

`python -m pk_components.inv30_capability_hardware_sandbox.release --out evidence/` produces:
`RELEASE_EVIDENCE.json` (INV30_RELEASE_EVIDENCE/1), `MANIFEST.sha256.json`, `SBOM.cdx.json`, `ENVIRONMENT.json`.

The exit gate aggregates: architecture (ADR sign-off), requirements/traceability (TRACEABILITY.json), interfaces
(contract suite), implementation (unit/property), security (adversarial suite, threat model), resilience (fault
suite), performance (bench regression), observability (service suite), testing (all suites ×2 modes), rollback
(ops suite), ownership (sign-offs).

Verdicts: `NO_GO` (any invariant failure — unwaivable — or any blocker) · `CONDITIONAL_GO_MODEL_ONLY` /
`GO_MODEL_ONLY` (all green, no hardware evidence; the hardware tier stays NO_GO) · `CONDITIONAL_GO` / `GO`
(hardware conformance green). Conditions = missing human sign-offs. `release --verify` re-checks offline that the
evidence is bound to the exact tree.
