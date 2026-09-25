# ADR-0001 — Enterprise Wasm control plane: architecture of INV-66

| Field | Value |
|---|---|
| ID | ADR-0001 |
| Status | **PROPOSED** (not approved — needs architecture, security and SRE approval; see `governance/owners.json`) |
| Date | 2026-09-22 |
| Deciders | UNASSIGNED (architecture owner, security owner, SRE owner) |
| Technical owners | UNASSIGNED |
| Review expiry | 2027-03-31, or earlier on any change to an interface in `schemas/` |
| Links | RTM rows `REQ-INV66-ARCH-*` (`release/rtm.json`), exit gate section `architecture` (`release/exit_gate.json`) |

## Context

INV-66 sits above many wasmCloud lattices and many teams. It owns organisation/lattice RBAC,
manifest admission guardrails, approved registries and signers, the change audit trail and a
cross-lattice inventory (`contract.py`). It does **not** own the lattice runtime, reconciliation,
signing keys, the identity provider or billing.

The hard constraints in `contract.py` are:

- every peer, network path and store can fail independently;
- callers are untrusted until their identity is established;
- behaviour must be the same whether a dependency is local or remote.

## Decision drivers

multi-lattice governance · tenant isolation · signer/registry policy · GitOps integration ·
append-only audit · p99 < 50 ms admission SLO · edge/site autonomy · operational ownership.

## Decision

1. **Cosmonic Control / wasmCloud-aligned concepts, product-neutral contracts.** INV-66 speaks its
   own versioned contracts (`PK_ECP_ADMIT/1`, `PK_ECP_RBAC/1`, `PK_ECP_AUDIT/2`, `PK_ECP_DELIVER/1`).
   Product-specific dependencies (wadm over NATS, Cosmonic Control APIs) stay behind the
   `DeploymentManager` adapter. No product type crosses the admission boundary.
2. **Journal-first source of truth.** Every decision, refusal, config generation, RBAC change,
   freeze and lifecycle transition is an append-only, hash-chained, Ed25519-anchored journal record
   (`production/journal.py`). All other state is a projection that is rebuilt by replay.
3. **Admission before delivery, always.** A decision is durably journaled before anything is
   delivered. Delivery is at-least-once, and the receiver deduplicates on the decision id.
4. **One policy document.** RBAC, registries, signers, provenance rules, quotas, limits and org
   rules live in one digested `PK_ECP_CONFIG/1` generation. Changing it takes N distinct approvers
   plus a compare-and-swap activation, and it can be rolled back.
5. **Authentication at the boundary.** EdDSA JWT from a trusted issuer, or a SPIFFE mTLS peer.
   A caller-supplied username is never an identity.
6. **Single writer with a lease and fencing epochs** over shared durable storage for HA. Replicas
   that do not hold the lease serve reads.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Custom wasmCloud controller that also does admission | Merges admission with reconciliation (a non-goal). A controller bug would become a policy bypass, and the failure domains become coupled. |
| Kubernetes admission webhook + GitOps controller (Flux/Argo patterns) | Requires Kubernetes, which the post-Kubernetes series is trying to remove. Webhooks fail open by default, and lattice concepts don't map onto namespaces cleanly. The **GitOps pattern** is kept (`GitOpsIngestor`) and the platform is not. |
| Direct lattice management by each team | No cross-team guardrails, no single audit trail, and registry/signer policy would be duplicated in every lattice. |
| Policy engine as the sole decision point (OPA/Gatekeeper-style) | Policy code can't hold the non-overridable invariants (signature verification, tenant isolation, audit-before-forward). GAP-13 is kept as an **additional** deny-capable input (`ExternalPolicy`). |
| Relational database as the source of truth, with audit as a side table | Two writes that can disagree. The journal-first design has no dual-write ambiguity (MC-005-T04). |

## Consequences

- New durable store (journal + anchors), with backup/restore tooling (`cli backup/restore`).
- Identity federation dependency. The static-JWKS source ships; live OIDC discovery is an adapter slot (OPEN_EXTERNAL).
- Policy-engine coupling. GAP-13 is version-pinned, failure defaults to deny, and cached answers have a TTL.
- The deployment-manager adapter contract `PK_ECP_DELIVER/1` has to be agreed with the INV-63 owners.
- Audit anchoring needs a signing key that the writer role doesn't hold. A KMS/HSM key is OPEN_EXTERNAL.
- HA needs shared storage with correct `flock` + `fsync` semantics. Multi-region consensus is out of scope (waiver W-04).
- Operations burden: runbooks RB-DAY0/1/2, RB-BACKUP, RB-INCIDENT, and the review automation.

## Approval

Not approved. This ADR is evidence of design, **not** of authorisation. Exit gate item
`architecture.adr_approved` stays BLOCKED until three distinct named approvers are recorded in
`release/reviews.jsonl`.
