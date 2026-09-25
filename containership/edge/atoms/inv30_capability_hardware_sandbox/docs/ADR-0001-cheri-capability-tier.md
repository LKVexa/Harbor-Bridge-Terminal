# ADR-0001 — CHERI capability tier with a labelled semantic model (INV30-GAP-007 · INV-30-C010)

* **Status:** Proposed (4.3.0). Becomes *Accepted* when `evidence/SIGNOFFS.json → architecture_approver` is signed.
* **Date:** 2026-09-23 · **Deciders:** accountable owner (see OWNERSHIP.md)

## Context
INV-30 owns fine-grained hardware memory capabilities. CHERI (Arm Morello, CHERI-RISC-V) is the only mature family
that enforces bounds/permissions/tags in hardware. Almost no production nodes have it. 4.2.0 shipped a pure-Python
semantic model that was easy to mistake for enforcement.

## Decision
1. **Two backends behind one interface** (`backend.py`): `SemanticModelBackend` (`enforcement="semantic-model"`) and
   `CheriHardwareBackend` (`enforcement="cheri-hardware"`, native helper built with CHERI LLVM, pure-capability ABI).
2. **Every success record carries `enforcement`.** Schema `access_result` rejects records without it.
3. **No silent downgrade.** A workload or config that sets `require_hardware` is refused with `HARDWARE_REQUIRED`
   when no hardware backend is available — in every mode. Config `allow_model_for_hardware_workloads` is forbidden.
4. **Opaque handles at the boundary**; callers never hold `Capability` objects. Root capabilities only come from the
   `MintingAuthority` as signed, tenant-bound grants.
5. **Volatile state**: a restart invalidates every handle (fail-safe for capabilities).
6. Discovery is published through GAP-02 with the tri-state `present/absent/unprobed`.

## Consequences
* The model is useful for semantics, CI and non-hardware workloads; it is never counted as hardware evidence.
* The hardware tier stays **NO_GO** until the hardware-conformance suite runs green on an approved CHERI profile
  (docs/CHERI_SPEC_PIN.md). The release gate encodes this (`hardware_tier_verdict`).
* Rejected alternatives: *software emulation claimed as the tier* (violates non-goal); *QEMU-only certification*
  (allowed for development evidence, not for a production hardware claim); *folding INV-45 SFI in as a fallback
  under the INV-30 label* (it is a different tier and is reported as such).
