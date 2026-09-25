# ADR-0002 — Resolution of the checklist's Software Fault Isolation (SFI) requirement

**Status:** PROPOSED (not approved; see OWNERS.json). **Controls:** C010, C031. **Remediation item:** 06.

## Problem

`CHECKLIST.json` C010 asks for an architecture decision that names Software Fault Isolation. 4.2.0 implemented CPU mitigation-state / co-tenancy policy and nothing SFI-shaped. The audit flagged that these must not be silently treated as equivalent.

## Analysis

- **SFI** (e.g. WebAssembly bounds checking, NaCl, LFI) constrains *memory addressing within one address space* so untrusted code cannot read/write outside its sandbox architecturally.
- **Transient-execution mitigations** address *micro-architectural* leakage that bypasses architectural bounds — the very thing Spectre v1 does to SFI bounds checks.
- Therefore SFI is neither a substitute for nor a subset of INV-43. They compose: an SFI tier (e.g. a Wasm "process" tier in PLN-04) shares an address space and so needs the *strictest* mitigation set (spectre_v1 hardening, spec_store_bypass), which is what the `process` tier in the policy requires.

## Decision (proposed)

1. INV-43 does **not** implement SFI and does not claim C010's SFI clause.
2. SFI is owned by the execution plane (PLN-04) as an isolation tier. INV-43's contribution is the tier→required-mitigation mapping (`policy/default_policy.json` → `isolation_tiers.process`).
3. C010 is recorded as **split**: architecture decision for transient-execution defense = ADR-0001; SFI technology choice = PLN-04's ADR (not in this repository → external dependency, BLOCKED).
4. A waiver entry (`governance/EXCEPTIONS.json` EXC-002) records this until PLN-04 publishes its SFI ADR.
