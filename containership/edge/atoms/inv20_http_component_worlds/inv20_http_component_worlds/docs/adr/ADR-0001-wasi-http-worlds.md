# ADR-0001 — WASI HTTP world shapes for INV-20

- **Status:** Proposed (approver: UNASSIGNED — see governance/OWNERSHIP.md)
- **Date:** 2026-09-23 · **Release:** 4.3.0 · **Work item:** WI-INV20-02

## Context
The contract names `wasi:http/service` and `wasi:http/middleware`. Those are the world names of the
WASI 0.3 (`wasi:http@0.3.0-rc`) proposal; WASI 0.2.x ships a single `wasi:http/proxy` world
(imports `outgoing-handler`, exports `incoming-handler`). No upstream revision was pinned before this pass.

## Decision
1. INV-20 owns a local package **`pk:inv20@4.3.0`** (`wit/inv20.wit`) with worlds:
   - `service` → exports `handler`; **no** HTTP import (egress structurally absent);
   - `service-with-egress` → imports `outgoing` (capability-token parameter), exports `handler`;
   - `middleware` → imports `handler`, exports `handler` (INV-21 chaining).
2. Terminology resolution: `wasi:http/service` ≡ `service` / `service-with-egress`; `wasi:http/middleware` ≡ `middleware`.
3. Supported upstream targets: **0.2.x** (`proxy` world, via adapter) and **0.3.0-rc** (`service`,
   `middleware`). The exact upstream commit + digest go in `wit/wit.lock`; until then the lock status
   is `BLOCKED` and the evidence gate cannot PASS C029–C031 / C082–C084.
4. Outgoing HTTP is always an explicit import that takes an `INV20_CAP/1` token; the host verifies it
   before any DNS lookup or connect (identity.py, egress.py).
5. Streaming: `body` resource with bounded reads; trailers are a `future-trailers` resource resolved
   exactly once (`finish`). Errors are the `error-code` variant, 1:1 with `errors.REGISTRY`
   (asserted by `tests/test_ops.py::WitTest.test_error_variants_match_registry`).

## Consequences
- `witgen.py --check` gates structure and freshness in CI; true ABI bindings require `wit-bindgen`/
  `wasm-tools` and a component runtime (wasmtime ≥ 25 or jco) — **not available in this build
  environment**, recorded as a residual blocker.
- Unsupported: HTTP/1.0 upgrade semantics, CONNECT tunnelling, WebSockets.
