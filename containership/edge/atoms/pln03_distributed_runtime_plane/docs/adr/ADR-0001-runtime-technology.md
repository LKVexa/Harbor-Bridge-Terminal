# ADR-0001 — Runtime technology and binding model for PLN-03

- **Status:** Proposed — awaiting Architecture Board approval (OWNERS.yaml `architecture_board`)
- **Date:** 2026-09-23
- **Closes (on approval):** MC-002; informs MC-020, MC-053

## Context
The PLN-03 checklist names wasmCloud, wRPC, Wadm and Dapr-style building blocks. The archive through 4.2.0 shipped a Python reference runtime only; none of those technologies was chosen, pinned or rejected on record.

## Decision (proposed)
1. **Contract first.** The normative contract is the four versioned interfaces (`PK_STATE/1`, `PK_MESSAGE/1`, `PK_SECRET/1`, `PK_INVOKE/1`) expressed both as JSON Schema (`schemas/`) and as a WebAssembly Component Model WIT package (`wit/pk-runtime.wit`, `pk:runtime@1.0.0`).
2. **Reference implementation** stays dependency-free Python (`plane.py` + `runtime.py`) and is the conformance oracle: every other host must pass `fixtures/conformance/`.
3. **Production host (proposed):** wasmCloud host with capability providers per interface, wRPC as the component-to-component transport, Wadm manifests for placement handoff to PLN-04. Adopt only after the interop test in MC-053 passes against pinned versions recorded in `DEPENDENCIES.lock.json`.
4. **Dapr** is treated as a *semantic reference* (building-block shapes, idempotent pub/sub, state transactions), not a runtime dependency — the plane is sidecar-free by responsibility statement.

## Alternatives considered
| Option | Why not (now) |
|---|---|
| Dapr sidecar | Contradicts the sidecar-free responsibility; adds a per-pod process and its own security boundary |
| gRPC + protobuf only | No component-model isolation story; kept as an equivalent wire mapping via `envelope.CODES` gRPC statuses |
| Bespoke Rust host | Highest effort; revisit if wasmCloud interop fails |

## Consequences
- Wire and WIT contracts are now the compatibility surface (COMPATIBILITY.md).
- MC-053 cannot close until real wasmCloud/wRPC versions are pinned and an interop test runs in CI.
- Approval record (who, when, comments dispositioned) must be appended below before release.

## Approval record
_Empty — required before MC-002 can close._
