# INV-64 application manifest schema notes

This repository implements the `app/v1` manifest contract in `manifest.py`.
These notes describe the behavior implemented by this archive. Formal JSON
Schemas live in `schema/` (`app-v1.schema.json` for the manifest; 4.3.0 adds
request/response/error/status/overlay/authz-policy/audit/decision/exit-gate
schemas). JSON Schema cannot express cross-references (dangling links) or the
secret rule; those are semantic checks in `manifest.py`. Normative semantics:
SPECIFICATION.md.

## Top-level fields

- `schema` — required string. The only supported value is `app/v1`.
- `components` — list of mappings; each entry has a valid `name`.
- `providers` — list of mappings; each entry has a valid `name`.
- `links` — list of mappings with `from` and `to` names. `from` must name a
  declared component; `to` must name a declared component or provider.
- `traits` — list of mappings with a non-empty identifier `type` and a
  `component` that names a declared component.

Component and provider names share one namespace. Names are 1–128 characters,
start with an ASCII alphanumeric character, and otherwise contain ASCII
alphanumerics, `.`, `_`, or `-`.

## Refusal semantics

`validate_issues()` returns every detectable semantic error in one pass as
machine-readable `(code, path, message)` records. `validate()` preserves the
legacy list-of-strings interface. `parse_manifest_json()` additionally rejects
oversized payloads, duplicate JSON object keys, invalid UTF-8, non-finite JSON
numbers, nesting deeper than 64 levels (4.3.0), and semantic invalidity.
Inline secret material anywhere in the manifest is a semantic error
(`secret.inline`, 4.3.0); use `secretref://<provider>/<key>[@<version>]`.

## Resource ceilings

- encoded JSON input: 1 MiB
- components: 10,000
- providers: 10,000
- links: 50,000
- traits: 50,000

These are defensive implementation ceilings, not tenant quotas.

## Canonical identity

`canonical_document()` first requires a valid manifest, deep-copies it through
strict JSON serialization, sorts the four set-like sections by deterministic
JSON bytes, and emits compact UTF-8 JSON with sorted object keys and finite
numbers only. `canonical()` is the lowercase SHA-256 digest of those bytes.
Unknown extension fields remain in the canonical document and therefore affect
the digest.
