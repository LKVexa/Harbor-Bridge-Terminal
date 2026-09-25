# Licensing status — INV-44 v4.3.0

**Status: PENDING OWNER DECISION.** No license has been granted. Until the owner
chooses one, all rights are reserved and the package must not be redistributed.

Nothing was invented here: a license is a legal decision for the copyright
holder, not something an implementation pass may pick.

## What the owner needs to decide (checklist component 4)

- [ ] Outbound license for source and wheels (e.g. a permissive licence, or proprietary terms).
- [ ] Whether contributions require a CLA or DCO sign-off.
- [ ] SPDX identifier to replace `LicenseRef-Proprietary-Pending` in `pyproject.toml`.
- [ ] License terms for `pk_core` once it is supplied (it is required by `contract.py`/`component.py`).
- [ ] License terms of the eventual Swivel toolchain and Wasm runtime (component 8), which ship beside, not inside, this package.

## Third-party content

None. v4.3.0 is stdlib-only and vendors no third-party code or data. The
Wasm fixtures in `tests/wasm_fixtures.py` are hand-assembled for this package.
