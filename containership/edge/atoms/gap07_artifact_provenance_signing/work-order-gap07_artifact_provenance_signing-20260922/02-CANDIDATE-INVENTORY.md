# 02 — Candidate inventory

The ledger recall could not run (no `_YARDOFFICE`). A name scan of the first 2,000 yard entries for
sigstore / cosign / in-toto / rekor / tuf / slsa / dsse / notary / sbom / cyclonedx / spdx / trillian / merkle found
nothing. The listing was capped at 2,000 entries, so the scan is incomplete.

| finding | donor | decision |
|---|---|---|
| all 48 components | — | **build-new**, with dependency `cryptography` (Apache-2.0 OR BSD-3-Clause, permissive) |

No copyleft or unlicensed parts entered the package. `THIRD-PARTY-NOTICES.md` records the one runtime dependency.
