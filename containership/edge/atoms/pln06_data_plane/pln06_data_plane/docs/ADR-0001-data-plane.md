# ADR-0001 — PLN-06 data-plane admission and transport selection

- **Status:** Proposed; repository owner approval is not present in this archive.
- **Version introduced:** 4.2.0
- **Amended by:** ADR-0002 (4.3.0) — concrete transports, trust and state profile. Both remain Proposed until approved (W-002).
- **Decision scope:** reference admission/routing runtime, not concrete transport implementations.

## Context

PLN-06 must prevent illegal data placement, keep non-inline movement bounded, and choose a path using both payload size and locality. The source architecture also names in-process Component Model calls, wRPC across nodes, vsock for VM control, and shared-memory/RDMA paths for large local data. Those concrete transports are adjacent capabilities and are not implemented by this standalone component.

## Decision

1. Residency admission is fail-closed and precedes non-inline capacity reservation.
2. The active residency policy is copied/validated and can be replaced atomically only when the candidate policy does not invalidate an in-flight transfer.
3. Legacy `locality="auto"` preserves size-only tiering for compatibility. Explicit locality acts as a safety floor:
   - `in_process` may use inline/local/bulk according to size;
   - `same_node` and `same_host_vm` cannot select `inline`;
   - `remote` cannot select `inline` or `local`.
4. Non-inline capacity is bounded globally and may also be bounded per tenant.
5. Admission decisions are versioned (`PK_TRANSFER/1`) and include the active configuration revision plus an operator-readable reason.
6. Completion is idempotent for duplicates/unknown IDs and fails closed if a live transfer ID is paired with mutated admission metadata.
7. Payload digest computation/verification remains a transport responsibility. PLN-06 carries SHA-256 digest metadata when supplied and marks every decision as requiring integrity verification.

## Consequences

The reference runtime can enforce admission and saturation semantics without importing `pk_core` or a concrete transport. It cannot by itself prove encryption, remote peer identity, transport integrity, zero-copy behavior, RDMA/vsock/wRPC interoperability, or production SLO compliance. Those are explicit post-audit gaps rather than implicit claims.

## Approval required

An accountable repository/service owner must approve this ADR, name the supported concrete transport mapping, and record the escalation path before production certification.
