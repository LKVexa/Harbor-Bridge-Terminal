# v0.2.0 closure addendum (2026-09-23)

This pass executed the missing-components checklist against v0.1.1. All engineering work that could be done without the owner was implemented and tested. See `CLOSURE_STATUS.md` for each item and `evidence/closure/` for the run transcripts. Summary:

| ID | v0.1.1 | v0.2.0 |
|---|---|---|
| M01 | missing | Provisioning/validation machinery and docs are done and tested. Genuine toolchains and the redistribution decision are **BLOCKED** (owner) |
| M02 | missing | Acceptance checker and simulated transactional evidence are done. Genuine `VERIFY/2` is **BLOCKED** (needs toolchains and pins) |
| M03 | missing | Privileged workflow is written. Environment, runner, required checks and CODEOWNERS are **BLOCKED** (owner settings) |
| M04 | missing | Lock, schema, enforcement and negative tests are done. Pins are **BLOCKED** (owner) |
| M05 | missing | Decision packet only. **BLOCKED** (owner/legal); no license was invented |
| M06 | missing | Specification only. **BLOCKED** (needs a real contact); no contact was invented |
| M07 | missing | Generator and validator are done. The SBOM is published as a DRAFT until pins and a license exist |
| M08 | missing | Packaging, provenance, sign and verify are done and proven with a throwaway key. The owner signing identity is **BLOCKED** |
| M09 | missing | **Done**: three schemas, a validator, fixtures and a compatibility policy |

`evidence/VERIFY.json` is still the historical `IOS735_LCTL/VERIFY/1`. No genuine `VERIFY/2` exists yet, and none was simulated into the evidence tree.

---

# iOS735 → LCTL v0.1.1 Post-Update Audit

## Audit result

**Offline repository integrity: PASS.** The updated repository preserves the complete v0.1.0 generated payload while hardening regeneration and verification behavior.

Validated on 2026-09-23:

- 735/735 components round-trip from canonical LCTL and `TRANSLATION_MAP.json` to the Swift skeleton.
- 18,375/18,375 control-ledger entries reconcile with the map.
- 44 source LCTL-C units and 44 canonical LCTL units have identical unit membership.
- 43 phase units plus the application unit are present.
- Canonical corpus contains the documented 17,481 tuple rows and 822 frames.
- Historical bundled owner-toolchain evidence reports 44/44 PASS for LCTL 1.6.1 column verification/compilation and 44/44 PASS for LCTL 1.6.0 canonical verification.
- 132 LCTL 1.6.0 analysis artifacts are present: 44 causal-DAG, 44 parallel-plan, and 44 provenance outputs; all are non-empty and match the canonical unit set.
- 9/9 semantic corruption falsifiers are caught.
- Clean regeneration of `source/` and `map/` is byte-identical.
- `source/`, `canonical/`, and `map/` are byte-identical to the v0.1.0 archive; the v0.1.1 bump changes tooling, tests, CI, release metadata, and audit controls only.
- Transactional full-verifier behavior was exercised with a simulated toolchain: a complete simulated PASS committed staged outputs; a forced provenance failure produced FAIL and did not modify canonical output.
- No symlinks, temporary `.tmp`/`.new` files, bytecode caches, TODO/FIXME/HACK markers in tooling/docs, or unit-set drift remained at packaging time.

## Fixed/hardened components

1. **Translator input validation.** Exact component/phase/control cardinality, duplicate/orphan control detection, safe module/type path components, known status/family validation, Swift capability parity, lifecycle/error-table drift checks, atomic writes, stale generated-unit reconciliation, and isolated `--out` regeneration were added.
2. **Independent semantic checker.** Exact canonical-unit membership, region/status metadata, lifecycle event metadata, dependency edges, failure map, state domain, budgets, capability gates, hardware/fallbacks, family clause operator/evidence mapping, app/phase composition, phase source seals, and the complete translation map are now checked independently of the translator.
3. **Falsifier coverage.** The corruption suite expanded from six to nine cases and now includes capability-gate weakening, family-metadata corruption, and translation-map contract-hash corruption.
4. **Transactional owner-toolchain verifier.** Canonical/evidence generation is staged; all required gates must pass before generated outputs are committed. Toolchain roots/JARs and Java 21+ are validated, subprocess errors/timeouts are captured, stale generated outputs are reconciled only after success, and future `VERIFY/2` evidence records observed Java/JAR identities.
5. **Automated offline regression.** Dependency-free tests now cover semantic round-trip, all falsifiers, byte determinism, repository/evidence shape, and the release manifest. CI runs on Windows and Linux with Python 3.10 and 3.13.
6. **Release integrity.** `VERSION`, `CHANGELOG.md`, `.gitignore`, `MANIFEST.sha256`, manifest verification tooling, and this audit report were added.

## Remaining missing components

The following list is scoped to components needed for a **self-contained, externally redistributable, continuously reproducible, release-grade verification package**. Within that scope, these are the remaining gaps found after the v0.1.1 hardening pass.

### M01 — Owner LCTL toolchains are not bundled or provisioned

**Impact: High (self-contained reproducibility).** The repository cannot perform a real fresh LCTL 1.6.1 compile or LCTL 1.6.0 verify/analysis run by itself. `tools/verify.py` requires external roots containing `lctl-hyperfederated.jar` and `lctl-runtime.jar`.

**Needed component:** an authorized distribution/provisioning mechanism for the exact LCTL 1.6.1-RC1 and 1.6.0-RC1 toolchains, or documented retrieval instructions if redistribution is not permitted.

### M02 — Hardened `VERIFY/2` evidence from the real toolchains is not yet present

**Impact: High (attestation of the new verifier).** The bundled `evidence/VERIFY.json` is the original `IOS735_LCTL/VERIFY/1` PASS. It remains applicable to the unchanged generated payload, but it does not demonstrate an actual owner-toolchain run through the new transactional verifier and does not contain the new Java/JAR SHA-256 identity fields.

**Needed component:** rerun `tools/verify.py` with the actual LCTL 1.6.1/1.6.0 roots and retain the resulting `IOS735_LCTL/VERIFY/2` evidence.

### M03 — Full owner-toolchain CI gate is not configured

**Impact: High (continuous end-to-end assurance).** CI currently performs the complete offline integrity suite on Windows/Linux, but it cannot compile and re-verify canonical LCTL because the external toolchains are unavailable in CI.

**Needed component:** a protected CI job that securely provisions the authorized LCTL toolchains and runs `tools/verify.py` as a required release gate.

### M04 — Trusted external-toolchain identity pins are absent

**Impact: High (supply-chain reproducibility).** `VERIFY/2` will record the *observed* JAR hashes at execution time, but the repository does not contain an independently trusted allowlist/lockfile declaring which LCTL JAR hashes are approved.

**Needed component:** a version-controlled toolchain lock/allowlist containing expected SHA-256 values (and, ideally, publisher/signature metadata) for the authorized LCTL JARs and Java distribution policy.

### M05 — License is absent

**Impact: High (legal redistribution/use).** There is no root `LICENSE`/`COPYING` file, so reuse, modification, and redistribution rights are not stated by this repository.

**Needed component:** an owner-approved license file and any required third-party notices. This was not invented during the audit because licensing terms require the repository owner's decision.

### M06 — Security reporting policy is absent

**Impact: Medium (security governance).** No `SECURITY.md` defines supported versions, vulnerability-reporting channels, embargo expectations, or response policy.

**Needed component:** an owner-approved security policy with a real private reporting contact/process.

### M07 — SBOM / formal dependency inventory is absent

**Impact: Medium (supply-chain transparency).** The Python tooling uses only the standard library, but Java 21+ and the two external LCTL runtimes are operational dependencies. There is no SPDX/CycloneDX SBOM or equivalent formal dependency inventory.

**Needed component:** a release SBOM covering repository tooling plus externally supplied Java/LCTL runtime dependencies and their versions/hashes.

### M08 — Cryptographic release signing / provenance attestation is absent

**Impact: Medium (authenticity).** `MANIFEST.sha256` detects accidental or post-release byte changes when a trusted manifest is available, but the manifest itself is not signed and there is no SLSA/in-toto/Sigstore or detached-signature attestation tying the release archive to an authorized publisher/build.

**Needed component:** signed release provenance and/or detached signatures for the archive and checksum manifest, backed by an owner-controlled identity/key.

### M09 — Published JSON Schemas for machine consumers are absent

**Impact: Low-to-Medium (interoperability/contract stability).** `tools/check_translation.py` now validates the map/evidence semantics directly, but there are no standalone JSON Schema documents for `TRANSLATION_MAP.json` or `VERIFY/2` that external systems can validate without executing repository Python.

**Needed component:** versioned schemas (for example `schemas/translation-map-v1.schema.json` and `schemas/verify-v2.schema.json`) plus compatibility/versioning rules.

## Audit limitation

A real owner-toolchain re-verification could not be performed in this environment because the LCTL 1.6.1-RC1 and 1.6.0-RC1 toolchain roots are not included in the uploaded repository. The existing canonical/evidence payload was therefore preserved byte-for-byte, validated internally, and exercised against the hardened checker; the new full verifier was additionally tested with a simulated toolchain for transactional success/failure behavior. M01–M04 describe what is still required to close that external-verification gap.
