# INV-39 Repository Audit Report

## Result

- **Input version:** 4.1.0
- **Updated version:** 5.0.0
- **Release type:** major security/correctness bump because fail-closed read-back changes runtime behavior
- **Core Python compile:** PASS
- **Dependency-free/core unit suite:** PASS, 14/14 (17 discovered, 3 `pk_core` skips)
- **Dependency-free/core suite under `python -O`:** PASS, 14/14 (17 discovered, 3 `pk_core` skips)
- **`pk_core` conformance suite:** NOT EXECUTED; 3/3 tests skipped because `pk_core` is not present in the supplied archive/environment
- **Residual missing-component inventory:** 106 entries in `MISSING_COMPONENTS.md`

## Material defects found in 4.1.0

1. **False applied-state verification:** `Sandbox.start()` treated the requested profile as the applied state whenever no read-back was supplied. A caller could therefore receive a successful `PK_SANDBOX_APPLIED/1` record without any enforcement evidence.
2. **No production enforcer:** the repository did not install seccomp, namespaces, capabilities, bubblewrap, or Seatbelt despite describing a process sandbox tier.
3. **Capability canonicalization bypass:** forbidden-capability comparison was case-sensitive and accepted arbitrary token shapes.
4. **Lifecycle ambiguity:** syscall modelling was possible before a verified start, and start could be called repeatedly without an explicit state transition rule.
5. **Unbounded denial history:** attacker-controlled denied syscall names could grow the in-memory denial list without bound.
6. **No binding between profile and evidence:** applied records lacked a deterministic digest of the canonical policy.
7. **Public interface schemas were named but absent.**
8. **Core tests depended on an external package and silently skipped when it was unavailable**, leaving no independent test gate for the security-critical policy model.
9. **README overstated repository contents**, claiming a `MASTER.md` archive that was not present.
10. **Source-of-truth wording assumed exact read-back of enforcement state** without acknowledging backend/kernel limitations.

## Changes applied in 5.0.0

- Extracted the dependency-free policy/read-back verifier into `sandbox.py`.
- Made missing applied-state evidence fail closed.
- Added canonical input validation for profile/process/read-back tokens.
- Closed capability case/whitespace bypasses.
- Added strict single-start lifecycle semantics and pre-start syscall rejection.
- Bounded denial logs and added a dropped-denial counter.
- Added deterministic SHA-256 profile digests and bound applied evidence to the digest.
- Added explicit verification-scope fields so read-back equality cannot be mistaken for proven OS enforcement.
- Added JSON Schemas for both public contracts.
- Added 11 dependency-free security/lifecycle unit tests, including optimized-mode execution.
- Made the policy model importable without `pk_core`; the integration contract remains explicitly unavailable until that dependency is installed.
- Corrected README assurance language and removed the false `MASTER.md` claim.
- Added `ARCHITECTURE.md` and `SECURITY.md` to state the real trust boundary and required backend ordering.
- Updated the `pk_core` integration test version pin to 5.0.0.

## Remaining assurance limitation

The package can now prove that a supplied applied-state record exactly matches a canonical profile, but it still cannot prove that an operating system actually enforced that record. That requires platform-specific launch/enforcement adapters plus backend integration and adversarial certification. Those residual components are enumerated in `MISSING_COMPONENTS.md`.


---

## Addendum — 5.1.0 implementation pass (2026-09-22)

Scope: every MC-001..MC-106 work package in `docs/INV39_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST_v5.0.0.md`.

* The 5.0.0 finding "no OS enforcement" is closed for Linux: controls are applied by `linux/launcher.py` and verified from the kernel before `execve`; 17 escape probes are blocked on kernel 6.18.44 / x86_64.
* Result: 50 IMPLEMENTED, 47 PARTIAL, 9 BLOCKED, 0 ACCEPTED. Exit gate NO_GO.
* Items that cannot be closed inside a repository (owner, licence, macOS, fleet, hardware, signing keys, pk_core, independent review) are BLOCKED with the input named, never marked done.
* The checklist's completion standard ("implementation, negative-path behaviour, tests, operational visibility and release evidence") is met only by the IMPLEMENTED rows, and even those await acceptance.
