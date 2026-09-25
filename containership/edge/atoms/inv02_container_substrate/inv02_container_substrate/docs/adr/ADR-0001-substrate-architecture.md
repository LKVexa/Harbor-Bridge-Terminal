# ADR-0001 — Substrate architecture for v5.0.0 (MC72)

**Status:** accepted (engineering) · owner ratification pending · **Date:** 2026-09-22

## Context

v4.2.0 was an in-memory image-identity reference model with 78 production components
listed as missing. The package must stay importable in partial checkouts (no `pk_core`),
must not take third-party dependencies (supply-chain surface), and must be testable
without a registry service or kernel privileges.

## Decisions

1. **Stdlib only.** Everything, including Ed25519 verification, is implemented from
   public specifications. Cost: slower crypto (≈250 verifies/s) and no zstd.
2. **Drive, don't be, the runtime.** Generate OCI runtime-spec bundles and call an OCI
   runtime binary. Kernel isolation stays in runc/crun/runsc/kata. Namespace, seccomp and
   capability *policy* lives here; *enforcement* is the runtime's and kernel's.
3. **Filesystem-backed store with one writer lock.** `fcntl` advisory lock + atomic
   rename + fsync. Single-host authority; multi-node needs an external lease service
   (open item under MC35).
4. **Digests are authoritative; tags are CAS-updated records** with version and
   previous value. Mirrors serve digests only.
5. **Fail closed.** Unknown schema, rule error, missing signature, corrupt content,
   quarantined digest and unsupported media type all deny.
6. **Policy is data + pure rules.** Bundles are versioned and digested; each decision
   records both, and waivers are explicit, scoped and expiring.
7. **Keep `registry.Registry`.** It remains the v4.x-compatible model and the target of
   the `pk_core` conformance adapter.

## Trust boundaries

untrusted: registry responses, manifests, layers, attestations, SBOMs, tenant requests ·
trusted configuration: policy bundle, keyring, config file, waivers ·
privileged boundary: OCI runtime invocation, cgroupfs, bind sources.

## Authoritative state

`store/meta.json` (tags, leases, quarantine), `store/blobs/`, lifecycle records,
audit ledger (head hash anchored in release evidence).

## Consequences

Single-host store; multi-node coordination, remote-registry certification and the
cross-platform runtime matrix remain open (see `COMPONENT_STATUS.json`).
