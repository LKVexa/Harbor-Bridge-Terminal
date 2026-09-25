# Schema and interface migration plan (MC-091)

## Versioning rules
- Every document carries `schema: "<NAME>/<major>"`. A loader accepts exactly the majors it knows and refuses the rest. It never guesses.
- A **breaking** change (removing or renaming a field, or tightening a meaning) bumps the major. The old major stays readable for at least one minor release, marked `deprecated` in `ops/COMPATIBILITY_MATRIX.json`.
- An **additive** change (a new optional field or a new reason code) keeps the major. Consumers must ignore reason codes they do not know and treat them as not-success.
- A reason code is never renamed or reused. It is deprecated, and a new code is added.

## v4.2.0 to v4.3.0

| From | To | Path |
|---|---|---|
| `PK_TOOLCHAIN/1` (`component.Toolchain`) | `PK_TOOLCHAIN/2` (`model.ToolchainRecord`) | Map `languages` and `architectures` unchanged. Set `version` to the exact pinned release. Map `security_contact: bool` to `security.contact_ref` (a real reference; `true` alone is not enough in production). Replace `reviewed_at: int` (ticks) with `review: ReviewRecord`, using UTC and provenance. Convert `limitations: [str]` to `Limitation` objects with `excludes_features` and `excludes_environments`. Add `integrity` and `lifecycle`. |
| `ToolchainRegister.select(...) -> dict` | `Selector.select(SelectionRequest, now=...) -> SelectionResult` / `RefusalError(Refusal)` | Keyword strings become a `SelectionRequest`. A `NoSuitableToolchain` string becomes a `Refusal` with reason codes. |
| (none) | `PK_TOOLCHAIN_REGISTRY/1`, `PK_TOOLCHAIN_POLICY/1`, `PK_TOOLCHAIN_TICKET/1`, `PK_RUNTIME_CERT/1`, `PK_ADVISORY_FEED/1` | New. |

The v1 API still works. It emits `DeprecationWarning` and applies the MC-094 production rule. It will be removed no earlier than 5.0.0.

## Registry data migration
1. Export the v1 entries.
2. Build a `ToolchainRecord` for each, following the table.
3. `register(..., expected_revision=...)` into a fresh `Registry`.
4. `FileStore.save(registry.snapshot())`.
5. Run `tools/release_gate.py`.

Rollback is `Registry.rollback(revision)` or restoring the previous snapshot file. Both are exercised in `tests/test_registry.py`.

## Tests
`tests/test_interfaces.py::Migration` checks three things: v1 documents are refused by the v2 loader, the v1 API still runs, and every schema file named in the compatibility matrix exists.
