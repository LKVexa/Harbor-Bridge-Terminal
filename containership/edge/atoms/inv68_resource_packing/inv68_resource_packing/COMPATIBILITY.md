# INV-68 compatibility (MC-35; C093)

Machine-readable matrix: `compatibility.json` (protocols, schemas, Python,
platforms, pk_core, adjacent components, deprecations, support window).

* **Support states:** `supported` (tested in the release run), `declared` (expected to
  work, not tested in this build), `deprecated` (works, removal scheduled), `eol`, `unsupported`.
* **Tested in 4.3.0:** CPython 3.11 on Linux x86_64 only. Python 3.10/3.12/3.13 and
  Windows/macOS/aarch64 are *declared*; the CI matrix that would test them is defined
  (`.github/workflows/ci.yml`) but was not executed.
* **Runtime enforcement:** protocol negotiation refuses unsupported `PK_PACK` versions;
  preflight refuses Python < 3.10 and checks the installed version matches `VERSION`.
* **pk_core:** version unknown and deliberately unpinned (MC-02 BLOCKED_EXTERNAL).
* **Maintenance:** the matrix is updated in the same change as any dependency, protocol
  or platform change and reviewed every 90 days (ops/REVIEWS.json).
