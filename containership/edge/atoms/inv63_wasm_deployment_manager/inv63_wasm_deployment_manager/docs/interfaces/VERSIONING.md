# INV-63 Interface Versioning

| Field | Value |
|---|---|
| Document ID | INV63-IF-VERSIONING |
| INV-63 C-IDs covered | C016, C022, C027, C029 (with C082) |
| Status | DRAFT — pending approval |
| Owner | Service owner (role) — UNASSIGNED |
| Reviewers | Architecture reviewer (role), INV-64 owner (role), INV-66 owner (role) — UNASSIGNED |
| Revision | 4.3.0 |
| Approval date | pending |
| Supersedes | none |
| Change-review triggers | Revisit when interfaces, state ownership, topology or dependencies change, and on any edit to `schemas/*.json` or `schema.SUPPORTED` / `schema.DEPRECATED`. |

## 1. Schema identifiers (C022)
- Id form `<NAME>/<major>` (regex in `schema.parse_id`: `[A-Z][A-Z0-9_]{2,63}/[1-9][0-9]{0,2}`); file `schemas/<NAME>_v<major>.json`; `$id` `urn:inv63:<NAME>/<major>`.
- Validation: `schema.validate(payload, id)` — strict subset validator, fails closed on unknown keywords; wire entry `schema.parse_bytes` (64 KiB, depth 8, no duplicate keys, no NaN/Infinity). Unknown schema file → `INV63-E-UNSUPPORTED-VERSION`; violation → `INV63-E-SCHEMA`.

## 2. Supported and deprecated (`schema.SUPPORTED`, `schema.DEPRECATED`)

| Contract | Supported majors | Deprecated |
|---|---|---|
| PK_DEPLOY_DESIRED | 1, 2 | v1 on 2027-09-30; v1 already rejected with `INV63-E-ARTIFACT-UNTRUSTED` whenever `require_signed_artifacts` is true (prod) |
| PK_DEPLOY_DIFF | 1 | — |
| PK_DEPLOY_ROLLOUT | 1 | — |
| PK_DEPLOY_ERROR | 1 | — |
| PK_DEPLOY_EVENT | 1 | — |
| PK_DEPLOY_CONFIG | 1 | — |
| PK_DEPLOY_REQUEST | 1 | — |
| PK_DEPLOY_GATE | 1 | — |

Unversioned response/status documents: `PK_DEPLOY_RESPONSE/1`, `INV63_STATUS/1`, `INV63_EXPLAIN/1`, `INV63_BACKUP/1` have no schema file in `schemas/` (open item).

## 3. Change rules (C016)
- **Major**: any removal, rename, type change, new required field, tightened limit, or semantic change → new file `_v<N+1>.json`, add to `SUPPORTED`, keep the old major until its `DEPRECATED` date.
- **Minor (additive only)**: new optional properties, relaxed limits, new enum values on outputs only. Because schemas use `additionalProperties: false`, an added optional field is rejected by older receivers — so additive minors must be deployed receiver-first. Minor versions are not encoded in the id; they are tracked by schema digest (`schema.digest`, `schema.all_schema_digests`).
- **Deprecation**: record date in `DEPRECATED`; reject after that date (date enforcement is not implemented in code — open item).

## 4. Negotiation (C027)
Request envelope may carry `accept_versions` (1–99, max 8 items). `service.handle` calls `schema.negotiate("PK_DEPLOY_REQUEST", accept_versions)`: highest common major, or `INV63-E-UNSUPPORTED-VERSION` with `{ours, peer}`. `op_set_desired` dispatches on the body's `schema` id (v1 vs v2). Test: `tests/test_contracts.py::CompatibilityTest::test_version_negotiation`, `::test_v1_desired_accepted_when_signing_not_required`.

## 5. Fixtures (C029)
- `fixtures/*.json` + `fixtures/FIXTURES.json` (digest manifest binding each case to schema digests).
- Regenerate: `python tools/gen_fixtures.py` (18 cases: valid/invalid for DESIRED v1/v2, DIFF, ROLLOUT, ERROR, EVENT, REQUEST, CONFIG, and `PK_DEPLOY_DESIRED/9` → `INV63-E-UNSUPPORTED-VERSION`).
- Verified by `tests/test_contracts.py::SchemaTest::test_conformance_fixtures`, `::test_every_contract_has_a_versioned_schema`, `::test_documented_limits_are_enforced`, `::test_error_catalog_complete`.
- Any schema edit requires regenerating fixtures and committing the new digests.

## 6. Legacy Manager API compatibility
`manager.Manager` public API (`set_desired`, `diff`, `apply`, `reconcile`, `rollout`, `verify_audit_chain`, `DesiredState`) is preserved. 4.3.0 adds only the optional keyword `eligible_hosts` to `Manager.diff` (default `None` = all hosts), which is backward compatible. Test: `tests/test_contracts.py::CompatibilityTest::test_legacy_manager_api_unchanged`. `manager.py` does not depend on `pk_core` (`test_core_engine_survives_optimized_mode_without_pk_core`). `contract.py` imports `pk_core.contract`, which is UNPINNED and not supplied (`pins.json`).
