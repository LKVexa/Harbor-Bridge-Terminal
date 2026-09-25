# INV-34 supply chain (MC-001, MC-032, MC-033, MC-064, MC-071)

* Runtime dependencies: none beyond CPython >= 3.10 stdlib. `pk_core` is certification-only and is pinned as
  `UNRESOLVED` in `governance/DEPENDENCIES.lock.json`; `tools/pk_core_gate.py` fails production certification until a
  digest is pinned and matches (a wrong or unpinned `pk_core` cannot certify).
* Build: `tools/build.py` produces a gzip tarball with fixed mtime/uid/order twice and requires identical SHA-256;
  it writes `governance/MANIFEST.sha256`, `SBOM.cdx.json` (CycloneDX 1.5) and `BUILD_RESULT.json`.
  Known non-determinism: none in the archive; the Python used is recorded as run evidence, not embedded in files.
* Signing: NOT performed — no key is bound (B-KEYS). Promotion must verify a signature; the exit gate refuses an unsigned artifact.
* CI actions are pinned by commit digest in `.github/workflows/ci.yml`.

## Emergency dependency update / revocation (DRAFT — needs an owner, B-OWNER)
1. Freeze expansion fleet-wide (`POST /v1/ops/disable` per VM or config `expansion_enabled=false` + rollback-able activation).
2. Pin the replacement digest in the lock file; rebuild; compare SBOMs; re-run CI.
3. Record a waiver in `governance/WAIVERS.json` if any gate is bypassed, with owner and <=180-day expiry.

## Patch / vulnerability / EOL (DRAFT)
Proposed SLAs: critical 72 h, high 14 d, medium 90 d; 5.x supported until 12 months after 6.0 — all PROPOSED.
