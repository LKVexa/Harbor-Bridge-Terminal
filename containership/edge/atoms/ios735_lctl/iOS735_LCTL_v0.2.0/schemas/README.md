# Published JSON Schemas (M09)

| Schema | `$id` | Validates | Version |
|---|---|---|---|
| `translation-map-v1.schema.json` | `https://ios735-lctl.invalid/schemas/translation-map-v1.schema.json` | `map/TRANSLATION_MAP.json` (`IOS735_LCTL/MAP/1`) | 1 |
| `verify-v2.schema.json` | `…/verify-v2.schema.json` | `evidence/VERIFY.json` when `IOS735_LCTL/VERIFY/2` | 2 |
| `toolchain-lock-v1.schema.json` | `…/toolchain-lock-v1.schema.json` | `toolchains/LOCK.json` (`IOS735_LCTL/TOOLCHAIN_LOCK/1`) | 1 |

All are JSON Schema Draft 2020-12 with `additionalProperties: false`. The `$id` host is a
reserved `.invalid` name: identifiers are stable names, not fetch locations; change them only if
the owner publishes the schemas at a real URL.

```text
python tools/schema_check.py                       # all repository artifacts, stdlib only
python tools/schema_check.py --strict              # also runs the `jsonschema` package + meta-schema
python tools/schema_check.py schemas/verify-v2.schema.json path/to/VERIFY.json
```

`fixtures/verify-v2.valid.json` is a minimal valid example (two units, produced with the
test-only simulator; it is not evidence). Negative cases live in
`tests/test_release_hardening.py`.

## Schema-valid is not repository-valid

Schemas check wire format only. These remain semantic checks:

- map: exactly 735 components / 43 phases, phase membership, boot order, control-ledger
  reconciliation, hashes against the Swift sources — `tools/check_translation.py`;
- VERIFY/2: PASS ⇒ every aggregate gate = `units` = |`source/*.lctlc`|, every per-unit gate
  PASS, outputs committed, toolchain unchanged during run, unit/canonical/analysis membership
  exact, JAR hashes and lock digest equal to the approved lock — `tools/evidence_check.py`.

## Compatibility rules

- Any breaking wire change (removed/renamed field, narrowed type, new required field) → new
  schema file and identifier (`verify-v3`, `translation-map-v2`) plus a migration note; old
  schemas stay for historical evidence.
- Additive optional fields → still a new minor revision of the file, recorded in CHANGELOG;
  because `additionalProperties` is false, consumers must update the schema with the producer.
- `IOS735_LCTL/VERIFY/1` evidence is historical and is never reinterpreted as VERIFY/2.
- Compatibility: `verify-v2` ↔ `tools/verify.py` / `tools/evidence_check.py` from 0.2.0;
  `translation-map-v1` ↔ `tools/check_translation.py` from 0.1.1; lock v1 ↔
  `tools/toolchain_trust.py` from 0.2.0.
