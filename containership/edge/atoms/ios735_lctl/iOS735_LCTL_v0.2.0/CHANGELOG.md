# Changelog

## 0.2.0 — 2026-09-23

Missing-components closure pass against the v0.1.1 audit (M01–M09). Engineering items that do not need the owner are implemented and tested; owner-dependent items stay explicitly open (see `CLOSURE_STATUS.md`). `source/`, `canonical/`, `map/` and the historical `evidence/` are byte-identical to 0.1.1.

- M04: `toolchains/LOCK.json` trust lock (`IOS735_LCTL/TOOLCHAIN_LOCK/1`) and `tools/toolchain_trust.py`; entries are `PENDING_OWNER_APPROVAL`, so the full verifier currently refuses to run by design.
- M01: `tools/verify.py` authenticates both JARs and the Java policy before any `java -jar`, re-hashes them after the run, returns stable exit codes 10–16, and records Java path/vendor/runtime, OS/arch and the lock version/digest in `VERIFY/2`. Safe atomic archive extraction and log redaction. `docs/TOOLCHAIN_PROVISIONING.md`.
- M02: `tools/evidence_check.py` automates `VERIFY/2` acceptance (schema, seven gates × units, membership, 132 analyses, lock correlation). Transactional failure behaviour demonstrated with a test-only simulator (`tests/fixtures/simtoolchain/`).
- M03: `.github/workflows/owner-toolchain-verify.yml` (privileged, no PR triggers, protected environment, self-hosted runner, generated-file policy, evidence retention); offline workflow extended with Java 21, simulator tests, schema/lock/SBOM checks.
- M07: `tools/sbom.py` (SPDX 2.3) and a DRAFT SBOM.
- M08: `tools/release.py` preflight gate, deterministic ZIP, in-toto/SLSA provenance, Ed25519 sign/verify with refusal rules; `docs/RELEASE_PROCESS.md`.
- M09: JSON Schemas for the map, `VERIFY/2` and the lock; stdlib validator (`tools/schema_check.py`); fixtures; compatibility policy.
- M05/M06: decision packets in `docs/OWNER_DECISIONS.md`; no licence or security contact was invented.
- Tests: 5 → 49.

## 0.1.1 — 2026-09-23

Hardening release. The generated LCTL-C, canonical LCTL, and translation-map payloads remain byte-identical to v0.1.0 so the existing owner-toolchain canonical verification evidence is preserved.

- Hardened `tools/translate.py` with strict 735-component / 43-phase / 25-control input validation, orphan-record rejection, path-safe source lookup, Swift capability parity checks, runtime-table drift detection, atomic writes, stale generated-source reconciliation, and an explicit `--out` target for deterministic testing.
- Expanded `tools/check_translation.py` from core semantic checks to full canonical/map integrity checks, including exact unit membership, component metadata, status counts, lifecycle events, memory domains, capability gates, hardware fallbacks, family clause operators, app/phase composition, source seals, and translation-map records.
- Expanded the corruption/falsifier suite from 6 to 9 cases; all nine must be caught.
- Reworked `tools/verify.py` to stage outputs transactionally, require every compile/verify/analysis/stats gate, validate toolchain/JAR paths, handle subprocess timeouts/errors, check staged canonical output before commit, and reconcile stale generated evidence only after a complete PASS.
- Added dependency-free offline regression tests and GitHub Actions coverage for Python 3.10 and 3.13 on Windows and Linux.
- Added release-file SHA-256 manifest generation/verification.
- Added a repository-level post-update audit report documenting remaining external/release gaps.

## 0.1.0

Initial iOS735 Swift-skeleton to LCTL translation package: 735 components, 43 phase units plus application unit, canonical LCTL, translation map, and LCTL 1.6.1/1.6.0 verification evidence.
