# PK_COMPOSITION_ID/2 — canonicalization and digest specification (MC-05)

Status: normative for INV-10 ≥ 4.2.0. Conformance vectors: `conformance/vectors.json`.

## 1. Input
A successful link of units `U` (each: `name`, `imports`, `exports`) with declared externals `X`.
Identifiers are validated per INV-10: non-empty `str`, no leading/trailing whitespace, NFC-normalized,
no Unicode category `C*` characters, length ≤ `max_identifier_length` (default 512).

## 2. Identity material
A JSON object with exactly these members:

| member | value |
|---|---|
| `schema` | `"PK_COMPOSITION/1"` |
| `identity_profile` | `"PK_COMPOSITION_ID/2"` |
| `units` | array of `{"name", "imports", "exports"}` sorted by `name`; `imports`/`exports` sorted arrays |
| `bindings` | array of `{"consumer","interface","provider"}` or `{"consumer","interface","external":true}`, sorted by `(consumer, interface, provider or "")` |
| `external_imports` | sorted array of externals **actually used** (unused declarations do not affect identity) |

Sorting is by Unicode code point (Python `sorted` on `str`).

## 3. Canonical encoding
UTF-8 bytes of JSON with: object keys sorted by code point; separators `,` and `:` with no whitespace;
non-ASCII characters emitted literally (no `\u` escapes, `ensure_ascii=False`); `true` literal for `external`.
No floats, nulls or duplicate keys appear.

## 4. Digest
`composition = lowercase_hex(SHA-256(canonical_bytes))` — 64 hex characters, never truncated.

## 5. Properties
* Input-order independent (units, imports, exports, externals).
* Graph-sensitive: any change in a unit's declarations or any binding changes the id.
* Metadata excluded: `PK_COMPONENT/1.metadata`, context, policy and provenance do not enter the id.
  Bind those through the store/audit trail, or the extension digests below.

## 6. Extension digests (4.3.0, additive)
* `extension_digest = SHA-256(canon({"composition", "aliases", "eliminated_exports", "keep_exports"}))`
* `tree_digest = SHA-256(canon({"composition", "nested": {name: inner_id}}))`
The base `composition` id always addresses the graph actually linked (after alias / DCE rewrites).

## 7. Compatibility policy
* Any change to §2–§4 requires a new profile name (`PK_COMPOSITION_ID/3`); consumers MUST persist
  `identity_profile` alongside every id and MUST NOT compare ids across profiles.
* Additive result fields never change the id.
* Legacy 4.1.0 ids (96-bit, incomplete graph) are migrated with `features.migrate_legacy`, which
  recomputes from persisted unit declarations; a truncated legacy id cannot be inverted.
