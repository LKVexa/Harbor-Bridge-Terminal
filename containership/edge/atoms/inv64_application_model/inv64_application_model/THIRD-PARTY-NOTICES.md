# Third-party notices — INV-64 4.3.0

| Donor / dependency | Part(s) | License | How it is used |
|---|---|---|---|
| INV-44 wasm hardening system v4.3.0 (yard work order `INV44-20260922-missing-components`) | `audit_log.py` → `audit.py`; `provenance.py` → `provenance.py`; `release_gate.py` structure → `release_gate.py` | Owner's own code (LicenseRef-Proprietary-Pending; same copyright holder) | Adapted and extended; not redistributed separately |
| oam-dev/spec v0.3.0 (commit `3104d27a0ecb55cac84755950e53371aa3e1d2b2`) | none copied — field names and concepts only, pinned by digest in `provenance/oam-baseline.json` | Open Web Foundation Agreement (per upstream CONTRIBUTING.md; upstream LICENSE sha256 `7d14523a…f139`) | Compatibility profile `oam_profile.py`, `OAM_PROFILE.md` |
| cryptography (PyPI) | not bundled; optional extra `crypto` | Apache-2.0 OR BSD-3-Clause | Ed25519 / EdDSA verification, AES-256-GCM sealing |
| pk_core | not bundled; required for `contract.py` / `component.py` only | UNKNOWN — not supplied | Integration framework (BLOCKED_EXTERNAL) |

No GPL/AGPL/copyleft material is included.
