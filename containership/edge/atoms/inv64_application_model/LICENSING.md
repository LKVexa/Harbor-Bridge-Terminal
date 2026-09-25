# Licensing status — INV-64 v4.3.0

**Status: PENDING OWNER DECISION.** No distribution license has been granted.
Until the owner (David Paul Russell / LinearFinance.org) chooses one, all
rights are reserved and the package must not be redistributed. The SPDX
expression in `pyproject.toml` is `LicenseRef-Proprietary-Pending`, and the
wheel carries the classifier `Private :: Do Not Upload` so an accidental upload
to a public index is refused.

A license is a legal decision for the copyright holder; this remediation pass
did not pick one (MC-38 stays `GOVERNANCE_PENDING`).

## Decisions the owner needs to make (MC-38)

- [ ] Outbound license for source, wheel and sdist, with legal approval.
- [ ] Copyright holder/year line (proposed: `Copyright (c) 2026 LinearFinance.org`).
- [ ] Whether source files get SPDX headers (organizational policy).
- [ ] CLA or DCO for contributions.
- [ ] Terms for `pk_core` once it is supplied (required by `contract.py` / `component.py`).

## Third-party material

See `THIRD-PARTY-NOTICES.md`. Summary: the runtime is stdlib-only; the optional
`cryptography` extra is Apache-2.0 OR BSD-3-Clause; the OAM v0.3.0 specification
is referenced by commit and digest only (no text copied); two modules adapt code
from the owner's own INV-44 v4.3.0 package.

## License policy for dependencies (enforced by `tools/release.py` SBOM step)

Allowed without review: MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0, ISC, PSF-2.0,
Unlicense, CC0-1.0. Needs owner review before shipping: LGPL/MPL/EPL. Blocks
release: GPL/AGPL/SSPL/unknown. Exceptions go in `ops/REGISTER.json` (type `exception`).
