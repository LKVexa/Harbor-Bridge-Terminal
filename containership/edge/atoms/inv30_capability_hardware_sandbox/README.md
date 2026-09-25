# INV-30 - Capability hardware sandbox

**Version:** 4.3.0 (see `CHANGELOG.md`)
**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`

The capability hardware sandbox is CHERI-shaped: pointers carry bounds and permissions the hardware itself checks, so a bug cannot be turned into an arbitrary write. It is the one tier where memory safety is enforced below the software stack -- and it exists on very little hardware, which this element states rather than glosses over.

## Responsibility

Own capability-hardware sandboxing: represent memory capabilities with their bounds and permissions, enforce monotonic narrowing on derivation, and refuse any access outside a capability's bounds or permission set.

## Owns

- Capability representation (base, length, permissions, validity)
- Monotonic narrowing on derivation
- Bounds and permission checking on access
- Capability invalidation
- Refusal of permission amplification

## Explicitly does not own

- The CPU implementation
- Compiler toolchains
- Operating-system policy
- Other isolation tiers
- Placement

## Non-goals

- Implementing the CPU
- Emulating capability hardware in software
- Claiming this tier where the hardware is absent
- Replacing software capability security

## Interfaces

- `access` - PK_CAPABILITY_ACCESS/1 - a bounds- and permission-checked access
- `derive` - PK_CAPABILITY/1 - derive a narrower capability from a held one

## Service-level objectives

- **bounds** - zero accesses served outside a capability's bounds (error budget: no budget)
- **monotonicity** - zero derivations widening bounds or permissions (error budget: no budget)
- **invalidation** - zero uses of an invalidated capability (error budget: no budget)

## Running it

```
python inv30_capability_hardware_sandbox/tests/test_component.py   # set PK_CORE_PATH if pk_core is elsewhere
python -m pk_core list
python -m pk_core run INV-30 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-30 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-30`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-30`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback, canary and emergency disable are executable: see `docs/ROLLOUT.md` and `ops.py`.

## 4.3.0 production layer

| Area | Where |
|---|---|
| Service boundary (opaque handles, auth, authz, admission, deadlines, audit, metrics, traces, decisions) | `service.py` |
| Backends: labelled semantic model vs CHERI hardware adapter (fails closed) | `backend.py`, `docs/CHERI_BACKEND.md` |
| Discovery → GAP-02 | `discovery.py` |
| Schemas (JSON Schema 2020-12) + validator | `schemas/`, `schema.py` |
| Failure envelope PK_FAILURE/1 | `errors.py` |
| Config (overlays, validation, atomic activation, rollback) + secret refs | `config.py`, `config/`, `secret_refs.py` |
| Audit ledger (hash chain + HMAC) | `audit.py` |
| Resilience (retry, breaker, admission, stall, lease) | `resilience.py`, `service.Lease` |
| Operator CLI (env, health, config-check, rollout, rollback, disable) | `ops.py` |
| Bench + regression gate, release evidence + exit gate | `bench.py`, `release.py` |
| Traceability (100 controls) | `traceability.py`, `docs/TRACEABILITY.md` |
| Governance/ops docs | `docs/` |

**Enforcement truth:** every success record carries `enforcement`. On this build it is always `semantic-model`;
workloads that require hardware are refused with `HARDWARE_REQUIRED`. The hardware tier is NO_GO until the
hardware-conformance suite passes on an approved CHERI profile.

```
python -m unittest discover -s pk_components/inv30_capability_hardware_sandbox/tests -t .        # 99 tests
python -m pk_components.inv30_capability_hardware_sandbox.release --out pk_components/inv30_capability_hardware_sandbox/evidence
python -m pk_components.inv30_capability_hardware_sandbox.release --verify --out pk_components/inv30_capability_hardware_sandbox/evidence
python -m pk_components.inv30_capability_hardware_sandbox.ops health
```

## Standalone verification

The capability model in `core.py` has no `pk_core` dependency. This prevents a
missing framework installation from turning all security-semantic tests into
skips. Run:

```
python -m unittest discover -s inv30_capability_hardware_sandbox/tests -v
```

The framework conformance tests still require `pk_core`; the standalone core
tests do not. `Capability` is a semantic model of attenuation and access checks,
not a claim that ordinary Python objects are unforgeable CHERI capabilities.
