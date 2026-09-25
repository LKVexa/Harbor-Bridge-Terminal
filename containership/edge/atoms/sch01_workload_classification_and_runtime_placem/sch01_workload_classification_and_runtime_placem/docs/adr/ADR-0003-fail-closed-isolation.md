# ADR-0003: Fail Closed Isolation

- Status: PROPOSED
- Approver: UNASSIGNED
- Supersedes: none
- Date proposed: 2026-09-23

## Context
Occupancy recorded only workload->tenant, so shared placement could not be proven safe.

## Decision
Cross-tenant co-location only when both sides run on attested, hardware-isolated tiers (microvm/vm) on distinct tier instances; legacy occupants keep failing closed.

## Consequences
Lower utilisation on process/wasm/unikernel nodes; safety provable from recorded metadata.
