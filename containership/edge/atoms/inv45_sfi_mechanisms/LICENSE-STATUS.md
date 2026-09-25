# License status (A6)

**No license has been selected for this repository.** The remediation checklist forbids assuming one
(e.g. Apache-2.0) without the project/legal process, so no `LICENSE` file is shipped. Until the owner
selects a license, all rights are reserved by the copyright holder and redistribution terms are undefined.

Third-party material: none is vendored. Runtime dependencies are declared, not bundled:
`cryptography` (Apache-2.0 OR BSD-3-Clause), Node.js (MIT, with bundled third-party licenses),
test-only `jsonschema` (MIT). See `release/sbom.cdx.json`.

To close A6: choose the license → add `LICENSE` (and `NOTICE` if required) → set `license` in
`pyproject.toml` → enable the license check in `tools/ci.py` (`license` lane currently reports NOT RUN).
