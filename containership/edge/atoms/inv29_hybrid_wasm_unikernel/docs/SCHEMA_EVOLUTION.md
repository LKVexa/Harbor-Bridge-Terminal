# Schema evolution and compatibility policy (INV29-MC011)

Applies to `PK_HYBRID_COMPOSITION/1` and `PK_HYBRID_VERIFICATION/1` (machine-readable schemas in `schemas/`).

## Rules

1. **Major version in the identifier.** `/1` is the major. Any removal, rename, type change, tightening of an existing constraint, or change of meaning is a new major (`/2`).
2. **Within a major, additive only.** New *optional* properties may be added; `additionalProperties: false` is kept, so the schema file is updated in the same release. Consumers validate with the schema version they were built for and **refuse unknown majors**.
3. **Producers never emit a field that an older same-major consumer's schema would reject** unless every consumer has been upgraded first (see upgrade order below).
4. **Security fields are one-way.** Once a consumer requires `admission` and `signature` (production PLN-04 must), a producer that stops emitting them is refused, not tolerated.
5. **Deprecation window.** A superseded major is emitted in parallel for at least two minor releases or 90 days, whichever is longer, then removed with a CHANGELOG entry.

## 4.3.0 change log for the schemas

* First machine-readable publication of both schemas.
* `PK_HYBRID_COMPOSITION/1` gains optional `admission` and `signature` (additive). Records produced by bare `compose()` (4.2.0 behaviour) still validate; records produced by `Admitter.admit()` carry both.
* `layers[].layer` enum reserves `hardware-capability` for INV-30.

## Upgrade / downgrade order

1. Upgrade consumers (PLN-04) to a build that understands the new optional fields.
2. Upgrade INV-29 producers.
3. Flip consumer policy to *require* the new fields.

Downgrade reverses the order; step 3 must be undone first or older producers will be refused (fail closed, by design).

## Migration procedure for a new major

Publish `schemas/<name>_2.schema.json`, add it to `records.SCHEMA_FILES`, dual-emit behind a policy flag, add contract tests for both, run the gate, then retire `/1` after the window.
