# ADR-0001 — Execution technology for INV-70 (INV-70-C010)

**Status:** PROPOSED — needs sign-off (see Approval below)
**Date:** 2026-09-23 **Deciders:** accountable owner, security reviewer

## Context
The checklist asks for a *pinned per-operation Wasm sandbox*. Versions up to 4.2.0 only have a Python reference stack VM (`runtime.py`). Inside one process that VM cannot pre-empt its own execution or a hung host callback.

## Options
| Option | Isolation | Pre-emption | Maturity | Notes |
|---|---|---|---|---|
| A. Reference VM in-process | Python-level only | none | in repo | dev only |
| B. Reference VM in single-use child process | OS process + no inherited state (`spawn`) | kill on wall clock | implemented 4.3.0 | ~2 ms warm, ~60 ms cold |
| C. Wasmtime, fresh `Store` per operation | Wasm linear-memory sandbox | fuel + epoch interruption | industry standard; Bytecode Alliance security process | needs native wheel |
| D. Wasmer / WAMR | Wasm | varies | viable | smaller Python ecosystem |

## Decision
- **Production target: option C** — wasmtime with an exact pin in `requirements/wasm.lock`. Per-operation `Store`, `consume_fuel`, `epoch_interruption`, `StoreLimits`, no WASI, imports only for authorized capabilities. Seam: `executor.WasmBackend`.
- **Interim supported profile: option B** for the reference bytecode, in every prod-like environment (config rejects `inline-dev` in prod/edge). Option A is for development only.
- If the configured backend is `wasm` and the pinned engine is missing or at another version, runs fail closed with `FB-I002 backend unavailable`. There is no silent fallback.
- Caller auth uses HMAC-SHA256 key-id tokens behind a verifier seam. Moving to asymmetric keys (Ed25519/Sigstore) is a follow-up tracked as EXC-003.

## Consequences
- The reference VM and the Wasm engine have different semantics. Parity applies only to the reason-code mapping (`service.REASON_CODES`).
- CI sets `INV70_REQUIRE_WASM=1` for release certification, so a missing engine is a failure, not a skip.
- Option B costs roughly 2 ms per run when a warm worker is available (`perf/baseline.json`). The contract's old "p99 start < 50 µs" SLO applies only to the in-process VM and was re-scoped in `contract.py`.

## Approval
| Role | Name | Date | Signature |
|---|---|---|---|
| Accountable owner | David Paul Russell | | |
| Security reviewer | UNASSIGNED | | |
