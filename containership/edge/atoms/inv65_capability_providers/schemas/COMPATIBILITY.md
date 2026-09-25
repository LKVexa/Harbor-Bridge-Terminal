# Schema compatibility policy (M03)

- Every externally visible or durable INV-65 format ships as `schemas/<name>/v1.json` (JSON Schema 2020-12 subset enforced by `schemas.validate`).
- Within `v1` only additive, optional properties may be added; every v1 object sets `additionalProperties: false`, so an addition is a new schema release with `x-version` bumped (1.0 → 1.1) and a fixture in `conformance/fixtures/v1/`.
- Removing/renaming a field, tightening a pattern, or changing an enum's meaning is breaking → new `v2.json`, both versions served for one deprecation window (see `docs/release-process.md`).
- `tests/contract/test_golden_vectors.py` fails if any schema changes without its fixture set, and `tools/check_schemas.py` fails on an unsupported keyword.
