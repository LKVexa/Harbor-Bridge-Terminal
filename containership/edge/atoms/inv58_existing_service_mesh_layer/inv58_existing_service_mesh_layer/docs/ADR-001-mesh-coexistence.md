# ADR-001 — Coexist with the incumbent Istio/mTLS mesh; INV-58 owns retry and identity hand-off

- **Status:** PROPOSED — not approved. Approval requires the accountable owner and an independent architecture reviewer (both UNASSIGNED in `governance/OWNERSHIP.json`). INV-58-C010 stays BLOCKED until this line records the approvers and date.
- **Date proposed:** 2026-09-22

## Context
Workloads already run behind an Istio mesh providing mTLS, retries and routing. The new runtime also retries. Uncoordinated, retries multiply (3 app × 3 mesh = 9 attempts), identities are lost at the layer boundary, and a workload can bypass mTLS unnoticed.

## Decision
1. Keep the incumbent mesh as the data plane and certificate path; INV-58 never runs the mesh or issues certificates.
2. Exactly one layer retries per route. The app layer is preferred when both request retries (it carries idempotency context); the mesh keeps ownership when only it retries; budget 1 disables retries.
3. Mesh SPIFFE SANs map to runtime identities strictly (no normalisation), tenant-scoped.
4. Plaintext flows to meshed destinations are flagged, bounded and audited.
5. Policy moves off the mesh route by route through a revisioned, fenced, idempotent registry.

## Alternatives considered
- **Replace the mesh** — rejected: high blast radius; certificate issuance is not ours.
- **Mesh owns all retries** — rejected: the mesh cannot see application idempotency, so non-idempotent calls would be replayed.
- **Budget product only (both may retry if app×mesh ≤ budget)** — rejected in 4.2.0: it violates the single-owner rule.
- **Prefix-matching identities** — rejected in 4.2.0: `estate.local.evil.com` would match.

## Consequences
Positive: bounded attempts, a single source of truth for effective policy, auditable identity hand-off. Negative: INV-58 depends on node agents to report flows (RR-04); the route registry is O(n) per write (TD-01).

## Migration constraints
Route-by-route only; each migration carries an idempotency key and a fencing token; rollback is operator rollback of configuration plus re-migration, never bulk mutation.
