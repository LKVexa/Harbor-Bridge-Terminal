# INV-60 - Wasm application fabric

**Version:** 4.3.0 (see `CHANGELOG.md`)
**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` restored verbatim from the owner's series (digest and status in `docs/MASTER_INDEX.md`).

A Wasm application fabric runs components across a lattice of hosts and wires them to capability providers by link name at run time. A component says 'I need a key-value store'; the fabric links it to one, routes calls across hosts, and restarts it elsewhere if a host goes. Artifacts are content-addressed, so what runs is exactly what was signed.

## Responsibility

Own the lattice runtime: host membership, component instantiation from content-addressed artifacts, run-time linking to providers, cross-host call routing and failover.

## Owns

- Lattice host membership
- Content-addressed component instantiation
- Run-time links to providers
- Cross-host call routing
- Failover of components off lost hosts

## Explicitly does not own

- Declarative deployment specs
- Provider implementations
- Artifact signing
- The component model
- Edge topology decisions

## Non-goals

- Declaring deployments
- Implementing providers
- Signing artifacts

## Interfaces

- `call` - PK_LATTICE_CALL/1 - a routed cross-host invocation
- `instantiate` - PK_LATTICE_START/1 - a component from a digest reference
- `link` - PK_LATTICE_LINK/1 - component, link name, provider

## Service-level objectives

- **artifact integrity** - zero components started from mismatched bytes (error budget: no budget)
- **failover** - components on a lost host restarted within 10s (error budget: 1% may exceed)
- **routing overhead** - p99 cross-host call overhead under 3ms (error budget: 1% may exceed)

## Running it

```
python -B inv60_wasm_application_fabric/tools/ci.py --strict   # full gate (tests, -O, Node fixtures, pk_core, bench, SBOM, traceability, evidence, exit gate)
python inv60_wasm_application_fabric/tests/test_runtime.py     # dependency-free runtime checks
python inv60_wasm_application_fabric/tests/test_component.py   # pk_core conformance (pk_core is vendored beside this folder)
python -m pk_core list
python -m pk_core run INV-60 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-60 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-60`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-60`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.


## Reference runtime hardening (4.2.0)

The dependency-free `runtime.py` model now validates host membership and identifiers,
copies artifact bytes to immutable storage, rejects duplicate starts, validates providers,
supports host addition plus component stop/unlink, revokes links on stop, verifies that a
routed component still resides on a live host, and makes host-loss refusal transactional.
These are reference-model guarantees; they are not a substitute for a production wasmCloud
deployment, durable control plane, real transport, identity, policy, telemetry, or provider layer.


## Hardened control plane (4.3.0)

4.3.0 implements the M01–M86 missing-components checklist as far as it can be closed inside this repository.
`fabric/` wraps the reference `runtime.Lattice` in a control plane where every public operation goes
authenticate → authorize → admission/limits → validate → signature/provenance → lifecycle transition →
placement → durable write → audit → telemetry and returns a `Result` envelope.

| Area | Module / artifact |
|---|---|
| Result + error registry (M09/M20) | `fabric/errors.py`, `schemas/ERROR_REGISTRY.json`, `schemas/RESULT.schema.json` |
| Lifecycle state machines (M10) | `fabric/lifecycle.py`, `docs/LIFECYCLE.md` |
| Identity, enrolment, tokens (M17/M36/M39) | `fabric/identity.py`, `fabric/ed25519.py` |
| Default-deny authz + capability grants (M18) | `fabric/authz.py` |
| Signature + provenance admission (M35) | `fabric/signing.py` |
| Quotas and limits (M12/M22/M54) | `fabric/limits.py` |
| Deadlines, retries, idempotency, breakers (M19/M43/M44) | `fabric/resilience.py` |
| Placement precedence, residency-aware failover (M14/M45) | `fabric/placement.py`, `docs/PLACEMENT.md` |
| Failure detection, leases/fencing, partitions (M13/M42/M48) | `fabric/membership.py` |
| Durable state (M47) and audit ledger (M40) | `fabric/store.py`, `fabric/ledger.py` |
| Config schema, overlays, provenance, 2-phase activation, rollback, secrets (M27–M32) | `fabric/config.py`, `config/base.json`, `config/overlays/`, `docs/CONFIG_REFERENCE.md` |
| Metrics, logs, traces, status, decisions (M58–M63) | `fabric/telemetry.py`, `ops/alerts.json`, `ops/dashboard.json` |
| Version negotiation (M21) | `fabric/negotiation.py` |
| WIT + JSON wire schemas, fixtures, Node consumer (M16/M23) | `wit/lattice.wit`, `schemas/`, `fixtures/validate.mjs` |
| Real WebAssembly execution tier; wasmCloud seam (M25 partial) | `fabric/wasm_backend.py` |
| Governance | `docs/ADR-0001-wasm-fabric.md`, `docs/REQUIREMENTS.md`, `docs/THREAT_MODEL.md`, `docs/SLO.md`, `docs/runbooks/`, `OWNERSHIP.json`, `WAIVERS.json`, `REVIEWS.json`, `SUPPORT_MATRIX.json` |
| Release evidence | `tools/ci.py` → `release/` (TEST_RESULTS, CONFORMANCE, BENCHMARK, sbom, TRACEABILITY, ACCEPTANCE, EXIT_GATE) |

**Result of this release:** 50 of 86 M-items locally verified, 27 partial, 9 blocked; the production exit gate is
**NO_GO** — see `AUDIT_REPORT.md` (4.3.0 addendum) and `release/EXIT_GATE.json`. The `WasmCloudBackend` fails closed
until a pinned wasmCloud/NATS/wadm lattice is supplied.
