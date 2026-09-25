# INV-13 - System interface

**Version:** 4.3.0 (see `CHANGELOG.md`)  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`  
**Master prompts:** `MASTER.md` (source workflow series retained unchanged for auditability)

INV-13 models a WASI-style system interface: a component receives only the capabilities and preopened roots declared by its world. There is no implicit filesystem, clock, network, environment, or other ambient authority.

> **Scope note (4.3.0):** the 4.2.0 reference policy model (`runtime.py`) is retained unchanged. 4.3.0 adds a stdlib-only **host layer** (`host/`) implementing the MC-001..MC-032 components that can be built and tested without a fleet: a versioned WIT contract with a surface-diff gate, descriptor-relative (openat2 / O_NOFOLLOW) filesystem confinement, INV-42-style capability descriptors, a deny-by-default policy engine, actor identity/attestation gate, socket/HTTP providers with SSRF defences, env/stdio/secret boundary, clocks, CSPRNG, generation-protected resource table, error taxonomy, async/backpressure primitives, atomic config activation, durable tamper-evident audit sink, telemetry with privacy filter, quotas/admission, rollback/quarantine controls, and a **real Wasm engine binding** (V8 via Node, core modules). It is **not production-certified**: component-model engine integration, PKI/attestation, org ownership, signing and multi-platform CI remain open — see `MISSING_COMPONENTS.md` and `COMPONENT_STATUS.json`.

## Responsibility

Own the host-interface policy surface a component sees: grant only capabilities its declared world lists, maintain explicit preopens, lexically resolve relative paths within those roots, and refuse undeclared authority.

## Owns

- The world declaration a component is instantiated against
- Immutable world capability snapshots
- Validated preopen policy tables and explicit replacement/revocation
- Lexical POSIX path confinement within declared preopens
- Refusal of undeclared capability requests
- Deterministic hash-chained in-process security events
- Clock/randomness **capability gating** (not the host provider implementation)

## Explicitly does not own

- Host implementations behind the interface
- WIT/interface type definitions
- Canonical ABI implementation
- Composition linking
- Placement/scheduling
- Kernel/OS descriptor operations, symlink-safe opens, or filesystem implementations
- Durable audit storage or telemetry export

## Security invariants in v4.2.0

1. `World` snapshots the supplied capability iterable into a validated `frozenset`; mutating the caller's input cannot widen authority later.
2. Instance preopen state is private; callers receive a read-only mapping view.
3. Logical and host preopen roots must be canonical, single-rooted absolute POSIX paths. Ambiguous `//`, NUL, relative paths, and `..`-normalizing roots are rejected.
4. Replacing an existing preopen with a different host root requires explicit `replace=True`; silent authority retargeting is denied.
5. Preopen count, names, and path inputs are bounded.
6. Absolute guest paths, NUL-containing paths, traversal escapes, absent preopens, and absent capabilities fail closed.
7. Security-relevant operations generate deterministic SHA-256 hash-chained events without consulting an ambient clock.
8. `resolve()` uses lexical POSIX semantics only; it deliberately does not claim protection against host symlink/TOCTOU attacks. That protection belongs in the missing descriptor-based host adapter.

## Interfaces

- `PK_WORLD/1` — capability grant result for an instantiated component
- `PK_PREOPEN/1` — validated logical preopen to host-root policy mapping
- `PK_PATH_RESOLVE/1` — lexical relative-path resolution result inside a preopen

## Service-level objectives

The contract retains these architectural targets:

- **confinement** — zero lexically resolved paths outside a preopen (no error budget)
- **no ambient** — zero capabilities granted outside the declared world (no error budget)
- **resolve latency** — p99 under 1 µs per path (1% may exceed)

**Measured in 4.3.0 (finding B-01): the Python reference resolve runs at p99 ≈ 50–60 µs on the reference host — the 1 µs target is not met.** The target is retained unchanged in the contract pending an owner decision (native fast path vs. SLO revision). The latency item is not certified production evidence. Release certification still requires the benchmark/fleet evidence listed in `MISSING_COMPONENTS.md`.

## Host layer (4.3.0)

| Module | Component | Module | Component |
|---|---|---|---|
| `wit/*.wit`, `host/wit_surface.py` | MC-001 | `host/aio.py` | MC-013 |
| `host/wasm_loader.py`, `host/runtime_adapter.py`, `host/adapter_v8.mjs` | MC-002 | `host/config.py` | MC-014 |
| `host/fs.py` | MC-003 | `host/audit_sink.py` | MC-015 |
| `host/descriptors.py` | MC-004 | `host/telemetry.py` | MC-016, MC-029 |
| `host/policy.py` | MC-005 | `host/quotas.py` | MC-017 |
| `host/identity.py` | MC-006 | `host/http_out.py` | MC-018 |
| `host/net.py` | MC-007 | `host/compat.py`, `COMPAT_MATRIX.json` | MC-019 |
| `host/stdio_env.py` | MC-008 | `ci/matrix.yml` | MC-020 |
| `host/clocks.py` | MC-009 | `tests/test_adversarial.py` | MC-021..023 |
| `host/randomness.py` | MC-010 | `tools/bench.py` | MC-024 |
| `host/resources.py` | MC-011 | `tools/build.py`, `SBOM.cdx.json`, `PROVENANCE.intoto.json` | MC-025 |
| `host/errors.py` | MC-012 | `pyproject.toml`, `tools/build_backend.py` | MC-026 |
| `host/host.py` | end-to-end integration | `host/control.py` | MC-027 |
| `OWNERSHIP.md` | MC-028 (template) | `EDGE_CHARACTERIZATION.md` | MC-030 |
| `tools/gate.py`, `TRACEABILITY.json` | MC-031 | `docs/adr/`, `THREAT_MODEL.md` | MC-032 |

## Tests and release gate

One command runs every suite (normal and `python -O`), the WIT surface gate, benchmark regression gate, reproducible build, offline wheel install and traceability check, and writes `evidence/`:

```text
python inv13_system_interface/tools/gate.py --checklist <COMPONENT_CHECKLISTS.md>
```

Individual suites, e.g.:

```text
python inv13_system_interface/tests/test_runtime.py
python inv13_system_interface/tests/test_fs_descriptor.py
```

Requirements: Python ≥ 3.10 (stdlib only). Optional: Node ≥ 18 for the V8 engine tests; `openssl` CLI for the TLS fixture.

Framework conformance tests (requires `pk_core`):

```text
python inv13_system_interface/tests/test_component.py
```

The framework test verifies checklist accounting and assessment execution, including `python -O` parity. It does **not** turn absent external runtime/integration artifacts into production evidence; see `AUDIT_REPORT.md` and `MISSING_COMPONENTS.md`.

## pk_core workflow

When the adjacent framework is installed:

```text
python -m pk_core list
python -m pk_core run INV-13 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-13 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

## Day-0 / day-1 / day-2

- **Day 0:** import the package, execute the dependency-free security suite, then run the framework assessment if `pk_core` is available.
- **Day 1:** require the system-interface host adapter, WIT contracts, provenance, real integration tests, and benchmark evidence before production deployment.
- **Day 2:** re-run tests/gates on every world, preopen, runtime, or interface change; preserve evidence continuity and verify audit/export chains.

Rollback is to the previous sealed evidence/artifact set. Emergency disable should revoke the affected preopen/capability or remove the component from the registry, with that action recorded by the surrounding control plane.
