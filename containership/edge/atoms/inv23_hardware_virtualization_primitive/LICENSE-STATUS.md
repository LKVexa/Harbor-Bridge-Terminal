# License status — UNDETERMINED

No license has been granted for INV-23. The supplied archive, the Post-Kubernetes
master-applied build (`PK_Master_Applied_All_Batches.zip`) and the vendored `pk_core`
carry no LICENSE file, and a license is not inferred from neighbouring projects.

Until the owner (David Paul Russell) chooses one, the code is **all rights reserved** by
default law and must not be redistributed. There is deliberately no `LICENSE` file and no
`license` field in `pyproject.toml` (the `Private :: Do Not Upload` classifier blocks
accidental PyPI upload).

To close (MC-13, waiver WVR-003): pick the license, add the full `LICENSE` text, add the
SPDX `license` expression to `pyproject.toml`, and update `THIRD-PARTY-NOTICES.md`.

Third-party inventory: runtime has **no** third-party code (stdlib only). The only
non-original code is the vendored `pk_core` 4.0.0, which is the owner's own material.
Optional dev/test tools (jsonschema, hypothesis, ruff, mypy, opentelemetry-api) are not
redistributed.
