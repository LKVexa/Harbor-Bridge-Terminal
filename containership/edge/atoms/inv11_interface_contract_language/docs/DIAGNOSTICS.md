# Diagnostic codes (generated from wit/diagnostics.py CODES)

Stability: codes are append-only; a code's meaning never changes; retired codes stay reserved.

| Code | Severity | Meaning | Remediation |
|---|---|---|---|
| `E-DUP-DECL` | error | duplicate declaration | rename or remove one declaration |
| `E-DUP-GATE` | error | duplicate feature gate | use at most one @since/@unstable per item |
| `E-DUP-MEMBER` | error | duplicate member | field/case/param names must be unique |
| `E-GATE-PAIR` | error | @deprecated must be paired with @since or @unstable | add @since(version = ...) |
| `E-LEX-CHAR` | error | unexpected character | remove or escape the character |
| `E-LEX-COMMENT` | error | unterminated block comment | close the comment with */ |
| `E-LEX-IDENT` | error | malformed identifier | identifiers are kebab-case words of [a-z0-9] (or [A-Z0-9]) starting with a letter |
| `E-LEX-VERSION` | error | malformed semantic version | use MAJOR.MINOR.PATCH[-pre][+build] |
| `E-LIMIT` | error | resource limit exceeded | reduce input size or raise the configured limit |
| `E-PARSE-EOF` | error | unexpected end of input | the declaration is truncated |
| `E-PARSE-EXPECTED` | error | unexpected token | see the expected token list |
| `E-PARSE-PACKAGE` | error | package declaration problem | declare exactly one `package ns:name@ver;` per package |
| `E-PARSE-UNSUPPORTED` | error | unsupported grammar production | see docs/GRAMMAR.md unsupported list |
| `E-RES-CYCLE` | error | dependency cycle | break the cycle between interfaces/worlds |
| `E-RES-HANDLE` | error | handle of non-resource type | own/borrow only apply to resources |
| `E-RES-KIND` | error | name refers to the wrong kind of item | reference an interface/world/type as appropriate |
| `E-RES-PACKAGE` | error | unknown or conflicting package | provide the dependency package or pin one version |
| `E-RES-TYPECYCLE` | error | recursive type definition | WIT types may not be recursive; use a resource |
| `E-RES-UNKNOWN` | error | unresolved name | declare or `use` the name |
| `E-SRC-BOM` | warning | UTF-8 byte-order mark ignored | remove the BOM |
| `E-SRC-IO` | error | source could not be read | check the path and permissions |
| `E-SRC-UTF8` | error | source is not valid UTF-8 | re-encode the file as UTF-8 |
| `W-DIAG-TRUNCATED` | warning | further diagnostics suppressed | fix reported errors first |

`E-LIMIT` messages name the limit (`limit <name> exceeded: <value> > <max>`).
CLI exit codes: 0 ok, 1 diagnostics, 2 environment/BLOCKED, 3 breaking with --fail-on-breaking.
