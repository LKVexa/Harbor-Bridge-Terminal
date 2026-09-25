# INV-27 Unikernel Execution — Missing-Component Implementation Checklist

**Repository baseline:** v4.2.0 hardened  
**Source audit:** `AUDIT_REPORT.md` dated 2026-09-23  
**Missing components covered:** 94 / 94  
**Purpose:** engineering execution plan and production-exit evidence checklist.

> Completion rule: a checkbox is complete only when the implementation/artifact exists **and** the referenced verification evidence is reproducible from the repository/release pipeline. Documentation-only completion is insufficient for controls that require executable enforcement.

## Priority definitions

- **P0 — Security/semantic release blocker:** the core unikernel seal/isolation claim or a fundamental trust boundary is not established without it.
- **P1 — Production-readiness blocker:** required for reliable production operation/certification but may build on P0 foundations.
- **P2 — Governance/maturity blocker:** required for a professional production program and formal exit gate, but generally not the first code-path dependency.

## Global acceptance gates — apply to every component

- [ ] Implementation is merged with code/document review by the accountable owner and the relevant security/architecture/operations reviewer(s).
- [ ] All new schemas/configs/policies are versioned, strictly validated, and documented with migration/compatibility behavior.
- [ ] Positive, negative, boundary, and failure-path tests pass in CI; mandatory tests do not skip.
- [ ] Machine-readable evidence is generated and linked from the RTM for the applicable Cxxx requirements.
- [ ] The repository-local production gate reports PASS for this component with no unexpired P0/P1 waiver masking the gap.
- [ ] Operational/runbook/observability changes required to support the component are deployed and exercised in a non-production environment.

---

# A. Critical execution & seal verification

## MC-001 — Real unikernel binary parser/inspector

**Priority:** P0  
**Audit finding:** (`C034`, `C045`, `C081`, `C082`). `linked_syscalls` is caller-supplied metadata; the code does not inspect an ELF/PE/other unikernel image to derive linked imports/syscalls.  
**Risk:** Without this component, INV-27 can accept claimed metadata as fact or execute without an independently verified isolation boundary, undermining the core seal guarantee.  
**Suggested blockers/dependencies:** none; may begin immediately.  
**Mapped INV-27 requirements:**

- `C034` — Validate configuration before activation and fail closed on security-critical errors.
- `C045` — Verify signatures, digests, provenance, and approved versions for executable or policy artifacts consumed by Unikernel execution.
- `C081` — Create unit tests for deterministic Unikernel execution logic and state transitions.
- `C082` — Create contract tests for every public Unikernel execution interface.

### Component-specific engineering checklist

- [ ] Define the supported executable formats and architectures (at minimum the exact formats accepted by production), including magic, class/word-size, endianness, machine type, ABI, segment/section table rules, and maximum file/section/symbol counts.
- [ ] Implement parsing from immutable image bytes or a read-only file descriptor; never accept caller-supplied `linked_syscalls` as authoritative evidence.
- [ ] Extract imports, exported/undefined symbols, relocation targets, dynamic-section records, notes, build IDs, and platform-specific metadata needed to infer the linked syscall/capability surface.
- [ ] Normalize observed syscall/capability identifiers into a canonical vocabulary and preserve raw evidence for forensic review.
- [ ] Reject malformed, truncated, overlapping, integer-overflowing, recursively nested, or resource-amplifying structures before semantic verification.
- [ ] Enforce parser CPU/memory/input-size budgets and deterministic error codes so a malicious image cannot turn admission into a denial-of-service primitive.
- [ ] Bind parser output to the image digest, parser version, architecture, and exact byte length to prevent TOCTOU substitution.
- [ ] Add golden fixtures for valid images and adversarial fixtures for malformed headers, duplicate sections, corrupt relocation tables, symbol bombs, and architecture spoofing.

### Cross-cutting hardening / verification gates

- [ ] Define the trust boundary explicitly: which inputs are untrusted, which facts must be derived independently, and which external attestations are trusted only after cryptographic verification.
- [ ] Implement fail-closed behavior for unknown versions, incomplete evidence, unsupported formats/backends, parser errors, or ambiguous facts; no security-critical `unknown` state may silently become allow.
- [ ] Use immutable/content-addressed objects across verify-to-execute handoff to eliminate path substitution and TOCTOU gaps.
- [ ] Add negative tests for malicious inputs plus an end-to-end test proving a rejected artifact causes zero VMM/device/network side effects.
- [ ] Emit machine-readable evidence containing verifier version, policy/config revision, image digest, decision/reason code, and exact observed facts used by the decision.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-001` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-001`.
- [ ] RTM entry linking `MC-001` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-001` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-002 — Independent single-address-space proof

**Priority:** P0  
**Audit finding:** (`C011`, `C034`, `C041`, `C046`). `single_address_space` is a supplied boolean, not a property proven from the executable/image format.  
**Risk:** Without this component, INV-27 can accept claimed metadata as fact or execute without an independently verified isolation boundary, undermining the core seal guarantee.  
**Suggested blockers/dependencies:** `MC-001`  
**Mapped INV-27 requirements:**

- `C011` — Translate the source function of Unikernel execution — Application plus only required OS primitives — into testable SHALL-level requirements.
- `C034` — Validate configuration before activation and fail closed on security-critical errors.
- `C041` — Threat-model Unikernel execution against malicious tenants, compromised workloads, hostile inputs, supply-chain compromise, and control-plane abuse.
- `C046` — Enforce tenant/workload isolation across Unikernel execution execution, memory, state, network, and device boundaries as applicable.

### Component-specific engineering checklist

- [ ] Write a precise, format-specific definition of what constitutes a single-address-space unikernel for each supported toolchain/image format.
- [ ] Identify binary evidence that demonstrates one application address space: entry model, absence of process-loader facilities, runtime metadata, and toolchain-specific markers.
- [ ] Implement a proof function that derives the result from parsed image facts and signed build attestations; remove the caller-controlled boolean from the trust boundary.
- [ ] Require positive evidence, not merely absence of a known bad symbol, and fail closed for unknown toolchains or incomplete metadata.
- [ ] Record proof type, toolchain-specific verifier version, evidence locations, and confidence class in the seal evidence.
- [ ] Create counterexample fixtures containing process creation/runtime loader support that previously could have claimed `single_address_space=True`.
- [ ] Verify that stripping symbols does not bypass the proof by relying on stable format/runtime evidence or trusted provenance rather than debug symbols alone.

### Cross-cutting hardening / verification gates

- [ ] Define the trust boundary explicitly: which inputs are untrusted, which facts must be derived independently, and which external attestations are trusted only after cryptographic verification.
- [ ] Implement fail-closed behavior for unknown versions, incomplete evidence, unsupported formats/backends, parser errors, or ambiguous facts; no security-critical `unknown` state may silently become allow.
- [ ] Use immutable/content-addressed objects across verify-to-execute handoff to eliminate path substitution and TOCTOU gaps.
- [ ] Add negative tests for malicious inputs plus an end-to-end test proving a rejected artifact causes zero VMM/device/network side effects.
- [ ] Emit machine-readable evidence containing verifier version, policy/config revision, image digest, decision/reason code, and exact observed facts used by the decision.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-002` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-002`.
- [ ] RTM entry linking `MC-002` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-002` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-003 — Independent dynamic-loading / fork / exec detection

**Priority:** P0  
**Audit finding:** (`C041-C046`). `features` is caller-supplied; the implementation does not inspect symbols, relocations, runtime sections, imports, or toolchain metadata to prove these capabilities absent.  
**Risk:** Without this component, INV-27 can accept claimed metadata as fact or execute without an independently verified isolation boundary, undermining the core seal guarantee.  
**Suggested blockers/dependencies:** `MC-001`  
**Mapped INV-27 requirements:**

- `C041` — Threat-model Unikernel execution against malicious tenants, compromised workloads, hostile inputs, supply-chain compromise, and control-plane abuse.
- `C042` — Apply least privilege to every identity and capability used by Unikernel execution.
- `C043` — Eliminate ambient filesystem, network, device, kernel, and secret authority wherever Unikernel execution permits.
- `C044` — Authenticate nodes, peers, artifacts, providers, and control-plane actors before trust is granted.
- `C045` — Verify signatures, digests, provenance, and approved versions for executable or policy artifacts consumed by Unikernel execution.
- `C046` — Enforce tenant/workload isolation across Unikernel execution execution, memory, state, network, and device boundaries as applicable.

### Component-specific engineering checklist

- [ ] Define a disallowed capability taxonomy covering fork/clone/process creation, exec/image replacement, runtime dynamic loading, shell/debug entry paths, ptrace/debug controls, and equivalent toolchain-specific mechanisms.
- [ ] Derive the capability set from imports, relocation targets, runtime sections, linked libraries/modules, compiler metadata, and approved toolchain attestations rather than the `features` field.
- [ ] Handle aliases and platform equivalents (for example `clone`, `posix_spawn`, loader stubs, module loaders, JIT/plugin APIs) through versioned detection rules.
- [ ] Detect statically linked implementations and wrapper symbols where possible; document residual blind spots and require attestation when byte-level proof is insufficient.
- [ ] Fail closed on unknown dynamic-linker metadata or unsupported runtime features.
- [ ] Emit the exact evidence location that triggered rejection so operators can reproduce the finding.
- [ ] Add evasive fixtures using symbol casing, prefixes, stripped names, indirect relocations, dead-code sections, and manifest omissions.

### Cross-cutting hardening / verification gates

- [ ] Define the trust boundary explicitly: which inputs are untrusted, which facts must be derived independently, and which external attestations are trusted only after cryptographic verification.
- [ ] Implement fail-closed behavior for unknown versions, incomplete evidence, unsupported formats/backends, parser errors, or ambiguous facts; no security-critical `unknown` state may silently become allow.
- [ ] Use immutable/content-addressed objects across verify-to-execute handoff to eliminate path substitution and TOCTOU gaps.
- [ ] Add negative tests for malicious inputs plus an end-to-end test proving a rejected artifact causes zero VMM/device/network side effects.
- [ ] Emit machine-readable evidence containing verifier version, policy/config revision, image digest, decision/reason code, and exact observed facts used by the decision.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-003` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-003`.
- [ ] RTM entry linking `MC-003` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-003` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-004 — Cryptographic image identity

**Priority:** P0  
**Audit finding:** (`C044-C045`). No content digest is required or bound to the seal record, so the admitted evidence is not cryptographically tied to exact image bytes.  
**Risk:** Without this component, INV-27 can accept claimed metadata as fact or execute without an independently verified isolation boundary, undermining the core seal guarantee.  
**Suggested blockers/dependencies:** `MC-006`  
**Mapped INV-27 requirements:**

- `C044` — Authenticate nodes, peers, artifacts, providers, and control-plane actors before trust is granted.
- `C045` — Verify signatures, digests, provenance, and approved versions for executable or policy artifacts consumed by Unikernel execution.

### Component-specific engineering checklist

- [ ] Choose and document the canonical content-identity algorithm (for example SHA-256 or stronger approved digest) and digest domain: exact image bytes plus explicitly versioned canonical manifest bytes.
- [ ] Compute the digest inside the trusted admission path before any semantic parsing and verify it again immediately before VMM handoff or use an immutable content-addressed handle.
- [ ] Add digest fields to `PK_UNIKERNEL_IMAGE` and the immutable seal evidence, including algorithm identifier, byte length, and canonical representation version.
- [ ] Reject missing, malformed, unsupported, or mismatched digests with stable machine-readable failure codes.
- [ ] Use constant-time comparison where digest comparison is security sensitive and avoid normalizing executable bytes prior to hashing.
- [ ] Store/propagate the digest as the primary image identity through lifecycle, logs, metrics, audit ledger, and runtime instance records.
- [ ] Test byte-for-byte mutation, manifest mutation, truncation, appended data, and TOCTOU replacement between verify and run.

### Cross-cutting hardening / verification gates

- [ ] Define the trust boundary explicitly: which inputs are untrusted, which facts must be derived independently, and which external attestations are trusted only after cryptographic verification.
- [ ] Implement fail-closed behavior for unknown versions, incomplete evidence, unsupported formats/backends, parser errors, or ambiguous facts; no security-critical `unknown` state may silently become allow.
- [ ] Use immutable/content-addressed objects across verify-to-execute handoff to eliminate path substitution and TOCTOU gaps.
- [ ] Add negative tests for malicious inputs plus an end-to-end test proving a rejected artifact causes zero VMM/device/network side effects.
- [ ] Emit machine-readable evidence containing verifier version, policy/config revision, image digest, decision/reason code, and exact observed facts used by the decision.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-004` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-004`.
- [ ] RTM entry linking `MC-004` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-004` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-005 — Signature and provenance verification

**Priority:** P0  
**Audit finding:** (`C044-C045`). No signature, certificate/key identity, SBOM/provenance attestation, transparency evidence, or approved-toolchain attestation verifier exists.  
**Risk:** Without this component, INV-27 can accept claimed metadata as fact or execute without an independently verified isolation boundary, undermining the core seal guarantee.  
**Suggested blockers/dependencies:** `MC-004`, `MC-006`, `MC-088`  
**Mapped INV-27 requirements:**

- `C044` — Authenticate nodes, peers, artifacts, providers, and control-plane actors before trust is granted.
- `C045` — Verify signatures, digests, provenance, and approved versions for executable or policy artifacts consumed by Unikernel execution.

### Component-specific engineering checklist

- [ ] Define accepted signature envelope(s), key types, trust roots, certificate/identity constraints, and signature algorithm policy.
- [ ] Implement verification of artifact signatures over the canonical image identity and seal manifest; reject unsigned artifacts unless an explicitly governed non-production policy allows them.
- [ ] Verify provenance attestations describing builder identity, source revision, toolchain version, build parameters, reproducibility status, and subject digest.
- [ ] Verify SBOM subject digests and optionally transparency-log inclusion/consistency proofs where the selected supply-chain system supports them.
- [ ] Implement key rotation, revocation, expiry, clock-skew handling, trust-root rollover, and emergency distrust.
- [ ] Enforce an approved-toolchain allowlist keyed by immutable identity/version/digest rather than free-form toolchain name.
- [ ] Add negative tests for revoked/expired keys, wrong subject digest, signature wrapping/substitution, stale provenance, unknown builder, and mismatched SBOM.

### Cross-cutting hardening / verification gates

- [ ] Define the trust boundary explicitly: which inputs are untrusted, which facts must be derived independently, and which external attestations are trusted only after cryptographic verification.
- [ ] Implement fail-closed behavior for unknown versions, incomplete evidence, unsupported formats/backends, parser errors, or ambiguous facts; no security-critical `unknown` state may silently become allow.
- [ ] Use immutable/content-addressed objects across verify-to-execute handoff to eliminate path substitution and TOCTOU gaps.
- [ ] Add negative tests for malicious inputs plus an end-to-end test proving a rejected artifact causes zero VMM/device/network side effects.
- [ ] Emit machine-readable evidence containing verifier version, policy/config revision, image digest, decision/reason code, and exact observed facts used by the decision.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-005` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-005`.
- [ ] RTM entry linking `MC-005` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-005` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-006 — Seal-manifest parser and schema implementation

**Priority:** P0  
**Audit finding:** (`C021-C022`, `C026`, `C029`). `PK_UNIKERNEL_IMAGE/1` is a string label; no JSON/CBOR/Protobuf/WIT schema, parser, canonicalization rules, validation fixture, or compatibility implementation is present.  
**Risk:** Without this component, INV-27 can accept claimed metadata as fact or execute without an independently verified isolation boundary, undermining the core seal guarantee.  
**Suggested blockers/dependencies:** none; may begin immediately.  
**Mapped INV-27 requirements:**

- `C021` — Enumerate every API, WIT contract, RPC, event, file, device, hypervisor, or control-plane boundary exposed by Unikernel execution.
- `C022` — Use versioned typed schemas for all externally visible Unikernel execution contracts.
- `C026` — Define structured failure codes and machine-readable error details for Unikernel execution.
- `C029` — Provide reference examples and conformance fixtures for Unikernel execution.

### Component-specific engineering checklist

- [ ] Select a concrete manifest encoding and canonicalization strategy (for example canonical JSON/CBOR or a versioned Protobuf/WIT schema) and define `PK_UNIKERNEL_IMAGE/1` as an actual schema artifact.
- [ ] Model image identity, digest, architecture, entry point, declared syscall/capability set, toolchain identity, provenance references, signatures, compatibility version, and optional extensions with strict types and bounds.
- [ ] Define unknown-field behavior, duplicate-key behavior, Unicode normalization, number representation, ordering/canonicalization, and maximum nesting/collection sizes.
- [ ] Generate or implement a parser that validates syntax and semantics before constructing internal objects; do not pass unvalidated dictionaries to security logic.
- [ ] Define version negotiation and forward/backward compatibility rules, including how unsupported major/minor versions fail.
- [ ] Provide canonical valid/invalid fixtures and round-trip/canonicalization vectors for every supported schema version.
- [ ] Sign the canonical representation or an explicit detached digest so parser differences cannot change the authenticated meaning.

### Cross-cutting hardening / verification gates

- [ ] Define the trust boundary explicitly: which inputs are untrusted, which facts must be derived independently, and which external attestations are trusted only after cryptographic verification.
- [ ] Implement fail-closed behavior for unknown versions, incomplete evidence, unsupported formats/backends, parser errors, or ambiguous facts; no security-critical `unknown` state may silently become allow.
- [ ] Use immutable/content-addressed objects across verify-to-execute handoff to eliminate path substitution and TOCTOU gaps.
- [ ] Add negative tests for malicious inputs plus an end-to-end test proving a rejected artifact causes zero VMM/device/network side effects.
- [ ] Emit machine-readable evidence containing verifier version, policy/config revision, image digest, decision/reason code, and exact observed facts used by the decision.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-006` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-006`.
- [ ] RTM entry linking `MC-006` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-006` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-007 — Actual unikernel boot/execution adapter

**Priority:** P0  
**Audit finding:** (`C011`, `C021`, `C030`, `C031`, `C040`). `run()` constructs an in-memory Python object; it does not launch a unikernel through a hypervisor/VMM/runtime.  
**Risk:** Without this component, INV-27 can accept claimed metadata as fact or execute without an independently verified isolation boundary, undermining the core seal guarantee.  
**Suggested blockers/dependencies:** `MC-001`, `MC-002`, `MC-003`, `MC-004`, `MC-005`, `MC-006`, `MC-009`, `MC-010`, `MC-023`, `MC-024`, `MC-025`, `MC-026`, `MC-029`  
**Mapped INV-27 requirements:**

- `C011` — Translate the source function of Unikernel execution — Application plus only required OS primitives — into testable SHALL-level requirements.
- `C021` — Enumerate every API, WIT contract, RPC, event, file, device, hypervisor, or control-plane boundary exposed by Unikernel execution.
- `C030` — Create automated integration tests proving Unikernel execution interoperates with adjacent architectural layers.
- `C031` — Select and pin approved implementations, versions, or specifications for Unikernel execution: Unikernels.
- `C040` — Provide a deterministic bootstrap path from an empty node/environment to healthy Unikernel execution operation.

### Component-specific engineering checklist

- [ ] Define an execution-adapter interface that accepts only a verified immutable image handle plus a seal record and returns a strongly typed instance identity/state.
- [ ] Implement at least one real backend for the target platform (for example KVM/Firecracker, QEMU, Hyper-V, Xen, or another approved VMM/runtime) rather than constructing a Python object.
- [ ] Create the VM/microVM, allocate bounded vCPU/memory, attach only approved devices, set the kernel/boot image, and launch through a documented boot contract.
- [ ] Pass the verified content-addressed image object to the VMM without reopening an attacker-controlled path; enforce digest equality at handoff.
- [ ] Implement boot deadline, startup health criteria, failure teardown, idempotent stop, forced termination, and resource reclamation.
- [ ] Persist runtime instance metadata: instance ID, tenant/workload, image digest, VMM/backend version, host identity, seal ID, start/stop timestamps, and terminal reason.
- [ ] Ensure the adapter cannot run if verification evidence is absent, stale, mismatched, or created under an incompatible policy revision.
- [ ] Provide integration fixtures that boot a minimal known-good unikernel and prove a rejected image never reaches the VMM start call.

### Cross-cutting hardening / verification gates

- [ ] Define the trust boundary explicitly: which inputs are untrusted, which facts must be derived independently, and which external attestations are trusted only after cryptographic verification.
- [ ] Implement fail-closed behavior for unknown versions, incomplete evidence, unsupported formats/backends, parser errors, or ambiguous facts; no security-critical `unknown` state may silently become allow.
- [ ] Use immutable/content-addressed objects across verify-to-execute handoff to eliminate path substitution and TOCTOU gaps.
- [ ] Add negative tests for malicious inputs plus an end-to-end test proving a rejected artifact causes zero VMM/device/network side effects.
- [ ] Emit machine-readable evidence containing verifier version, policy/config revision, image digest, decision/reason code, and exact observed facts used by the decision.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-007` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-007`.
- [ ] RTM entry linking `MC-007` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-007` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-008 — Entry-point/boot-contract enforcement

**Priority:** P0  
**Audit finding:** (`C021-C022`, `C034`). The contract says the component owns the image entry-point and boot contract, but no entry-point structure, validator, handoff protocol, or boot-state verification exists.  
**Risk:** Without this component, INV-27 can accept claimed metadata as fact or execute without an independently verified isolation boundary, undermining the core seal guarantee.  
**Suggested blockers/dependencies:** `MC-006`, `MC-007`  
**Mapped INV-27 requirements:**

- `C021` — Enumerate every API, WIT contract, RPC, event, file, device, hypervisor, or control-plane boundary exposed by Unikernel execution.
- `C022` — Use versioned typed schemas for all externally visible Unikernel execution contracts.
- `C034` — Validate configuration before activation and fail closed on security-critical errors.

### Component-specific engineering checklist

- [ ] Define a versioned boot-contract schema covering entry point, load address/format, command-line or boot-info structure, memory-map expectations, initial register state, required devices, and readiness signal.
- [ ] Derive/validate the executable entry point from the image format and compare it with signed manifest/provenance claims.
- [ ] Validate load ranges for alignment, overlap, executable/writable permissions, reserved regions, and architecture-specific canonical address rules.
- [ ] Specify how runtime configuration is injected without creating ambient filesystem or shell authority (for example read-only config device, kernel args, or measured shared memory).
- [ ] Implement a boot-state handshake proving the expected image reached the expected initialization milestone before marking the instance `running`.
- [ ] Reject entry points into non-executable/unmapped regions, ambiguous multi-entry images, or manifests that disagree with parsed binary headers.
- [ ] Capture boot-contract version and validated values in seal/instance evidence and test incompatible-version behavior.

### Cross-cutting hardening / verification gates

- [ ] Define the trust boundary explicitly: which inputs are untrusted, which facts must be derived independently, and which external attestations are trusted only after cryptographic verification.
- [ ] Implement fail-closed behavior for unknown versions, incomplete evidence, unsupported formats/backends, parser errors, or ambiguous facts; no security-critical `unknown` state may silently become allow.
- [ ] Use immutable/content-addressed objects across verify-to-execute handoff to eliminate path substitution and TOCTOU gaps.
- [ ] Add negative tests for malicious inputs plus an end-to-end test proving a rejected artifact causes zero VMM/device/network side effects.
- [ ] Emit machine-readable evidence containing verifier version, policy/config revision, image digest, decision/reason code, and exact observed facts used by the decision.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-008` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-008`.
- [ ] RTM entry linking `MC-008` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-008` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-009 — Hypervisor isolation integration

**Priority:** P0  
**Audit finding:** (`C030`, `C046`, `C083-C084`). No Firecracker/QEMU/KVM/Hyper-V/Xen/other VMM integration, VM creation, memory map, vCPU, device, interrupt, or teardown implementation is present.  
**Risk:** Without this component, INV-27 can accept claimed metadata as fact or execute without an independently verified isolation boundary, undermining the core seal guarantee.  
**Suggested blockers/dependencies:** `MC-007`, `MC-029`  
**Mapped INV-27 requirements:**

- `C030` — Create automated integration tests proving Unikernel execution interoperates with adjacent architectural layers.
- `C046` — Enforce tenant/workload isolation across Unikernel execution execution, memory, state, network, and device boundaries as applicable.
- `C083` — Create integration tests with every supported adjacent layer and execution tier.
- `C084` — Create compatibility tests across supported CPU architectures, runtimes, hypervisors, providers, and protocol versions relevant to Unikernel execution.

### Component-specific engineering checklist

- [ ] Select and pin the supported hypervisor/VMM backend(s), host kernel/firmware prerequisites, and feature baseline for each architecture.
- [ ] Implement VM creation with explicit vCPU topology, memory size/map, privilege mode, interrupt controller, timer, boot source, and teardown semantics.
- [ ] Use least-privilege VMM process/service credentials; constrain host filesystem/device/network access with OS sandboxing where supported.
- [ ] Configure memory isolation and prevent host/guest writable aliasing outside explicitly designed shared-memory channels.
- [ ] Configure CPU feature exposure to a documented allowlist and mask unsafe/unsupported features consistently across migration/failover targets.
- [ ] Implement deterministic cleanup for partial creation failures so leaked TAP devices, file descriptors, VM handles, memory mappings, or cgroups cannot accumulate.
- [ ] Expose VMM/backend version and effective isolation configuration in runtime evidence.
- [ ] Create integration tests that inspect the backend configuration and prove forbidden device/network/storage attachments cannot be introduced by untrusted metadata.

### Cross-cutting hardening / verification gates

- [ ] Define the trust boundary explicitly: which inputs are untrusted, which facts must be derived independently, and which external attestations are trusted only after cryptographic verification.
- [ ] Implement fail-closed behavior for unknown versions, incomplete evidence, unsupported formats/backends, parser errors, or ambiguous facts; no security-critical `unknown` state may silently become allow.
- [ ] Use immutable/content-addressed objects across verify-to-execute handoff to eliminate path substitution and TOCTOU gaps.
- [ ] Add negative tests for malicious inputs plus an end-to-end test proving a rejected artifact causes zero VMM/device/network side effects.
- [ ] Emit machine-readable evidence containing verifier version, policy/config revision, image digest, decision/reason code, and exact observed facts used by the decision.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-009` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-009`.
- [ ] RTM entry linking `MC-009` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-009` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-010 — Device/network/storage boundary enforcement

**Priority:** P0  
**Audit finding:** (`C042-C043`, `C046`). No concrete deny-by-default device model, network capability, block/storage access, MMIO/I/O-port, or filesystem authority configuration is implemented.  
**Risk:** Without this component, INV-27 can accept claimed metadata as fact or execute without an independently verified isolation boundary, undermining the core seal guarantee.  
**Suggested blockers/dependencies:** `MC-009`, `MC-025`, `MC-029`  
**Mapped INV-27 requirements:**

- `C042` — Apply least privilege to every identity and capability used by Unikernel execution.
- `C043` — Eliminate ambient filesystem, network, device, kernel, and secret authority wherever Unikernel execution permits.
- `C046` — Enforce tenant/workload isolation across Unikernel execution execution, memory, state, network, and device boundaries as applicable.

### Component-specific engineering checklist

- [ ] Define a deny-by-default capability model for virtual devices, network interfaces, storage/block devices, filesystems, MMIO ranges, I/O ports, shared memory, entropy, console, and host services.
- [ ] Represent each allowed attachment as an explicit typed capability bound to tenant/workload/image digest and policy revision.
- [ ] Implement network attachment with explicit namespace/vSwitch/segment, MAC/IP policy, egress/ingress filters, and no implicit host networking.
- [ ] Implement storage attachment with immutable/read-only defaults, explicit writable volumes, size limits, discard/flush semantics, encryption requirements, and tenant ownership checks.
- [ ] Disable shell/console/debug devices in production unless a separately authorized break-glass profile is selected and fully audited.
- [ ] Validate MMIO/I/O-port ranges and device IDs against backend policy; reject overlap or undeclared passthrough.
- [ ] Require IOMMU/isolation controls for passthrough devices and refuse unsafe host configurations.
- [ ] Test that omitted capabilities produce no access and that malicious manifests cannot escalate by naming host paths/devices directly.

### Cross-cutting hardening / verification gates

- [ ] Define the trust boundary explicitly: which inputs are untrusted, which facts must be derived independently, and which external attestations are trusted only after cryptographic verification.
- [ ] Implement fail-closed behavior for unknown versions, incomplete evidence, unsupported formats/backends, parser errors, or ambiguous facts; no security-critical `unknown` state may silently become allow.
- [ ] Use immutable/content-addressed objects across verify-to-execute handoff to eliminate path substitution and TOCTOU gaps.
- [ ] Add negative tests for malicious inputs plus an end-to-end test proving a rejected artifact causes zero VMM/device/network side effects.
- [ ] Emit machine-readable evidence containing verifier version, policy/config revision, image digest, decision/reason code, and exact observed facts used by the decision.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-010` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-010`.
- [ ] RTM entry linking `MC-010` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-010` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

# B. Architecture, requirements & governance

## MC-011 — Upstream master prompt corpus `MASTER.md`

**Priority:** P2  
**Audit finding:** The supplied README previously claimed it was included; it is absent.  
**Risk:** Without this artifact, production expectations and accountability are ambiguous, making implementation and certification non-repeatable.  
**Suggested blockers/dependencies:** none; may begin immediately.  
**Mapped INV-27 requirements:** repository-integrity gap identified by the v4.2.0 audit (not tied to a single Cxxx item).

### Component-specific engineering checklist

- [ ] Locate the authoritative upstream source for the 100-item master prompt corpus and establish whether it is normative, historical, or generated.
- [ ] Recover or regenerate `MASTER.md` without inventing missing source content; preserve provenance, source revision, and generation method.
- [ ] Add a content digest and version header so downstream repositories can detect prompt-corpus drift.
- [ ] Cross-check every C001-C100 requirement against the recovered corpus and document intentional deviations.
- [ ] Update README references and repository verification so a declared-required `MASTER.md` cannot silently disappear in future packaging.
- [ ] If the corpus is intentionally external, replace the missing-file expectation with a pinned external source identifier and an offline snapshot policy.

### Cross-cutting hardening / verification gates

- [ ] Use stable document/requirement IDs and place the artifact under version control with owner, status, last-review date, and change history.
- [ ] Write normative statements so each mandatory requirement has one objectively testable verification method and an evidence location.
- [ ] Cross-link the artifact into the RTM and production gate; documentation completion without traceability/evidence is not sufficient.
- [ ] Require security/architecture/operations review appropriate to the artifact and record approval identity/date.
- [ ] Add a freshness/review rule so stale governance artifacts become BLOCKED rather than being treated as permanently valid.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-011` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-011`.
- [ ] RTM entry linking `MC-011` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-011` PASS for the exact source/build digest being released.

### Definition of done

- [ ] The artifact is authoritative, versioned, owned, reviewed, and referenced by automated verification rather than existing as disconnected prose.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-012 — Accountable owner and escalation record

**Priority:** P2  
**Audit finding:** (`C009`). No owner, on-call team, escalation contact, or RACI artifact exists.  
**Risk:** Without this artifact, production expectations and accountability are ambiguous, making implementation and certification non-repeatable.  
**Suggested blockers/dependencies:** none; may begin immediately.  
**Mapped INV-27 requirements:**

- `C009` — Assign an accountable owner and escalation path for Unikernel execution.

### Component-specific engineering checklist

- [ ] Name a single accountable service/component owner and at least one backup/on-call owning group.
- [ ] Define responsibilities for architecture, code, production operations, security triage, release approval, and incident command using a RACI/DACI-style matrix.
- [ ] Document paging/escalation routes, severity handoff expectations, business-hours vs 24x7 coverage, and external dependency escalation paths.
- [ ] Store ownership in a machine-readable file (for example `OWNERS.yaml`/CODEOWNERS plus runbook metadata) validated in CI.
- [ ] Require owner approval for changes to security boundaries, production SLOs, supported hypervisors/toolchains, and production gate logic.
- [ ] Add an ownership-review cadence and fail the production exit gate if critical roles are unassigned or stale.

### Cross-cutting hardening / verification gates

- [ ] Use stable document/requirement IDs and place the artifact under version control with owner, status, last-review date, and change history.
- [ ] Write normative statements so each mandatory requirement has one objectively testable verification method and an evidence location.
- [ ] Cross-link the artifact into the RTM and production gate; documentation completion without traceability/evidence is not sufficient.
- [ ] Require security/architecture/operations review appropriate to the artifact and record approval identity/date.
- [ ] Add a freshness/review rule so stale governance artifacts become BLOCKED rather than being treated as permanently valid.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-012` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-012`.
- [ ] RTM entry linking `MC-012` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-012` PASS for the exact source/build digest being released.

### Definition of done

- [ ] The artifact is authoritative, versioned, owned, reviewed, and referenced by automated verification rather than existing as disconnected prose.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-013 — Approved architecture decision record (ADR)

**Priority:** P2  
**Audit finding:** (`C010`). No ADR captures the unikernel technology choice, alternatives, consequences, approval, or status.  
**Risk:** Without this artifact, production expectations and accountability are ambiguous, making implementation and certification non-repeatable.  
**Suggested blockers/dependencies:** none; may begin immediately.  
**Mapped INV-27 requirements:**

- `C010` — Approve an architecture decision record for Unikernel execution, its technologies (Unikernels), and its function (Application plus only required OS primitives).

### Component-specific engineering checklist

- [ ] Create an ADR that states the problem, decision drivers, selected unikernel execution architecture, and the separation between image verification and hypervisor responsibilities.
- [ ] Evaluate credible alternatives such as containers, microVMs, WASI components, process sandboxes, and hybrid designs against isolation, startup, density, tooling, observability, and operational complexity.
- [ ] Record consequences and risks of single-address-space execution, static linking, restricted debugging, device-model choices, and supply-chain trust.
- [ ] Document chosen binary formats, VMM backend strategy, manifest/signature format, trust model, and unsupported deployment modes.
- [ ] Include decision status, approvers, date, supersession links, and measurable conditions that would trigger reconsideration.
- [ ] Link the ADR to the RTM and require updates when architecture-affecting production assumptions change.

### Cross-cutting hardening / verification gates

- [ ] Use stable document/requirement IDs and place the artifact under version control with owner, status, last-review date, and change history.
- [ ] Write normative statements so each mandatory requirement has one objectively testable verification method and an evidence location.
- [ ] Cross-link the artifact into the RTM and production gate; documentation completion without traceability/evidence is not sufficient.
- [ ] Require security/architecture/operations review appropriate to the artifact and record approval identity/date.
- [ ] Add a freshness/review rule so stale governance artifacts become BLOCKED rather than being treated as permanently valid.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-013` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-013`.
- [ ] RTM entry linking `MC-013` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-013` PASS for the exact source/build digest being released.

### Definition of done

- [ ] The artifact is authoritative, versioned, owned, reviewed, and referenced by automated verification rather than existing as disconnected prose.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-014 — Normative SHALL-level requirements specification

**Priority:** P1  
**Audit finding:** (`C011-C019`). `CHECKLIST.json` asks for these artifacts, but there is no dedicated normative requirements document covering deployment contexts, failure semantics, capacity, network loss, or precedence rules.  
**Risk:** Without this artifact, production expectations and accountability are ambiguous, making implementation and certification non-repeatable.  
**Suggested blockers/dependencies:** `MC-013`  
**Mapped INV-27 requirements:**

- `C011` — Translate the source function of Unikernel execution — Application plus only required OS primitives — into testable SHALL-level requirements.
- `C012` — Define functional requirements for Unikernel execution across cloud, datacenter, near-edge, and far-edge contexts where applicable.
- `C013` — Define non-functional requirements for latency, availability, durability, consistency, isolation, or determinism as applicable.
- `C014` — Define success, partial success, degraded operation, retryable failure, and terminal failure semantics for Unikernel execution.
- `C015` — Define lifecycle states and legal state transitions managed or exposed by Unikernel execution.
- `C016` — Define versioning and backward-compatibility requirements for Unikernel execution.
- `C017` — Define capacity ceilings, quotas, and fairness semantics relevant to Unikernel execution.
- `C018` — Define behavior when network connectivity is intermittent or absent.
- `C019` — Define precedence rules when Unikernel execution requirements conflict with security, residency, SLO, or cost constraints.

### Component-specific engineering checklist

- [ ] Create a normative requirements specification using RFC 2119/8174-style SHALL/SHOULD/MAY language and stable requirement IDs.
- [ ] Translate the responsibility statement into testable requirements for image verification, single-address-space proof, syscall fidelity, prohibited features, execution handoff, and seal evidence.
- [ ] Specify supported deployment contexts (cloud/datacenter/near-edge/far-edge) and explicitly state where a requirement is not applicable.
- [ ] Define measurable non-functional requirements for availability, admission latency, boot latency, determinism, isolation, durability of evidence, and resource limits.
- [ ] Define success, partial/degraded success, retryable failure, terminal failure, and operator-visible consequences for each major operation.
- [ ] Specify capacity/quota/fairness, disconnected operation, and security/residency/SLO/cost precedence rules.
- [ ] Require each SHALL to have a verification method and traceability entry before it can be marked complete.

### Cross-cutting hardening / verification gates

- [ ] Use stable document/requirement IDs and place the artifact under version control with owner, status, last-review date, and change history.
- [ ] Write normative statements so each mandatory requirement has one objectively testable verification method and an evidence location.
- [ ] Cross-link the artifact into the RTM and production gate; documentation completion without traceability/evidence is not sufficient.
- [ ] Require security/architecture/operations review appropriate to the artifact and record approval identity/date.
- [ ] Add a freshness/review rule so stale governance artifacts become BLOCKED rather than being treated as permanently valid.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-014` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-014`.
- [ ] RTM entry linking `MC-014` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-014` PASS for the exact source/build digest being released.

### Definition of done

- [ ] The artifact is authoritative, versioned, owned, reviewed, and referenced by automated verification rather than existing as disconnected prose.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-015 — Requirements traceability matrix (RTM)

**Priority:** P1  
**Audit finding:** (`C020`). There is no requirement -> design -> implementation -> test -> evidence mapping.  
**Risk:** Without this artifact, production expectations and accountability are ambiguous, making implementation and certification non-repeatable.  
**Suggested blockers/dependencies:** `MC-014`  
**Mapped INV-27 requirements:**

- `C020` — Maintain a requirements traceability matrix from each Unikernel execution requirement to implementation and verification evidence.

### Component-specific engineering checklist

- [ ] Create an RTM with stable rows linking requirement ID -> architecture/design artifact -> implementation symbol/path -> test ID -> evidence artifact -> release/gate result.
- [ ] Populate all C001-C100 items and all additional normative SHALL requirements introduced by the hardened design.
- [ ] Allow one-to-many relationships and explicitly mark `N/A`, `deferred`, or `waived` only with an approved waiver ID and expiry.
- [ ] Automate stale-link detection in CI (missing files/tests/evidence, renamed symbols, unknown requirement IDs).
- [ ] Generate release-specific RTM snapshots so evidence for v4.2.x cannot be silently reused for incompatible later releases.
- [ ] Require every P0/P1 requirement to have passing evidence before the production gate can issue GO.

### Cross-cutting hardening / verification gates

- [ ] Use stable document/requirement IDs and place the artifact under version control with owner, status, last-review date, and change history.
- [ ] Write normative statements so each mandatory requirement has one objectively testable verification method and an evidence location.
- [ ] Cross-link the artifact into the RTM and production gate; documentation completion without traceability/evidence is not sufficient.
- [ ] Require security/architecture/operations review appropriate to the artifact and record approval identity/date.
- [ ] Add a freshness/review rule so stale governance artifacts become BLOCKED rather than being treated as permanently valid.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-015` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-015`.
- [ ] RTM entry linking `MC-015` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-015` PASS for the exact source/build digest being released.

### Definition of done

- [ ] The artifact is authoritative, versioned, owned, reviewed, and referenced by automated verification rather than existing as disconnected prose.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-016 — Formal lifecycle/state-transition specification

**Priority:** P1  
**Audit finding:** (`C014-C015`). Runtime has only a minimal `running`/`stopped` model; no admitted/staged/starting/running/degraded/quarantined/stopping/failed/terminated model or legal transition table exists.  
**Risk:** Without this artifact, production expectations and accountability are ambiguous, making implementation and certification non-repeatable.  
**Suggested blockers/dependencies:** `MC-014`  
**Mapped INV-27 requirements:**

- `C014` — Define success, partial success, degraded operation, retryable failure, and terminal failure semantics for Unikernel execution.
- `C015` — Define lifecycle states and legal state transitions managed or exposed by Unikernel execution.

### Component-specific engineering checklist

- [ ] Define a lifecycle state machine at least covering `received`, `validating`, `rejected`, `admitted`, `staged`, `starting`, `running`, `degraded`, `quarantined`, `stopping`, `stopped`, `failed`, and `terminated` where applicable.
- [ ] Specify legal transitions, initiating actors/events, guard conditions, side effects, timeouts, idempotency semantics, and terminal states.
- [ ] Assign monotonically increasing state revision/epoch data to prevent stale controllers from overwriting newer state.
- [ ] Define crash recovery behavior for each nonterminal state and how reconciliation converges after controller restart.
- [ ] Implement transition validation centrally rather than allowing arbitrary string assignment.
- [ ] Emit a durable reason/evidence reference for every transition, especially rejection, quarantine, failure, and forced termination.
- [ ] Create state-transition property tests covering illegal transitions, repeated commands, concurrent stop/start, and crash/reconcile paths.

### Cross-cutting hardening / verification gates

- [ ] Use stable document/requirement IDs and place the artifact under version control with owner, status, last-review date, and change history.
- [ ] Write normative statements so each mandatory requirement has one objectively testable verification method and an evidence location.
- [ ] Cross-link the artifact into the RTM and production gate; documentation completion without traceability/evidence is not sufficient.
- [ ] Require security/architecture/operations review appropriate to the artifact and record approval identity/date.
- [ ] Add a freshness/review rule so stale governance artifacts become BLOCKED rather than being treated as permanently valid.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-016` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-016`.
- [ ] RTM entry linking `MC-016` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-016` PASS for the exact source/build digest being released.

### Definition of done

- [ ] The artifact is authoritative, versioned, owned, reviewed, and referenced by automated verification rather than existing as disconnected prose.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-017 — Versioning/backward-compatibility policy

**Priority:** P2  
**Audit finding:** (`C016`, `C027`, `C093`). Version numbers exist, but no support window, compatibility rules, deprecation policy, or adjacent-version matrix exists.  
**Risk:** Without this artifact, production expectations and accountability are ambiguous, making implementation and certification non-repeatable.  
**Suggested blockers/dependencies:** `MC-006`, `MC-023`  
**Mapped INV-27 requirements:**

- `C016` — Define versioning and backward-compatibility requirements for Unikernel execution.
- `C027` — Define compatibility behavior when peers use different supported versions.
- `C093` — Maintain a supported-version compatibility matrix for Unikernel execution and adjacent dependencies.

### Component-specific engineering checklist

- [ ] Define semantic versioning rules for repository code, public schemas, seal manifests, evidence records, backend adapters, and configuration schemas.
- [ ] Define supported major/minor release windows, security-fix policy, deprecation notice periods, and end-of-support behavior.
- [ ] Specify wire/schema compatibility rules for N/N-1 (or the selected window), including unknown fields and feature negotiation.
- [ ] Maintain an adjacent-dependency compatibility matrix for `pk_core`, VMM/backend versions, OS/kernel versions, toolchains, and image schema versions.
- [ ] Require explicit migrations for breaking state/config/evidence changes and prohibit silent reinterpretation of existing fields.
- [ ] Test supported mixed-version scenarios and ensure unsupported combinations fail before execution rather than at runtime.

### Cross-cutting hardening / verification gates

- [ ] Use stable document/requirement IDs and place the artifact under version control with owner, status, last-review date, and change history.
- [ ] Write normative statements so each mandatory requirement has one objectively testable verification method and an evidence location.
- [ ] Cross-link the artifact into the RTM and production gate; documentation completion without traceability/evidence is not sufficient.
- [ ] Require security/architecture/operations review appropriate to the artifact and record approval identity/date.
- [ ] Add a freshness/review rule so stale governance artifacts become BLOCKED rather than being treated as permanently valid.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-017` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-017`.
- [ ] RTM entry linking `MC-017` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-017` PASS for the exact source/build digest being released.

### Definition of done

- [ ] The artifact is authoritative, versioned, owned, reviewed, and referenced by automated verification rather than existing as disconnected prose.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-018 — Capacity/quota/fairness policy

**Priority:** P1  
**Audit finding:** (`C017`, `C028`, `C067`, `C069`). No per-tenant quotas, concurrency ceilings, admission tokens, fairness scheduler, or saturation model exists.  
**Risk:** Without this artifact, production expectations and accountability are ambiguous, making implementation and certification non-repeatable.  
**Suggested blockers/dependencies:** `MC-014`, `MC-029`  
**Mapped INV-27 requirements:**

- `C017` — Define capacity ceilings, quotas, and fairness semantics relevant to Unikernel execution.
- `C028` — Document payload, concurrency, queue, connection, or resource limits at Unikernel execution interfaces.
- `C067` — Bound memory growth, queue depth, buffer size, concurrency, and resource fan-out.
- `C069` — Define capacity models and saturation signals that predict when Unikernel execution needs more resources.

### Component-specific engineering checklist

- [ ] Define quota dimensions: admitted images, concurrent/running instances, vCPU, memory, network bandwidth/connections, storage, verification CPU, queue depth, and per-tenant burst limits.
- [ ] Define hierarchical quotas (global/site/environment/tenant/workload) with deterministic precedence and reservation accounting.
- [ ] Implement admission tokens/reservations so verification success does not race with capacity allocation.
- [ ] Define fairness policy (for example weighted fair queueing or explicit priority classes) and starvation bounds.
- [ ] Specify behavior at limits: reject, queue, shed, or preempt; return machine-readable retry guidance where appropriate.
- [ ] Protect control-plane verification resources separately from guest resources so hostile tenants cannot exhaust the verifier.
- [ ] Test exact-limit, one-over-limit, concurrent admission, quota release after failure, and noisy-neighbor scenarios.

### Cross-cutting hardening / verification gates

- [ ] Use stable document/requirement IDs and place the artifact under version control with owner, status, last-review date, and change history.
- [ ] Write normative statements so each mandatory requirement has one objectively testable verification method and an evidence location.
- [ ] Cross-link the artifact into the RTM and production gate; documentation completion without traceability/evidence is not sufficient.
- [ ] Require security/architecture/operations review appropriate to the artifact and record approval identity/date.
- [ ] Add a freshness/review rule so stale governance artifacts become BLOCKED rather than being treated as permanently valid.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-018` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-018`.
- [ ] RTM entry linking `MC-018` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-018` PASS for the exact source/build digest being released.

### Definition of done

- [ ] The artifact is authoritative, versioned, owned, reviewed, and referenced by automated verification rather than existing as disconnected prose.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-019 — Disconnected/intermittent-network behavior specification

**Priority:** P1  
**Audit finding:** (`C018`). No explicit offline admission, cached policy, revocation, reconnect, or stale-trust semantics exist.  
**Risk:** Without this artifact, production expectations and accountability are ambiguous, making implementation and certification non-repeatable.  
**Suggested blockers/dependencies:** `MC-014`, `MC-024`, `MC-046`  
**Mapped INV-27 requirements:**

- `C018` — Define behavior when network connectivity is intermittent or absent.

### Component-specific engineering checklist

- [ ] Classify dependencies required for admission and execution as hard-online, soft-online, or cacheable (identity, policy, attestation, keys, time, placement, telemetry).
- [ ] Define whether new admissions are allowed offline and the maximum acceptable age of cached policy, trust roots, revocation data, and attestations.
- [ ] Define existing-instance behavior during partitions, including whether execution may continue, must quarantine, or must terminate for specific trust changes.
- [ ] Implement monotonic freshness metadata and reject cache rollback/replay to older trust state.
- [ ] Define reconnect reconciliation: refresh policy/revocations, compare epochs, re-evaluate running instances, and resolve conflicting state.
- [ ] Specify trusted-time fallback and clock uncertainty behavior for expiring signatures/certificates.
- [ ] Test partition at each lifecycle phase, stale-cache boundaries, reconnect with revoked image/key, and control-plane divergence.

### Cross-cutting hardening / verification gates

- [ ] Use stable document/requirement IDs and place the artifact under version control with owner, status, last-review date, and change history.
- [ ] Write normative statements so each mandatory requirement has one objectively testable verification method and an evidence location.
- [ ] Cross-link the artifact into the RTM and production gate; documentation completion without traceability/evidence is not sufficient.
- [ ] Require security/architecture/operations review appropriate to the artifact and record approval identity/date.
- [ ] Add a freshness/review rule so stale governance artifacts become BLOCKED rather than being treated as permanently valid.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-019` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-019`.
- [ ] RTM entry linking `MC-019` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-019` PASS for the exact source/build digest being released.

### Definition of done

- [ ] The artifact is authoritative, versioned, owned, reviewed, and referenced by automated verification rather than existing as disconnected prose.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-020 — Security/residency/SLO/cost precedence rules

**Priority:** P1  
**Audit finding:** (`C019`). No conflict-resolution policy or deterministic precedence table exists.  
**Risk:** Without this artifact, production expectations and accountability are ambiguous, making implementation and certification non-repeatable.  
**Suggested blockers/dependencies:** `MC-014`, `MC-042`  
**Mapped INV-27 requirements:**

- `C019` — Define precedence rules when Unikernel execution requirements conflict with security, residency, SLO, or cost constraints.

### Component-specific engineering checklist

- [ ] Create a deterministic precedence table covering at least security policy, legal/residency constraints, integrity, tenant isolation, safety, availability/SLO, performance, cost, and operator override.
- [ ] State non-overridable invariants (for example never run an unverifiable or signature-invalid image) separately from tunable preferences.
- [ ] Define how placement/failover reacts when residency conflicts with capacity or availability requirements.
- [ ] Define how cost optimization is constrained by security/isolation and minimum capacity headroom.
- [ ] Implement policy evaluation that returns the winning rule/constraint and losing alternatives as structured decision evidence.
- [ ] Require break-glass overrides to be scoped, time-bounded, authenticated, authorized, and tamper-evidently audited.
- [ ] Create conflict fixtures proving identical inputs yield identical precedence decisions.

### Cross-cutting hardening / verification gates

- [ ] Use stable document/requirement IDs and place the artifact under version control with owner, status, last-review date, and change history.
- [ ] Write normative statements so each mandatory requirement has one objectively testable verification method and an evidence location.
- [ ] Cross-link the artifact into the RTM and production gate; documentation completion without traceability/evidence is not sufficient.
- [ ] Require security/architecture/operations review appropriate to the artifact and record approval identity/date.
- [ ] Add a freshness/review rule so stale governance artifacts become BLOCKED rather than being treated as permanently valid.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-020` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-020`.
- [ ] RTM entry linking `MC-020` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-020` PASS for the exact source/build digest being released.

### Definition of done

- [ ] The artifact is authoritative, versioned, owned, reviewed, and referenced by automated verification rather than existing as disconnected prose.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

# C. Interfaces & dependencies

## MC-021 — Pinned `pk_core` dependency or vendored core

**Priority:** P0  
**Audit finding:** (`C031`, `C040`, `C083`, `C090`, `C100`). The archive imports `pk_core` but does not contain it, pin it in packaging metadata, or provide an install/bootstrap mechanism.  
**Risk:** Without this interface control, adjacent systems can disagree on meaning, authority, retries, or errors at a security-sensitive boundary.  
**Suggested blockers/dependencies:** none; may begin immediately.  
**Mapped INV-27 requirements:**

- `C031` — Select and pin approved implementations, versions, or specifications for Unikernel execution: Unikernels.
- `C040` — Provide a deterministic bootstrap path from an empty node/environment to healthy Unikernel execution operation.
- `C083` — Create integration tests with every supported adjacent layer and execution tier.
- `C090` — Require machine-readable acceptance evidence before certifying a Unikernel execution release for production.
- `C100` — Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness.

### Component-specific engineering checklist

- [ ] Decide whether `pk_core` is vendored, published as an internal/external package, or replaced by a local implementation; document the source of truth.
- [ ] Pin an exact compatible version or immutable revision plus integrity hash; prohibit floating branches/tags in production builds.
- [ ] Declare the dependency in packaging metadata and provide deterministic offline/online bootstrap behavior.
- [ ] Validate `pk_core` API/version compatibility before importing security-critical contract/gate code and fail with a clear diagnostic.
- [ ] If vendored, preserve upstream license/provenance and add update automation; if external, document repository/package registry availability and outage behavior.
- [ ] Run the 100-check conformance/gate suite in a clean environment using only declared dependencies.
- [ ] Add a repository verification check that fails if the import exists but the dependency cannot be resolved from declared metadata.

### Cross-cutting hardening / verification gates

- [ ] Version every externally visible contract and define compatibility/negotiation behavior before implementation consumers depend on it.
- [ ] Apply strict input bounds, canonicalization, authentication/authorization, timeout, and error semantics at the boundary rather than inside arbitrary callers.
- [ ] Provide golden positive/negative fixtures and run producer/consumer contract tests in CI.
- [ ] Prevent raw/unvalidated dictionaries, tenant-controlled identifiers, or backend-native errors from crossing the trusted internal boundary.
- [ ] Record interface/schema version and correlation/decision IDs in telemetry/evidence for every call.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-021` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-021`.
- [ ] RTM entry linking `MC-021` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-021` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-022 — Python packaging/install metadata

**Priority:** P1  
**Audit finding:** (`C031`, `C040`, `C093`). No `pyproject.toml`/lockfile/wheel metadata or reproducible dependency declaration exists.  
**Risk:** Without this interface control, adjacent systems can disagree on meaning, authority, retries, or errors at a security-sensitive boundary.  
**Suggested blockers/dependencies:** `MC-021`  
**Mapped INV-27 requirements:**

- `C031` — Select and pin approved implementations, versions, or specifications for Unikernel execution: Unikernels.
- `C040` — Provide a deterministic bootstrap path from an empty node/environment to healthy Unikernel execution operation.
- `C093` — Maintain a supported-version compatibility matrix for Unikernel execution and adjacent dependencies.

### Component-specific engineering checklist

- [ ] Add `pyproject.toml` with build backend, project metadata, Python version constraints, package discovery, dependencies, optional dev/test groups, and console entry points where appropriate.
- [ ] Create a fully pinned/hashed lock strategy for runtime and development dependencies and document the resolver/tool used.
- [ ] Build sdist/wheel artifacts in CI and test installation into a clean virtual environment with no repository-path leakage.
- [ ] Define reproducible package contents and exclude caches, secrets, local paths, test artifacts, and undeclared generated files.
- [ ] Add package metadata for license, source repository, issue tracker, supported platforms, and classifiers as applicable.
- [ ] Verify `pip install`/equivalent followed by import, verifier tests, and CLI smoke tests on every supported Python/platform matrix entry.

### Cross-cutting hardening / verification gates

- [ ] Version every externally visible contract and define compatibility/negotiation behavior before implementation consumers depend on it.
- [ ] Apply strict input bounds, canonicalization, authentication/authorization, timeout, and error semantics at the boundary rather than inside arbitrary callers.
- [ ] Provide golden positive/negative fixtures and run producer/consumer contract tests in CI.
- [ ] Prevent raw/unvalidated dictionaries, tenant-controlled identifiers, or backend-native errors from crossing the trusted internal boundary.
- [ ] Record interface/schema version and correlation/decision IDs in telemetry/evidence for every call.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-022` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-022`.
- [ ] RTM entry linking `MC-022` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-022` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-023 — Typed external interface definitions

**Priority:** P1  
**Audit finding:** (`C021-C022`). Interfaces are prose strings only; no WIT/IDL/OpenAPI/Protobuf/schema artifacts are included.  
**Risk:** Without this interface control, adjacent systems can disagree on meaning, authority, retries, or errors at a security-sensitive boundary.  
**Suggested blockers/dependencies:** `MC-006`  
**Mapped INV-27 requirements:**

- `C021` — Enumerate every API, WIT contract, RPC, event, file, device, hypervisor, or control-plane boundary exposed by Unikernel execution.
- `C022` — Use versioned typed schemas for all externally visible Unikernel execution contracts.

### Component-specific engineering checklist

- [ ] Inventory every external boundary and choose an IDL/schema per boundary: admission API, instance API, evidence/audit event, configuration, VMM adapter, and adjacent-plane integration.
- [ ] Define strongly typed request/response/message schemas with explicit field bounds, enums, units, optionality, and version identifiers.
- [ ] Generate language bindings or validators from the schema where practical to avoid duplicated hand-written interpretation.
- [ ] Define canonical serialization, maximum message sizes, recursion/collection limits, and unknown-field behavior.
- [ ] Publish compatibility rules and machine-readable schema artifacts under version control.
- [ ] Add golden wire fixtures and contract tests that validate both acceptance and rejection of malformed/unsupported messages.
- [ ] Ensure security decisions consume validated typed objects only; raw maps/strings must not cross the trust boundary.

### Cross-cutting hardening / verification gates

- [ ] Version every externally visible contract and define compatibility/negotiation behavior before implementation consumers depend on it.
- [ ] Apply strict input bounds, canonicalization, authentication/authorization, timeout, and error semantics at the boundary rather than inside arbitrary callers.
- [ ] Provide golden positive/negative fixtures and run producer/consumer contract tests in CI.
- [ ] Prevent raw/unvalidated dictionaries, tenant-controlled identifiers, or backend-native errors from crossing the trusted internal boundary.
- [ ] Record interface/schema version and correlation/decision IDs in telemetry/evidence for every call.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-023` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-023`.
- [ ] RTM entry linking `MC-023` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-023` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-024 — Authentication implementation

**Priority:** P0  
**Audit finding:** (`C023`, `C044`). No peer/node/artifact/control-plane authentication mechanism is present.  
**Risk:** Without this interface control, adjacent systems can disagree on meaning, authority, retries, or errors at a security-sensitive boundary.  
**Suggested blockers/dependencies:** `MC-023`, `MC-004`, `MC-005`  
**Mapped INV-27 requirements:**

- `C023` — Define authentication requirements at each Unikernel execution boundary.
- `C044` — Authenticate nodes, peers, artifacts, providers, and control-plane actors before trust is granted.

### Component-specific engineering checklist

- [ ] Identify every principal type: control-plane service, node/host agent, operator, build system, artifact signer, tenant/workload identity, and VMM backend.
- [ ] Choose authentication mechanisms per boundary (for example mTLS workload identity, signed tokens, host attestation, artifact signatures) and bind them to stable identities.
- [ ] Implement certificate/token validation including issuer/audience, key usage, expiry, revocation, nonce/replay protection, and trusted-time policy.
- [ ] Mutually authenticate privileged service-to-service links; do not infer trust from network location or tenant-supplied names.
- [ ] Bind authenticated actor identity into every authorization decision and security audit event.
- [ ] Implement credential rotation and trust-root rollover without requiring unsafe global downtime.
- [ ] Test wrong issuer/audience, expired/revoked credentials, stolen/replayed tokens, identity confusion, and downgrade attempts.

### Cross-cutting hardening / verification gates

- [ ] Version every externally visible contract and define compatibility/negotiation behavior before implementation consumers depend on it.
- [ ] Apply strict input bounds, canonicalization, authentication/authorization, timeout, and error semantics at the boundary rather than inside arbitrary callers.
- [ ] Provide golden positive/negative fixtures and run producer/consumer contract tests in CI.
- [ ] Prevent raw/unvalidated dictionaries, tenant-controlled identifiers, or backend-native errors from crossing the trusted internal boundary.
- [ ] Record interface/schema version and correlation/decision IDs in telemetry/evidence for every call.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-024` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-024`.
- [ ] RTM entry linking `MC-024` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-024` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-025 — Authorization/capability model

**Priority:** P0  
**Audit finding:** (`C024`, `C042`). Tenant is a string only; no policy decision, capability token, identity binding, or least-privilege enforcement exists.  
**Risk:** Without this interface control, adjacent systems can disagree on meaning, authority, retries, or errors at a security-sensitive boundary.  
**Suggested blockers/dependencies:** `MC-023`, `MC-024`  
**Mapped INV-27 requirements:**

- `C024` — Define authorization and explicit capability requirements at each Unikernel execution boundary.
- `C042` — Apply least privilege to every identity and capability used by Unikernel execution.

### Component-specific engineering checklist

- [ ] Define a capability/action vocabulary for admit, inspect, execute, stop, quarantine, attach-network, attach-storage, read-evidence, change-policy, and break-glass operations.
- [ ] Create policies that bind authenticated principals to tenant/site/environment-scoped capabilities using default deny.
- [ ] Separate control-plane administrative authority from workload/tenant authority; prevent tenants from requesting host paths, devices, or policies outside delegated scope.
- [ ] Use unforgeable capability handles or server-side authorization checks rather than trusting role strings embedded in request metadata.
- [ ] Add resource ownership/tenant checks to every object lookup and lifecycle mutation.
- [ ] Implement policy decision IDs and record effective grants/denials in the audit ledger without leaking secret policy internals.
- [ ] Test confused-deputy, horizontal/vertical privilege escalation, stale capability, tenant-ID substitution, and break-glass expiry.

### Cross-cutting hardening / verification gates

- [ ] Version every externally visible contract and define compatibility/negotiation behavior before implementation consumers depend on it.
- [ ] Apply strict input bounds, canonicalization, authentication/authorization, timeout, and error semantics at the boundary rather than inside arbitrary callers.
- [ ] Provide golden positive/negative fixtures and run producer/consumer contract tests in CI.
- [ ] Prevent raw/unvalidated dictionaries, tenant-controlled identifiers, or backend-native errors from crossing the trusted internal boundary.
- [ ] Record interface/schema version and correlation/decision IDs in telemetry/evidence for every call.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-025` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-025`.
- [ ] RTM entry linking `MC-025` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-025` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-026 — Timeout/cancellation/retry/idempotency/backpressure contract

**Priority:** P1  
**Audit finding:** (`C025`). No executable semantics or interface metadata define these behaviors.  
**Risk:** Without this interface control, adjacent systems can disagree on meaning, authority, retries, or errors at a security-sensitive boundary.  
**Suggested blockers/dependencies:** `MC-023`  
**Mapped INV-27 requirements:**

- `C025` — Define timeout, cancellation, retry, idempotency, and backpressure semantics for Unikernel execution.

### Component-specific engineering checklist

- [ ] Define per-operation deadlines and cancellation propagation from API boundary through verifier, scheduler, VMM, and cleanup paths.
- [ ] Classify each operation as non-retryable, conditionally retryable, or idempotent and document the exact idempotency key semantics.
- [ ] Use bounded exponential backoff with jitter and retry budgets; never retry integrity/authentication/policy denials automatically.
- [ ] Define server/client behavior when cancellation arrives after side effects begin, including reconciliation responsibilities.
- [ ] Specify queue/backpressure signals, maximum in-flight work, and overload errors with retry hints.
- [ ] Persist or deterministically derive idempotency state for create/start operations so retries cannot produce duplicate VMs.
- [ ] Test timeout at every side-effect boundary, lost response after success, duplicate request IDs, cancellation races, and retry storms.

### Cross-cutting hardening / verification gates

- [ ] Version every externally visible contract and define compatibility/negotiation behavior before implementation consumers depend on it.
- [ ] Apply strict input bounds, canonicalization, authentication/authorization, timeout, and error semantics at the boundary rather than inside arbitrary callers.
- [ ] Provide golden positive/negative fixtures and run producer/consumer contract tests in CI.
- [ ] Prevent raw/unvalidated dictionaries, tenant-controlled identifiers, or backend-native errors from crossing the trusted internal boundary.
- [ ] Record interface/schema version and correlation/decision IDs in telemetry/evidence for every call.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-026` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-026`.
- [ ] RTM entry linking `MC-026` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-026` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-027 — Structured machine-readable failure model

**Priority:** P1  
**Audit finding:** (`C026`). Python exceptions are used; stable failure codes, typed details, retryability, and wire representation are absent.  
**Risk:** Without this interface control, adjacent systems can disagree on meaning, authority, retries, or errors at a security-sensitive boundary.  
**Suggested blockers/dependencies:** `MC-023`, `MC-026`  
**Mapped INV-27 requirements:**

- `C026` — Define structured failure codes and machine-readable error details for Unikernel execution.

### Component-specific engineering checklist

- [ ] Define a stable error namespace with codes for schema invalid, digest mismatch, signature invalid, unsupported architecture, prohibited capability, syscall drift, authn/authz denial, quota, timeout, backend failure, and internal defect.
- [ ] Create a typed error envelope containing code, safe message, retryability, operation, correlation/decision ID, and optional structured details.
- [ ] Map internal exceptions/backend errors to stable public codes without exposing host paths, secrets, stack traces, or tenant-crossing data.
- [ ] Version the error schema and guarantee backward-compatible interpretation within the supported protocol window.
- [ ] Define HTTP/RPC/CLI exit-code mappings consistently and ensure retries are driven by code/metadata rather than string matching.
- [ ] Add snapshot/contract tests for every documented code and redaction tests for malformed untrusted input.

### Cross-cutting hardening / verification gates

- [ ] Version every externally visible contract and define compatibility/negotiation behavior before implementation consumers depend on it.
- [ ] Apply strict input bounds, canonicalization, authentication/authorization, timeout, and error semantics at the boundary rather than inside arbitrary callers.
- [ ] Provide golden positive/negative fixtures and run producer/consumer contract tests in CI.
- [ ] Prevent raw/unvalidated dictionaries, tenant-controlled identifiers, or backend-native errors from crossing the trusted internal boundary.
- [ ] Record interface/schema version and correlation/decision IDs in telemetry/evidence for every call.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-027` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-027`.
- [ ] RTM entry linking `MC-027` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-027` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-028 — Reference fixtures and adjacent-layer integration harnesses

**Priority:** P1  
**Audit finding:** (`C029-C030`, `C083`). No real image fixtures, malformed seal fixtures, VMM fixtures, execution-plane fixtures, or end-to-end test harness exists.  
**Risk:** Without this interface control, adjacent systems can disagree on meaning, authority, retries, or errors at a security-sensitive boundary.  
**Suggested blockers/dependencies:** `MC-001`, `MC-006`, `MC-007`, `MC-009`, `MC-023`  
**Mapped INV-27 requirements:**

- `C029` — Provide reference examples and conformance fixtures for Unikernel execution.
- `C030` — Create automated integration tests proving Unikernel execution interoperates with adjacent architectural layers.
- `C083` — Create integration tests with every supported adjacent layer and execution tier.

### Component-specific engineering checklist

- [ ] Create a fixture taxonomy: valid sealed images, malformed images, digest/signature failures, capability violations, architecture variants, boot failures, and VMM/device/network/storage scenarios.
- [ ] Include minimal real executable images or legally redistributable synthetic fixtures for every supported format/toolchain, with reproducible build recipes and hashes.
- [ ] Add malformed seal/manifest fixtures covering every schema validation branch and canonicalization ambiguity.
- [ ] Build fake/stub adjacent-layer services plus at least one real VMM integration environment for end-to-end tests.
- [ ] Provide hermetic test setup/teardown that cannot affect host networking/storage/devices outside an isolated test namespace/VM.
- [ ] Version fixtures with expected parse/verdict/evidence outputs and reject unreviewed fixture drift in CI.
- [ ] Include failure-injection controls to force timeouts, partial starts, cleanup failures, partition, and stale-policy conditions.

### Cross-cutting hardening / verification gates

- [ ] Version every externally visible contract and define compatibility/negotiation behavior before implementation consumers depend on it.
- [ ] Apply strict input bounds, canonicalization, authentication/authorization, timeout, and error semantics at the boundary rather than inside arbitrary callers.
- [ ] Provide golden positive/negative fixtures and run producer/consumer contract tests in CI.
- [ ] Prevent raw/unvalidated dictionaries, tenant-controlled identifiers, or backend-native errors from crossing the trusted internal boundary.
- [ ] Record interface/schema version and correlation/decision IDs in telemetry/evidence for every call.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-028` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-028`.
- [ ] RTM entry linking `MC-028` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-028` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

# D. Configuration & release control

## MC-029 — Declarative runtime configuration model

**Priority:** P1  
**Audit finding:** (`C032-C035`). No site/environment policy file/schema exists for architectures, syscall sets, toolchains, devices, networks, or admission policy.  
**Risk:** Without this control, deployment/configuration changes can become non-reproducible, partially applied, unrecoverable, or unsafe.  
**Suggested blockers/dependencies:** `MC-006`  
**Mapped INV-27 requirements:**

- `C032` — Separate immutable artifacts from mutable configuration and state for Unikernel execution.
- `C033` — Define declarative configuration and secure defaults for Unikernel execution.
- `C034` — Validate configuration before activation and fail closed on security-critical errors.
- `C035` — Support site- and environment-specific configuration without rebuilding immutable artifacts.

### Component-specific engineering checklist

- [ ] Design a versioned declarative runtime-policy schema for supported architectures, toolchains, image formats, syscall/capability allowlists, VMM backend, devices, network/storage classes, quotas, and trust roots/references.
- [ ] Separate site-, environment-, and tenant-scoped fields with explicit inheritance/override rules and immutable security floors.
- [ ] Provide secure production defaults: unknown architecture/toolchain/capability denied, no ambient devices/network/storage, bounded resources, signature required, strict schema validation.
- [ ] Implement semantic validation for cross-field invariants such as architecture/backend compatibility and device/IOMMU prerequisites.
- [ ] Compute a canonical configuration digest/revision and attach it to every admission decision and running instance.
- [ ] Support dry-run validation and machine-readable diagnostics before activation.
- [ ] Provide example configs for dev/test/prod that differ only through documented policy, not hidden code branches.

### Cross-cutting hardening / verification gates

- [ ] Represent policy/config/release state as immutable versioned revisions with provenance and explicit activation semantics.
- [ ] Make the safe state the default: partial, stale, unverifiable, or unsupported configuration must not broaden privileges or enable execution.
- [ ] Provide rollback/recovery that preserves revocations and monotonic security state; test rollback rather than documenting it only.
- [ ] Automate validation in bootstrap/CI/release gates and emit machine-readable evidence for every control.
- [ ] Keep secrets and environment-specific values out of source artifacts; use references and least-privilege runtime resolution.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-029` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-029`.
- [ ] RTM entry linking `MC-029` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-029` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-030 — Configuration provenance/history

**Priority:** P1  
**Audit finding:** (`C036`). No author/version/activation timestamp/signature record exists.  
**Risk:** Without this control, deployment/configuration changes can become non-reproducible, partially applied, unrecoverable, or unsafe.  
**Suggested blockers/dependencies:** `MC-029`, `MC-024`  
**Mapped INV-27 requirements:**

- `C036` — Record configuration provenance, version, author, and activation time.

### Component-specific engineering checklist

- [ ] Represent each activated configuration as an immutable revision with content digest, schema version, author/actor identity, source repository/revision, review/approval metadata, and activation timestamp.
- [ ] Sign or otherwise integrity-protect production configuration revisions and verify before activation.
- [ ] Maintain append-only activation history linking previous/new revisions and the change/request ID.
- [ ] Record the active configuration revision on every seal decision and runtime instance.
- [ ] Prevent anonymous/local manual edits from becoming active production policy outside an explicitly audited emergency path.
- [ ] Expose provenance through operator explain/status endpoints and include it in incident evidence bundles.
- [ ] Test detection of tampered history, rollback to unapproved revision, and missing provenance fields.

### Cross-cutting hardening / verification gates

- [ ] Represent policy/config/release state as immutable versioned revisions with provenance and explicit activation semantics.
- [ ] Make the safe state the default: partial, stale, unverifiable, or unsupported configuration must not broaden privileges or enable execution.
- [ ] Provide rollback/recovery that preserves revocations and monotonic security state; test rollback rather than documenting it only.
- [ ] Automate validation in bootstrap/CI/release gates and emit machine-readable evidence for every control.
- [ ] Keep secrets and environment-specific values out of source artifacts; use references and least-privilege runtime resolution.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-030` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-030`.
- [ ] RTM entry linking `MC-030` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-030` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-031 — Atomic configuration update mechanism

**Priority:** P1  
**Audit finding:** (`C037`). No transactional activation or compare-and-swap policy update exists.  
**Risk:** Without this control, deployment/configuration changes can become non-reproducible, partially applied, unrecoverable, or unsafe.  
**Suggested blockers/dependencies:** `MC-029`, `MC-030`  
**Mapped INV-27 requirements:**

- `C037` — Apply atomic or transactional configuration updates where partial application is unsafe.

### Component-specific engineering checklist

- [ ] Implement a prepare/validate/commit model for configuration updates so no reader can observe a partially applied policy.
- [ ] Use compare-and-swap/expected-generation semantics to reject updates based on stale active revisions.
- [ ] Preload/compile expensive policy structures before the atomic pointer/revision swap.
- [ ] Define cluster/site activation semantics: all-at-once, quorum, or staged; ensure the selected model cannot violate security invariants.
- [ ] On commit failure, retain the prior known-good revision and return deterministic recovery information.
- [ ] Persist activation outcome and revision transition in the tamper-evident audit ledger.
- [ ] Stress-test concurrent updates, process crash between prepare/commit, disk-full/write-failure, and readers during activation.

### Cross-cutting hardening / verification gates

- [ ] Represent policy/config/release state as immutable versioned revisions with provenance and explicit activation semantics.
- [ ] Make the safe state the default: partial, stale, unverifiable, or unsupported configuration must not broaden privileges or enable execution.
- [ ] Provide rollback/recovery that preserves revocations and monotonic security state; test rollback rather than documenting it only.
- [ ] Automate validation in bootstrap/CI/release gates and emit machine-readable evidence for every control.
- [ ] Keep secrets and environment-specific values out of source artifacts; use references and least-privilege runtime resolution.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-031` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-031`.
- [ ] RTM entry linking `MC-031` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-031` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-032 — Configuration rollback mechanism

**Priority:** P1  
**Audit finding:** (`C038`, `C092`). README mentions evidence rollback, but there is no implemented config/release rollback controller.  
**Risk:** Without this control, deployment/configuration changes can become non-reproducible, partially applied, unrecoverable, or unsafe.  
**Suggested blockers/dependencies:** `MC-029`, `MC-030`, `MC-031`  
**Mapped INV-27 requirements:**

- `C038` — Define automatic and operator-driven rollback for failed Unikernel execution changes.
- `C092` — Define canary, staged rollout, rollback, and emergency-disable procedures for Unikernel execution.

### Component-specific engineering checklist

- [ ] Define what state is rollbackable (configuration, policy, schemas, code release, VMM adapter) and what security revocations must never be rolled back.
- [ ] Store previous known-good immutable revisions and signed metadata needed to validate them.
- [ ] Implement operator and automatic rollback triggers based on health/SLO/security gates with bounded oscillation protection.
- [ ] Use transactional rollback with expected-generation checks and preserve audit lineage from failed revision to restored revision.
- [ ] Reconcile already-running instances when rollback changes admissibility or capability policy; define whether they continue, quarantine, or restart.
- [ ] Test rollback after partial rollout, incompatible schema change, backend failure, revoked trust root, and failed rollback itself.
- [ ] Verify rollback completes within a documented objective and does not resurrect known-vulnerable/revoked state.

### Cross-cutting hardening / verification gates

- [ ] Represent policy/config/release state as immutable versioned revisions with provenance and explicit activation semantics.
- [ ] Make the safe state the default: partial, stale, unverifiable, or unsupported configuration must not broaden privileges or enable execution.
- [ ] Provide rollback/recovery that preserves revocations and monotonic security state; test rollback rather than documenting it only.
- [ ] Automate validation in bootstrap/CI/release gates and emit machine-readable evidence for every control.
- [ ] Keep secrets and environment-specific values out of source artifacts; use references and least-privilege runtime resolution.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-032` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-032`.
- [ ] RTM entry linking `MC-032` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-032` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-033 — Secrets integration and diagnostics redaction

**Priority:** P1  
**Audit finding:** (`C039`, `C047`). No secret provider, key reference model, redaction policy/test, or secret-absence scanner exists.  
**Risk:** Without this control, deployment/configuration changes can become non-reproducible, partially applied, unrecoverable, or unsafe.  
**Suggested blockers/dependencies:** `MC-024`, `MC-046`  
**Mapped INV-27 requirements:**

- `C039` — Keep credentials and secret material out of ordinary Unikernel execution configuration and diagnostics.
- `C047` — Encrypt sensitive Unikernel execution data in transit and at rest with managed key rotation.

### Component-specific engineering checklist

- [ ] Define secret classes and prohibit raw secret material in normal runtime configuration, manifests, logs, metrics, traces, exceptions, fixture outputs, and support bundles.
- [ ] Integrate with an approved secret/KMS provider using opaque references/handles and short-lived credentials.
- [ ] Minimize secret exposure lifetime in memory; avoid copying into immutable evidence or serialized instance state.
- [ ] Implement centralized redaction with field-aware rules plus entropy/pattern scanners for diagnostics and test artifacts.
- [ ] Define rotation/renewal behavior and failure semantics when the secret provider is unavailable.
- [ ] Add pre-commit/CI secret scanning and repository history scanning policy.
- [ ] Test known secret canaries through every log/error/telemetry path and assert they never appear in emitted output.

### Cross-cutting hardening / verification gates

- [ ] Represent policy/config/release state as immutable versioned revisions with provenance and explicit activation semantics.
- [ ] Make the safe state the default: partial, stale, unverifiable, or unsupported configuration must not broaden privileges or enable execution.
- [ ] Provide rollback/recovery that preserves revocations and monotonic security state; test rollback rather than documenting it only.
- [ ] Automate validation in bootstrap/CI/release gates and emit machine-readable evidence for every control.
- [ ] Keep secrets and environment-specific values out of source artifacts; use references and least-privilege runtime resolution.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-033` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-033`.
- [ ] RTM entry linking `MC-033` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-033` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-034 — Deterministic bootstrap/install path

**Priority:** P1  
**Audit finding:** (`C040`). No installer/bootstrap that provisions dependencies, validates host capabilities, and reaches a healthy execution service exists.  
**Risk:** Without this control, deployment/configuration changes can become non-reproducible, partially applied, unrecoverable, or unsafe.  
**Suggested blockers/dependencies:** `MC-021`, `MC-022`, `MC-029`  
**Mapped INV-27 requirements:**

- `C040` — Provide a deterministic bootstrap path from an empty node/environment to healthy Unikernel execution operation.

### Component-specific engineering checklist

- [ ] Provide a single documented bootstrap entry point that validates Python/runtime dependencies, `pk_core`, VMM/backend availability, host CPU virtualization, permissions, network/storage prerequisites, and trust material.
- [ ] Pin/download dependencies with integrity verification or support an offline bundle with an explicit manifest.
- [ ] Create required directories/state with least-privilege ownership and safe permissions; never silently write to user/global locations outside the declared layout.
- [ ] Run schema/config validation, self-tests, VMM smoke test, and health/readiness checks before declaring bootstrap successful.
- [ ] Make bootstrap idempotent and resumable; repeated execution must converge without duplicate resources.
- [ ] Emit a machine-readable bootstrap report listing versions, capability checks, configuration digest, and failed prerequisite codes.
- [ ] Test from a clean VM/host image and from deliberately misconfigured hosts, including missing virtualization/IOMMU/kernel features.

### Cross-cutting hardening / verification gates

- [ ] Represent policy/config/release state as immutable versioned revisions with provenance and explicit activation semantics.
- [ ] Make the safe state the default: partial, stale, unverifiable, or unsupported configuration must not broaden privileges or enable execution.
- [ ] Provide rollback/recovery that preserves revocations and monotonic security state; test rollback rather than documenting it only.
- [ ] Automate validation in bootstrap/CI/release gates and emit machine-readable evidence for every control.
- [ ] Keep secrets and environment-specific values out of source artifacts; use references and least-privilege runtime resolution.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-034` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-034`.
- [ ] RTM entry linking `MC-034` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-034` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-035 — Canary/staged rollout/emergency-disable implementation

**Priority:** P1  
**Audit finding:** (`C092`). Procedures are only sketched; no rollout controller, health gate, kill switch, or tested emergency path is present.  
**Risk:** Without this control, deployment/configuration changes can become non-reproducible, partially applied, unrecoverable, or unsafe.  
**Suggested blockers/dependencies:** `MC-032`, `MC-051`, `MC-069`  
**Mapped INV-27 requirements:**

- `C092` — Define canary, staged rollout, rollback, and emergency-disable procedures for Unikernel execution.

### Component-specific engineering checklist

- [ ] Define rollout units (host/site/tenant/percentage) and explicit promotion gates using health, error rate, tail latency, security verdicts, and backend failure signals.
- [ ] Implement canary selection and staged progression with deterministic pause/abort conditions.
- [ ] Keep old/new protocol/config compatibility valid throughout the rollout window.
- [ ] Implement an authenticated, authorized emergency-disable/kill switch scoped by image digest, toolchain, tenant, site, or release and designed to fail safely.
- [ ] Define behavior for running instances when a release/image is disabled: no-new-start, quarantine, graceful stop, or immediate terminate based on severity.
- [ ] Exercise rollback and emergency-disable paths in non-production regularly and capture evidence.
- [ ] Prevent a broken control plane from silently re-enabling a disabled artifact by using monotonic policy/revocation epochs.

### Cross-cutting hardening / verification gates

- [ ] Represent policy/config/release state as immutable versioned revisions with provenance and explicit activation semantics.
- [ ] Make the safe state the default: partial, stale, unverifiable, or unsupported configuration must not broaden privileges or enable execution.
- [ ] Provide rollback/recovery that preserves revocations and monotonic security state; test rollback rather than documenting it only.
- [ ] Automate validation in bootstrap/CI/release gates and emit machine-readable evidence for every control.
- [ ] Keep secrets and environment-specific values out of source artifacts; use references and least-privilege runtime resolution.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-035` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-035`.
- [ ] RTM entry linking `MC-035` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-035` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-036 — Patch/vulnerability/EOL policy

**Priority:** P2  
**Audit finding:** (`C094`). No vulnerability intake, patch SLA, supported-release policy, or EOL schedule exists.  
**Risk:** Without this control, deployment/configuration changes can become non-reproducible, partially applied, unrecoverable, or unsafe.  
**Suggested blockers/dependencies:** `MC-088`, `MC-089`, `MC-090`  
**Mapped INV-27 requirements:**

- `C094` — Define patching, vulnerability response, and end-of-life SLAs for Unikernel execution.

### Component-specific engineering checklist

- [ ] Define severity-based vulnerability remediation SLAs for critical/high/medium/low findings and separate emergency zero-day handling.
- [ ] Inventory monitored sources for runtime, VMM, Python, `pk_core`, parser libraries, OS/kernel, firmware, toolchains, and cryptographic dependencies.
- [ ] Define supported release lines, patch backport rules, minimum secure versions, and explicit end-of-life dates.
- [ ] Automate dependency/security advisories and map findings to affected releases/images/sites.
- [ ] Require risk acceptance/waiver with owner and expiry when an SLA cannot be met.
- [ ] Define customer/operator notification and forced-block behavior for actively exploitable vulnerabilities affecting isolation or verification.
- [ ] Audit SLA compliance and EOL removals as part of the production gate/review process.

### Cross-cutting hardening / verification gates

- [ ] Represent policy/config/release state as immutable versioned revisions with provenance and explicit activation semantics.
- [ ] Make the safe state the default: partial, stale, unverifiable, or unsupported configuration must not broaden privileges or enable execution.
- [ ] Provide rollback/recovery that preserves revocations and monotonic security state; test rollback rather than documenting it only.
- [ ] Automate validation in bootstrap/CI/release gates and emit machine-readable evidence for every control.
- [ ] Keep secrets and environment-specific values out of source artifacts; use references and least-privilege runtime resolution.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-036` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-036`.
- [ ] RTM entry linking `MC-036` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-036` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-037 — Backup/restore/migration/reconstruction procedure

**Priority:** P1  
**Audit finding:** (`C095`). No operational artifact defines recovery of policy/evidence/configuration state.  
**Risk:** Without this control, deployment/configuration changes can become non-reproducible, partially applied, unrecoverable, or unsafe.  
**Suggested blockers/dependencies:** `MC-029`, `MC-030`, `MC-031`, `MC-032`, `MC-048`  
**Mapped INV-27 requirements:**

- `C095` — Provide backup, restore, migration, or reconstruction procedures for Unikernel execution state where applicable.

### Component-specific engineering checklist

- [ ] Classify durable state that must be recoverable: policy/config revisions, trust roots, revocations, audit ledger, image metadata, instance ownership/epochs, and release/gate evidence.
- [ ] Define whether each state is backed up, replicated, or reconstructible from authoritative sources and specify RPO/RTO targets.
- [ ] Encrypt backups, authenticate restore sources, and preserve integrity/signature metadata.
- [ ] Document restore ordering so trust/policy/audit state is valid before instances are admitted.
- [ ] Implement migration/version conversion for state schemas with reversible or forward-only rules explicitly documented.
- [ ] Test full loss of a node/site state store, point-in-time restore, corrupted backup detection, and reconstruction from source repositories/artifact stores.
- [ ] Verify restored state cannot roll back revocations, epochs, or security policy below the minimum safe generation.

### Cross-cutting hardening / verification gates

- [ ] Represent policy/config/release state as immutable versioned revisions with provenance and explicit activation semantics.
- [ ] Make the safe state the default: partial, stale, unverifiable, or unsupported configuration must not broaden privileges or enable execution.
- [ ] Provide rollback/recovery that preserves revocations and monotonic security state; test rollback rather than documenting it only.
- [ ] Automate validation in bootstrap/CI/release gates and emit machine-readable evidence for every control.
- [ ] Keep secrets and environment-specific values out of source artifacts; use references and least-privilege runtime resolution.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-037` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-037`.
- [ ] RTM entry linking `MC-037` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-037` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-038 — Incident response runbook

**Priority:** P2  
**Audit finding:** (`C097`). No severity model, paging matrix, containment playbook, forensic preservation procedure, or recovery checklist exists.  
**Risk:** Without this control, deployment/configuration changes can become non-reproducible, partially applied, unrecoverable, or unsafe.  
**Suggested blockers/dependencies:** `MC-042`, `MC-048`, `MC-058`  
**Mapped INV-27 requirements:**

- `C097` — Define incident severity, paging, escalation, containment, and recovery procedures.

### Component-specific engineering checklist

- [ ] Define incident severity criteria specifically for seal-verification bypass, signature/key compromise, isolation escape, cross-tenant access, widespread boot failure, and control-plane outage.
- [ ] Document paging, incident commander, security lead, communications, legal/compliance, and dependency-vendor escalation roles.
- [ ] Create containment playbooks: disable affected digest/toolchain/release, freeze admissions, quarantine instances, revoke keys, isolate hosts, preserve evidence.
- [ ] Define forensic data collection with chain-of-custody, immutable image/config digests, audit-log ranges, host/VMM versions, and memory/disk evidence where appropriate.
- [ ] Document eradication/recovery and explicit criteria for reopening admissions.
- [ ] Create post-incident review requirements and tracking of corrective actions to closure.
- [ ] Run tabletop/game-day exercises for at least seal bypass, compromised signing key, VMM escape suspicion, and widespread policy failure.

### Cross-cutting hardening / verification gates

- [ ] Represent policy/config/release state as immutable versioned revisions with provenance and explicit activation semantics.
- [ ] Make the safe state the default: partial, stale, unverifiable, or unsupported configuration must not broaden privileges or enable execution.
- [ ] Provide rollback/recovery that preserves revocations and monotonic security state; test rollback rather than documenting it only.
- [ ] Automate validation in bootstrap/CI/release gates and emit machine-readable evidence for every control.
- [ ] Keep secrets and environment-specific values out of source artifacts; use references and least-privilege runtime resolution.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-038` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-038`.
- [ ] RTM entry linking `MC-038` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-038` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-039 — Recurring review process

**Priority:** P2  
**Audit finding:** (`C098`). No scheduled access/policy/dependency/configuration/architecture review artifact exists.  
**Risk:** Without this control, deployment/configuration changes can become non-reproducible, partially applied, unrecoverable, or unsafe.  
**Suggested blockers/dependencies:** `MC-012`, `MC-036`, `MC-088`, `MC-090`  
**Mapped INV-27 requirements:**

- `C098` — Perform recurring access, policy, dependency, configuration, and architecture reviews.

### Component-specific engineering checklist

- [ ] Define recurring review cadences for access/capabilities, signing keys/trust roots, supported dependencies, runtime policy, exceptions/waivers, SLOs, and architecture assumptions.
- [ ] Assign reviewer roles and required evidence for each review type.
- [ ] Automate review reminders and generate a current inventory of items requiring review rather than relying on static documents.
- [ ] Require explicit reaffirm/modify/revoke decisions and preserve review history.
- [ ] Escalate overdue reviews and block production certification when critical reviews exceed their maximum age.
- [ ] Include threat-model and ADR refresh triggers after major architecture/backend/toolchain changes.
- [ ] Sample audit-log/config changes during reviews to verify documented policy matches actual enforcement.

### Cross-cutting hardening / verification gates

- [ ] Represent policy/config/release state as immutable versioned revisions with provenance and explicit activation semantics.
- [ ] Make the safe state the default: partial, stale, unverifiable, or unsupported configuration must not broaden privileges or enable execution.
- [ ] Provide rollback/recovery that preserves revocations and monotonic security state; test rollback rather than documenting it only.
- [ ] Automate validation in bootstrap/CI/release gates and emit machine-readable evidence for every control.
- [ ] Keep secrets and environment-specific values out of source artifacts; use references and least-privilege runtime resolution.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-039` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-039`.
- [ ] RTM entry linking `MC-039` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-039` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-040 — Exception/waiver/technical-debt registry

**Priority:** P2  
**Audit finding:** (`C099`). No owner/expiry/rationale tracking artifact exists.  
**Risk:** Without this control, deployment/configuration changes can become non-reproducible, partially applied, unrecoverable, or unsafe.  
**Suggested blockers/dependencies:** `MC-012`, `MC-014`, `MC-015`  
**Mapped INV-27 requirements:**

- `C099` — Track exceptions, waivers, technical debt, and deprecated behaviors with owners and expiry dates.

### Component-specific engineering checklist

- [ ] Create a machine-readable registry for exceptions, waivers, temporary risk acceptances, deprecated behavior, and technical debt.
- [ ] Require unique ID, affected requirement/control, exact scope, rationale, compensating controls, owner, approver, creation date, expiry date, and remediation target.
- [ ] Disallow permanent/expiry-less waivers for P0 security invariants.
- [ ] Integrate registry checks into CI/production gate so expired waivers fail closed.
- [ ] Link waivers to RTM rows, incidents/vulnerabilities, code/config changes, and evidence.
- [ ] Generate reports by owner/age/severity and automatically flag repeatedly extended waivers.
- [ ] Test that removing/expiring a waiver causes the expected gate failure or policy behavior.

### Cross-cutting hardening / verification gates

- [ ] Represent policy/config/release state as immutable versioned revisions with provenance and explicit activation semantics.
- [ ] Make the safe state the default: partial, stale, unverifiable, or unsupported configuration must not broaden privileges or enable execution.
- [ ] Provide rollback/recovery that preserves revocations and monotonic security state; test rollback rather than documenting it only.
- [ ] Automate validation in bootstrap/CI/release gates and emit machine-readable evidence for every control.
- [ ] Keep secrets and environment-specific values out of source artifacts; use references and least-privilege runtime resolution.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-040` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-040`.
- [ ] RTM entry linking `MC-040` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-040` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-041 — Self-contained formal production exit gate

**Priority:** P0  
**Audit finding:** (`C100`). The README references `pk_core gate`, but this archive cannot execute it without the missing external core and contains no independently runnable full gate.  
**Risk:** Without this control, deployment/configuration changes can become non-reproducible, partially applied, unrecoverable, or unsafe.  
**Suggested blockers/dependencies:** `MC-021`, `MC-086`  
**Mapped INV-27 requirements:**

- `C100` — Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness.

### Component-specific engineering checklist

- [ ] Implement one repository-local production-gate command that requires no undeclared dependency and produces deterministic machine-readable results.
- [ ] Gate architecture/requirements/interface completeness, runtime/security tests, compatibility matrix, static analysis, coverage, SBOM/build provenance, performance thresholds, rollback evidence, ownership, and unresolved waivers.
- [ ] Require every gate check to have stable ID, severity, evidence pointer, timestamp, tool/version, and PASS/FAIL/BLOCKED status.
- [ ] Fail closed when a mandatory verifier, fixture, dependency, or evidence artifact is unavailable; skipped is not PASS.
- [ ] Cryptographically bind the gate result to source revision, built artifact digest, configuration/schema versions, and test environment identity.
- [ ] Produce human-readable summary plus signed/hashed JSON evidence suitable for archival.
- [ ] Test the gate itself with injected failures to prove each mandatory control can force a non-zero/non-GO result.

### Cross-cutting hardening / verification gates

- [ ] Represent policy/config/release state as immutable versioned revisions with provenance and explicit activation semantics.
- [ ] Make the safe state the default: partial, stale, unverifiable, or unsupported configuration must not broaden privileges or enable execution.
- [ ] Provide rollback/recovery that preserves revocations and monotonic security state; test rollback rather than documenting it only.
- [ ] Automate validation in bootstrap/CI/release gates and emit machine-readable evidence for every control.
- [ ] Keep secrets and environment-specific values out of source artifacts; use references and least-privilege runtime resolution.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-041` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-041`.
- [ ] RTM entry linking `MC-041` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-041` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

# E. Security, trust & isolation

## MC-042 — Complete threat model artifact

**Priority:** P0  
**Audit finding:** (`C041`). Contract lists four threats, but no assets/trust boundaries/attacker capabilities/abuse cases/mitigations/residual-risk model exists.  
**Risk:** Without this control, a malicious or compromised tenant/artifact/service may cross a trust boundary or suppress evidence of compromise.  
**Suggested blockers/dependencies:** `MC-013`, `MC-014`  
**Mapped INV-27 requirements:**

- `C041` — Threat-model Unikernel execution against malicious tenants, compromised workloads, hostile inputs, supply-chain compromise, and control-plane abuse.

### Component-specific engineering checklist

- [ ] Create a threat model using data-flow/trust-boundary diagrams covering image intake, manifest/signature verification, parser, policy, scheduler, VMM, host kernel, devices, network/storage, telemetry, audit, and operator paths.
- [ ] Enumerate assets, principals, attacker capabilities, entry points, trust assumptions, and security objectives.
- [ ] Model malicious tenant images, compromised build systems/toolchains, malicious insiders/operators, stolen credentials/keys, compromised hosts, hostile network peers, and dependency/control-plane compromise.
- [ ] Enumerate abuse cases for parser exploitation, signature/provenance substitution, TOCTOU, privilege escalation, device abuse, VM escape, side channels, DoS, replay, and audit tampering.
- [ ] Map each threat to preventive/detective/recovery controls and residual risk with owner.
- [ ] Derive explicit security test IDs from the threat model and link them into the RTM.
- [ ] Re-review the model when adding a new image format, VMM, device class, trust provider, or privileged interface.

### Cross-cutting hardening / verification gates

- [ ] Map the control to a named threat and security objective and document residual risk after implementation.
- [ ] Apply least privilege/default deny and ensure tenant-controlled data never becomes authority merely because it is syntactically valid.
- [ ] Make security state and decisions tamper-evidently auditable with stable reason/decision IDs.
- [ ] Add abuse/negative tests and at least one regression fixture for each fixed vulnerability class or bypass found during development.
- [ ] Fail closed when required trust, identity, policy, cryptographic, or isolation evidence cannot be established.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-042` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-042`.
- [ ] RTM entry linking `MC-042` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-042` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-043 — Tenant/workload memory isolation proof

**Priority:** P0  
**Audit finding:** (`C046`). No VMM memory isolation configuration or test evidence exists.  
**Risk:** Without this control, a malicious or compromised tenant/artifact/service may cross a trust boundary or suppress evidence of compromise.  
**Suggested blockers/dependencies:** `MC-009`, `MC-042`  
**Mapped INV-27 requirements:**

- `C046` — Enforce tenant/workload isolation across Unikernel execution execution, memory, state, network, and device boundaries as applicable.

### Component-specific engineering checklist

- [ ] Define the exact memory-isolation mechanism for each backend: hardware virtualization mode, second-level address translation, guest physical memory mappings, shared-memory exceptions, and host-side process isolation.
- [ ] Ensure every instance receives disjoint guest memory ownership and zero/poison memory before reuse between tenants.
- [ ] Prevent writable/executable host mappings of guest memory except narrowly scoped backend requirements; document any shared pages and permissions.
- [ ] Configure host resource isolation (cgroup/job object/process sandbox as applicable) to constrain VMM memory and prevent cross-instance memory access through host APIs.
- [ ] Validate CPU/IOMMU virtualization prerequisites at host admission and refuse degraded unsafe modes.
- [ ] Create cross-tenant memory disclosure/injection tests, memory-reuse tests, out-of-bounds shared-memory tests, and backend-specific escape regressions.
- [ ] Capture effective memory isolation configuration and host capability evidence in certification artifacts.

### Cross-cutting hardening / verification gates

- [ ] Map the control to a named threat and security objective and document residual risk after implementation.
- [ ] Apply least privilege/default deny and ensure tenant-controlled data never becomes authority merely because it is syntactically valid.
- [ ] Make security state and decisions tamper-evidently auditable with stable reason/decision IDs.
- [ ] Add abuse/negative tests and at least one regression fixture for each fixed vulnerability class or bypass found during development.
- [ ] Fail closed when required trust, identity, policy, cryptographic, or isolation evidence cannot be established.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-043` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-043`.
- [ ] RTM entry linking `MC-043` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-043` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-044 — Network isolation proof

**Priority:** P0  
**Audit finding:** (`C046`). No network namespace/vSwitch/filter/capability implementation or test evidence exists.  
**Risk:** Without this control, a malicious or compromised tenant/artifact/service may cross a trust boundary or suppress evidence of compromise.  
**Suggested blockers/dependencies:** `MC-009`, `MC-010`, `MC-025`, `MC-042`  
**Mapped INV-27 requirements:**

- `C046` — Enforce tenant/workload isolation across Unikernel execution execution, memory, state, network, and device boundaries as applicable.

### Component-specific engineering checklist

- [ ] Define network isolation per tenant/workload using namespaces/vSwitches/segments/virtual NIC ownership and explicit routing boundaries.
- [ ] Default to no network; attach only policy-authorized NICs and enforce tenant-scoped ingress/egress ACLs at a layer the guest cannot bypass.
- [ ] Prevent L2 spoofing, MAC/IP impersonation, promiscuous mode, unauthorized DHCP/RA, and cross-tenant broadcast/multicast leakage where applicable.
- [ ] Enforce egress destinations/protocols/ports or service capabilities consistent with least privilege.
- [ ] Rate-limit connection/state growth and protect host/control-plane endpoints from guest-originated traffic.
- [ ] Test east-west isolation, spoofing, policy updates, host-service reachability, network namespace/vSwitch escape, and cleanup after failed starts.
- [ ] Record network policy revision and attachment identifiers in instance evidence without exposing other tenants' topology.

### Cross-cutting hardening / verification gates

- [ ] Map the control to a named threat and security objective and document residual risk after implementation.
- [ ] Apply least privilege/default deny and ensure tenant-controlled data never becomes authority merely because it is syntactically valid.
- [ ] Make security state and decisions tamper-evidently auditable with stable reason/decision IDs.
- [ ] Add abuse/negative tests and at least one regression fixture for each fixed vulnerability class or bypass found during development.
- [ ] Fail closed when required trust, identity, policy, cryptographic, or isolation evidence cannot be established.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-044` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-044`.
- [ ] RTM entry linking `MC-044` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-044` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-045 — Device isolation/IOMMU policy and proof

**Priority:** P0  
**Audit finding:** (`C046`). No passthrough/device authorization/IOMMU configuration or tests exist.  
**Risk:** Without this control, a malicious or compromised tenant/artifact/service may cross a trust boundary or suppress evidence of compromise.  
**Suggested blockers/dependencies:** `MC-009`, `MC-010`, `MC-042`  
**Mapped INV-27 requirements:**

- `C046` — Enforce tenant/workload isolation across Unikernel execution execution, memory, state, network, and device boundaries as applicable.

### Component-specific engineering checklist

- [ ] Inventory supported virtual and passthrough device classes and define a default-deny device policy.
- [ ] For passthrough, require IOMMU isolation group validation, DMA remapping, interrupt remapping, ACS/topology checks where relevant, and exclusive ownership.
- [ ] Prohibit unsafe shared devices or define mediated-device isolation with vendor/backend-specific evidence.
- [ ] Validate device firmware/driver/VMM versions against the supported compatibility matrix and vulnerability policy.
- [ ] Reset/sanitize device state between tenants and verify teardown revokes DMA/access before reassignment.
- [ ] Test unauthorized device request, malicious MMIO/I/O access, DMA isolation, stale assignment, reset failure, and concurrent ownership attempts.
- [ ] Capture device/IOMMU configuration and host capability evidence for certification.

### Cross-cutting hardening / verification gates

- [ ] Map the control to a named threat and security objective and document residual risk after implementation.
- [ ] Apply least privilege/default deny and ensure tenant-controlled data never becomes authority merely because it is syntactically valid.
- [ ] Make security state and decisions tamper-evidently auditable with stable reason/decision IDs.
- [ ] Add abuse/negative tests and at least one regression fixture for each fixed vulnerability class or bypass found during development.
- [ ] Fail closed when required trust, identity, policy, cryptographic, or isolation evidence cannot be established.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-045` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-045`.
- [ ] RTM entry linking `MC-045` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-045` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-046 — Encryption in transit/at rest and key rotation

**Priority:** P0  
**Audit finding:** (`C047`). No cryptographic transport/storage/key-management implementation exists.  
**Risk:** Without this control, a malicious or compromised tenant/artifact/service may cross a trust boundary or suppress evidence of compromise.  
**Suggested blockers/dependencies:** `MC-004`, `MC-005`, `MC-024`, `MC-033`  
**Mapped INV-27 requirements:**

- `C047` — Encrypt sensitive Unikernel execution data in transit and at rest with managed key rotation.

### Component-specific engineering checklist

- [ ] Classify sensitive data in motion and at rest: manifests, policies, audit/evidence, credentials, tenant metadata, images where confidentiality is required, and control-plane traffic.
- [ ] Require authenticated encryption for network transport using approved protocol/cipher policy and strong peer identity.
- [ ] Encrypt durable sensitive state/backups with managed keys; avoid embedding long-lived raw keys in config or source.
- [ ] Define key hierarchy, key IDs, rotation interval, revocation, compromise recovery, and separation of duties.
- [ ] Bind encrypted objects to integrity/authentication context so ciphertext cannot be replayed/substituted across tenant/site/object identity.
- [ ] Define certificate/key rotation with overlap windows that do not permit indefinite old-key use.
- [ ] Test downgrade, wrong-key, revoked-key, corrupted ciphertext, rotation during operation, and loss of key-service scenarios.

### Cross-cutting hardening / verification gates

- [ ] Map the control to a named threat and security objective and document residual risk after implementation.
- [ ] Apply least privilege/default deny and ensure tenant-controlled data never becomes authority merely because it is syntactically valid.
- [ ] Make security state and decisions tamper-evidently auditable with stable reason/decision IDs.
- [ ] Add abuse/negative tests and at least one regression fixture for each fixed vulnerability class or bypass found during development.
- [ ] Fail closed when required trust, identity, policy, cryptographic, or isolation evidence cannot be established.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-046` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-046`.
- [ ] RTM entry linking `MC-046` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-046` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-047 — Safe degraded trust-service behavior

**Priority:** P0  
**Audit finding:** (`C048`). No fail-closed behavior is implemented for identity, attestation, policy, key, or trusted-time outages.  
**Risk:** Without this control, a malicious or compromised tenant/artifact/service may cross a trust boundary or suppress evidence of compromise.  
**Suggested blockers/dependencies:** `MC-024`, `MC-046`, `MC-029`  
**Mapped INV-27 requirements:**

- `C048` — Define safe behavior when identity, attestation, policy, key, or time services are unavailable.

### Component-specific engineering checklist

- [ ] Classify identity, attestation, policy, key-management, revocation, and trusted-time services by whether admission/execution may proceed during outage.
- [ ] For security-critical trust inputs, implement fail-closed new admission when freshness cannot be established beyond a defined bound.
- [ ] Define bounded cached-trust operation with signed epochs/expiry where continuity is allowed; prevent rollback to older cached state.
- [ ] Define running-instance actions when a key/image/policy may have been revoked but the revocation service is unreachable.
- [ ] Expose degraded state and precise reason without treating it as healthy/normal operation.
- [ ] Implement recovery reconciliation that revalidates affected instances as soon as trust services return.
- [ ] Test outage/partition at admission, start, steady state, rotation, and reconnect, including stale/revoked data.

### Cross-cutting hardening / verification gates

- [ ] Map the control to a named threat and security objective and document residual risk after implementation.
- [ ] Apply least privilege/default deny and ensure tenant-controlled data never becomes authority merely because it is syntactically valid.
- [ ] Make security state and decisions tamper-evidently auditable with stable reason/decision IDs.
- [ ] Add abuse/negative tests and at least one regression fixture for each fixed vulnerability class or bypass found during development.
- [ ] Fail closed when required trust, identity, policy, cryptographic, or isolation evidence cannot be established.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-047` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-047`.
- [ ] RTM entry linking `MC-047` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-047` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-048 — Tamper-evident security audit log

**Priority:** P0  
**Audit finding:** (`C049`). Runtime returns immutable in-process evidence, but there is no append-only chained/signed durable audit ledger in this repository.  
**Risk:** Without this control, a malicious or compromised tenant/artifact/service may cross a trust boundary or suppress evidence of compromise.  
**Suggested blockers/dependencies:** `MC-004`, `MC-005`, `MC-030`  
**Mapped INV-27 requirements:**

- `C049` — Emit tamper-evident audit events for security-sensitive Unikernel execution operations.

### Component-specific engineering checklist

- [ ] Define a stable security-audit event schema with event ID, monotonic sequence/epoch, timestamp/trusted-time status, actor, tenant/workload, operation, resource/image digest, policy/config revision, decision, reason, and correlation ID.
- [ ] Write events to durable append-only storage outside the mutable runtime process and protect them with hash chaining, signatures/MACs, or an equivalent tamper-evident mechanism.
- [ ] Guarantee that security-sensitive actions (admit/reject/start/stop/quarantine/policy change/key/trust change/break-glass) emit audit events or fail safely.
- [ ] Protect against event truncation/reordering/duplication and define continuity across rotation/archival.
- [ ] Separate sensitive forensic detail from operator-readable summaries with access control and redaction.
- [ ] Implement verification tooling that detects missing links/tampering and produces machine-readable validation evidence.
- [ ] Test crash during append, disk full, log rotation, replay/substitution, concurrent writers, and deliberate record mutation.

### Cross-cutting hardening / verification gates

- [ ] Map the control to a named threat and security objective and document residual risk after implementation.
- [ ] Apply least privilege/default deny and ensure tenant-controlled data never becomes authority merely because it is syntactically valid.
- [ ] Make security state and decisions tamper-evidently auditable with stable reason/decision IDs.
- [ ] Add abuse/negative tests and at least one regression fixture for each fixed vulnerability class or bypass found during development.
- [ ] Fail closed when required trust, identity, policy, cryptographic, or isolation evidence cannot be established.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-048` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-048`.
- [ ] RTM entry linking `MC-048` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-048` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-049 — Adversarial security test suite

**Priority:** P0  
**Audit finding:** (`C050`, `C087`). No privilege-escalation, injection, replay, spoofing, VM escape, side-channel, or resource-exhaustion suite exists.  
**Risk:** Without this control, a malicious or compromised tenant/artifact/service may cross a trust boundary or suppress evidence of compromise.  
**Suggested blockers/dependencies:** `MC-042`, `MC-043`, `MC-044`, `MC-045`, `MC-046`, `MC-047`, `MC-048`  
**Mapped INV-27 requirements:**

- `C050` — Run adversarial tests for privilege escalation, injection, replay, spoofing, escape, side channels, and resource exhaustion.
- `C087` — Create security tests derived directly from the Unikernel execution threat model.

### Component-specific engineering checklist

- [ ] Derive an adversarial test catalog directly from threat-model IDs and require traceability from each high-risk threat to at least one negative test.
- [ ] Add parser/input attacks: malformed lengths/counts, integer boundaries, path/URI tricks, duplicate/ambiguous fields, decompression/resource bombs if applicable.
- [ ] Add identity/policy attacks: token replay, issuer/audience confusion, tenant substitution, capability forgery, stale policy, break-glass abuse.
- [ ] Add supply-chain attacks: signature substitution, compromised/unapproved toolchain, provenance mismatch, revoked key, SBOM subject mismatch.
- [ ] Add isolation attacks: forbidden device/network/storage access, cross-tenant probing, memory reuse, backend escape regression cases, hostile boot behavior.
- [ ] Add availability attacks: verification CPU/memory exhaustion, connection/queue floods, repeated failing boots, retry amplification.
- [ ] Run tests in isolated infrastructure and capture reproducible seeds/configuration/results as release evidence.

### Cross-cutting hardening / verification gates

- [ ] Map the control to a named threat and security objective and document residual risk after implementation.
- [ ] Apply least privilege/default deny and ensure tenant-controlled data never becomes authority merely because it is syntactically valid.
- [ ] Make security state and decisions tamper-evidently auditable with stable reason/decision IDs.
- [ ] Add abuse/negative tests and at least one regression fixture for each fixed vulnerability class or bypass found during development.
- [ ] Fail closed when required trust, identity, policy, cryptographic, or isolation evidence cannot be established.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-049` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-049`.
- [ ] RTM entry linking `MC-049` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-049` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-050 — Fuzzing harness/corpus

**Priority:** P0  
**Audit finding:** (`C085`). No fuzz target exists for manifests, binary parsers (none exist), schemas, or untrusted inputs.  
**Risk:** Without this control, a malicious or compromised tenant/artifact/service may cross a trust boundary or suppress evidence of compromise.  
**Suggested blockers/dependencies:** `MC-001`, `MC-003`, `MC-006`, `MC-023`, `MC-026`  
**Mapped INV-27 requirements:**

- `C085` — Fuzz parsers, schemas, protocol handlers, WIT/RPC boundaries, or untrusted inputs handled by Unikernel execution.

### Component-specific engineering checklist

- [ ] Select fuzzing engines appropriate to implementation languages and expose narrowly scoped fuzz targets for manifest/schema parsing, binary parsing, error-envelope decoding, policy inputs, and any RPC/WIT boundary.
- [ ] Seed corpora with every golden and malformed fixture plus minimized historical crashes/security bugs.
- [ ] Define invariants: parser never crashes/hangs/unbounded-allocates, invalid inputs never become admitted, canonicalization is deterministic, and successful parses round-trip as specified.
- [ ] Apply explicit per-input CPU/memory/size limits and sanitizer/instrumented builds where available.
- [ ] Run continuous short fuzz jobs in CI and longer scheduled campaigns; preserve crashing inputs as regression fixtures.
- [ ] Track code/path coverage and dictionary tokens for binary/schema formats to avoid superficial fuzzing.
- [ ] Treat a fuzzer timeout/OOM/panic in a trust-boundary parser as a release-blocking defect until triaged.

### Cross-cutting hardening / verification gates

- [ ] Map the control to a named threat and security objective and document residual risk after implementation.
- [ ] Apply least privilege/default deny and ensure tenant-controlled data never becomes authority merely because it is syntactically valid.
- [ ] Make security state and decisions tamper-evidently auditable with stable reason/decision IDs.
- [ ] Add abuse/negative tests and at least one regression fixture for each fixed vulnerability class or bypass found during development.
- [ ] Fail closed when required trust, identity, policy, cryptographic, or isolation evidence cannot be established.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-050` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-050`.
- [ ] RTM entry linking `MC-050` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-050` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

# F. Resilience & failure handling

## MC-051 — Health/readiness/stall detector

**Priority:** P1  
**Audit finding:** (`C052`). No watchdog, boot timeout, liveness/readiness state, or progress detector exists.  
**Risk:** Without this mechanism, ordinary failures or partitions can cascade into duplicate execution, unsafe recovery, or prolonged outage.  
**Suggested blockers/dependencies:** `MC-016`  
**Mapped INV-27 requirements:**

- `C052` — Define automated health and stall detection thresholds for Unikernel execution.

### Component-specific engineering checklist

- [ ] Build a failure-mode catalog spanning verifier process, parser, VMM, guest, node, storage, network, site, provider, identity/policy/key/time services, telemetry/audit, and control-plane components.
- [ ] For each failure, specify detectability, blast radius, expected state transition, retryability, cleanup, operator action, and recovery objective.
- [ ] Distinguish independent from correlated/common-mode failures (kernel bug, bad policy rollout, expired root, provider outage).
- [ ] Map each failure to metrics/logs/alerts and a fault-injection test or documented reason why injection is impractical.
- [ ] Define which failures may continue existing instances versus block new admissions or require quarantine/termination.
- [ ] Link failure modes to SLO/error-budget impact and incident severity.
- [ ] Review the catalog after every significant incident or architecture change.

### Cross-cutting hardening / verification gates

- [ ] Define detection threshold, state transition, side effects, retryability, cleanup, operator signal, and recovery objective for the failure scenario.
- [ ] Use bounded deadlines/retries and idempotent reconciliation; never allow recovery logic to create duplicate execution or bypass current policy.
- [ ] Preserve ownership/fencing/config epochs across crashes and partitions so stale actors cannot mutate current state.
- [ ] Inject the failure deterministically and assert resource cleanup, audit continuity, expected alerting, and measured recovery time.
- [ ] Document and test compound/common-mode failures, not only a single idealized component failure.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-051` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-051`.
- [ ] RTM entry linking `MC-051` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-051` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-052 — Bounded retry/backoff/jitter mechanism

**Priority:** P1  
**Audit finding:** (`C053`). No retry implementation or retry-safety classification exists.  
**Risk:** Without this mechanism, ordinary failures or partitions can cascade into duplicate execution, unsafe recovery, or prolonged outage.  
**Suggested blockers/dependencies:** `MC-016`, `MC-069`, `MC-070`  
**Mapped INV-27 requirements:**

- `C053` — Implement bounded retry with backoff and jitter only where operations are safe to retry.

### Component-specific engineering checklist

- [ ] Define liveness/readiness criteria for verifier, policy/trust dependencies, VMM backend, audit sink, and each running instance.
- [ ] Implement boot/startup deadlines plus progress milestones so a hung boot is distinguishable from a slow but progressing boot.
- [ ] Implement watchdog/heartbeat or backend state polling with bounded intervals and false-positive tolerances.
- [ ] Define readiness to mean safe-to-accept-work, not merely process-alive; fail readiness on stale critical policy/trust/audit state where required.
- [ ] Add stall detection for queues, reconciliation loops, and instance lifecycle operations using age/attempt/progress metrics.
- [ ] Ensure health checks are bounded and cannot themselves overload the service or VMM.
- [ ] Test frozen guest, wedged backend call, stuck queue, audit sink outage, dependency timeout, and clock discontinuity.

### Cross-cutting hardening / verification gates

- [ ] Define detection threshold, state transition, side effects, retryability, cleanup, operator signal, and recovery objective for the failure scenario.
- [ ] Use bounded deadlines/retries and idempotent reconciliation; never allow recovery logic to create duplicate execution or bypass current policy.
- [ ] Preserve ownership/fencing/config epochs across crashes and partitions so stale actors cannot mutate current state.
- [ ] Inject the failure deterministically and assert resource cleanup, audit continuity, expected alerting, and measured recovery time.
- [ ] Document and test compound/common-mode failures, not only a single idealized component failure.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-052` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-052`.
- [ ] RTM entry linking `MC-052` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-052` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-053 — Admission control/load shedding/circuit breaker

**Priority:** P1  
**Audit finding:** (`C054`). No overload protection exists.  
**Risk:** Without this mechanism, ordinary failures or partitions can cascade into duplicate execution, unsafe recovery, or prolonged outage.  
**Suggested blockers/dependencies:** `MC-018`, `MC-029`, `MC-070`  
**Mapped INV-27 requirements:**

- `C054` — Implement admission control, load shedding, or circuit breaking to prevent Unikernel execution failure cascades.

### Component-specific engineering checklist

- [ ] Inventory operations and classify retry safety, side effects, idempotency key, maximum attempts, total retry deadline, and non-retryable error codes.
- [ ] Implement capped exponential backoff with decorrelated/full jitter and global retry budgets to prevent synchronized retry storms.
- [ ] Never auto-retry authentication, authorization, digest/signature, policy, schema, or deterministic compatibility failures.
- [ ] Persist/deduplicate create/start operations so a lost response cannot create duplicate instances.
- [ ] Cancel retries when request deadline, ownership epoch, policy revision, or operator disable state changes.
- [ ] Emit attempt count, delay, final outcome, and retry-exhausted reason as structured telemetry.
- [ ] Test transient success, permanent failure, lost response, duplicate IDs, mass dependency outage, and cancellation during backoff.

### Cross-cutting hardening / verification gates

- [ ] Define detection threshold, state transition, side effects, retryability, cleanup, operator signal, and recovery objective for the failure scenario.
- [ ] Use bounded deadlines/retries and idempotent reconciliation; never allow recovery logic to create duplicate execution or bypass current policy.
- [ ] Preserve ownership/fencing/config epochs across crashes and partitions so stale actors cannot mutate current state.
- [ ] Inject the failure deterministically and assert resource cleanup, audit continuity, expected alerting, and measured recovery time.
- [ ] Document and test compound/common-mode failures, not only a single idealized component failure.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-053` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-053`.
- [ ] RTM entry linking `MC-053` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-053` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-054 — Failover/residency-aware recovery

**Priority:** P1  
**Audit finding:** (`C055`). No scheduler/failover implementation exists.  
**Risk:** Without this mechanism, ordinary failures or partitions can cascade into duplicate execution, unsafe recovery, or prolonged outage.  
**Suggested blockers/dependencies:** `MC-029`, `MC-052`  
**Mapped INV-27 requirements:**

- `C055` — Define failover behavior without violating isolation, residency, or consistency requirements.

### Component-specific engineering checklist

- [ ] Define admission capacity signals for verifier CPU, parser memory, work queue, VMM create rate, host vCPU/memory, network/storage resources, and critical dependency health.
- [ ] Implement bounded queues and reject/load-shed before resource exhaustion; never allow unbounded in-memory pending admissions.
- [ ] Define per-tenant and global concurrency limits so one tenant cannot consume all verifier or start slots.
- [ ] Add circuit breakers for unhealthy dependencies/backends with half-open recovery and separate security denials from infrastructure failures.
- [ ] Return structured overload responses with safe retry-after guidance where applicable.
- [ ] Prioritize stop/quarantine/recovery/control operations over new starts during saturation.
- [ ] Load-test overload to prove memory/queue bounds, stable latency, and recovery without retry amplification.

### Cross-cutting hardening / verification gates

- [ ] Define detection threshold, state transition, side effects, retryability, cleanup, operator signal, and recovery objective for the failure scenario.
- [ ] Use bounded deadlines/retries and idempotent reconciliation; never allow recovery logic to create duplicate execution or bypass current policy.
- [ ] Preserve ownership/fencing/config epochs across crashes and partitions so stale actors cannot mutate current state.
- [ ] Inject the failure deterministically and assert resource cleanup, audit continuity, expected alerting, and measured recovery time.
- [ ] Document and test compound/common-mode failures, not only a single idealized component failure.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-054` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-054`.
- [ ] RTM entry linking `MC-054` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-054` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-055 — Defined degraded operation

**Priority:** P1  
**Audit finding:** (`C056`). No executable degraded mode exists.  
**Risk:** Without this mechanism, ordinary failures or partitions can cascade into duplicate execution, unsafe recovery, or prolonged outage.  
**Suggested blockers/dependencies:** `MC-019`, `MC-052`  
**Mapped INV-27 requirements:**

- `C056` — Provide degraded operation when noncritical dependencies are unavailable.

### Component-specific engineering checklist

- [ ] Define failover ownership boundaries and what state must be replicated/shared for another controller/node/site to take over safely.
- [ ] Enforce residency/sovereignty constraints before selecting a failover target; fail closed if no compliant target exists.
- [ ] Use fencing/leases/epochs so failover cannot create two active owners/instances for a singleton workload.
- [ ] Define whether instance state is restart-only, checkpointable, or migratable and what consistency/durability guarantees apply.
- [ ] Validate image digest, seal evidence, policy revision, architecture, backend, and device compatibility on the target before start.
- [ ] Specify failback behavior and prevent oscillation during unstable sites/providers.
- [ ] Test node/site/provider loss, partition, stale owner recovery, no-compliant-target, and failover while policy changes.

### Cross-cutting hardening / verification gates

- [ ] Define detection threshold, state transition, side effects, retryability, cleanup, operator signal, and recovery objective for the failure scenario.
- [ ] Use bounded deadlines/retries and idempotent reconciliation; never allow recovery logic to create duplicate execution or bypass current policy.
- [ ] Preserve ownership/fencing/config epochs across crashes and partitions so stale actors cannot mutate current state.
- [ ] Inject the failure deterministically and assert resource cleanup, audit continuity, expected alerting, and measured recovery time.
- [ ] Document and test compound/common-mode failures, not only a single idealized component failure.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-055` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-055`.
- [ ] RTM entry linking `MC-055` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-055` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-056 — Crash consistency/restart/resume/replay semantics

**Priority:** P1  
**Audit finding:** (`C057`). No durable runtime state/recovery implementation exists.  
**Risk:** Without this mechanism, ordinary failures or partitions can cascade into duplicate execution, unsafe recovery, or prolonged outage.  
**Suggested blockers/dependencies:** `MC-016`, `MC-029`  
**Mapped INV-27 requirements:**

- `C057` — Define crash-consistency, restart, resume, or replay semantics for mutable Unikernel execution state.

### Component-specific engineering checklist

- [ ] Identify noncritical dependencies whose loss can support a defined degraded mode (for example telemetry export) and explicitly exclude trust/integrity controls that must fail closed.
- [ ] Define each degraded mode's allowed operations, duration limit, risk, operator signal, and exit condition.
- [ ] Implement state flag/reason and propagate it to readiness, metrics, logs, explain output, and gate/incident tooling.
- [ ] Ensure degraded mode cannot broaden capability or silently disable signature/policy/isolation checks.
- [ ] Queue/buffer noncritical outputs only within strict resource bounds and define drop behavior.
- [ ] Reconcile buffered/stateful work after dependency recovery without duplication or reordering surprises.
- [ ] Test entry/exit, maximum duration, repeated flapping, buffer exhaustion, and simultaneous critical dependency failure.

### Cross-cutting hardening / verification gates

- [ ] Define detection threshold, state transition, side effects, retryability, cleanup, operator signal, and recovery objective for the failure scenario.
- [ ] Use bounded deadlines/retries and idempotent reconciliation; never allow recovery logic to create duplicate execution or bypass current policy.
- [ ] Preserve ownership/fencing/config epochs across crashes and partitions so stale actors cannot mutate current state.
- [ ] Inject the failure deterministically and assert resource cleanup, audit continuity, expected alerting, and measured recovery time.
- [ ] Document and test compound/common-mode failures, not only a single idealized component failure.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-056` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-056`.
- [ ] RTM entry linking `MC-056` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-056` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-057 — Duplicate execution/split-brain protection

**Priority:** P0  
**Audit finding:** (`C058`). No lease, fencing token, epoch, ownership lock, or duplicate-instance detector exists.  
**Risk:** Without this mechanism, ordinary failures or partitions can cascade into duplicate execution, unsafe recovery, or prolonged outage.  
**Suggested blockers/dependencies:** `MC-016`, `MC-024`, `MC-029`  
**Mapped INV-27 requirements:**

- `C058` — Protect against split-brain, duplicate ownership, stale controllers, or duplicate execution where relevant.

### Component-specific engineering checklist

- [ ] Inventory mutable state and define durability/consistency expectations for instance ownership, lifecycle state, idempotency records, config/policy revisions, audit offsets, and queued operations.
- [ ] Use transactional/atomic persistence for state transitions that cannot be partially visible.
- [ ] Define write-ahead/event/reconciliation strategy so process/node crash at any instruction point converges to a safe state.
- [ ] Make replay operations idempotent and validate current ownership epoch/policy before reapplying side effects.
- [ ] Define treatment of orphan VMs/resources discovered after restart and how they are adopted, quarantined, or terminated.
- [ ] Prevent recovery from replaying revoked/obsolete policy or restarting an image no longer admissible.
- [ ] Add crash-point tests around each state transition and side-effect boundary with deterministic recovery assertions.

### Cross-cutting hardening / verification gates

- [ ] Define detection threshold, state transition, side effects, retryability, cleanup, operator signal, and recovery objective for the failure scenario.
- [ ] Use bounded deadlines/retries and idempotent reconciliation; never allow recovery logic to create duplicate execution or bypass current policy.
- [ ] Preserve ownership/fencing/config epochs across crashes and partitions so stale actors cannot mutate current state.
- [ ] Inject the failure deterministically and assert resource cleanup, audit continuity, expected alerting, and measured recovery time.
- [ ] Document and test compound/common-mode failures, not only a single idealized component failure.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-057` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-057`.
- [ ] RTM entry linking `MC-057` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-057` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-058 — Quarantine/freeze/disable control

**Priority:** P0  
**Audit finding:** (`C059`). No per-image/per-tenant quarantine or live execution freeze mechanism exists.  
**Risk:** Without this mechanism, ordinary failures or partitions can cascade into duplicate execution, unsafe recovery, or prolonged outage.  
**Suggested blockers/dependencies:** `MC-025`, `MC-047`  
**Mapped INV-27 requirements:**

- `C059` — Provide quarantine, freeze, disable, or isolation controls for unsafe Unikernel execution behavior.

### Component-specific engineering checklist

- [ ] Define a unique workload/instance ownership model using leases, fencing tokens, generations/epochs, or equivalent monotonic authority.
- [ ] Require the current token on every destructive/start/attach mutation to prevent stale controllers from acting.
- [ ] Make VM/resource names/IDs collision resistant and tie them to tenant/workload identity plus ownership generation.
- [ ] Detect existing backend instances before create and reconcile rather than blindly duplicating.
- [ ] Define lease expiry/renewal under partitions and ensure two sides cannot both remain authoritative.
- [ ] Audit ownership transfer and duplicate-detection decisions.
- [ ] Stress-test concurrent starts/stops, controller failover, long GC pauses, network partition, delayed messages, and stale retries.

### Cross-cutting hardening / verification gates

- [ ] Define detection threshold, state transition, side effects, retryability, cleanup, operator signal, and recovery objective for the failure scenario.
- [ ] Use bounded deadlines/retries and idempotent reconciliation; never allow recovery logic to create duplicate execution or bypass current policy.
- [ ] Preserve ownership/fencing/config epochs across crashes and partitions so stale actors cannot mutate current state.
- [ ] Inject the failure deterministically and assert resource cleanup, audit continuity, expected alerting, and measured recovery time.
- [ ] Document and test compound/common-mode failures, not only a single idealized component failure.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-058` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-058`.
- [ ] RTM entry linking `MC-058` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-058` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-059 — Fault-injection suite

**Priority:** P1  
**Audit finding:** (`C060`, `C089`). No VM/node/site/network/provider/control-plane fault harness exists.  
**Risk:** Without this mechanism, ordinary failures or partitions can cascade into duplicate execution, unsafe recovery, or prolonged outage.  
**Suggested blockers/dependencies:** `MC-051`, `MC-052`, `MC-053`, `MC-054`, `MC-055`, `MC-056`, `MC-057`, `MC-058`  
**Mapped INV-27 requirements:**

- `C060` — Run fault-injection tests proving Unikernel execution recovery against documented objectives.
- `C089` — Create disaster, partition, reconnect, and degraded-control-plane tests.

### Component-specific engineering checklist

- [ ] Implement quarantine scopes for image digest, signer/toolchain, tenant/workload, host/site, backend version, and policy revision.
- [ ] Separate `deny new admissions`, `freeze lifecycle mutations`, `isolate network/devices`, `graceful stop`, and `force terminate` actions with explicit authorization.
- [ ] Make quarantine state durable, monotonic where necessary, and visible to all controllers before new starts.
- [ ] Ensure quarantined images cannot bypass policy by renaming/reuploading; key the rule to immutable identity/digest/provenance.
- [ ] Provide a break-glass release path requiring multi-party or elevated approval for high-severity quarantines and full audit evidence.
- [ ] Test quarantine during admission, boot, running state, controller outage, and rollout.
- [ ] Verify emergency controls remain usable during partial outages and cannot be disabled by the affected tenant/workload.

### Cross-cutting hardening / verification gates

- [ ] Define detection threshold, state transition, side effects, retryability, cleanup, operator signal, and recovery objective for the failure scenario.
- [ ] Use bounded deadlines/retries and idempotent reconciliation; never allow recovery logic to create duplicate execution or bypass current policy.
- [ ] Preserve ownership/fencing/config epochs across crashes and partitions so stale actors cannot mutate current state.
- [ ] Inject the failure deterministically and assert resource cleanup, audit continuity, expected alerting, and measured recovery time.
- [ ] Document and test compound/common-mode failures, not only a single idealized component failure.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-059` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-059`.
- [ ] RTM entry linking `MC-059` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-059` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

# G. Performance & resource efficiency

## MC-060 — Reproducible performance baseline suite

**Priority:** P1  
**Audit finding:** (`C061`). No benchmarks measure admission/boot latency, throughput, CPU, memory, storage, network, or power.  
**Risk:** Without this evidence/control, capacity and performance limits are unknown and releases can regress unpredictably under real load.  
**Suggested blockers/dependencies:** `MC-007`, `MC-009`, `MC-069`, `MC-070`  
**Mapped INV-27 requirements:**

- `C061` — Establish reproducible baselines for Unikernel execution latency, throughput, startup, CPU, memory, storage, network, and power overhead.

### Component-specific engineering checklist

- [ ] Build a fault-injection framework capable of failing verifier/parser calls, VMM operations, host/node availability, network links, storage, trust/policy/key services, audit sink, and control-plane APIs.
- [ ] Associate each injected fault with an expected state transition, cleanup behavior, alert, and recovery objective.
- [ ] Support latency, timeout, error, partial-success, corruption (where safe), packet loss/reordering, partition, process kill, node reboot, and capacity exhaustion scenarios.
- [ ] Run tests in isolated environments with deterministic seeds and automatic cleanup.
- [ ] Measure recovery time, data/evidence integrity, duplicate execution, leaked resources, and SLO impact.
- [ ] Include compound faults/common-mode scenarios rather than testing only one failure at a time.
- [ ] Archive scenario definition, seed, topology, versions, telemetry, and verdict as certification evidence.

### Cross-cutting hardening / verification gates

- [ ] Use reproducible benchmark/test environments with immutable fixture/workload versions and recorded hardware/software fingerprints.
- [ ] Collect distributions and raw data, not only averages, and define statistically meaningful pass/fail thresholds.
- [ ] Measure security/control-plane overhead separately from guest workload usage and attribute shared costs explicitly.
- [ ] Integrate approved thresholds into the release gate and preserve baseline history for regression analysis.
- [ ] Verify optimizations do not weaken isolation, verification, durability, or fail-closed semantics.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-060` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-060`.
- [ ] RTM entry linking `MC-060` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-060` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-061 — p50/p95/p99/worst-case thresholds

**Priority:** P1  
**Audit finding:** (`C062`). Only one prose p99 admission SLO is present; no complete threshold set or benchmark gate exists.  
**Risk:** Without this evidence/control, capacity and performance limits are unknown and releases can regress unpredictably under real load.  
**Suggested blockers/dependencies:** `MC-060`  
**Mapped INV-27 requirements:**

- `C062` — Define p50, p95, p99, and worst-case performance thresholds for Unikernel execution.

### Component-specific engineering checklist

- [ ] Define benchmark workloads and immutable fixture digests covering admission-only, signature/provenance verification, binary parsing, VM creation, boot-to-ready, steady-state runtime overhead, and teardown.
- [ ] Pin test environment details: CPU model/features, cores, memory, storage, kernel/OS, VMM/backend, Python/runtime, power mode, and competing load.
- [ ] Measure wall-clock latency distributions plus CPU time, allocations/RSS, I/O, network, storage, and host/guest memory footprint.
- [ ] Separate cold-cache/cold-start from warm-path results and record warmup methodology.
- [ ] Use enough samples/duration to characterize tails; preserve raw data and statistical summaries.
- [ ] Automate benchmark execution and machine-readable result export so releases can be compared.
- [ ] Establish noise/variance thresholds and rerun rules so environmental noise is not mistaken for regression.

### Cross-cutting hardening / verification gates

- [ ] Use reproducible benchmark/test environments with immutable fixture/workload versions and recorded hardware/software fingerprints.
- [ ] Collect distributions and raw data, not only averages, and define statistically meaningful pass/fail thresholds.
- [ ] Measure security/control-plane overhead separately from guest workload usage and attribute shared costs explicitly.
- [ ] Integrate approved thresholds into the release gate and preserve baseline history for regression analysis.
- [ ] Verify optimizations do not weaken isolation, verification, durability, or fail-closed semantics.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-061` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-061`.
- [ ] RTM entry linking `MC-061` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-061` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-062 — Steady/burst/overload/scale/recovery load tests

**Priority:** P1  
**Audit finding:** (`C063`, `C088`). No workload generator or results artifact exists.  
**Risk:** Without this evidence/control, capacity and performance limits are unknown and releases can regress unpredictably under real load.  
**Suggested blockers/dependencies:** `MC-060`, `MC-061`  
**Mapped INV-27 requirements:**

- `C063` — Measure Unikernel execution under steady load, burst load, overload, scale-out, scale-in, and recovery.
- `C088` — Create benchmark, soak, burst, and fleet-scale tests appropriate to Unikernel execution.

### Component-specific engineering checklist

- [ ] Define p50/p95/p99 and bounded worst-case/timeout objectives separately for manifest parse, seal verification, admission decision, VM create, boot-to-ready, stop, and quarantine.
- [ ] Define throughput/density/resource ceilings tied to specified hardware classes and workload profiles.
- [ ] Specify thresholds for both nominal and stressed operating modes rather than one global number.
- [ ] Define failure behavior when a hard limit is exceeded and ensure timeouts are below upstream deadlines.
- [ ] Store thresholds as versioned machine-readable policy consumed by the performance gate.
- [ ] Require statistical confidence/sample minimums and document whether thresholds are absolute, relative-to-baseline, or both.
- [ ] Review thresholds when hardware/backend architecture changes, not merely when code changes.

### Cross-cutting hardening / verification gates

- [ ] Use reproducible benchmark/test environments with immutable fixture/workload versions and recorded hardware/software fingerprints.
- [ ] Collect distributions and raw data, not only averages, and define statistically meaningful pass/fail thresholds.
- [ ] Measure security/control-plane overhead separately from guest workload usage and attribute shared costs explicitly.
- [ ] Integrate approved thresholds into the release gate and preserve baseline history for regression analysis.
- [ ] Verify optimizations do not weaken isolation, verification, durability, or fail-closed semantics.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-062` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-062`.
- [ ] RTM entry linking `MC-062` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-062` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-063 — Per-tenant/per-workload overhead accounting

**Priority:** P1  
**Audit finding:** (`C064`). No accounting/telemetry implementation exists.  
**Risk:** Without this evidence/control, capacity and performance limits are unknown and releases can regress unpredictably under real load.  
**Suggested blockers/dependencies:** `MC-060`, `MC-070`  
**Mapped INV-27 requirements:**

- `C064` — Measure per-workload and per-tenant overhead introduced by Unikernel execution.

### Component-specific engineering checklist

- [ ] Create workload profiles for steady-state, burst, overload, scale-out, scale-in, restart/recovery, and mixed-tenant behavior.
- [ ] Drive realistic arrival processes and resource mixes rather than only tight loops/microbenchmarks.
- [ ] Measure queue depth, rejection/load shedding, tail latency, CPU/memory pressure, VMM create rate, boot failures, and recovery after overload.
- [ ] Verify per-tenant fairness and that overload in one class does not starve critical stop/quarantine/control operations.
- [ ] Exercise autoscaling/capacity changes if present and verify no duplicate ownership during scale transitions.
- [ ] Run long enough to expose leaks and post-burst backlog behavior.
- [ ] Archive workload generator version/configuration, environment identity, raw measurements, and pass/fail thresholds.

### Cross-cutting hardening / verification gates

- [ ] Use reproducible benchmark/test environments with immutable fixture/workload versions and recorded hardware/software fingerprints.
- [ ] Collect distributions and raw data, not only averages, and define statistically meaningful pass/fail thresholds.
- [ ] Measure security/control-plane overhead separately from guest workload usage and attribute shared costs explicitly.
- [ ] Integrate approved thresholds into the release gate and preserve baseline history for regression analysis.
- [ ] Verify optimizations do not weaken isolation, verification, durability, or fail-closed semantics.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-063` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-063`.
- [ ] RTM entry linking `MC-063` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-063` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-064 — Copy/hop/context-switch/duplication analysis

**Priority:** P1  
**Audit finding:** (`C065-C066`). No profiling evidence or optimization implementation exists.  
**Risk:** Without this evidence/control, capacity and performance limits are unknown and releases can regress unpredictably under real load.  
**Suggested blockers/dependencies:** `MC-060`  
**Mapped INV-27 requirements:**

- `C065` — Identify avoidable serialization, copies, context switches, network hops, duplicated images, or duplicated state in Unikernel execution.
- `C066` — Apply locality, caching, direct composition, batching, zero-copy, or kernel-bypass optimizations where semantics permit.

### Component-specific engineering checklist

- [ ] Define resource-attribution keys for tenant, workload, image digest, instance, host, and operation.
- [ ] Measure verifier CPU/time, parser allocations, VMM overhead, host memory, vCPU time, network bytes/packets, storage I/O, and telemetry/audit overhead per workload where attributable.
- [ ] Separate fixed per-instance overhead from workload-driven usage and shared control-plane costs.
- [ ] Prevent high-cardinality accounting from destabilizing telemetry; use bounded labels and detailed sampled records when needed.
- [ ] Compare observed usage against quotas/reservations and expose chargeback/capacity inputs if required.
- [ ] Test attribution under concurrent tenants and resource cleanup after termination.
- [ ] Validate that accounting metadata cannot be spoofed by guest-controlled values.

### Cross-cutting hardening / verification gates

- [ ] Use reproducible benchmark/test environments with immutable fixture/workload versions and recorded hardware/software fingerprints.
- [ ] Collect distributions and raw data, not only averages, and define statistically meaningful pass/fail thresholds.
- [ ] Measure security/control-plane overhead separately from guest workload usage and attribute shared costs explicitly.
- [ ] Integrate approved thresholds into the release gate and preserve baseline history for regression analysis.
- [ ] Verify optimizations do not weaken isolation, verification, durability, or fail-closed semantics.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-064` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-064`.
- [ ] RTM entry linking `MC-064` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-064` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-065 — Resource bounds enforcement

**Priority:** P1  
**Audit finding:** (`C067`). No memory, queue, buffer, concurrency, CPU, vCPU, or fan-out limits are enforced by runtime code.  
**Risk:** Without this evidence/control, capacity and performance limits are unknown and releases can regress unpredictably under real load.  
**Suggested blockers/dependencies:** `MC-060`, `MC-064`  
**Mapped INV-27 requirements:**

- `C067` — Bound memory growth, queue depth, buffer size, concurrency, and resource fan-out.

### Component-specific engineering checklist

- [ ] Profile the full admission/start path and enumerate serialization/deserialization boundaries, memory copies, filesystem reads, process/thread context switches, RPC/network hops, image copies, and duplicated metadata/state.
- [ ] Quantify cost of each stage using tracing/profiling rather than assuming optimization targets.
- [ ] Identify image re-reading/re-hashing opportunities that can be eliminated safely using immutable content-addressed handles.
- [ ] Identify redundant policy/schema/provenance validation and cache only results that are cryptographically bound to the same inputs/policy revision.
- [ ] Measure VMM boot/device setup path for avoidable orchestration round trips.
- [ ] Document which copies/hops are required security boundaries and must not be removed.
- [ ] Create regression measurements so optimizations can prove improvement without weakening verification semantics.

### Cross-cutting hardening / verification gates

- [ ] Use reproducible benchmark/test environments with immutable fixture/workload versions and recorded hardware/software fingerprints.
- [ ] Collect distributions and raw data, not only averages, and define statistically meaningful pass/fail thresholds.
- [ ] Measure security/control-plane overhead separately from guest workload usage and attribute shared costs explicitly.
- [ ] Integrate approved thresholds into the release gate and preserve baseline history for regression analysis.
- [ ] Verify optimizations do not weaken isolation, verification, durability, or fail-closed semantics.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-065` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-065`.
- [ ] RTM entry linking `MC-065` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-065` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-066 — Edge power/thermal measurement

**Priority:** P2  
**Audit finding:** (`C068`). No methodology or data exists.  
**Risk:** Without this evidence/control, capacity and performance limits are unknown and releases can regress unpredictably under real load.  
**Suggested blockers/dependencies:** `MC-065`  
**Mapped INV-27 requirements:**

- `C068` — Measure power and thermal impact on constrained edge nodes where relevant.

### Component-specific engineering checklist

- [ ] Evaluate locality of verifier, image store, policy/trust services, and VMM control path; co-locate only when trust and fault-domain requirements permit.
- [ ] Implement content-addressed caching keyed by image/provenance/policy digests with explicit validity/freshness rules.
- [ ] Use batching for independent non-security-critical lookups/telemetry where it reduces overhead without delaying fail-closed decisions.
- [ ] Use zero-copy/mmap/read-only sharing only when lifetime, immutability, and tenant-isolation properties are proven.
- [ ] Consider direct VMM composition or kernel-bypass networking only with documented threat-model and operational trade-offs.
- [ ] Benchmark every optimization against baseline for tail latency, CPU/memory, and failure behavior.
- [ ] Provide a kill switch/fallback path for optional optimizations so correctness never depends on them.

### Cross-cutting hardening / verification gates

- [ ] Use reproducible benchmark/test environments with immutable fixture/workload versions and recorded hardware/software fingerprints.
- [ ] Collect distributions and raw data, not only averages, and define statistically meaningful pass/fail thresholds.
- [ ] Measure security/control-plane overhead separately from guest workload usage and attribute shared costs explicitly.
- [ ] Integrate approved thresholds into the release gate and preserve baseline history for regression analysis.
- [ ] Verify optimizations do not weaken isolation, verification, durability, or fail-closed semantics.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-066` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-066`.
- [ ] RTM entry linking `MC-066` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-066` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-067 — Capacity model and saturation signals

**Priority:** P1  
**Audit finding:** (`C069`). No model or telemetry exists.  
**Risk:** Without this evidence/control, capacity and performance limits are unknown and releases can regress unpredictably under real load.  
**Suggested blockers/dependencies:** `MC-018`, `MC-029`, `MC-060`  
**Mapped INV-27 requirements:**

- `C069` — Define capacity models and saturation signals that predict when Unikernel execution needs more resources.

### Component-specific engineering checklist

- [ ] Set explicit hard limits for manifest/image size, sections/symbols/relocations, parser allocations, verification concurrency, request body size, queue depth, retries, diagnostic output, VMMs per host, vCPU, memory, network connections, and attached devices.
- [ ] Enforce limits at the earliest trusted boundary before allocating proportional resources.
- [ ] Use per-tenant and global ceilings with reserved capacity for control/recovery operations.
- [ ] Make limits configuration-backed but bounded by non-overridable safety maxima.
- [ ] Emit structured `RESOURCE_LIMIT`/`OVERLOADED` errors and metrics without dumping attacker-controlled payloads.
- [ ] Test exact boundary, over-boundary, concurrent pressure, integer overflow, and slow-loris/resource-hoarding scenarios.
- [ ] Prove resources are released after rejection, timeout, failed boot, and forced termination.

### Cross-cutting hardening / verification gates

- [ ] Use reproducible benchmark/test environments with immutable fixture/workload versions and recorded hardware/software fingerprints.
- [ ] Collect distributions and raw data, not only averages, and define statistically meaningful pass/fail thresholds.
- [ ] Measure security/control-plane overhead separately from guest workload usage and attribute shared costs explicitly.
- [ ] Integrate approved thresholds into the release gate and preserve baseline history for regression analysis.
- [ ] Verify optimizations do not weaken isolation, verification, durability, or fail-closed semantics.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-067` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-067`.
- [ ] RTM entry linking `MC-067` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-067` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-068 — Performance regression release gate

**Priority:** P2  
**Audit finding:** (`C070`). No benchmark history/threshold gate exists.  
**Risk:** Without this evidence/control, capacity and performance limits are unknown and releases can regress unpredictably under real load.  
**Suggested blockers/dependencies:** `MC-060`  
**Mapped INV-27 requirements:**

- `C070` — Block releases that regress approved Unikernel execution startup, density, throughput, or tail-latency thresholds.

### Component-specific engineering checklist

- [ ] Identify edge hardware classes where power/thermal behavior is a real deployment constraint and define representative test devices.
- [ ] Measure idle, verification, boot burst, steady runtime, network/storage activity, and teardown power using a repeatable instrumentation method.
- [ ] Capture thermal throttling, sustained frequency, energy per admission/boot/work unit, and battery impact where applicable.
- [ ] Run tests at controlled ambient conditions or record environmental variables that materially affect results.
- [ ] Define acceptable thermal/power envelopes and behavior when host sensors indicate unsafe conditions.
- [ ] Correlate power regressions with software/backend changes and preserve raw measurement data.
- [ ] Document when C068 is not applicable to a deployment class rather than leaving it silently untested.

### Cross-cutting hardening / verification gates

- [ ] Use reproducible benchmark/test environments with immutable fixture/workload versions and recorded hardware/software fingerprints.
- [ ] Collect distributions and raw data, not only averages, and define statistically meaningful pass/fail thresholds.
- [ ] Measure security/control-plane overhead separately from guest workload usage and attribute shared costs explicitly.
- [ ] Integrate approved thresholds into the release gate and preserve baseline history for regression analysis.
- [ ] Verify optimizations do not weaken isolation, verification, durability, or fail-closed semantics.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-068` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-068`.
- [ ] RTM entry linking `MC-068` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-068` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

# H. Observability & explainability

## MC-069 — Runtime health/readiness/version/config/dependency endpoint

**Priority:** P1  
**Audit finding:** (`C071`). No service endpoint/status schema exists.  
**Risk:** Without this telemetry/explainability capability, operators cannot distinguish policy, dependency, capacity, attack, and software-failure causes reliably.  
**Suggested blockers/dependencies:** `MC-023`, `MC-029`  
**Mapped INV-27 requirements:**

- `C071` — Expose Unikernel execution health, readiness, version, configuration, dependency status, and active capability set.

### Component-specific engineering checklist

- [ ] Define a stable status schema containing component version/build ID, active config/policy revision, trust freshness, backend/VMM version/status, supported architectures/capabilities, queue/capacity state, and dependency health.
- [ ] Separate liveness from readiness and include explicit degraded/quarantined states.
- [ ] Expose the endpoint over an authenticated/authorized local or control-plane interface with bounded response size and no secrets.
- [ ] Include timestamp/age for dependency status so cached green values cannot look current indefinitely.
- [ ] Make status generation nonblocking and resilient to a failed dependency; time-bound subchecks and report unknown rather than hanging.
- [ ] Provide a CLI rendering and machine-readable form that share the same source data.
- [ ] Test stale dependency, partial backend outage, config transition, and secret-redaction behavior.

### Cross-cutting hardening / verification gates

- [ ] Define stable telemetry schemas with units, cardinality bounds, privacy classification, retention, and versioning rules.
- [ ] Correlate logs/metrics/traces/audit/decision records through stable IDs without using telemetry as an authorization source.
- [ ] Redact secrets and tenant-sensitive values centrally; test redaction with canary values and hostile strings.
- [ ] Bound telemetry resource use and define behavior when exporters/backends are unavailable.
- [ ] Create operator-visible evidence that distinguishes policy rejection, dependency degradation, suspected attack, capacity saturation, and software defect.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-069` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-069`.
- [ ] RTM entry linking `MC-069` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-069` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-070 — Metrics implementation

**Priority:** P1  
**Audit finding:** (`C072`). Contract names conceptual signals, but no counters/histograms/gauges exporter exists.  
**Risk:** Without this telemetry/explainability capability, operators cannot distinguish policy, dependency, capacity, attack, and software-failure causes reliably.  
**Suggested blockers/dependencies:** `MC-069`  
**Mapped INV-27 requirements:**

- `C072` — Emit structured metrics for rate, errors, latency, saturation, backlog, and resource use.

### Component-specific engineering checklist

- [ ] Define metrics for request/admission rate, verdicts by stable reason code, parse/verify/start/boot/stop latency histograms, queue depth/age, retry counts, resource saturation, running instances, failures, and cleanup leaks.
- [ ] Use bounded label sets; never label by raw tenant/workload/image IDs in globally aggregated metrics unless a controlled cardinality strategy is defined.
- [ ] Define units, histogram buckets/SLO alignment, monotonicity, reset semantics, and exporter failure behavior.
- [ ] Instrument critical path timing from validated entry to final decision and separate backend latency from verifier latency.
- [ ] Expose resource metrics needed for admission control and capacity planning, not just dashboards.
- [ ] Test metric emission on success/failure/degraded paths and validate cardinality under adversarial input.
- [ ] Version metric names/semantics and document deprecation before breaking dashboards/alerts.

### Cross-cutting hardening / verification gates

- [ ] Define stable telemetry schemas with units, cardinality bounds, privacy classification, retention, and versioning rules.
- [ ] Correlate logs/metrics/traces/audit/decision records through stable IDs without using telemetry as an authorization source.
- [ ] Redact secrets and tenant-sensitive values centrally; test redaction with canary values and hostile strings.
- [ ] Bound telemetry resource use and define behavior when exporters/backends are unavailable.
- [ ] Create operator-visible evidence that distinguishes policy rejection, dependency degradation, suspected attack, capacity saturation, and software defect.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-070` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-070`.
- [ ] RTM entry linking `MC-070` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-070` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-071 — Structured logging implementation

**Priority:** P1  
**Audit finding:** (`C073`). No stable structured log schema/emitter exists.  
**Risk:** Without this telemetry/explainability capability, operators cannot distinguish policy, dependency, capacity, attack, and software-failure causes reliably.  
**Suggested blockers/dependencies:** `MC-069`  
**Mapped INV-27 requirements:**

- `C073` — Emit structured logs with stable node, tenant, workload, component, and operation identifiers.

### Component-specific engineering checklist

- [ ] Define a versioned structured log schema with timestamp, severity, component/build, operation, request/correlation ID, decision ID, host/site, safe tenant/workload identifiers, image digest prefix/full protected field, and stable event code.
- [ ] Use structured fields rather than parsing human message strings for automation.
- [ ] Centralize redaction/escaping and cap attacker-controlled string lengths to prevent log injection/resource abuse.
- [ ] Never log raw manifests, credentials, secrets, signatures/private material, or cross-tenant payloads by default.
- [ ] Define sampling/rate limits for repetitive failures while preserving security-audit events losslessly.
- [ ] Ensure logs distinguish policy rejection, malformed input, dependency failure, backend defect, operator action, and internal bug.
- [ ] Add schema tests, redaction canaries, newline/control-character injection tests, and log-volume stress tests.

### Cross-cutting hardening / verification gates

- [ ] Define stable telemetry schemas with units, cardinality bounds, privacy classification, retention, and versioning rules.
- [ ] Correlate logs/metrics/traces/audit/decision records through stable IDs without using telemetry as an authorization source.
- [ ] Redact secrets and tenant-sensitive values centrally; test redaction with canary values and hostile strings.
- [ ] Bound telemetry resource use and define behavior when exporters/backends are unavailable.
- [ ] Create operator-visible evidence that distinguishes policy rejection, dependency degradation, suspected attack, capacity saturation, and software defect.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-071` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-071`.
- [ ] RTM entry linking `MC-071` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-071` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-072 — Distributed trace propagation

**Priority:** P1  
**Audit finding:** (`C074`). No trace context support exists.  
**Risk:** Without this telemetry/explainability capability, operators cannot distinguish policy, dependency, capacity, attack, and software-failure causes reliably.  
**Suggested blockers/dependencies:** `MC-069`  
**Mapped INV-27 requirements:**

- `C074` — Propagate trace context across all relevant Unikernel execution boundaries.

### Component-specific engineering checklist

- [ ] Adopt a trace-context standard and define trust rules for inbound trace headers so untrusted tenants cannot forge privileged correlation identity.
- [ ] Create spans for admission, manifest parse, digest/signature/provenance verification, policy evaluation, VMM create, boot/readiness, stop, and cleanup.
- [ ] Propagate trace context across internal RPC/queue/backend boundaries and link asynchronous reconciliation with span links where direct parentage is inappropriate.
- [ ] Attach bounded stable attributes such as operation, verdict code, backend, architecture, policy revision—not raw high-cardinality secrets/tenant payloads.
- [ ] Sample ordinary traffic according to policy while retaining/forcing traces for critical failures where privacy permits.
- [ ] Correlate trace IDs with logs/audit/decision IDs without making the trace system an authorization source.
- [ ] Test missing/malformed/oversized trace headers and exporter outage.

### Cross-cutting hardening / verification gates

- [ ] Define stable telemetry schemas with units, cardinality bounds, privacy classification, retention, and versioning rules.
- [ ] Correlate logs/metrics/traces/audit/decision records through stable IDs without using telemetry as an authorization source.
- [ ] Redact secrets and tenant-sensitive values centrally; test redaction with canary values and hostile strings.
- [ ] Bound telemetry resource use and define behavior when exporters/backends are unavailable.
- [ ] Create operator-visible evidence that distinguishes policy rejection, dependency degradation, suspected attack, capacity saturation, and software defect.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-072` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-072`.
- [ ] RTM entry linking `MC-072` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-072` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-073 — Safe high-cardinality diagnostics

**Priority:** P1  
**Audit finding:** (`C075`). No diagnostics endpoint/redaction/cardinality guard exists.  
**Risk:** Without this telemetry/explainability capability, operators cannot distinguish policy, dependency, capacity, attack, and software-failure causes reliably.  
**Suggested blockers/dependencies:** `MC-071`  
**Mapped INV-27 requirements:**

- `C075` — Expose high-cardinality diagnostic detail safely without leaking tenant or secret data.

### Component-specific engineering checklist

- [ ] Define an authenticated diagnostic API/CLI that can retrieve per-request/instance decision detail without exposing other tenants' data.
- [ ] Separate high-cardinality diagnostic storage from low-cardinality metrics and apply quotas/retention limits.
- [ ] Redact secrets, credentials, raw signatures where unnecessary, host-sensitive paths, and cross-tenant topology.
- [ ] Use opaque internal IDs and authorization checks rather than accepting arbitrary tenant/workload selectors without ownership validation.
- [ ] Cap query ranges/result sizes and rate-limit expensive diagnostic operations.
- [ ] Record who accessed sensitive diagnostic data in the security audit ledger.
- [ ] Test cross-tenant lookup, wildcard abuse, oversized queries, redaction, and diagnostic-store exhaustion.

### Cross-cutting hardening / verification gates

- [ ] Define stable telemetry schemas with units, cardinality bounds, privacy classification, retention, and versioning rules.
- [ ] Correlate logs/metrics/traces/audit/decision records through stable IDs without using telemetry as an authorization source.
- [ ] Redact secrets and tenant-sensitive values centrally; test redaction with canary values and hostile strings.
- [ ] Bound telemetry resource use and define behavior when exporters/backends are unavailable.
- [ ] Create operator-visible evidence that distinguishes policy rejection, dependency degradation, suspected attack, capacity saturation, and software defect.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-073` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-073`.
- [ ] RTM entry linking `MC-073` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-073` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-074 — Decision-reason recording for every automated action

**Priority:** P1  
**Audit finding:** (`C076`). Seal exceptions explain some rejections, but there is no durable decision record for all actions.  
**Risk:** Without this telemetry/explainability capability, operators cannot distinguish policy, dependency, capacity, attack, and software-failure causes reliably.  
**Suggested blockers/dependencies:** `MC-048`, `MC-071`  
**Mapped INV-27 requirements:**

- `C076` — Record the reason for every automated decision made by Unikernel execution.

### Component-specific engineering checklist

- [ ] Define a durable decision record for every automated admit/reject, policy choice, placement/backend selection if owned, retry, quarantine, stop/terminate, rollback, and emergency action.
- [ ] Record normalized inputs by immutable references/digests, evaluated policy/config revision, matched rules, constraint values, outcome, stable reason code, and software version.
- [ ] Use a unique decision ID propagated to response, logs, audit, metrics exemplars/traces, and operator explain output.
- [ ] Avoid storing secrets/raw untrusted payloads; preserve hashes/field-level evidence sufficient to reproduce the decision.
- [ ] Ensure the record is committed atomically with or before security-sensitive side effects where practical.
- [ ] Provide deterministic replay/evaluation tooling against archived policy/config for supported versions.
- [ ] Test every action path for a decision record, including internal errors and rejected malformed input.

### Cross-cutting hardening / verification gates

- [ ] Define stable telemetry schemas with units, cardinality bounds, privacy classification, retention, and versioning rules.
- [ ] Correlate logs/metrics/traces/audit/decision records through stable IDs without using telemetry as an authorization source.
- [ ] Redact secrets and tenant-sensitive values centrally; test redaction with canary values and hostile strings.
- [ ] Bound telemetry resource use and define behavior when exporters/backends are unavailable.
- [ ] Create operator-visible evidence that distinguishes policy rejection, dependency degradation, suspected attack, capacity saturation, and software defect.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-074` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-074`.
- [ ] RTM entry linking `MC-074` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-074` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-075 — Operator explain view

**Priority:** P1  
**Audit finding:** (`C077`). No CLI/API/UI explain surface exists.  
**Risk:** Without this telemetry/explainability capability, operators cannot distinguish policy, dependency, capacity, attack, and software-failure causes reliably.  
**Suggested blockers/dependencies:** `MC-074`  
**Mapped INV-27 requirements:**

- `C077` — Provide an operator-readable explain view linking decisions to input state, policies, topology, and constraints.

### Component-specific engineering checklist

- [ ] Build an operator-facing `explain` command/API that accepts decision/instance/image identifiers and returns the causal chain from inputs to policy to outcome.
- [ ] Show image digest/signature/provenance status, parser findings, architecture/capability/syscall evidence, active config/policy revision, quota/capacity facts, dependency health, and final reason codes.
- [ ] Clearly distinguish observed facts, policy rules, inferred properties, and operator overrides.
- [ ] Link to relevant audit events, trace/log correlation IDs, release lineage, and runbook actions.
- [ ] Enforce authorization/redaction and tenant scoping on explain data.
- [ ] Provide stable JSON output plus readable text rendering for incident use.
- [ ] Test explanations for success, each major rejection family, degraded state, stale policy, and partially unavailable telemetry.

### Cross-cutting hardening / verification gates

- [ ] Define stable telemetry schemas with units, cardinality bounds, privacy classification, retention, and versioning rules.
- [ ] Correlate logs/metrics/traces/audit/decision records through stable IDs without using telemetry as an authorization source.
- [ ] Redact secrets and tenant-sensitive values centrally; test redaction with canary values and hostile strings.
- [ ] Bound telemetry resource use and define behavior when exporters/backends are unavailable.
- [ ] Create operator-visible evidence that distinguishes policy rejection, dependency degradation, suspected attack, capacity saturation, and software defect.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-075` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-075`.
- [ ] RTM entry linking `MC-075` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-075` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-076 — Release-lineage/infrastructure-graph correlation

**Priority:** P1  
**Audit finding:** (`C078`). No release IDs/topology IDs or graph integration exists.  
**Risk:** Without this telemetry/explainability capability, operators cannot distinguish policy, dependency, capacity, attack, and software-failure causes reliably.  
**Suggested blockers/dependencies:** `MC-004`, `MC-030`, `MC-071`  
**Mapped INV-27 requirements:**

- `C078` — Correlate Unikernel execution events with application release lineage and the live infrastructure graph.

### Component-specific engineering checklist

- [ ] Define immutable release/build identifiers and attach them to verifier, backend adapter, schema, configuration, and running instance records.
- [ ] Integrate with infrastructure/topology identifiers for host, site, network segment, storage/device attachments, and control-plane revision without exposing sensitive topology broadly.
- [ ] Record source revision, artifact digest, SBOM/provenance subject, deployment wave, and active config/policy revision for each running instance.
- [ ] Allow incident tooling to answer which instances are affected by a vulnerable release/toolchain/backend/config revision.
- [ ] Handle topology changes and instance migration/failover with temporal lineage rather than overwriting history.
- [ ] Propagate lineage IDs into logs/traces/audit/decision records.
- [ ] Test correlation completeness on start, rollout, rollback, failover, and termination.

### Cross-cutting hardening / verification gates

- [ ] Define stable telemetry schemas with units, cardinality bounds, privacy classification, retention, and versioning rules.
- [ ] Correlate logs/metrics/traces/audit/decision records through stable IDs without using telemetry as an authorization source.
- [ ] Redact secrets and tenant-sensitive values centrally; test redaction with canary values and hostile strings.
- [ ] Bound telemetry resource use and define behavior when exporters/backends are unavailable.
- [ ] Create operator-visible evidence that distinguishes policy rejection, dependency degradation, suspected attack, capacity saturation, and software defect.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-076` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-076`.
- [ ] RTM entry linking `MC-076` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-076` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-077 — Telemetry retention/sampling/privacy/export policy

**Priority:** P2  
**Audit finding:** (`C079`). No policy artifact or implementation exists.  
**Risk:** Without this telemetry/explainability capability, operators cannot distinguish policy, dependency, capacity, attack, and software-failure causes reliably.  
**Suggested blockers/dependencies:** `MC-069`, `MC-070`, `MC-071`, `MC-072`, `MC-073`  
**Mapped INV-27 requirements:**

- `C079` — Define telemetry retention, sampling, privacy, and export policy.

### Component-specific engineering checklist

- [ ] Define retention periods by telemetry class: security audit, operational logs, traces, metrics, diagnostic detail, performance evidence, and incident artifacts.
- [ ] Define sampling policies and mandatory-unsampled security/SLO events.
- [ ] Classify personal/tenant-sensitive data and minimize, tokenize, aggregate, or redact according to privacy/residency requirements.
- [ ] Define allowed export destinations, encryption/authentication requirements, tenant/site residency constraints, and data-processing ownership.
- [ ] Document deletion/expiration/legal-hold behavior and audit privileged telemetry access.
- [ ] Bound local buffering during exporter outage and define loss/backpressure behavior per telemetry class.
- [ ] Test retention enforcement, sampling invariants, cross-region export denial, redaction, and exporter outage.

### Cross-cutting hardening / verification gates

- [ ] Define stable telemetry schemas with units, cardinality bounds, privacy classification, retention, and versioning rules.
- [ ] Correlate logs/metrics/traces/audit/decision records through stable IDs without using telemetry as an authorization source.
- [ ] Redact secrets and tenant-sensitive values centrally; test redaction with canary values and hostile strings.
- [ ] Bound telemetry resource use and define behavior when exporters/backends are unavailable.
- [ ] Create operator-visible evidence that distinguishes policy rejection, dependency degradation, suspected attack, capacity saturation, and software defect.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-077` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-077`.
- [ ] RTM entry linking `MC-077` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-077` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-078 — Dashboards and differentiated alerts

**Priority:** P2  
**Audit finding:** (`C080`). No dashboard/alert definitions exist.  
**Risk:** Without this telemetry/explainability capability, operators cannot distinguish policy, dependency, capacity, attack, and software-failure causes reliably.  
**Suggested blockers/dependencies:** `MC-070`, `MC-071`, `MC-072`, `MC-073`, `MC-074`, `MC-075`, `MC-076`, `MC-077`  
**Mapped INV-27 requirements:**

- `C080` — Create dashboards and alerts distinguishing ordinary load, degradation, policy rejection, dependency failure, attack, and software defect.

### Component-specific engineering checklist

- [ ] Create dashboards for admission volume/outcome, seal/signature/provenance failures, syscall/capability violations, boot success/latency, running/degraded/quarantined instances, capacity, backend/dependency health, and cleanup leaks.
- [ ] Create distinct alerts for ordinary saturation, SLO degradation, policy rejection spikes, trust-service failure, VMM/backend failure, suspected attack patterns, audit-chain break, and software defects.
- [ ] Tie every actionable alert to runbook URL/ID, owner, severity, threshold rationale, and suppression/deduplication behavior.
- [ ] Use multi-window/burn-rate alerts for SLOs where appropriate rather than single noisy thresholds.
- [ ] Validate dashboards against metric schema versions and detect broken/missing queries in CI if tooling permits.
- [ ] Run alert fire drills/synthetic tests and verify routing/escalation.
- [ ] Review alert precision/recall after incidents and tune without hiding genuine security signals.

### Cross-cutting hardening / verification gates

- [ ] Define stable telemetry schemas with units, cardinality bounds, privacy classification, retention, and versioning rules.
- [ ] Correlate logs/metrics/traces/audit/decision records through stable IDs without using telemetry as an authorization source.
- [ ] Redact secrets and tenant-sensitive values centrally; test redaction with canary values and hostile strings.
- [ ] Bound telemetry resource use and define behavior when exporters/backends are unavailable.
- [ ] Create operator-visible evidence that distinguishes policy rejection, dependency degradation, suspected attack, capacity saturation, and software defect.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-078` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-078`.
- [ ] RTM entry linking `MC-078` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-078` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

# I. Testing & certification

## MC-079 — Full unit-state coverage

**Priority:** P1  
**Audit finding:** (`C081`). Dependency-free runtime tests exist, but state/lifecycle/policy/configuration/execution adapters are not implemented/tested.  
**Risk:** Without this certification evidence, production readiness is asserted rather than demonstrated across required behaviors and environments.  
**Suggested blockers/dependencies:** `MC-016`, `MC-029`, `MC-042`  
**Mapped INV-27 requirements:**

- `C081` — Create unit tests for deterministic Unikernel execution logic and state transitions.

### Component-specific engineering checklist

- [ ] Enumerate deterministic logic units and every lifecycle/policy/config state transition; create a coverage matrix before adding tests.
- [ ] Add unit tests for valid, invalid, boundary, and illegal transitions including idempotency and repeated commands.
- [ ] Use table-driven/property-based tests for syscall/capability sets, architecture policy, configuration invariants, and reason-code mapping.
- [ ] Test fail-closed behavior on malformed types, empty/oversized values, unknown enums/versions, and internal dependency errors.
- [ ] Inject deterministic clocks/IDs/randomness/backends so tests are hermetic and reproducible.
- [ ] Assert not only exceptions but stable error code, state, side effects, audit/decision evidence, and resource cleanup.
- [ ] Set a coverage threshold focused on security/state-machine branches and block regressions.

### Cross-cutting hardening / verification gates

- [ ] Make tests hermetic and deterministic where possible; pin fixtures, dependencies, clocks/randomness, and environment fingerprints.
- [ ] Cover success, boundary, malformed, adversarial, degraded, and recovery paths and assert side effects/evidence, not only return values.
- [ ] Emit machine-readable results with stable test IDs mapped into the RTM/production gate.
- [ ] Treat mandatory skipped tests as BLOCKED/FAIL for production certification.
- [ ] Preserve minimized failing inputs/seeds/schedules as permanent regression fixtures.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-079` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-079`.
- [ ] RTM entry linking `MC-079` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-079` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-080 — Public contract tests

**Priority:** P1  
**Audit finding:** (`C082`). No schema/wire contract exists to test.  
**Risk:** Without this certification evidence, production readiness is asserted rather than demonstrated across required behaviors and environments.  
**Suggested blockers/dependencies:** `MC-006`, `MC-023`, `MC-026`  
**Mapped INV-27 requirements:**

- `C082` — Create contract tests for every public Unikernel execution interface.

### Component-specific engineering checklist

- [ ] For each public typed schema/API, create producer/consumer contract tests using canonical golden requests/responses/events.
- [ ] Verify required/optional fields, bounds, enum handling, unknown fields, canonicalization, and stable error envelopes.
- [ ] Test every supported adjacent protocol version and explicit rejection of unsupported versions.
- [ ] Run generated bindings/validators from all supported languages/runtimes if multiple consumers exist.
- [ ] Include malformed wire encodings, duplicate/ambiguous fields, oversized payloads, and truncated messages.
- [ ] Ensure backward compatibility fixtures from supported previous releases remain in the suite until EOL.
- [ ] Publish contract-test results as machine-readable release evidence linked to schema digests.

### Cross-cutting hardening / verification gates

- [ ] Make tests hermetic and deterministic where possible; pin fixtures, dependencies, clocks/randomness, and environment fingerprints.
- [ ] Cover success, boundary, malformed, adversarial, degraded, and recovery paths and assert side effects/evidence, not only return values.
- [ ] Emit machine-readable results with stable test IDs mapped into the RTM/production gate.
- [ ] Treat mandatory skipped tests as BLOCKED/FAIL for production certification.
- [ ] Preserve minimized failing inputs/seeds/schedules as permanent regression fixtures.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-080` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-080`.
- [ ] RTM entry linking `MC-080` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-080` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-081 — Adjacent-layer integration tests

**Priority:** P1  
**Audit finding:** (`C083`). None are self-contained in this archive.  
**Risk:** Without this certification evidence, production readiness is asserted rather than demonstrated across required behaviors and environments.  
**Suggested blockers/dependencies:** `MC-007`, `MC-009`, `MC-021`, `MC-028`  
**Mapped INV-27 requirements:**

- `C083` — Create integration tests with every supported adjacent layer and execution tier.

### Component-specific engineering checklist

- [ ] Create an integration topology that includes the real admission service/library, policy/config, image store/fixture, VMM backend, audit sink, and representative upstream/downstream interfaces.
- [ ] Run happy-path admission->verify->start->ready->stop plus major rejection/failure flows end to end.
- [ ] Verify exact digest/seal/config/decision identity is preserved across layer boundaries and a rejected image never reaches VMM start.
- [ ] Exercise cleanup of network/storage/device/VM resources after failures at every stage.
- [ ] Include a hermetic fake mode for fast CI and at least one real backend lane for authoritative certification.
- [ ] Test version skew with supported adjacent components and dependency restarts.
- [ ] Capture topology, component versions, logs/traces/audit, and assertions as release evidence.

### Cross-cutting hardening / verification gates

- [ ] Make tests hermetic and deterministic where possible; pin fixtures, dependencies, clocks/randomness, and environment fingerprints.
- [ ] Cover success, boundary, malformed, adversarial, degraded, and recovery paths and assert side effects/evidence, not only return values.
- [ ] Emit machine-readable results with stable test IDs mapped into the RTM/production gate.
- [ ] Treat mandatory skipped tests as BLOCKED/FAIL for production certification.
- [ ] Preserve minimized failing inputs/seeds/schedules as permanent regression fixtures.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-081` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-081`.
- [ ] RTM entry linking `MC-081` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-081` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-082 — Architecture/runtime/hypervisor/provider/protocol compatibility matrix tests

**Priority:** P1  
**Audit finding:** (`C084`). Only one synthetic architecture mismatch unit test exists.  
**Risk:** Without this certification evidence, production readiness is asserted rather than demonstrated across required behaviors and environments.  
**Suggested blockers/dependencies:** `MC-007`, `MC-009`, `MC-023`, `MC-029`  
**Mapped INV-27 requirements:**

- `C084` — Create compatibility tests across supported CPU architectures, runtimes, hypervisors, providers, and protocol versions relevant to Unikernel execution.

### Component-specific engineering checklist

- [ ] Define the supported matrix dimensions: CPU architecture/features, host OS/kernel, VMM/backend and version, unikernel toolchain/image format, device/network/storage mode, provider/site class, Python/runtime, `pk_core`, and protocol/schema version.
- [ ] Classify combinations as certified, supported-with-limitations, experimental, or unsupported with explicit rationale.
- [ ] Automate pairwise or risk-based matrix reduction while ensuring all security-critical boundaries and each architecture/backend are exercised.
- [ ] Include negative tests proving unsupported combinations fail before execution.
- [ ] Run architecture-specific binary fixtures on native or trustworthy emulation infrastructure and distinguish emulation from certification.
- [ ] Record known backend/CPU errata and feature-mask differences relevant to isolation/boot behavior.
- [ ] Publish machine-readable matrix results with environment fingerprints and expiry/retest policy.

### Cross-cutting hardening / verification gates

- [ ] Make tests hermetic and deterministic where possible; pin fixtures, dependencies, clocks/randomness, and environment fingerprints.
- [ ] Cover success, boundary, malformed, adversarial, degraded, and recovery paths and assert side effects/evidence, not only return values.
- [ ] Emit machine-readable results with stable test IDs mapped into the RTM/production gate.
- [ ] Treat mandatory skipped tests as BLOCKED/FAIL for production certification.
- [ ] Preserve minimized failing inputs/seeds/schedules as permanent regression fixtures.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-082` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-082`.
- [ ] RTM entry linking `MC-082` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-082` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-083 — Concurrency/race tests

**Priority:** P1  
**Audit finding:** (`C086`). No shared/distributed state implementation or race tests exist.  
**Risk:** Without this certification evidence, production readiness is asserted rather than demonstrated across required behaviors and environments.  
**Suggested blockers/dependencies:** `MC-016`, `MC-029`  
**Mapped INV-27 requirements:**

- `C086` — Create concurrency and race-condition tests for shared/distributed Unikernel execution state.

### Component-specific engineering checklist

- [ ] Identify all shared mutable state and concurrent operations: admission, quota reservation, config activation, ownership lease, start/stop, quarantine, retries, audit sequence, and reconciliation.
- [ ] Write race tests with barriers/fault hooks that force problematic interleavings rather than relying only on random timing.
- [ ] Verify linearizable/transactional invariants where required: no double start, no quota overcommit, no stale config commit, no lost quarantine, no duplicate ownership.
- [ ] Run thread/process stress plus multi-controller/distributed tests for lease/epoch logic.
- [ ] Use language/platform race detectors or equivalent instrumentation where available.
- [ ] Test cancellation/timeout concurrently with success callbacks and cleanup.
- [ ] Preserve failing seeds/schedules as deterministic regressions.

### Cross-cutting hardening / verification gates

- [ ] Make tests hermetic and deterministic where possible; pin fixtures, dependencies, clocks/randomness, and environment fingerprints.
- [ ] Cover success, boundary, malformed, adversarial, degraded, and recovery paths and assert side effects/evidence, not only return values.
- [ ] Emit machine-readable results with stable test IDs mapped into the RTM/production gate.
- [ ] Treat mandatory skipped tests as BLOCKED/FAIL for production certification.
- [ ] Preserve minimized failing inputs/seeds/schedules as permanent regression fixtures.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-083` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-083`.
- [ ] RTM entry linking `MC-083` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-083` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-084 — Benchmark/soak/fleet-scale certification

**Priority:** P1  
**Audit finding:** (`C088`). Missing.  
**Risk:** Without this certification evidence, production readiness is asserted rather than demonstrated across required behaviors and environments.  
**Suggested blockers/dependencies:** `MC-060`, `MC-061`, `MC-062`, `MC-063`, `MC-081`  
**Mapped INV-27 requirements:**

- `C088` — Create benchmark, soak, burst, and fleet-scale tests appropriate to Unikernel execution.

### Component-specific engineering checklist

- [ ] Define certification environments for benchmark, soak, burst, and fleet-scale tests including hardware class, backend, topology, and workload mix.
- [ ] Run multi-hour/day soak tests sufficient to expose memory/FD/device/network leaks, queue drift, timer issues, and audit/telemetry accumulation.
- [ ] Run burst tests above expected peak arrival rates and verify load shedding plus recovery.
- [ ] Run fleet-scale tests at representative instance/image/tenant counts, including control-plane reconciliation after restart.
- [ ] Measure performance, error rates, leaked resources, state divergence, and telemetry cost continuously.
- [ ] Set explicit certification thresholds and automatic failure criteria; no subjective pass.
- [ ] Archive raw results, environment fingerprint, test code revision, and signed machine-readable verdict.

### Cross-cutting hardening / verification gates

- [ ] Make tests hermetic and deterministic where possible; pin fixtures, dependencies, clocks/randomness, and environment fingerprints.
- [ ] Cover success, boundary, malformed, adversarial, degraded, and recovery paths and assert side effects/evidence, not only return values.
- [ ] Emit machine-readable results with stable test IDs mapped into the RTM/production gate.
- [ ] Treat mandatory skipped tests as BLOCKED/FAIL for production certification.
- [ ] Preserve minimized failing inputs/seeds/schedules as permanent regression fixtures.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-084` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-084`.
- [ ] RTM entry linking `MC-084` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-084` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-085 — Disaster/partition/reconnect/degraded-control-plane certification

**Priority:** P1  
**Audit finding:** (`C089`). Missing.  
**Risk:** Without this certification evidence, production readiness is asserted rather than demonstrated across required behaviors and environments.  
**Suggested blockers/dependencies:** `MC-051`, `MC-052`, `MC-053`, `MC-054`, `MC-055`, `MC-081`  
**Mapped INV-27 requirements:**

- `C089` — Create disaster, partition, reconnect, and degraded-control-plane tests.

### Component-specific engineering checklist

- [ ] Create disaster scenarios for node loss, site isolation, provider/service outage, control-plane partition, trust-service outage, storage loss/corruption, and network reconnect.
- [ ] Define expected continuity, RTO/RPO, ownership/fencing, admission policy, and operator actions for each scenario.
- [ ] Test partition from both sides to prove duplicate execution/split-brain protection.
- [ ] On reconnect, test epoch/policy/revocation reconciliation and treatment of instances admitted under stale state.
- [ ] Include recovery when telemetry/audit export was unavailable and verify buffered data integrity/bounds.
- [ ] Exercise backup/restore or reconstruction under disaster conditions.
- [ ] Capture objective measurements and compare them to the documented resilience requirements.

### Cross-cutting hardening / verification gates

- [ ] Make tests hermetic and deterministic where possible; pin fixtures, dependencies, clocks/randomness, and environment fingerprints.
- [ ] Cover success, boundary, malformed, adversarial, degraded, and recovery paths and assert side effects/evidence, not only return values.
- [ ] Emit machine-readable results with stable test IDs mapped into the RTM/production gate.
- [ ] Treat mandatory skipped tests as BLOCKED/FAIL for production certification.
- [ ] Preserve minimized failing inputs/seeds/schedules as permanent regression fixtures.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-085` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-085`.
- [ ] RTM entry linking `MC-085` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-085` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-086 — Machine-readable release acceptance evidence generated locally

**Priority:** P0  
**Audit finding:** (`C090`). The referenced `pk_core` path is unavailable in this archive; no local equivalent exists.  
**Risk:** Without this certification evidence, production readiness is asserted rather than demonstrated across required behaviors and environments.  
**Suggested blockers/dependencies:** `MC-041`, `MC-079`, `MC-080`, `MC-081`, `MC-082`, `MC-083`, `MC-084`, `MC-085`, `MC-088`, `MC-089`, `MC-090`, `MC-091`, `MC-092`  
**Mapped INV-27 requirements:**

- `C090` — Require machine-readable acceptance evidence before certifying a Unikernel execution release for production.

### Component-specific engineering checklist

- [ ] Define a release-evidence JSON/CBOR schema with release/source revision, artifact digests, dependency/SBOM/provenance IDs, environment fingerprint, gate-check IDs, results, evidence references, timestamps, and signer identity.
- [ ] Generate evidence locally from repository commands without relying on an unavailable implicit `pk_core` installation.
- [ ] Make every mandatory test/analysis/benchmark produce machine-readable outputs consumed by the gate instead of relying on console text.
- [ ] Hash/sign the evidence bundle and ensure referenced artifacts are content-addressed/immutable.
- [ ] Reject stale evidence generated for a different source, build, schema, config, platform, or expired certification window.
- [ ] Provide a verifier command that checks evidence integrity, completeness, signatures, and all mandatory gate predicates offline.
- [ ] Archive the bundle alongside each release artifact.

### Cross-cutting hardening / verification gates

- [ ] Make tests hermetic and deterministic where possible; pin fixtures, dependencies, clocks/randomness, and environment fingerprints.
- [ ] Cover success, boundary, malformed, adversarial, degraded, and recovery paths and assert side effects/evidence, not only return values.
- [ ] Emit machine-readable results with stable test IDs mapped into the RTM/production gate.
- [ ] Treat mandatory skipped tests as BLOCKED/FAIL for production certification.
- [ ] Preserve minimized failing inputs/seeds/schedules as permanent regression fixtures.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-086` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-086`.
- [ ] RTM entry linking `MC-086` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-086` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-087 — Optimized-mode 100-check conformance proof in this archive

**Priority:** P0  
**Audit finding:** The test exists but is skipped because `pk_core` is unavailable.  
**Risk:** Without this certification evidence, production readiness is asserted rather than demonstrated across required behaviors and environments.  
**Suggested blockers/dependencies:** `MC-021`, `MC-086`  
**Mapped INV-27 requirements:** repository-integrity gap identified by the v4.2.0 audit (not tied to a single Cxxx item).

### Component-specific engineering checklist

- [ ] Make the 100-check conformance suite runnable from a clean checkout/archive with only declared bootstrap steps.
- [ ] Resolve/pin `pk_core` or port the required conformance logic into repository-local tooling with preserved check semantics.
- [ ] Change skipped mandatory checks to BLOCKED/FAIL in production-gate mode; skips may remain only for explicitly optional developer lanes.
- [ ] Run the suite under optimized Python (`-O`) and normal mode to ensure assertions are not being used as enforcement logic.
- [ ] Emit per-C001-C100 machine-readable outcomes with evidence links and no ambiguous aggregate-only result.
- [ ] Add CI lanes proving all 100 checks execute (not skip) and that a deliberately broken requirement makes the suite fail.
- [ ] Bind the conformance report to source/build digest and include it in release acceptance evidence.

### Cross-cutting hardening / verification gates

- [ ] Make tests hermetic and deterministic where possible; pin fixtures, dependencies, clocks/randomness, and environment fingerprints.
- [ ] Cover success, boundary, malformed, adversarial, degraded, and recovery paths and assert side effects/evidence, not only return values.
- [ ] Emit machine-readable results with stable test IDs mapped into the RTM/production gate.
- [ ] Treat mandatory skipped tests as BLOCKED/FAIL for production certification.
- [ ] Preserve minimized failing inputs/seeds/schedules as permanent regression fixtures.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-087` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-087`.
- [ ] RTM entry linking `MC-087` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-087` PASS for the exact source/build digest being released.

### Definition of done

- [ ] No caller-controlled claim is treated as an observed security fact unless the design explicitly identifies it as authenticated/authorized policy input.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

# J. Repository & source integrity

## MC-088 — Source manifest/SBOM

**Priority:** P1  
**Audit finding:** No machine-readable inventory of files/dependencies/licenses/hashes exists.  
**Risk:** Without repository integrity controls, builds/releases cannot be reproduced, audited, licensed, or verified reliably from the shipped source.  
**Suggested blockers/dependencies:** `MC-021`, `MC-022`, `MC-089`  
**Mapped INV-27 requirements:** repository-integrity gap identified by the v4.2.0 audit (not tied to a single Cxxx item).

### Component-specific engineering checklist

- [ ] Generate a machine-readable SBOM/source manifest covering repository files, built packages, Python dependencies, `pk_core`, parser/VMM libraries, licenses, versions, hashes, and supplier/source information.
- [ ] Choose a standard format such as SPDX or CycloneDX and include both source/build dependency views where useful.
- [ ] Bind the SBOM subject to the exact release artifact/image digest and provenance statement.
- [ ] Detect undeclared/imported dependencies and packaged files not represented in the manifest.
- [ ] Include license information and policy checks for forbidden/unknown licenses.
- [ ] Produce the SBOM deterministically in CI and diff it across releases for unexpected changes.
- [ ] Sign/archive the SBOM with release evidence and test subject-digest mismatch rejection.

### Cross-cutting hardening / verification gates

- [ ] Make the artifact machine-verifiable in CI rather than depending on reviewer memory or README claims.
- [ ] Bind release metadata to immutable source/build/dependency identities and preserve provenance for generated artifacts.
- [ ] Fail the production gate on stale/missing required repository-integrity artifacts.
- [ ] Document ownership/update process and review security-sensitive changes under protected-branch policy.
- [ ] Test packaging from a clean checkout so the shipped archive contains every declared required file and no undeclared secret/local artifact.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-088` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-088`.
- [ ] RTM entry linking `MC-088` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-088` PASS for the exact source/build digest being released.

### Definition of done

- [ ] The artifact is authoritative, versioned, owned, reviewed, and referenced by automated verification rather than existing as disconnected prose.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-089 — Reproducible build/lock data

**Priority:** P1  
**Audit finding:** No lockfile or build recipe establishes repeatable artifacts.  
**Risk:** Without repository integrity controls, builds/releases cannot be reproduced, audited, licensed, or verified reliably from the shipped source.  
**Suggested blockers/dependencies:** `MC-022`, `MC-088`  
**Mapped INV-27 requirements:** repository-integrity gap identified by the v4.2.0 audit (not tied to a single Cxxx item).

### Component-specific engineering checklist

- [ ] Pin every build/runtime/test dependency to immutable versions/hashes and document the resolver/toolchain versions used to produce the lock.
- [ ] Define a clean, scripted build from source to distributable artifacts with no undeclared network/local filesystem inputs.
- [ ] Set reproducibility controls for timestamps, locale, ordering, generated metadata, and compiler/linker flags where applicable.
- [ ] Run at least two clean builds and compare artifact hashes or document/measure unavoidable non-determinism.
- [ ] Verify offline rebuild using the declared dependency bundle/cache where supply-chain requirements demand it.
- [ ] Record build environment/provenance and toolchain digests.
- [ ] Fail release if lock/build metadata is stale relative to declared dependencies or source configuration.

### Cross-cutting hardening / verification gates

- [ ] Make the artifact machine-verifiable in CI rather than depending on reviewer memory or README claims.
- [ ] Bind release metadata to immutable source/build/dependency identities and preserve provenance for generated artifacts.
- [ ] Fail the production gate on stale/missing required repository-integrity artifacts.
- [ ] Document ownership/update process and review security-sensitive changes under protected-branch policy.
- [ ] Test packaging from a clean checkout so the shipped archive contains every declared required file and no undeclared secret/local artifact.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-089` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-089`.
- [ ] RTM entry linking `MC-089` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-089` PASS for the exact source/build digest being released.

### Definition of done

- [ ] The artifact is authoritative, versioned, owned, reviewed, and referenced by automated verification rather than existing as disconnected prose.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-090 — CI workflow

**Priority:** P1  
**Audit finding:** No continuous test/security/lint/package/release pipeline is included.  
**Risk:** Without repository integrity controls, builds/releases cannot be reproduced, audited, licensed, or verified reliably from the shipped source.  
**Suggested blockers/dependencies:** `MC-079`, `MC-080`, `MC-081`, `MC-082`, `MC-083`, `MC-084`, `MC-085`, `MC-086`, `MC-087`, `MC-088`, `MC-089`, `MC-091`, `MC-092`  
**Mapped INV-27 requirements:** repository-integrity gap identified by the v4.2.0 audit (not tied to a single Cxxx item).

### Component-specific engineering checklist

- [ ] Add CI workflows for formatting/lint, type checking, unit tests, contract tests, integration tests, fuzz smoke tests, security/static analysis, coverage, packaging, SBOM/provenance generation, and production gate.
- [ ] Use least-privilege CI tokens, pinned action/task revisions, protected environments, and isolated untrusted pull-request execution.
- [ ] Cache only content-addressed/non-secret artifacts and prevent cache poisoning across trust levels.
- [ ] Run required platform/backend matrix lanes and clearly separate fast PR gates from authoritative release certification.
- [ ] Upload machine-readable results/evidence with retention and integrity metadata.
- [ ] Require protected-branch status checks and review for security-critical files/policies.
- [ ] Test CI failure behavior by intentionally breaking representative checks in a controlled validation branch/fixture.

### Cross-cutting hardening / verification gates

- [ ] Make the artifact machine-verifiable in CI rather than depending on reviewer memory or README claims.
- [ ] Bind release metadata to immutable source/build/dependency identities and preserve provenance for generated artifacts.
- [ ] Fail the production gate on stale/missing required repository-integrity artifacts.
- [ ] Document ownership/update process and review security-sensitive changes under protected-branch policy.
- [ ] Test packaging from a clean checkout so the shipped archive contains every declared required file and no undeclared secret/local artifact.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-090` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-090`.
- [ ] RTM entry linking `MC-090` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-090` PASS for the exact source/build digest being released.

### Definition of done

- [ ] The artifact is authoritative, versioned, owned, reviewed, and referenced by automated verification rather than existing as disconnected prose.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-091 — Static analysis/type checking configuration

**Priority:** P1  
**Audit finding:** No Ruff/Flake8/Pylint/Mypy/Pyright/Bandit or equivalent policy/config exists.  
**Risk:** Without repository integrity controls, builds/releases cannot be reproduced, audited, licensed, or verified reliably from the shipped source.  
**Suggested blockers/dependencies:** none; may begin immediately.  
**Mapped INV-27 requirements:** repository-integrity gap identified by the v4.2.0 audit (not tied to a single Cxxx item).

### Component-specific engineering checklist

- [ ] Select and pin formatting/lint/type/security tools appropriate to the codebase (for example Ruff plus mypy/Pyright and Bandit or equivalents) and commit configuration.
- [ ] Enable strictness for security-boundary modules: no implicit Any where avoidable, exhaustive enum/state handling, unreachable-code checks, and dangerous API rules.
- [ ] Define import/dependency rules preventing security-critical runtime logic from silently acquiring heavyweight/unsafe dependencies.
- [ ] Run static security checks for subprocess/shell use, unsafe deserialization, temporary files, path handling, cryptographic misuse, and exception leakage.
- [ ] Document justified suppressions inline with reason/owner and prevent broad blanket disables.
- [ ] Run tooling in CI against a pinned tool version and treat new high-severity findings as release blockers.
- [ ] Baseline existing debt explicitly rather than hiding it through global excludes.

### Cross-cutting hardening / verification gates

- [ ] Make the artifact machine-verifiable in CI rather than depending on reviewer memory or README claims.
- [ ] Bind release metadata to immutable source/build/dependency identities and preserve provenance for generated artifacts.
- [ ] Fail the production gate on stale/missing required repository-integrity artifacts.
- [ ] Document ownership/update process and review security-sensitive changes under protected-branch policy.
- [ ] Test packaging from a clean checkout so the shipped archive contains every declared required file and no undeclared secret/local artifact.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-091` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-091`.
- [ ] RTM entry linking `MC-091` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-091` PASS for the exact source/build digest being released.

### Definition of done

- [ ] The artifact is authoritative, versioned, owned, reviewed, and referenced by automated verification rather than existing as disconnected prose.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-092 — Coverage measurement and threshold

**Priority:** P1  
**Audit finding:** No coverage configuration/report/gate exists.  
**Risk:** Without repository integrity controls, builds/releases cannot be reproduced, audited, licensed, or verified reliably from the shipped source.  
**Suggested blockers/dependencies:** `MC-079`, `MC-090`  
**Mapped INV-27 requirements:** repository-integrity gap identified by the v4.2.0 audit (not tied to a single Cxxx item).

### Component-specific engineering checklist

- [ ] Configure branch and line coverage for the full package and a higher threshold for parser, verification, authn/authz, state-machine, and gate modules.
- [ ] Measure subprocess/integration coverage where practical or track those requirements separately so unit coverage is not misrepresented as total verification.
- [ ] Exclude only generated/structural code with documented rationale.
- [ ] Publish machine-readable coverage reports and trend them across releases.
- [ ] Fail CI on threshold regression and on uncovered newly added security-critical branches.
- [ ] Use mutation testing or targeted fault injection on core decision logic to detect tests that execute code without asserting behavior.
- [ ] Map uncovered critical paths back to RTM/test backlog until closed or formally waived.

### Cross-cutting hardening / verification gates

- [ ] Make the artifact machine-verifiable in CI rather than depending on reviewer memory or README claims.
- [ ] Bind release metadata to immutable source/build/dependency identities and preserve provenance for generated artifacts.
- [ ] Fail the production gate on stale/missing required repository-integrity artifacts.
- [ ] Document ownership/update process and review security-sensitive changes under protected-branch policy.
- [ ] Test packaging from a clean checkout so the shipped archive contains every declared required file and no undeclared secret/local artifact.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-092` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-092`.
- [ ] RTM entry linking `MC-092` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-092` PASS for the exact source/build digest being released.

### Definition of done

- [ ] The artifact is authoritative, versioned, owned, reviewed, and referenced by automated verification rather than existing as disconnected prose.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-093 — License/NOTICE files

**Priority:** P2  
**Audit finding:** No repository-level software license or notice is present in the supplied archive.  
**Risk:** Without repository integrity controls, builds/releases cannot be reproduced, audited, licensed, or verified reliably from the shipped source.  
**Suggested blockers/dependencies:** none; may begin immediately.  
**Mapped INV-27 requirements:** repository-integrity gap identified by the v4.2.0 audit (not tied to a single Cxxx item).

### Component-specific engineering checklist

- [ ] Select and add the repository's approved software license text at the root; ensure the license is compatible with all bundled/vendored dependencies and fixtures.
- [ ] Add `NOTICE`/attribution files required by the selected license and third-party components.
- [ ] Add SPDX license identifiers to source files where organizational policy requires them.
- [ ] Document third-party notices/licenses for vendored `pk_core`, parser libraries, fixtures, VMM integration code, and generated assets.
- [ ] Configure SBOM/CI license scanning and fail on unknown/incompatible licenses.
- [ ] Ensure packaged wheels/source distributions include license/notice metadata.
- [ ] Review fixture redistribution rights, especially for real unikernel binaries or vendor firmware/device artifacts.

### Cross-cutting hardening / verification gates

- [ ] Make the artifact machine-verifiable in CI rather than depending on reviewer memory or README claims.
- [ ] Bind release metadata to immutable source/build/dependency identities and preserve provenance for generated artifacts.
- [ ] Fail the production gate on stale/missing required repository-integrity artifacts.
- [ ] Document ownership/update process and review security-sensitive changes under protected-branch policy.
- [ ] Test packaging from a clean checkout so the shipped archive contains every declared required file and no undeclared secret/local artifact.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-093` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-093`.
- [ ] RTM entry linking `MC-093` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-093` PASS for the exact source/build digest being released.

### Definition of done

- [ ] The artifact is authoritative, versioned, owned, reviewed, and referenced by automated verification rather than existing as disconnected prose.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

## MC-094 — Contribution/security disclosure policy

**Priority:** P2  
**Audit finding:** No `CONTRIBUTING.md`, `SECURITY.md`, support policy, or vulnerability-reporting channel exists.  
**Risk:** Without repository integrity controls, builds/releases cannot be reproduced, audited, licensed, or verified reliably from the shipped source.  
**Suggested blockers/dependencies:** `MC-012`, `MC-036`, `MC-038`, `MC-039`  
**Mapped INV-27 requirements:** repository-integrity gap identified by the v4.2.0 audit (not tied to a single Cxxx item).

### Component-specific engineering checklist

- [ ] Add `CONTRIBUTING.md` with development environment, branch/commit expectations, test/gate commands, coding/security standards, review requirements, and how to update schemas/evidence.
- [ ] Add `SECURITY.md` with supported versions, private vulnerability-reporting channel, expected response timeline, disclosure coordination, and scope.
- [ ] Document support channels and severity/escalation paths without exposing sensitive on-call personal data.
- [ ] Define mandatory review ownership for security boundary, schema, policy, VMM/backend, and release-gate changes.
- [ ] Describe how external contributors handle test fixtures, licenses, provenance, and potentially malicious sample binaries safely.
- [ ] Link contribution rules to CI/pre-commit tooling and prohibit bypassing mandatory production gates.
- [ ] Review these policies at least per major release and whenever ownership/contact mechanisms change.

### Cross-cutting hardening / verification gates

- [ ] Make the artifact machine-verifiable in CI rather than depending on reviewer memory or README claims.
- [ ] Bind release metadata to immutable source/build/dependency identities and preserve provenance for generated artifacts.
- [ ] Fail the production gate on stale/missing required repository-integrity artifacts.
- [ ] Document ownership/update process and review security-sensitive changes under protected-branch policy.
- [ ] Test packaging from a clean checkout so the shipped archive contains every declared required file and no undeclared secret/local artifact.

### Required completion evidence

- [ ] Commit or artifact reference implementing `MC-094` and its configuration/schema/documentation changes.
- [ ] Automated test result(s) proving the positive path and the principal negative/failure paths for `MC-094`.
- [ ] RTM entry linking `MC-094` to the applicable requirement IDs, implementation paths, test IDs, and evidence artifacts.
- [ ] Machine-readable production-gate result showing `MC-094` PASS for the exact source/build digest being released.

### Definition of done

- [ ] The artifact is authoritative, versioned, owned, reviewed, and referenced by automated verification rather than existing as disconnected prose.
- [ ] Failure, ambiguity, version skew, and missing dependencies reach a defined safe state and produce a stable machine-readable reason.
- [ ] The implementation is bounded for time, memory, concurrency, and output size wherever it processes untrusted or tenant-influenced input.
- [ ] Operator-visible telemetry and tamper-evident audit evidence are sufficient to reproduce why the component allowed, denied, degraded, rolled back, or failed.

---

# Program-level closure sequence

1. **Establish trustable input facts first:** MC-001 through MC-006.
2. **Create the real execution/isolation boundary:** MC-007 through MC-010 and MC-043 through MC-046.
3. **Make dependencies/interfaces/configuration deterministic:** MC-021 through MC-034.
4. **Complete threat/security controls and tamper-evident evidence:** MC-042 through MC-050.
5. **Implement lifecycle, resilience, ownership, and emergency controls:** MC-016 and MC-051 through MC-059.
6. **Instrument and define capacity/performance behavior:** MC-060 through MC-078.
7. **Close certification and reproducibility:** MC-079 through MC-092.
8. **Close governance/repository/legal artifacts and run the formal exit gate:** remaining architecture/governance items, MC-093, MC-094, and MC-041.

# Release exit criteria

- [ ] All P0 components are complete with reproducible evidence and zero active waivers that weaken seal, signature, isolation, authorization, or audit invariants.
- [ ] All P1 components are complete or have an explicitly approved, time-bounded waiver that the production gate reports as non-GO unless policy explicitly permits conditional release.
- [ ] Every applicable C001-C100 requirement has an RTM row and a non-skipped verification result.
- [ ] The shipped artifact can be built, installed, verified, tested, gated, and audited from a clean environment using only declared inputs.
- [ ] Release evidence is bound to source/build/SBOM/config/schema identities and can be verified offline.
- [ ] A real supported unikernel image can be verified from immutable bytes, cryptographically authenticated, launched through the supported VMM isolation boundary, observed, stopped/quarantined, and fully cleaned up end to end.