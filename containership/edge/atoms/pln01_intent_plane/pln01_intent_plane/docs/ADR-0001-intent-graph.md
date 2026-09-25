# ADR-0001 — Desired state as a versioned dependency graph, planning separated from execution

- **Status:** Proposed — awaiting accountable-owner approval (`governance/APPROVALS.json`, status PENDING)
- **Date:** 2026-09-23 · **Deciders:** PLN-01 service owner · **Supersedes:** none

## Context
The estate's desired state was split across Terraform state and Kubernetes YAML. There was no single ordered
view of dependencies, no dry-run across layers, and no rollback target that spanned both.

## Decision
1. PLN-01 holds desired state as one graph per tenant, keyed `(tenant, environment, name)`; edges mean
   "reconcile after". Cross-tenant and cross-environment edges are refused.
2. Every mutation produces a new monotonic version with a retained delta, giving diff and rollback targets.
3. PLN-01 **plans only**. It emits a deterministic, fingerprinted dry-run plan (`PK_RECONCILIATION_PLAN/1`);
   downstream planes (PLN-02, SCH-01) execute. PLN-01 never runs a step.
4. Reported actual state is evidence, never authority.
5. The core is standard-library-only; integrations (identity, policy, KMS, consensus) sit behind interfaces.

## Alternatives considered
| Option | Why rejected |
|---|---|
| Keep Terraform state + YAML, add a reconciler | Two sources of truth; no cross-layer ordering or single rollback target |
| Planner that also executes | Couples blast radius of a bad plan to execution; violates separation required by contract |
| General-purpose config DB (etcd/KV only) | Declared non-goal; no dependency semantics or plan determinism |
| Event-sourced log only, no graph projection | Planning latency grows with history; graph projection needed for O(V+E) planning |

## Consequences
+ Deterministic plans, replay protection via plan fingerprint + graph version, cheap diff/rollback.
− Needs a durable store (ADR-0002) and a downstream executor contract; single-writer by design.
− Cross-tenant composition must happen above PLN-01.
