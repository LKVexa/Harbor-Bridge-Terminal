# INV-11 WIT grammar and feature level (INV11-MC-01/02)

**Feature level:** `wit-2024-10` — the WIT text grammar accepted by the pinned
reference toolchain **wasm-tools 1.219.1**, minus the productions listed as
unsupported below. The level is recorded in `wit/__init__.py`
(`WIT_FEATURE_LEVEL`), in `conformance/SUPPORT_MATRIX.json`, and in every
evidence bundle.

## Supported productions

| Production | Notes |
|---|---|
| `package ns:name[@semver];` | one per file; files of one package must agree |
| `package ns:name[@semver] { ... }` | nested package blocks (interfaces/worlds only) |
| top-level `use ns:pkg/iface[@v] [as alias];` | alias for interface references |
| `interface name { ... }` | types, functions, `use` items |
| `world name { ... }` | `import`/`export` of interface paths, inline interfaces (`import x: interface {...}`), functions; `include` with `with { a as b }`; `use`; type definitions |
| `use iface.{a, b as c};` | local or `ns:pkg/iface@v` paths |
| `type`, `record`, `variant`, `enum`, `flags`, `resource` | resources: `constructor(...)`, methods, `static` functions |
| types | `bool s8..s64 u8..u64 f32 f64 (float32/float64 aliases) char string`, `list<T>`, `option<T>`, `result`, `result<T>`, `result<_, E>`, `result<T, E>`, `tuple<...>`, `own<R>`, `borrow<R>`, bare resource name (= `own<R>`) |
| gates | `@since(version = x.y.z)`, `@unstable(feature = name)`, `@deprecated(version = x.y.z)` (must pair with `@since`/`@unstable`) |
| identifiers | kebab-case words; each word all-lowercase or all-uppercase; `%` escapes keywords |
| comments | `//`, nested `/* */`; `///` and `/** */` doc comments attach to the next item (trivia only) |

## Gated (off by default, `ParseConfig` opt-in)

| Feature | Flag | Diagnostic when off |
|---|---|---|
| `future<T>`, `stream<T>`, `async func` | `allow_async=True` | `E-PARSE-UNSUPPORTED` |
| `list<T, N>` fixed-size lists | `allow_fixed_lists=True` | `E-PARSE-UNSUPPORTED` |
| `@unstable(feature = x)` items | resolver `features={"x"}` | item is absent (same as reference) |

## Unsupported (always rejected)

| Production | Diagnostic | Reason |
|---|---|---|
| named/multiple results `-> (a: u32)` | `E-PARSE-UNSUPPORTED` | removed from WIT; registered divergence (reference 1.219.1 still accepts) |
| `error-context` | `E-PARSE-UNSUPPORTED` | beyond the pinned level |
| nested namespaces `a:b:c/...` | `E-PARSE-UNSUPPORTED` | beyond the pinned level |

## Error recovery guarantees (INV11-MC-01-009/018)

* A syntax error inside an interface/world/resource item abandons that item
  and resumes after the next `;` or at the `}` closing the enclosing block.
* A syntax error at top level resumes at the next `package`, `interface`,
  `world` or `use` keyword.
* Lexical errors (bad character, malformed identifier/version, unterminated
  comment), invalid UTF-8 and any limit breach are **fatal for that file**:
  parsing stops and `ParseResult.fatal` is set.
* Diagnostics are capped (`Limits.max_diagnostics`, default 200); overflow is
  reported once as `W-DIAG-TRUNCATED`.
* `ParseResult.status()` is one of `OK`, `OK_WITH_WARNINGS`,
  `RECOVERED_WITH_ERRORS`, `FATAL`. Only `OK`/`OK_WITH_WARNINGS` may be
  resolved and compared; `classify_packages` refuses anything else.

## Source handling

UTF-8 strictly (malformed sequences → `E-SRC-UTF8` with line/column of the
first bad byte); a UTF-8 BOM is removed with a warning; CRLF/CR are normalized
to LF before tokenizing. Offsets in spans are **code-point offsets into the
normalized text**; columns are 1-based code points. Directory loading sorts by
posix relative path and never follows symlinks; `deps/<name>/` directories are
loaded as dependency packages.
