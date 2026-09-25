# ADR-001 — Runtime and WASI target

**Status:** Accepted for 4.3.0 (reference); **re-review required** before production (see MC-002 gap)  
**Date:** 2026-09-22 · **Deciders:** INV-13 owner (placeholder — see OWNERSHIP.md), security reviewer (placeholder)

## Context
4.2.0 had no engine at all. The checklist requires a real adapter that instantiates guest code while preserving capability boundaries. The build sandbox offers Node 22 (V8 12.4) but no Wasmtime/wasm-tools; Python has no Wasm engine in the stdlib.

## Decision
1. The **contract** is WIT (`wit/inv13-system-interface.wit`, package `inv13:system-interface@4.3.0`), aligned with WASI 0.2 naming and the Component Model.
2. **Policy stays in Python** (`host/`), engines are pluggable behind the `Engine` protocol (`host/runtime_adapter.py`). Engine glue binds functions; it never decides policy.
3. The first shipped engine binding is **V8 via Node ≥ 18 for core Wasm modules** using the flattened core ABI namespace `inv13:<iface>@4.3.0`.
4. **Component-model binaries are refused** (`UNSUPPORTED_VERSION`) until a Wasmtime binding lands behind the same protocol.

## Consequences
+ Real engine instantiation, import-surface cross-checking (loader vs. `WebAssembly.Module.imports`) and trap/timeout mapping are tested now.
− Process-per-invocation isolation is slow (~100 ms spawn) and is not a production embedding. Canonical-ABI lifting/lowering for strings/lists/resources is not implemented (core ABI uses ptr/len only).
− Production closure of MC-002 requires ADR-001a selecting Wasmtime (version, security-support policy, feature flags).

## Tests tied to this decision
`tests/test_wit_wasm.py::V8Adapter.*`, `WasmLoader.*`, `WitSurface.*`
