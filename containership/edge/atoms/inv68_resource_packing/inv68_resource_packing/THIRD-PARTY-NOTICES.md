# Third-party notices — INV-68 4.3.0

| Donor / dependency | Part(s) | License | How it is used |
|---|---|---|---|
| INV-64 application model v4.3.0 (yard work order `inv64_application_model-20260923`, release `inv64_application_model_v4.3.0_mc_applied.zip`) | `redaction.py` → `redaction.py` (verbatim patterns, INV-68 docstring); `audit.py` → `audit.py` (schema names renamed to `PK_PACK_AUDIT/1`); `provenance.py` → `provenance.py`; `release_gate.py` structure → `release_gate.py` | Owner's own code (LicenseRef-Proprietary-Pending; same copyright holder) | Adapted; not redistributed separately |
| INV-44 wasm hardening system v4.3.0 (upstream of the INV-64 parts above) | `audit_log.py`, `provenance.py`, `release_gate.py` lineage | Owner's own code | Via INV-64 |
| jsonschema, referencing, rpds-py, attrs, jsonschema-specifications (PyPI) | not bundled; dev/evidence tooling only (`tools/schemas_check.py`) | MIT (jsonschema, referencing, rpds-py, attrs, jsonschema-specifications) | Validation of examples/live documents |
| setuptools, wheel (PyPI) | not bundled; build only | MIT | wheel/sdist build |
| pk_core | not bundled; required for `contract.py` / `component.py` only | UNKNOWN — not supplied | Integration framework (BLOCKED_EXTERNAL, MC-02) |

No GPL/LGPL/AGPL/MPL/SSPL/EUPL material is included.
