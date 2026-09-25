# ADR-0001 — Verify unikernel seals from image bytes, not metadata

- **Status:** Proposed. It needs approval from `inv27-architecture-reviewer` and `inv27-security-owner` (W-APPROVALS).
- **Date:** 2026-09-23
- **Supersedes:** the v4.2.0 `runtime.verify_seal` trust model.

## Context

v4.2.0 admitted an image when caller-supplied `linked_syscalls`, `features` and `single_address_space`
matched a caller-supplied manifest. Nothing tied either claim to the bytes that would run. The
contract's source of truth says: "a claim in metadata is not a seal".

## Decision

1. Identity is the sha256 of the immutable image bytes. Every later step uses the same `ImageBlob`,
   including the bytes the VMM receives, which are re-hashed on disk.
2. The image must carry a DSSE-style Ed25519 signature over a provenance statement. The statement
   must bind that digest, and its builder and toolchain version must be on an allow-list.
3. Seal facts (syscall surface, fork/exec/dlopen/debug capabilities, dynamic linking, and
   single-address-space) are derived from the ELF by a bounded parser and per-toolchain profiles.
   The manifest is a claim that must *equal* the derived facts.
4. Unknown toolchain, stripped image, parser error or stale trust root all fail closed. Attested
   facts are honoured only for stripped images, only when enabled, and only after the signature
   has verified.
5. Execution goes through a VMM adapter. That adapter receives an isolation plan derived from site
   policy, never the manifest.

## Alternatives considered

- **Trust the builder's attestation only.** Rejected as the default, because a compromised builder
  key would then equal a compromised seal. It is allowed as an opt-in for stripped images.
- **Dynamic tracing (run and observe syscalls).** Rejected for admission, because running an image
  that hasn't been admitted is the thing we are trying to prevent. The VMM seccomp sandbox is the
  run-time layer instead.
- **Disassembly for raw `syscall` instructions.** Deferred: it costs a lot and depends on the
  architecture. The gap is recorded as THREAT_MODEL T-11.

## Consequences

- Admission costs about 6 ms p50 for a typical image, most of it pure-Python Ed25519 (TD-2). An image with 20,000 symbols sits at the edge of the 100 ms p99 SLO (97–150 ms across runs; TD-1).
- Toolchain profiles are a maintained artifact. Each new toolchain needs fixtures and a minor
  release.
- The legacy `runtime.verify_seal` is kept for API compatibility and the pk_core conformance
  checks. The admission path never calls it; a test enforces this.
