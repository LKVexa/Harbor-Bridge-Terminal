# INV-23 - Hardware virtualization primitive

**Version:** 5.0.0 (see `CHANGELOG.md`)
**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md`, restored verbatim from the owner's Post-Kubernetes master-applied build (provenance only; see `MASTER_PROVENANCE.json`)

The hardware virtualization primitive is the floor everything above it stands on: the CPU's own trap-and-emulate machinery. It is either present and usable or it is not, and no amount of software above it can manufacture it, so this element reports it honestly and refuses to pretend nested virtualization is the same thing as bare metal.

## Responsibility

Own detection and gating of the CPU virtualization extensions: report whether VT-x/AMD-V, EPT/NPT, and nested virtualization are actually usable on this host, and refuse to advertise a primitive that is present in CPUID but disabled or already claimed.

## Owns

- Detection of CPU virtualization extensions
- The usable-versus-present distinction
- Nested-virtualization depth reporting
- Exclusivity of the KVM-equivalent device
- Refusal when the primitive is claimed by another hypervisor

## Explicitly does not own

- The VMM itself
- Guest lifecycle
- Device emulation
- Isolation policy
- Scheduling

## Non-goals

- Implementing a VMM
- Enabling the extension in firmware
- Emulating virtualization in software
- Reporting nested as equivalent to bare metal

## Interfaces

- `probe` - PK_VIRT_PRIMITIVE/2 (`schemas/PK_VIRT_PRIMITIVE-2.schema.json`) - host evidence report from `probe.Prober`
- `claim` - PK_VIRT_CLAIM/2 (`schemas/PK_VIRT_CLAIM-2.schema.json`) - fenced, lease-based claim from `claim.ClaimManager`
- Legacy `/1` schemas are frozen and describe the in-process `VirtPrimitive` model used by the pk_core reference assessment.

## Service-level objectives

- **report soundness** - zero hosts reporting the primitive usable when the device cannot be opened (error budget: no budget)
- **nesting honesty** - zero nested hosts reporting depth 0 (error budget: no budget)
- **probe latency** - p99 probe under 50ms (error budget: 1% may exceed)

## Architecture

| Layer | Module | Role |
|---|---|---|
| Probe | `probe.py`, `backends/` | Real host evidence -> `usable` / `present-disabled` / `absent` / `indeterminate` plus a reason code |
| Claim | `claim.py`, `ownership/` | Cross-process claim with a fresh probe, fencing generation, lease and token |
| Model | `model.py` | In-process state machine (legacy /1) used by the pk_core assessment |
| Interfaces | `schema.py`, `schemas/`, `admission.py` | Normative JSON Schemas; admission contract for consumers |
| Signals | `telemetry.py` | Contract signals with bounded labels and redaction |
| Assurance | `tools/`, `benchmarks/`, `tests/` | Gate, evidence, SBOM, provenance, benchmarks, suites |

Exclusivity semantics: the claim is on a **project-defined slot**. `/dev/kvm`, WHPX and HVF allow
more than one legitimate user at once, and INV-23 does not pretend they are exclusive. See
`ownership/base.py` and `THREAT_MODEL.md`.

## Running it

```
python -m inv23_hardware_virtualization_primitive.cli            # host probe (PK_VIRT_PRIMITIVE/2 JSON)
cd inv23_hardware_virtualization_primitive
python tools/run_suite.py unit           # also: schema property integration multiprocess conformance hardware
INV23_CONFORMANCE=release python tools/run_suite.py conformance    # pk_core missing => FAIL, not skip
python benchmarks/benchmark_probe.py     # p99 < 50 ms SLO gate
python tools/gate.py --wheel dist/<wheel>   # full production gate, writes conformance/ + evidence/
python tools/verify_evidence.py          # independent verification of sealed evidence
python -m pk_core --package <pkg> gate INV-23 --out conformance/PK_GATE_RESULTS.json   # pk_core-native, as before
```

Quality gates (CI): `ruff check`, `ruff format --check`, `mypy` (public API typed, with stricter
settings for `backends/`, `schema`, `admission`), `tools/check_version.py`, `tools/gen_compat.py --check`,
and `tools/waivers.py`. The release job fails if any mandatory job is skipped.

Supported platforms: see `COMPATIBILITY.md`. Only **verified** rows are supported. `tests/unit/test_repository.py`
checks that this README does not claim support beyond the matrix.

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-23`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-23`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
