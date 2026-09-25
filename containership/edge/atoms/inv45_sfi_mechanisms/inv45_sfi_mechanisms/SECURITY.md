# Security model

> 4.3.0: the production enforcement layer is `production/` (see `docs/security/THREAT_MODEL.md`,
> `docs/architecture/ADR-0001-sfi-production-profile.md`). The sections below describe the 4.2.0
> reference model, which remains as a differential oracle only.

## Reporting a vulnerability

Report privately to the security owner alias in `OWNERSHIP.md` (placeholder until bound). Do not open a
public issue. Triage and fix SLAs: `docs/operations/LIFECYCLE_POLICIES.md`.

## Reference model (4.2.0)

## What this package enforces

The dependency-free `sfi_core.py` reference model fails closed unless the current
security-sensitive state has been verified. A verification seal covers the
sandbox region, the complete access manifest, and the indirect-branch allowlist.
Caller-owned access/target collections are copied into immutable containers so
later mutation of the caller's collection cannot silently widen policy. A failed
re-verification clears the previous seal before validation starts.

`SandboxRegion` and `Access` are immutable and validate their input types and
basic invariants. Invalid region sizes, malformed access records, unmasked
accesses, unverified execution, and disallowed indirect targets are rejected.
Security exceptions expose stable machine-readable error codes via `as_dict()`.

## Trust boundary and limitations

This repository is a **reference/verifier model**, not a native SFI sandbox. It
does not decode or rewrite machine code or Wasm, prove that an access manifest is
complete, install pinned base registers, enforce a shadow stack, randomize code
pages, map protected executable pages, or provide a trusted loader. Python object
integrity is not a substitute for process, VM, hardware, or runtime isolation.

A production implementation must ensure the verifier examines the exact bytes
that are subsequently executed and must bind verification to an authenticated
artifact identity/digest. The code here does not implement artifact signature,
provenance, attestation, anti-rollback, or binary-to-manifest integrity checks.
In 4.3.0 these are provided at the Wasm level by `production/` (digest binding, Ed25519 artifact
statements, anti-rollback, sealed descriptors); `MISSING_COMPONENTS.md` lists what remains.

## Fail-closed expectations

- Never execute an unverified module.
- Invalidate verification after any change to region, access manifest, or branch policy.
- Reject a module if even one listed access is unmasked.
- Reject every indirect branch target not explicitly permitted.
- Treat malformed policy state as unverified, not as a permissive default.
- Do not use reported `overhead_percent` as trusted benchmark evidence; it is metadata supplied by the caller in this reference model.
