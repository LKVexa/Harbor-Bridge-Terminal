# INV-70 - Fast agent sandbox

**Version:** 4.3.0 (see `CHANGELOG.md`; remediation status in `AUDIT_REPORT_4.3.0.md`)  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`  
**Master prompt source:** not present in the supplied archive; the previous README reference to `MASTER.md` was therefore removed rather than fabricating that source artifact.

INV-70 provides a small bounded guest-bytecode runtime for stateless calculations, transforms, and capability-mediated tool calls. The guest receives no filesystem, network, device, kernel, or secret authority by default. Host callbacks are explicitly trusted capability implementations and are **outside** the guest isolation boundary.

> **4.3.0:** production callers use `service.Sandbox.handle()`, the governed entry point. It provides authentication, admission, process isolation with wall-clock kill, audit, telemetry and explain. The Wasm engine seam is in `executor.WasmBackend`; ADR-0001 chooses wasmtime and the engine is not yet installed. Run all tests with `for t in tests/test_*.py; do python $t; done` and generate release evidence with `python -m inv70_fast_agent_sandbox.tools.release_evidence` (run from the parent directory).

> Production architecture note (historical, 4.2.0): `CHECKLIST.json` calls for a **per-operation Wasm sandbox**. This repository currently implements a custom Python stack VM, not a Wasm engine. The VM is hardened as a reference/runtime primitive in 4.2.0, but the Wasm implementation gap remains open and is recorded in `AUDIT_REPORT_4.2.0.md`.

## Responsibility

Own the lightweight bounded execution primitive: strict bytecode validation, fuel metering, stack/value/logical-memory ceilings, capability-gated host calls, and deterministic guest termination reasons.

## Runtime safety model

- Programs are snapshotted from exact `list`/`tuple` containers and validated for opcode and arity before execution.
- Guest values are restricted to exact inert scalar types: `None`, `bool`, `int`, `float`, `str`, and `bytes`; subclasses are rejected so Python magic methods cannot execute through guest arithmetic.
- Fuel, stack depth, per-value size, logical guest memory, and program instruction count are bounded.
- Arithmetic/string growth is preflighted before allocation where it can expand materially.
- Host calls require an explicit capability grant and a bound callable. Returned values are revalidated before re-entering guest state.
- Host exception **messages** are not exposed to the guest; only the exception class is returned in the trap reason.
- A host callback can still block, allocate, perform I/O, or use ambient Python authority. Such callbacks must be trusted and separately bounded by the embedding system.

See `RUNTIME_SPEC.md` and `SECURITY.md` for the exact runtime and trust-boundary rules.

## Interfaces

- `run` — `PK_FASTBOX_RUN/1`: program, fuel, stack/value/memory/program limits, capabilities
- `result` — `PK_FASTBOX_RESULT/1`: value or deterministic termination reason
- `hostcall` — `PK_FASTBOX_HOSTCALL/1`: explicit capability-gated callback

Backward-compatible positional parameters remain `program`, `fuel`, `max_stack`, `caps`, and `host`. Version 4.2.0 adds keyword-only `max_memory_bytes`, `max_value_bytes`, and `max_program_instructions`.

## Testing

From this package directory:

```text
python tests/test_runtime.py
python -O tests/test_runtime.py
python tests/test_component.py
```

`tests/test_runtime.py` is dependency-free. `tests/test_component.py` requires the external `pk_core` package (or `PK_CORE_PATH`) and skips its conformance suite when that dependency is unavailable. A skip is **not** treated as production certification.

With a compatible `pk_core` checkout available, the intended framework commands remain:

```text
python -m pk_core list
python -m pk_core run INV-70 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-70 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

## Day-0 / day-1 / day-2

- **Day 0:** import the package, run the dependency-free runtime tests, then execute the `pk_core` conformance flow with the exact compatible core version.
- **Day 1:** generate and review machine-readable gate evidence before rollout; do not equate a skipped core test with a pass.
- **Day 2:** re-run runtime and conformance tests on every contract/runtime change and preserve evidence continuity.

The repository still lacks several production artifacts and integrations required by its own 100-item checklist. The complete post-update inventory is in `AUDIT_REPORT_4.2.0.md`.
