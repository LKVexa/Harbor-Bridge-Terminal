# INV-12 Compatibility Support Matrix (MC-056, MC-033)

Status key: **Certified** = executed in this release's evidence · **Declared** = configured in CI, not yet
executed · **Unsupported** = refused by the engine.

## Specifications

| Item | Version | Status | Deprecation window |
|---|---|---|---|
| Canonical ABI (layout, flattening) | "1" (Component Model, WASI 0.2 line) | Certified (golden corpus) | ≥ 2 minor releases notice |
| Mapping profile | `inv12-mapping@2.0.0` (`PROFILE_DIGEST` in `canon/registry.py`) | Certified | previous profile kept 1 minor release |
| Error envelope | `PK_INTEROP_ERROR/1` | Certified | codes append-only; never removed |
| Config document | `PK_INTEROP_CONFIG/1` | Certified | N-1 accepted during migration |
| Golden corpus | `inv12-golden@1.0.0` | Certified | frozen per major |
| Async `future`/`stream` | reference semantics | Engine only; runtime adapter refuses | feature-gated off |

## Language bindings

| Language | Toolchain executed | Encode golden | Decode golden | Reject invalid | Matrix pairs | Status |
|---|---|---|---|---|---|---|
| Python (reference) | CPython 3.11.15 | 50/50 | 50/50 | 17/17 | 4/4 | Certified |
| Rust fixture | rustc 1.95.0 (std only) | 50/50 | 50/50 | 17/17 | 4/4 | Certified (fixture) |
| Go fixture | go 1.24.7 | 50/50 | 50/50 | 17/17 | 4/4 | Certified (fixture) |
| JavaScript fixture | Node 22.22.2 (BigInt) | 50/50 | 50/50 | 17/17 | 4/4 | Certified (fixture) |
| Go → Wasm guest | go 1.24.7 `wasip1/wasm`, V8 (Node 22) | — | real linear memory | hostile ptr/realloc refused | — | Certified (integration harness) |

"Fixture" means a descriptor-driven implementation of the layout used for conformance; generated
production bindings (wit-bindgen, jco, componentize-py, wit-bindgen-go) are **Declared** targets, not shipped.
Exact numbers: `evidence/conformance.json`, `evidence/wasm_guest.json`.

## Platforms

| OS / arch | Status |
|---|---|
| Linux x86-64 | Certified (this evidence set) |
| Linux ARM64 | Declared (`ci/github-actions.yml`, `ubuntu-24.04-arm`) |
| macOS ARM64 | Declared (`macos-14`) |
| Windows x86-64 | Declared (`windows-2022`) |

Architecture assumptions: the canonical ABI is little-endian and fixed-width by definition; the engine never
depends on host endianness (`struct` `<` formats, explicit LE in all fixtures).

## Runtimes

| Runtime | Status |
|---|---|
| In-process reference adapter (`canon.boundary`) | Certified |
| V8 WebAssembly core modules via `tools/wasm_host.mjs` | Certified (integration harness) |
| Wasmtime component API | Declared target — adapter not shipped |
| `pk_core` gate (parent framework) | Blocked in this environment |
