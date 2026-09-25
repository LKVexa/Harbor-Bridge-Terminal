# PLN-04 Security Model

## Security boundary

PLN-04 decides whether a workload may use a configured execution tier; it does **not** implement the tier itself. The Python `Node` object is a trusted control-plane object, not a tenant-facing sandbox. Actual memory, kernel, device, storage, and network isolation must be enforced by the selected tier provider.

## Implemented controls in 4.2.0

- A fixed tier order and trust-class floor prevent admission below policy.
- Cross-tenant reuse of the same workload identifier is rejected.
- Live workloads are never silently migrated to a different tier during re-admission.
- Re-admission with a weaker trust label does not lower the existing policy label.
- Attestation failure removes the tier from future admission and quarantines its residents.
- Restoring catalogue eligibility does not reactivate quarantined workloads.
- Teardown requires matching tenant ownership unless the caller explicitly opts into a privileged control-plane operation.
- Node and per-tenant resident counts are bounded.
- Workload and tenant identifiers reject empty, whitespace-only, control-character, and over-256-character input.
- Security-sensitive transitions generate a SHA-256 hash chain in memory.
- Mutable execution state is protected by a re-entrant lock to prevent same-node duplicate ownership races.

## Trust assumptions

The local catalogue currently trusts the caller that creates a `Node` and the caller that invokes `restore_attestation`. Hardware-rooted attestation evidence, actor authentication, authorization/capability checks, signed workload classification, policy provenance, and durable audit anchoring are external/missing dependencies and are listed in `AUDIT_REPORT.md`.

## Privileged teardown

Tenant-scoped code should call `teardown(node, workload, tenant)`. A control-plane recovery path may call `teardown(node, workload, privileged=True)`. Omitting both tenant identity and the explicit privileged flag fails closed.

## Attestation recovery

`restore_attestation()` only makes a configured tier eligible for **future** admissions. A workload already quarantined by an attestation failure must be torn down and recreated. This prevents silent resumption of execution state that existed while trust was lost.

## 4.3.0 additions

The in-tree trust roots now cover:

- actor authentication and capability authorisation
- signed classification
- the artifact allowlist and provenance
- attestation with nonce, freshness and replay protection
- fencing epochs
- durable audit with anchors
- secret redaction
- zeroization receipts

The production profile refuses to start without them.

Remaining trust assumptions:

- **Signatures.** HS256 is a shared-key MAC. Register asymmetric or hardware verifiers for cross-organisation issuers and for TPM, SEV-SNP or TDX quotes (W-003).
- **Process tier.** It enforces rlimits, session, environment and scratch isolation only, which is why it accepts only `trusted` workloads.
- **Not covered in-tree:** encryption at rest (KMS), external audit anchoring, and a distributed state backend.

See `THREAT_MODEL.md`.
