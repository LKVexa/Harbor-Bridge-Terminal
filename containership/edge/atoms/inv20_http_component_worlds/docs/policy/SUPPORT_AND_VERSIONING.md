# Support, versioning, patch and EOL policy (component 22) — DRAFT, owner approval required

- **Versioning:** SemVer on the canonical `_version.__version__`. Breaking = removal/rename in the Python
  API, a WIT world/interface/variant change that is not additive, a config-schema change that rejects
  previously valid input (new `INV20_CONFIG/n`), an evidence-schema bump, or renaming/removing an error code.
  Error codes are append-only.
- **Supported:** current minor + previous minor. 4.2.x → 4.3.x is compatible (additive only; the
  pk_core adapter import path changed to lazy loading, same public names).
- **Deprecation:** ≥ 2 minor releases or 6 months, whichever is longer; removal only in a major.
- **Compatibility matrix (declared only where tested):**

| INV-20 | Python | pk_core | WIT / WASI HTTP | Runtime | INV-13/16/17/18/21 |
|---|---|---|---|---|---|
| 4.3.0 | 3.11 (tested) | 1.x (declared, **untested**) | pk:inv20@4.3.0 local (tested); upstream UNRESOLVED | none tested | none tested |

- **Patch SLAs (proposed):** critical 72 h, high 7 d, medium 30 d, low next minor. Emergency disable
  via `revoke_all()` available immediately. Backports to the previous minor for critical/high.
- **EOL:** 12 months after the next minor's release; 90-day notice; unsupported peer versions are
  rejected at WIT major-version check (`witgen` / host) rather than run silently.
