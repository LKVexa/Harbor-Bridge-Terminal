# INV-34 - Legacy CPU expansion path

**Version:** 5.1.0  
**Group:** 01_Source_Inventory  
**Function:** Conventional VM CPU scaling  
**Primary mechanism:** ACPI CPU hot-plug  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`

INV-34 is the legacy/conventional virtual-machine CPU expansion path. It accepts monotonic desired-vCPU increases only when the VM, guest and current host capacity permit them, and it keeps the accepted target separate from the independently observed online-vCPU count. That separation prevents the control plane from claiming that a CPU expansion completed merely because a request was accepted.

## Repository layout

- `expansion.py` — dependency-free validation, desired/observed state machine, generation guard and bounded idempotency cache.
- `component.py` — `pk_core` checklist adapter.
- `contract.py` — binding INV-34 framework contract.
- `schemas/` — versioned JSON Schemas for request, result and status payloads.
- `tests/test_expansion.py` — standalone unit/concurrency tests that run without `pk_core`.
- `tests/test_component.py` — framework conformance tests; framework-specific tests skip if `pk_core` is unavailable.
- `ARCHITECTURE.md`, `THREAT_MODEL.md`, `OPERATIONS.md`, `COMPATIBILITY.md` — design and operating constraints.
- `AUDIT_REPORT.md` — findings from the 5.0.0 repair pass.
- `MISSING_COMPONENTS.md` — remaining production gaps after the repair pass.

## Core semantics

1. Expansion is monotonic. CPU hot-unplug is outside INV-34.
2. Both the hypervisor ACPI CPU-hotplug path and guest CPU-hotplug support must be available for a real increase.
3. `target_vcpus` may not exceed the VM maximum or the currently discovered host capacity.
4. Optional `expected_generation` implements optimistic concurrency; stale writers are rejected.
5. Reusing an idempotency key with different parameters is rejected.
6. `desired_vcpus` records an accepted target; `observed_vcpus` records what the backend/guest has actually confirmed online.
7. A request is converged only when `observed_vcpus == desired_vcpus`.
8. The reference controller never performs hypervisor I/O itself; a production adapter/reconciler is still required and is explicitly listed as a missing component.

## Example

```python
from inv34_legacy_cpu_expansion_path import CpuExpansionController, VmCpuState

controller = CpuExpansionController(
    VmCpuState(
        vm_id="vm-42",
        observed_vcpus=2,
        desired_vcpus=2,
        max_vcpus=8,
        host_capacity_vcpus=8,
    )
)

accepted = controller.request_expansion("request-123", 4, expected_generation=0)
assert accepted.status == "accepted"
assert controller.snapshot().observed_vcpus == 2  # not falsely reported complete

# Later, after a hypervisor/guest adapter observes progress:
controller.record_observation(3)
controller.record_observation(4)
assert controller.snapshot().converged
```

## Run tests

From the directory that contains `inv34_legacy_cpu_expansion_path`:

```text
python -m unittest discover -s inv34_legacy_cpu_expansion_path/tests -v
python -O -m unittest discover -s inv34_legacy_cpu_expansion_path/tests -v
```

The standalone tests must pass with or without `pk_core`. If `pk_core` is available, the framework conformance tests also run.

## `pk_core` integration

When the external framework is installed or its parent directory is provided through `PK_CORE_PATH`:

```text
python -m pk_core list
python -m pk_core run INV-34 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-34 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

The ZIP does **not** vendor `pk_core`; absence of that dependency is therefore reported explicitly rather than silently treated as a complete production certification.

## Production status

The 5.0.0 repository contains a hardened reference control-plane implementation, schemas, tests and operational documentation. It is **not yet a complete production CPU-hotplug subsystem** because hypervisor/guest adapters, authorization, durable state, telemetry exporters, end-to-end certification and other infrastructure-dependent pieces remain external. See `MISSING_COMPONENTS.md` for the exhaustive gap list from the post-fix audit.


## 5.1.0 production overlay

`production/` adds the service around the 5.0.0 controller: adapters (Cloud Hypervisor REST + CI emulator), guest observation, durable store/lease/journal, reconciler, security/quota/policy, HTTP API, config, audit, telemetry. Run everything with:

```
python3 -B inv34_legacy_cpu_expansion_path/tools/ci.py
```

Results land in `governance/` (`CI_RESULT.json`, `RTM.md`, `CHECKLIST_STATUS.md`, `PERF_BASELINE.json`, `SBOM.cdx.json`, `BUILD_RESULT.json`, `EXIT_GATE_RESULT.json`).
**Production decision: NO_GO.** Local lanes pass. Certification cannot pass without the items in `governance/BLOCKERS.json`.
