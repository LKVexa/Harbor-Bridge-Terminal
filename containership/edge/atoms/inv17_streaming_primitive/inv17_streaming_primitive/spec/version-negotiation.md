# INV-17 Version Negotiation

**Controls:** C016, C027, C093 (checklist §10). Source: `control::negotiate`, `control::SUPPORTED_VERSIONS`, `stream::PROTOCOL_VERSIONS`.

## 1. Interfaces

`stream::PROTOCOL_VERSIONS` = `{PK_STREAM: 1, PK_STREAM_CREDIT: 1, PK_STREAM_CLOSE: 1}`. `control::SUPPORTED_VERSIONS` currently supports `(1,)` for each. Wire shapes are described in `schemas/*.schema.json` and `schemas/pk_stream.wit`. Package version (4.3.0, `VERSION`) is independent of interface versions.

## 2. Algorithm (`negotiate(interface, offered)`)

1. Unknown interface → `VersionUnsupported("unknown interface")`.
2. Filter `offered` to plain `int` (drops `bool` and non-ints).
3. Intersect with supported; empty → `VersionUnsupported` with `offered` and `supported` in details.
4. Return the **highest** common version.

There is no fallback, no guessing, and no downgrade to an unoffered version.

## 3. Use at open

`StreamRegistry.open(..., versions=None)` negotiates every interface in `versions`, defaulting to `{name: (1,)}` for all known interfaces. Any failure refuses the open. The negotiated values are not stored on the stream (single-version today).

## 4. Compatibility policy

| Change | Interface version | Package version |
|--------|-------------------|-----------------|
| New optional field / new error code | unchanged | minor |
| Changed error precedence, removed field, changed semantics | +1, old version kept in `SUPPORTED_VERSIONS` for the support window | major |
| Internal only | unchanged | patch |

Supporting N and N-1 concurrently is **PROPOSED**; the support window is defined in `governance/support-policy.md`. Mixed-version behaviour is tested in tests/test_schemas.py and tests/test_control.py.
