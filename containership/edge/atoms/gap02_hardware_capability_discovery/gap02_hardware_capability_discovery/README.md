# GAP-02 — Hardware Capability Discovery

**Version:** 4.3.0  
**Group:** 04_Gap_Subsystems  
**Series:** Post-Kubernetes Master Prompt & Workflow Series  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`

GAP-02 provides a conservative hardware-capability discovery model for heterogeneous nodes. A capability is never promoted to `present` unless the local probe returns the literal boolean `True`. Unsupported, blocked, ambiguous, or crashing probes become `unprobed`, which prevents a node from advertising capability it did not prove.

## 4.3.0 — production layer (checklist GAP02-MC-01..55)

v4.3.0 executes the 55-component professional checklist against 4.2.0. A new
stdlib-only `production/` subpackage adds vendor GPU/NPU probes, CPU/NUMA/
storage/NIC/virtualization/confidential-computing/TPM probes, a signed
envelope with replay protection and trusted time, a bounded executor with
atomic sweeps, publisher, broker, authz, provenance, sibling adapters and the
full observability/operations surface. **Every capability still passes through
one gate — `production/evidence.promote()` — which returns `present` only for
capability-specific proof; observations, name matches, driver presence and
cache entries can never be promoted.**

Honest status is machine-readable in `COMPONENT_STATUS.json` and per-component
bundles in `evidence/GAP02-MC-NN.json`. **Production-GO is NOT claimed**: no
component has independent sign-off, the physical-hardware lab was not run, the
sibling estate and `pk_core` are absent, and the original `MASTER.md` was not
supplied (it is deliberately not synthesized). `tools/release_gate.py` returns
`NO_GO` and says why.

```text
python -B -m unittest discover -s gap02_hardware_capability_discovery/tests
python -m gap02_hardware_capability_discovery.production.agent sweep
python -m gap02_hardware_capability_discovery.production.agent explain gpu.compute.nvidia
python -B -m gap02_hardware_capability_discovery.tools.evidence
python -m gap02_hardware_capability_discovery.tools.release_gate
python -m gap02_hardware_capability_discovery.tools.build OUT.zip
```

| Area | Modules |
|---|---|
| Probes (MC-01..09) | `production/accelerators.py cpu.py topology.py storage.py nic.py virt.py confidential.py securedev.py` |
| Trust (MC-10..12, 19, 20) | `envelope.py replay.py timepolicy.py authz.py provenance.py` |
| Runtime (MC-13..18, 28, 29, 37..40) | `config.py executor.py sweep.py publisher.py errors.py broker.py cache.py hotplug.py breaker.py quarantine.py limits.py agent.py` |
| Siblings (MC-21..27) | `integration.py compat.py` |
| Operations (MC-30..36, 41..55) | `health.py observability.py audit.py explain.py ops/ RUNBOOKS.md COMPATIBILITY_MATRIX.json conformance/ fixtures/ tools/ ADR-0001… SUPPORT_POLICY.md PK_CORE_CONTRACT.json` |

## 4.2.0 scope

This package now contains two layers:

1. **Dependency-free discovery/probe core** — `capabilities.py` and `discovery.py`; usable for bootstrap and local testing without `pk_core`.
2. **Post-Kubernetes integration** — `component.py` and `contract.py`; activated when the suite's external `pk_core` package is available.

The package can inventory basic CPU, memory, storage, network-interface exposure, display/DRM adapter observations, virtualization evidence where the OS exposes it safely, and TPM device exposure. GPU compute and NPU capability remain `unprobed` until a vendor/runtime-specific probe can prove them.

## Security model

- `present`, `absent`, and `unprobed` are distinct states.
- A failed re-probe overwrites an older `present` state with `unprobed` rather than leaving a sticky capability.
- Empty, malformed, future-dated, or stale reports fail closed at the consumer boundary.
- Report signing input is canonical JSON and excludes dynamic consumer-time `age`.
- Capability/node identifiers and timestamps are bounded and validated.
- Probe exception diagnostics are bounded to 512 characters and are not placed in the signed v1 report.
- Discovery does not collect MAC addresses, IP addresses, disk contents, serial numbers, credentials, or secrets.
- External system commands, where needed on macOS, are fixed absolute-path commands, executed without a shell, with bounded output and a timeout.

## Core interfaces

| Interface | Schema | Implementation |
|---|---|---|
| Capability probe | `PK_CAPABILITY_PROBE/1` | `capabilities.probe()` |
| Capability report | `PK_NODE_CAPABILITIES/1` | `CapabilityReport.for_consumer()` |
| Probe schedule | `PK_PROBE_SCHEDULE/1` | `ProbeSchedule` |
| Hardware inventory | `PK_HARDWARE_INVENTORY/1` | `collect_inventory()` |

Machine-readable JSON Schemas are in `schemas/`.

## Discovery semantics

`collect_inventory(node, now)` collects privacy-minimized host facts. `report_from_inventory()` then converts only reliably proven boolean conditions into the scheduling-facing capability report. Observations that are useful to an operator but insufficient to prove a schedulable capability remain inventory metadata and produce `unprobed` in the capability report.

Example:

```python
from gap02_hardware_capability_discovery import discover

inventory, report = discover("edge-node-17", now=1_000)
consumer_view = report.for_consumer(now=1_010)
signing_bytes = report.canonical_bytes(now=1_010)
```

## Re-probe scheduling

```python
from gap02_hardware_capability_discovery import ProbeSchedule

schedule = ProbeSchedule(("cpu", "memory", "gpu", "npu"), interval=60)
due = schedule.due(report, now=1_060, hot_added=("gpu",))
```

`ProbeSchedule` computes which declared probes are due. A long-running scheduler/agent that executes those due probes and publishes them to the control plane remains an integration component; see `MISSING_COMPONENTS.md`.

## `pk_core` integration

`pk_core` is an external suite dependency and is not bundled in this ZIP. When it is unavailable, the dependency-free discovery core still imports and `PK_CORE_AVAILABLE` is `False`. The production contract/component require `pk_core` plus the relevant sibling elements.

The integration declares these architectural relationships:

- GAP-06 — device identity / attestation
- GAP-07 — trust and signature service
- SCH-01 — workload classification / placement
- PLN-04 — execution plane
- GAP-11 — accelerator scheduling
- GAP-01 — edge node supervisor

## Verification

From the folder containing `gap02_hardware_capability_discovery/`:

```text
python -m unittest discover -s gap02_hardware_capability_discovery/tests -v
python -m gap02_hardware_capability_discovery.selftest
python -m compileall -q gap02_hardware_capability_discovery
```

With the full Post-Kubernetes suite available:

```text
python gap02_hardware_capability_discovery/tests/test_component.py
python -m pk_core run GAP-02 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate GAP-02 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

The standalone tests validate the local state model, discovery layer, version pinning, freshness semantics, canonical signing bytes, mutation detection, and scheduling logic. The 100-requirement `pk_core` conformance gate is intentionally skipped when `pk_core` is not installed; this package no longer claims that an unavailable external gate was executed.

## Files added in 4.2.0

- `capabilities.py` — hardened three-state report model and re-probe scheduler
- `discovery.py` — conservative cross-platform host inventory
- `selftest.py` — dependency-free smoke test
- `schemas/*.schema.json` — versioned public contract schemas
- `tests/test_capabilities.py` — deterministic unit tests
- `AUDIT_REPORT.md` — audit, fixes, hardening and validation record
- `MISSING_COMPONENTS.md` — remaining production components and priorities

## Source-package note

The prior README referred to `MASTER.md` as being carried in the component package, but that file is not present in the supplied archive. Version 4.2.0 corrects the documentation rather than fabricating a supposedly verbatim source artifact. Its restoration remains listed in `MISSING_COMPONENTS.md` if the original master prompt/workflow artifact is required for provenance.
