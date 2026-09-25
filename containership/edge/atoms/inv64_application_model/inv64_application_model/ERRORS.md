# Error contracts

## Boundary errors — `PK_APP_ERROR/1` (4.3.0)

Every refusal at the service boundary is an envelope `{version, code, status, message, retryable, correlation_id, details}` (`errors.py`, `schema/error-v1.schema.json`). The code catalog, retryability and outcome mapping are `errors.CATALOG` / `errors.outcome_for`; the schema's `code` enum is generated from the catalog and a test fails if they diverge. Families: `auth.*`, `authz.*`, `tenant.*`, `admission.*`, `deadline.*`, `request.*`, `idempotency.*`, `version.*`, `manifest.*`, `secret.inline`, `overlay.*`, `activation.*`, `artifact.*`, `crypto.*`, `service.disabled`, `internal`.

## Validation issue contract

`validate_issues()` returns stable machine-readable records with `code`, `path`,
and `message`. Callers should branch on `code`, not the human message.

| Code | Meaning |
|---|---|
| `manifest.type` | top-level value is not a mapping |
| `schema.type` | `schema` is not a string |
| `schema.unsupported` | schema identifier is not supported |
| `section.type` | one of the four collection sections is not a list |
| `section.limit` | a collection exceeds its defensive entry ceiling |
| `entry.type` | a collection member is not a mapping |
| `name.invalid` | component/provider name is missing or malformed |
| `name.duplicate` | a component/provider name appears more than once |
| `link.from.invalid` | link source is not a valid identifier |
| `link.from.undeclared` | link source is not a declared component |
| `link.to.invalid` | link target is not a valid identifier |
| `link.to.undeclared` | link target is not a declared component/provider |
| `trait.type.invalid` | trait type is missing or malformed |
| `trait.component.invalid` | trait component is not a valid identifier |
| `trait.component.undeclared` | trait targets an undeclared component |
| `manifest.too_deep` | nesting exceeds 64 levels (4.3.0) |
| `secret.inline` | inline credential material; path and pattern class only, never the value (4.3.0) |

Raw JSON parsing can additionally raise syntax/UTF-8 errors (`ValueError`),
`DuplicateKeyError`, `ManifestTooLargeError` and `ManifestDepthError` (all `ValueError` subclasses; 4.2.0 raised `RecursionError` for deep nesting). Canonicalization raises
`ManifestValidationError` rather than assigning an identity to invalid input.
