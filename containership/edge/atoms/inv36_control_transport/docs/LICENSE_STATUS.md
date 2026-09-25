# License status (MC-22)

**No license has been selected.** The supplied repository contained no LICENSE, NOTICE or license metadata, and this pass did not choose one on the owner's behalf (MC-22.001: do not assume a license from neighbouring projects).

Consequences until resolved:

- `pyproject.toml` carries no `license` expression and the `Private :: Do Not Upload` classifier;
- the SBOM records `NOASSERTION`;
- gate check G10 fails and the production exit gate cannot pass.

Third-party inventory (runtime): cryptography (Apache-2.0 OR BSD-3-Clause), cffi (MIT), pycparser (BSD-3-Clause) - all permissive and compatible with either a permissive or proprietary license for INV-36; see `THIRD-PARTY-NOTICES.md`. `tools/release.py licenses` flags copyleft/unknown licenses in runtime dependencies and runs in CI.

To close: the repository owner/legal contact selects the license; add the canonical unmodified text as `LICENSE` (plus `NOTICE` if Apache-2.0), set `license = "<SPDX>"` and `license-files` in `pyproject.toml`, add both files to `release/manifest.json` required lists, and record the decision in the release evidence.

Contribution expectations (until a license exists): contributions are accepted only from the repository owner's organization under its internal IP policy (`CONTRIBUTING.md`).
