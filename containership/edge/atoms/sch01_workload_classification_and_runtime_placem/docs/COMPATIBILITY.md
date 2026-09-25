# Versioning and compatibility policy (MC-09) — PROPOSED, approver UNASSIGNED

- Semantic versioning. Public surfaces: schemas in `schemas/`, error codes in `errors.CATALOG`, lifecycle states, config keys, metric/log field names.
- Additive changes -> minor. Removal or meaning change -> major, after a deprecation window of 2 minor releases.
- Supported schema versions are machine-readable in `lifecycle.SUPPORTED_SCHEMAS`; unknown versions are refused with `UNSUPPORTED_VERSION`.
- `PK_PLACEMENT/1` and `PK_SCHEDULER_ERROR/1` are deprecated in 4.3.0; `lifecycle.downgrade_placement_v2_to_v1` is the migration contract.
- Platform matrix (MC-45) target: CPython 3.10–3.13 × Linux/Windows/macOS × x86_64/arm64. **Executed in this pass: CPython 3.11.15 / Linux / x86_64 only.**
