# GAP-02 Hardware Capability Discovery — Audit Report

**Input version:** 4.1.0  
**Output version:** 4.2.0  
**Audit date:** 2026-09-22

## Executive result

The supplied package had a sound three-valued capability-state idea, but it was still primarily a conformance/reference component rather than an actual hardware discovery subsystem. The 4.2.0 pass preserves the fail-closed semantics, adds a real privacy-minimized host discovery layer, hardens report invariants/signing serialization, adds bounded re-probe scheduling and typed schemas, and corrects integration/documentation mismatches.

The package is locally testable without `pk_core`. Full 100-requirement certification still depends on the external Post-Kubernetes core and sibling components and therefore was not falsely certified inside the standalone audit environment.

## Findings and remediation

| Severity | Finding in 4.1.0 | 4.2.0 remediation |
|---|---|---|
| High | No implementation actually discovered the CPU/RAM/storage/NIC/GPU/NPU/virtualization hardware named by the component. | Added `discovery.py` with read-only host inventory plus conservative capability conversion. |
| High | Report signing used `repr(report.for_consumer(...))`, coupling the signed bytes to Python representation and dynamic consumer `age`. | Added deterministic canonical JSON signing bytes over stable report facts; dynamic `age` is excluded. |
| High | Future probe timestamps were not rejected and could yield negative age. | Future-dated records fail consistency checks at the consumer boundary. |
| High | An empty report could be consumed as if it were a valid fresh report. | Empty reports are rejected as invalid. |
| High | Re-probe scheduling was an owned/mandatory contract behavior but had no implementation. | Added `ProbeSchedule` with bounded interval and hot-add forcing. |
| Medium | Direct mutation of public `results` could produce malformed tuples/states and uncontrolled consumer failures. | Added defensive structural validation before consumer serialization. |
| Medium | Probe crashes became `unprobed` but discarded the reason. | Added bounded local diagnostics without changing the v1 signed report shape. |
| Medium | Node identifiers were not validated. | Added bounded safe-label validation for node and capability identifiers. |
| Medium | Timestamp validation accepted Python booleans because `bool` is an `int` subclass. | Clock inputs explicitly reject booleans and negative/non-integer values. |
| Medium | Public interface names existed without packaged typed schema artifacts. | Added JSON Schema 2020-12 definitions under `schemas/`. |
| Medium | GAP-07 was used by the security assessment but omitted from the contract dependency list. | Added explicit GAP-07 trust/signature dependency. |
| Medium | GPU/display observation risked being conflated with schedulable compute acceleration in a future implementation. | 4.2.0 records adapter observations but intentionally leaves `gpu` unprobed until a compute-runtime probe proves usability. |
| Medium | `pk_core` absence made the package unusable for its otherwise independent state/discovery primitives. | Standalone core import now works and exposes `PK_CORE_AVAILABLE=False`; integration contract still fails explicitly when invoked without `pk_core`. |
| Low | README claimed `MASTER.md` was included, but it was absent from the supplied archive. | Removed the false claim and tracked restoration as a provenance gap. |
| Low | Version-conformance test was pinned to 4.1.0. | Updated to 4.2.0. |

## Security/hardening decisions

1. **Fail closed:** only literal boolean `True` creates `present`; unavailable, crashing, or ambiguous probes create `unprobed`.
2. **No sticky capability:** every re-probe records a new state, including failures.
3. **Freshness cannot be laundered:** report age is the age of the oldest included probe.
4. **Dynamic fields are not signed:** `age` is derived at consumption time and therefore excluded from signing bytes.
5. **No shell execution:** the discovery code does not execute shell strings or user-controlled commands.
6. **Bounded external OS calls:** fixed absolute-path macOS `sysctl` calls have timeouts and output caps.
7. **Privacy minimization:** no address/MAC/serial/content collection in the baseline inventory.
8. **Conservative accelerators:** display adapter/DRM visibility is not sufficient to advertise compute GPU capability.
9. **Bounded diagnostics:** exception text is capped and stays out of the public signed v1 report.
10. **Defensive consumer boundary:** malformed, empty, future-dated, and stale reports are refused before publication/consumption.

## Validation performed

- `python -m compileall -q`: PASS.
- Dependency-free test suite: 12 local tests PASS.
- Existing `pk_core` integration test module loads and correctly skips its three integration tests when `pk_core` is unavailable.
- `python -m gap02_hardware_capability_discovery.selftest`: PASS; current audit host produced a valid `PK_HARDWARE_INVENTORY/1` and `PK_NODE_CAPABILITIES/1` report.
- JSON schema files parse as JSON.
- Static scan found no `eval`, `exec`, `pickle`, `shell=True`, or bare production `assert` use in the package implementation.

## Certification boundary

A standalone ZIP cannot prove GAP-02's full 100-check production gate because several checks require external actors: GAP-06 attestation, GAP-07 trust/signing, placement/execution/accelerator consumers, operational telemetry, release evidence, and the suite's `pk_core` evidence/gate machinery. Those gaps are enumerated in `MISSING_COMPONENTS.md` rather than silently represented as complete.
