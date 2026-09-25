# Security model

INV-41 enforces **explicit, least-authority object references at the Python API boundary**. An `Authority` is the root minting capability for one independent domain. Its immutable bootstrap policy limits which resource/operation pairs can be granted. `Holder` objects are immutable and accept only authentic references from the same domain. `Reference.attenuate()` can preserve or remove operations but cannot add them. `Membrane` objects revoke every still-live reference in their descendant set, including attenuated and nested-wrapped descendants.

## Trust boundary

This package is **not** a hostile-code sandbox for arbitrary code running in the same Python interpreter. Python reflection, debugger access, native extensions, unsafe FFI, process-memory access, or interpreter compromise can bypass Python-level encapsulation. Untrusted workloads require a stronger isolation layer such as a capability-aware language runtime, separate OS process with restricted handles, Wasm sandbox, microVM, VM, or hardware capability mechanism.

## Security-sensitive invariants

- No resource-returning global registry exists.
- Direct `Reference` and `Holder` construction is rejected by the supported API.
- References carry an authenticated process-local seal and are immutable/non-serializable.
- Holders reject cross-authority references.
- Grant and attenuation requests fail closed on widening.
- Revoked references cannot be invoked or further delegated.
- Reference tokens are redacted from `repr` output.

## 4.3.0 additions

The design rationale and invariants are in **ADR-0001** (`docs/ADR-0001-explicit-capabilities.md`); threats, controls and their tests in `docs/THREAT_MODEL.md`. 4.3.0 adds: identifier limits and control-character rejection, explicit non-serializability of `Authority`/`Holder`/`Membrane` (4.2.0 refused pickling them only incidentally, because of an internal `mappingproxy`), stable error codes, a tamper-evident audit chain, signed transactional configuration, identity adapters, a process-isolation tier with an opaque-handle bridge, and security-control mutation testing. Same-interpreter hostile code remains out of scope (waiver WVR-001).

## Reporting

Treat bypass of any invariant above (SEV1 per `OWNERS.json`; vulnerability SLA in `docs/OPERATIONS.md`), unexpected authority widening, revocation escape, or cross-domain acceptance as a security defect. Do not include live secrets, bearer credentials, or production capability tokens in a report.
