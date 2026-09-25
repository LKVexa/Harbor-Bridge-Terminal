# INV-09 - Portable compute ISA

**Version:** 4.3.0 (see `CHANGELOG.md`)
**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The portable compute ISA is the bytecode everything above it compiles to: a small, deterministic instruction set with no ambient environment and no undefined behaviour to exploit. Portability is only worth anything if the same module computes the same answer everywhere, so this element validates modules rather than trusting their headers.

## Responsibility

Own module validation and the deterministic execution profile: verify structure, types and the declared feature set before a module runs, and refuse any module using a non-deterministic or unapproved feature.

## Owns

- Module structural and type validation
- The approved feature set per profile
- Determinism profile enforcement
- Refusal of unvalidated or over-featured modules
- Module size and section limits

## Explicitly does not own

- Compilers producing modules
- Runtime hardening
- The component model above it
- Host function semantics
- Placement

## Non-goals

- Compiling source to bytecode
- Hardening the engine
- Running an unvalidated module
- Guaranteeing determinism for opted-out profiles

## Interfaces

- `profile` - PK_ISA_PROFILE/1 - permitted features and determinism class
- `validate` - PK_MODULE_VALIDATION/1 - validation verdict with the feature set actually used

## Service-level objectives

- **validation soundness** - zero modules executed without passing validation (error budget: no budget)
- **determinism** - identical modules and inputs produce identical results within a deterministic profile (error budget: no budget)
- **validation latency** - p99 under 20ms for modules up to 4MiB (error budget: 1% may exceed)

## Production validation boundary (v4.3.0)

`prod/` is a byte-level, fail-closed WebAssembly validation boundary implementing the P0 chain of the
missing-components checklist: raw decoder (M01), spec-algorithm type validator (M02), byte-derived
feature detector (M03), digest-bound capability manifests (M04), a strict signed policy bundle carrying the
spec/profile/engine registries (M05/M06/M22), SHA-256 module identity (M07), Ed25519 attestations (M08), an
integrity-protected epoch-keyed cache (M09), and an admission gate with TOCTOU protection (M10/M11), under a
structured failure schema (M12) and a resource governor (M13).

```python
from inv09_portable_compute_isa.prod import admission, attest
signer = attest.Signer("key-1")                       # production: HSM/KMS-backed
gate = admission.Gate(signer=signer, verifier=attest.Verifier({"key-1": signer.public_raw()}))
verdict = gate.validate(wasm_bytes, profile="deterministic", engine="reference-engine")
if verdict["outcome"] == "accept":
    ticket = gate.admit(wasm_bytes, verdict["attestation"], profile="deterministic", engine="reference-engine")
    gate.execute(ticket, engine_runner)               # runner receives only the attested bytes
```

`validator.py` (the v4.2.0 descriptor kernel) is retained as a policy mirror; its profiles are tested for
equality with the bundle, and it must never be fed caller-supplied facts (ADR-0001).

**Production status: NO_GO.** See `CHECKLIST_STATUS.md` (all 2,704 checklist items with evidence),
`evidence/production_gate.json` and `FINDINGS.md`. Main blockers: named owners (M50), the latency SLO
(measured p99 ≈ 2.4 s at 4 MiB, ADR-0006), a second differential reference (M15), certified real engines
and cross-architecture determinism (M06/M20/M21), and fleet-scale soak (M31).

## Running it

```
python -m unittest discover -s inv09_portable_compute_isa/tests -p "test_*.py" -v   # all standalone tests (prod + kernel)
python inv09_portable_compute_isa/tools/checklist_status.py                       # re-execute the 2,704-item checklist + M52 gate
sh inv09_portable_compute_isa/tools/ci.sh                                         # full clean-environment evidence run
python inv09_portable_compute_isa/tests/test_component.py             # set PK_CORE_PATH if pk_core is elsewhere
python -m pk_core list
python -m pk_core run INV-09 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-09 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-09`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-09`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
