# `inv61-wit-subset/1`

Pinned target: WebAssembly Component Model WIT text format, restricted to the constructs below. Everything else is a hard parse error.

* `package ns:name@X.Y.Z;` (exact semver required) followed by one or more `interface` blocks.
* Items: `record`, `enum`, and `name: func(params) [-> type];`.
* Types: `bool u8 u16 u32 u64 s8 s16 s32 s64 f32 f64 char string`, `list<T>`, `option<T>`, `result`, `result<T>`, `result<_, E>`, `result<T, E>`, `tuple<...>`, local record/enum names.
* Rejected: `world`, `use`, `import/export` at package level, `resource`, `flags`, `variant`, `borrow/own`, `stream/future`, nesting > 16, duplicate names, empty records/enums, uppercase identifiers.
* Canonical mapping: see `codec.py` header. Function results are single-valued (0 or 1 type).
* Interface digest: SHA-256 of the sorted-key JSON normalisation (`Interface.normalized`), independent of whitespace and comments.

Binding generation: the runtime binds dynamically from the parsed model (no generated source to drift). `tools/gen_fixtures.py` regenerates golden conformance fixtures; CI fails on drift.
