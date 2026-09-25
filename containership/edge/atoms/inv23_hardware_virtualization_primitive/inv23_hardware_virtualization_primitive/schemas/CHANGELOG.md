# Interface schema changelog

## Versioning rules
- **Compatible (same `/N`)**: adding an optional property to a schema whose
  `additionalProperties` is not `false`; loosening a description. Nothing else.
- **Breaking (`/N` → `/N+1`)**: adding/removing/renaming a required field, adding an enum
  value, changing a type, tightening a constraint, or adding any property to a schema
  with `additionalProperties: false`.
- **Deprecation**: a field is marked `"deprecated": true` for at least one minor release
  of the component before it is removed in the next `/N+1`.
- Prior schema files are never deleted; they remain for decoding historical evidence.

## PK_VIRT_PRIMITIVE/2, PK_VIRT_CLAIM/2, PK_VIRT_OWNERSHIP/1, PK_GATE_RESULTS/1 — component 5.0.0
- /2 adds `indeterminate` state, stable `reason` codes, nullable (unknown) `nesting_depth`,
  backend identity, timestamp and capability detail (breaking → /2).
- PK_VIRT_CLAIM/2 adds `claim_id`, fencing `generation`, lease timestamps, `resource`, `provider`.
- /1 schemas formalised verbatim from 4.2.0 behaviour and frozen.
